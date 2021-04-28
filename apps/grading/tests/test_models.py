import pytest

from django.utils.translation import gettext_lazy as _

from grading.api.yandex_contest import SubmissionVerdict
from grading.constants import SubmissionStatus
from grading.tests.factories import SubmissionFactory


@pytest.mark.parametrize("status,label",
                         [(SubmissionStatus.NEW, _("New")),
                          (SubmissionStatus.CHECKING, _("Checking")),
                          (SubmissionStatus.SUBMIT_FAIL, _("Not Submitted"))])
@pytest.mark.django_db
def test_submission_get_status_display_not_checked(status, label, mocker):
    mocker.patch('grading.tasks.add_new_submission_to_checking_system')
    submission = SubmissionFactory(status=status)
    assert submission.get_status_display == label


@pytest.mark.django_db
def test_submission_get_status_display_passed(mocker):
    mocker.patch('grading.tasks.add_new_submission_to_checking_system')
    submission = SubmissionFactory(status=SubmissionStatus.PASSED,
                                   meta={'verdict': SubmissionVerdict.OK.value})
    assert submission.get_status_display == SubmissionVerdict.OK.value


@pytest.mark.django_db
def test_submission_get_status_display_wrong_answer_show_test_number(mocker):
    mocker.patch('grading.tasks.add_new_submission_to_checking_system')
    meta = {
        'verdict': SubmissionVerdict.WA.value,
        'checkerLog': [
            {'sequenceNumber': 1, 'verdict': SubmissionVerdict.OK.value},
            {'sequenceNumber': 2, 'verdict': SubmissionVerdict.OK.value},
            {'sequenceNumber': 3, 'verdict': SubmissionVerdict.WA.value},
        ]
    }
    submission = SubmissionFactory(status=SubmissionStatus.FAILED,
                                   meta=meta)
    assert SubmissionVerdict.WA.name in submission.get_status_display
    assert '3' in submission.get_status_display
