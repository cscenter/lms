import logging
from datetime import timedelta
from typing import Optional

import django_rq
from django.db import transaction
from django_rq import job

from contests.api.yandex_contest import YandexContestAPI, Unavailable, \
    ContestAPIError, SubmissionVerdict

logger = logging.getLogger(__name__)


def get_submission(submission_id) -> Optional["Submission"]:
    from contests.models import Submission
    return (Submission.objects
            .filter(pk=submission_id)
            .select_related("assignment_comment",
                            "assignment_comment__student_assignment__assignment__checking_system")
            .first())


@job('default')
def add_new_submission_to_checking_system(submission_id, *, retries):
    from contests.models import SubmissionStatus
    submission = get_submission(submission_id)
    if not submission:
        return "Submission not found"
    assignment = submission.assignment_comment.student_assignment.assignment
    checker_settings = assignment.checking_system.settings
    access_token = 'AgAAAAANbLCrAAZtKUiNoGLqlEU6r0o7tn5LjrE'
    api = YandexContestAPI(
        access_token=access_token,
        refresh_token=access_token)
    data = {
        'problem': checker_settings["problem_id"],
        'compiler': submission.settings["compiler_id"]
    }
    submission_content = submission.assignment_comment.attached_file.read()
    files = {'file': ('test.txt', submission_content)}
    try:
        status, json_data = api.add_submission(checker_settings['contest_id'],
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
        submission.status = SubmissionStatus.SUBMIT_FAIL
        submission.save(update_fields=['status'])
        logger.error(f"Yandex.Contest api request error "
                     f"[submission_id = {submission_id}]")
        raise
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
    assignment = submission.assignment_comment.student_assignment.assignment
    checker_settings = assignment.checking_system.settings
    access_token = 'AgAAAAANbLCrAAZtKUiNoGLqlEU6r0o7tn5LjrE'
    api = YandexContestAPI(
        access_token=access_token,
        refresh_token=access_token)
    try:
        status, json_data = api.submission_details(
            checker_settings['contest_id'],
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