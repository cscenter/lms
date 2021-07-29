import logging
from datetime import timedelta
from typing import Optional

import django_rq
from django_rq import job

from django.db import transaction

from grading.api.yandex_contest import (
    ContestAPIError, SubmissionVerdict, Unavailable, YandexContestAPI
)

logger = logging.getLogger(__name__)


def get_submission(submission_id) -> Optional["Submission"]:
    from grading.models import Submission
    return (Submission.objects
            .filter(pk=submission_id)
            .select_related("assignment_submission",
                            "assignment_submission__student_assignment__assignment__checker",
                            "assignment_submission__student_assignment__assignment__checker__checking_system")
            .first())


@job('default')
def retrieve_yandex_contest_checker_compilers(checker_id, *, retries):
    from grading.models import Checker
    checker = (Checker.objects
               .filter(pk=checker_id)
               .first())
    if not checker:
        return "Checker not found"
    access_token = checker.checking_system.settings['access_token']
    api = YandexContestAPI(
        access_token=access_token,
        refresh_token=access_token
    )
    contest_id = checker.settings['contest_id']
    problem_id = checker.settings['problem_id']
    try:
        status, json_data = api.contest_problems(contest_id)
    except Unavailable as e:
        if retries:
            scheduler = django_rq.get_scheduler('default')
            scheduler.enqueue_in(timedelta(minutes=10),
                                 retrieve_yandex_contest_checker_compilers,
                                 checker_id,
                                 retries=retries - 1)
            logger.info("Remote server is unavailable. "
                        "Repeat job in 10 minutes.")
            return "Requeue job in 10 minutes"
        else:
            raise
    except ContestAPIError as e:
        logger.error(f"Yandex.Contest api request error "
                     f"[checker_id = {checker_id}]")
        raise
    problems = {problem['alias']: problem for problem in json_data}
    if problem_id in problems:
        problem = problems[problem_id]
        checker.settings['compilers'] = problem['compilers']
        checker.save(update_fields=['settings'])
        return "Done"
    logger.error(f"Did not find problem {problem_id} "
                 f"in contest {contest_id}")
    raise


@job('default')
def add_new_submission_to_checking_system(submission_id, *, retries):
    from grading.constants import SubmissionStatus
    submission = get_submission(submission_id)
    if not submission:
        return "Submission not found"
    assignment_submission = submission.assignment_submission
    checker = assignment_submission.student_assignment.assignment.checker
    checking_system_settings = checker.checking_system.settings
    access_token = checking_system_settings['access_token']
    api = YandexContestAPI(
        access_token=access_token,
        refresh_token=access_token)
    data = {
        'problem': checker.settings["problem_id"],
        'compiler': submission.settings["compiler"],
        'submission_meta': str(assignment_submission.pk)
    }
    submission_content = assignment_submission.attached_file.read()
    files = {'file': ('test.txt', submission_content)}
    try:
        status, json_data = api.add_submission(checker.settings['contest_id'],
                                               files=files, **data)
    except Unavailable as e:
        if retries:
            scheduler = django_rq.get_scheduler('default')
            scheduler.enqueue_in(timedelta(minutes=10),
                                 add_new_submission_to_checking_system,
                                 submission_id,
                                 retries=retries - 1)
            logger.info("Remote server is unavailable. "
                        "Repeat job in 10 minutes.")
            return "Requeue job in 10 minutes"
        else:
            raise
    except ContestAPIError as e:
        raise_error = True
        update_fields = ['status']
        if e.code == 400 and "Duplicate submission" in e.message:
            submission.meta = {'verdict': e.message}
            update_fields.append('meta')
            raise_error = False
        submission.status = SubmissionStatus.SUBMIT_FAIL
        submission.save(update_fields=update_fields)
        if raise_error:
            logger.error(f"Yandex.Contest api request error "
                         f"[submission_id = {submission_id}]")
            raise
        else:
            return e.message
    submission.meta = json_data
    submission.status = SubmissionStatus.CHECKING
    submission.save(update_fields=['meta', 'status'])
    scheduler = django_rq.get_scheduler('default')
    scheduler.enqueue_in(timedelta(seconds=15),
                         monitor_submission_status_in_yandex_contest,
                         submission_id,
                         json_data['runId'],
                         delay_min=1)


@job('default')
def monitor_submission_status_in_yandex_contest(submission_id,
                                                remote_submission_id,
                                                delay_min=1):
    submission = get_submission(submission_id)
    if not submission:
        return "Submission not found"
    checker = submission.assignment_submission.student_assignment.assignment.checker
    checking_system_settings = checker.checking_system.settings
    access_token = checking_system_settings['access_token']
    api = YandexContestAPI(
        access_token=access_token,
        refresh_token=access_token)
    try:
        status, json_data = api.submission_details(
            checker.settings['contest_id'],
            remote_submission_id, full=True)
    except Unavailable as e:
        scheduler = django_rq.get_scheduler('default')
        scheduler.enqueue_in(timedelta(minutes=10),
                             monitor_submission_status_in_yandex_contest,
                             submission_id,
                             remote_submission_id,
                             delay_min=1)
        logger.info(f"Remote server is unavailable. "
                    f"Repeat job in 10 minutes.")
        return f"Requeue job in 10 minutes"
    except ContestAPIError as e:
        raise
    # Wait until remote submission check is not finished
    if json_data['status'] == 'FAILED':
        logger.error(f"Remote check for local "
                     f"submission {submission_id} has failed!")
        raise ContestAPIError(f"runId {remote_submission_id} has failed")
    elif json_data['status'] != 'FINISHED':
        scheduler = django_rq.get_scheduler('default')
        scheduler.enqueue_in(timedelta(minutes=delay_min),
                             monitor_submission_status_in_yandex_contest,
                             submission_id,
                             remote_submission_id,
                             delay_min=delay_min + 1)
        logger.info(f"Submission check {remote_submission_id} is not finished. "
                    f"Rerun in {delay_min} minutes.")
        return f"Requeue job in {delay_min} minutes"
    # TODO: Investigate how to escape html and store it in json
    # TODO: g.e. look at encoders in simplejson
    json_data.pop("source", None)
    json_data.pop("diff", None)
    if "checkerLog" in json_data:
        # Output could contain null character \u0000 which is not valid for
        # the postgres jsonb field type
        for row in json_data["checkerLog"]:
            row.pop("input", None)
            row.pop("output", None)
    with transaction.atomic():
        submission.meta = json_data
        if json_data['verdict'] == SubmissionVerdict.OK.value:
            submission.status = submission.STATUSES.PASSED
        else:
            submission.status = submission.STATUSES.FAILED
        submission.save(update_fields=["status", "meta"])
