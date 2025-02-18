import datetime
import pytest
from unittest.mock import MagicMock
from datetime import timedelta

from pytest_mock import mocker
from apps.core.timezone.utils import now_local
from grading.api.yandex_contest import ContestAPIError, SubmissionVerdict, Unavailable
from apps.grading.tasks import add_new_submission_to_checking_system, monitor_submission_status_in_yandex_contest
from apps.grading.tests.factories import CheckerFactory, SubmissionFactory
from grading.constants import SubmissionStatus


@pytest.mark.django_db
def test_add_new_submission_success(mocker):
    mocked_add_submission = mocker.patch("grading.api.yandex_contest.YandexContestAPI.add_submission")
    mocked_django_rq = mocker.patch("django_rq.get_scheduler")
    mocked_add_submission.return_value = {"runId": "456"}
    mocked_django_rq.return_value = MagicMock()
    submission = SubmissionFactory(status=SubmissionStatus.PASSED,
                                   meta={'verdict': SubmissionVerdict.OK.value})
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()

    result = add_new_submission_to_checking_system(submission.pk, retries=3)
    assert result == None
    mocked_add_submission.assert_called_once()
    mocked_django_rq.return_value.enqueue_in.assert_called_once_with(timedelta(seconds=15), monitor_submission_status_in_yandex_contest, submission.pk, "456", delay_min=1)

@pytest.mark.django_db
def test_add_new_submission_not_found(mocker):
    mock_get_submission = mocker.patch("grading.tasks.get_submission")
    mock_get_submission.return_value = None

    result = add_new_submission_to_checking_system(1, retries=3)

    assert result == "Submission not found"

@pytest.mark.django_db
def test_add_new_submission_unavailable(mocker):
    mocker.patch("grading.api.yandex_contest.YandexContestAPI.add_submission", side_effect=Unavailable)
    mocked_django_rq = mocker.patch("django_rq.get_scheduler")
    mocked_django_rq.return_value = MagicMock()
    submission = SubmissionFactory(status=SubmissionStatus.PASSED)
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()

    result = add_new_submission_to_checking_system(submission.pk, retries=3)
    assert result == "Requeue check in 10 minutes"
    mocked_django_rq.return_value.enqueue_in.assert_called_once_with(timedelta(minutes=10), add_new_submission_to_checking_system, submission.pk, retries=2)
    
@pytest.mark.django_db
def test_add_new_submission_api_error(mocker):

    mocker.patch("grading.api.yandex_contest.YandexContestAPI.add_submission", side_effect=ContestAPIError(code=400, message="Duplicate submission"))
    mocked_django_rq = mocker.patch("django_rq.get_scheduler")
    mocked_django_rq.return_value = MagicMock()
    submission = SubmissionFactory(status=SubmissionStatus.PASSED)
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()

    result = add_new_submission_to_checking_system(submission.pk, retries=3)

    assert result == "Duplicate submission"


@pytest.mark.django_db
def test_monitor_submission_success(mocker):
    submission = SubmissionFactory(status=SubmissionStatus.PASSED,
                                   meta={'verdict': SubmissionVerdict.OK.value})
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()

    mocked_submission_details = mocker.patch("grading.api.yandex_contest.YandexContestAPI.submission_details")
    mocked_django_rq = mocker.patch("django_rq.get_scheduler")
    mocked_django_rq.return_value = MagicMock()
    mocked_submission_details.return_value = {"runId": "456",
                                              "verdict": SubmissionVerdict.OK.value}

    result = monitor_submission_status_in_yandex_contest(submission.pk, 456)

    assert result is None


@pytest.mark.django_db
def test_monitor_submission_not_found(mocker):
    mock_get_submission = mocker.patch("grading.tasks.get_submission")

    mock_get_submission.return_value = None

    result = monitor_submission_status_in_yandex_contest(1, 456)

    assert result == "Submission not found"


@pytest.mark.django_db
def test_monitor_submission_unavailable(mocker):
    mocked_submission_details = mocker.patch("grading.api.yandex_contest.YandexContestAPI.submission_details", side_effect=Unavailable)
    mocked_django_rq = mocker.patch("django_rq.get_scheduler")
    mocked_django_rq.return_value = MagicMock()
    submission = SubmissionFactory(status=SubmissionStatus.PASSED)
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()

    mocked_submission_details.return_value = {"runId": "456",
                                              "verdict": SubmissionVerdict.OK.value}

    result = monitor_submission_status_in_yandex_contest(submission.pk, 456)

    assert result == "Requeue check in 10 minutes"
    mocked_django_rq.return_value.enqueue_in.assert_called_once_with(timedelta(minutes=10), monitor_submission_status_in_yandex_contest, submission.pk, 456, delay_min=1)


@pytest.mark.django_db
def test_monitor_submission_api_error(mocker):
    mocked_submission_details = mocker.patch("grading.api.yandex_contest.YandexContestAPI.submission_details", side_effect=ContestAPIError(code=500, message="Duplicate submission"))
    mocked_django_rq = mocker.patch("django_rq.get_scheduler")
    mocked_django_rq.return_value = MagicMock()
    submission = SubmissionFactory(status=SubmissionStatus.PASSED)
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()
    mocked_submission_details.return_value = {"runId": "456",
                                              "verdict": SubmissionVerdict.OK.value}

    result = monitor_submission_status_in_yandex_contest(submission.pk, 456)

    assert result == "Yandex.Contest api error"

@pytest.mark.django_db
def test_monitor_submission_no_report_retry(mocker):
    mocked_submission_details = mocker.patch("grading.api.yandex_contest.YandexContestAPI.submission_details")
    mocked_django_rq = mocker.patch("django_rq.get_scheduler")
    mocked_django_rq.return_value = MagicMock()
    submission = SubmissionFactory(status=SubmissionStatus.PASSED)
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()
    mocked_submission_details.return_value = {"runId": "456",
                                              "verdict": 'No report'}

    result = monitor_submission_status_in_yandex_contest(submission.pk, 456, delay_min=5)

    assert result == "Requeue check"
    mocked_django_rq.return_value.enqueue_in.assert_called_once_with(timedelta(minutes=5), monitor_submission_status_in_yandex_contest, submission.pk, 456, delay_min=6)

@pytest.mark.django_db
def test_monitor_submission_no_report_fail(mocker):
    mocked_submission_details = mocker.patch("grading.api.yandex_contest.YandexContestAPI.submission_details")
    mocked_django_rq = mocker.patch("django_rq.get_scheduler")
    mocked_django_rq.return_value = MagicMock()
    submission = SubmissionFactory(status=SubmissionStatus.PASSED)
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()
    mocked_submission_details.return_value = {"runId": "456",
                                              "verdict": 'No report'}

    result = monitor_submission_status_in_yandex_contest(submission.pk, 456, delay_min=11)
    assert result == "Remote check for local submission has failed!"
