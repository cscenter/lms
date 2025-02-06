import logging
from datetime import timedelta
from typing import Optional

import django_rq
from django_rq import job

from django.db import transaction

from grading.api.yandex_contest import (
    ContestAPIError, SubmissionVerdict, Unavailable, YandexContestAPI
)
from django.utils.translation import gettext_lazy as _

from grading.constants import CheckingSystemTypes
from grading.models import Submission
from grading.utils import YandexContestScoreSource

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
def update_checker_yandex_contest_problem_compilers(checker_id, *, retries):
    from grading.models import Checker
    checker = (Checker.objects
               .filter(pk=checker_id)
               .first())
    if not checker:
        return "Checker not found"
    if checker.checking_system.type != CheckingSystemTypes.YANDEX_CONTEST:
        return "Checker is not supported"
    if checker.settings.get('score_input') != YandexContestScoreSource.PROBLEM.value:
        return "Action is not supported"

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
                                 update_checker_yandex_contest_problem_compilers,
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
    logger.error(f"Problem {problem_id} not found in contest {contest_id}")
    raise


@job('default')
def add_new_submission_to_checking_system(submission_id: int, *, retries: int) -> str | None:
    """
    Adds a new solution to the verification system (Yandex.Contest) and updates the submission status.

    The function performs the following actions:
    1. Receives the submission by its ID.
    2. Extracts the verification system settings and the access token.
    3. Creates a request to add a solution to Yandex.Contest.
    4. If the verification system is unavailable, the function schedules a retry after 10 minutes.
    5. In case of an API error (for example, duplicate sending), updates the sending status and logs the error.
    6. Upon successful sending, it updates the metadata and the status of sending to "CHECKING".
    7. Schedules a task to monitor the verification status after 15 seconds.

    Parameters:
    ----------
    submission_id : int
        ID of the submission to be added to the verification system.
    retries : int
        The number of remaining attempts to resend if the verification system is unavailable.

    Returns:
    -----------
    str or None
        - "Submission not found" if the shipment is not found.
        - "Request job in 10 minutes", if the verification system is unavailable and the task will be repeated.
        - An error message if an API error has occurred.
        - None if the sending was successfully added and the status is updated.
    """
    from grading.constants import SubmissionStatus
    submission_status = SubmissionStatus.CHECKING
    submission_verdict: str = ""
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
        json_data = api.add_submission(checker.settings['contest_id'],
                                               files=files, timeout=5, **data)
        submission.meta = json_data
    except Unavailable as e:
        submission_status = SubmissionStatus.RETRY
        submission_verdict = "Requeue check in 10 minutes"
        if retries:
            scheduler = django_rq.get_scheduler('default')
            scheduler.enqueue_in(timedelta(minutes=10),
                                 add_new_submission_to_checking_system,
                                 submission_id,
                                 retries=retries - 1)
            logger.info("Remote server is unavailable. Repeat job in 10 minutes.")
        else:
            submission_status = SubmissionStatus.SUBMIT_FAIL
            submission_verdict = "Checking failed after all retries"

    except ContestAPIError as e:
        submission_status = SubmissionStatus.SUBMIT_FAIL
        submission_verdict = e.message
        if e.code >= 500:
            submission_verdict = "Yandex.Contest api error"
        elif e.code == 400 and "Duplicate submission" in e.message:
            submission_verdict = "Duplicate submission"
        logger.error(f"Yandex.Contest api request error [{submission_id=}] {e.code=} {e.message=}")

    if not submission.meta:
        submission.meta['verdict'] = submission_verdict

    submission.status = submission_status
    submission.save(update_fields=['meta', 'status'])

    if submission_status in [SubmissionStatus.SUBMIT_FAIL, SubmissionStatus.RETRY]:
        return submission.meta['verdict']

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
            remote_submission_id, timeout=10)
    except Unavailable as e:
        scheduler = django_rq.get_scheduler('default')
        scheduler.enqueue_in(timedelta(minutes=10),
                             monitor_submission_status_in_yandex_contest,
                             submission_id,
                             remote_submission_id,
                             delay_min=1)
        logger.info(f"Remote server is unavailable. "
                    f"Repeat job in 10 minutes.")
        return f"Unavailable. Requeue job in 10 minutes. "
    except ContestAPIError as e:
        raise
    # Wait until remote submission check is not finished
    if json_data['verdict'] == 'No report':
        if delay_min > 10:
            logger.error(f"Remote check for local "
                        f"submission {submission_id} has failed!")
            raise ContestAPIError(f"runId {remote_submission_id} has failed")
        else:
            scheduler = django_rq.get_scheduler('default')
            scheduler.enqueue_in(timedelta(minutes=delay_min),
                                monitor_submission_status_in_yandex_contest,
                                submission_id,
                                remote_submission_id,
                                delay_min=delay_min + 1)
            logger.info(f"Submission check {remote_submission_id} is not finished. "
                        f"Rerun in {delay_min} minutes.")
            return f"ContestAPIError. Requeue job in {delay_min} minutes"
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
