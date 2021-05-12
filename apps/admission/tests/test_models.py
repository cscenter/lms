import pytest

from admission.constants import InterviewSections
from admission.models import Applicant, Contest
from admission.tests.factories import (
    ApplicantFactory, CampaignFactory, ContestFactory, InterviewInvitationFactory
)


@pytest.mark.django_db
def test_compute_contest_id():
    campaign = CampaignFactory.create()
    ContestFactory(campaign=campaign, type=Contest.TYPE_EXAM)
    contests = ContestFactory.create_batch(3, campaign=campaign,
                                           type=Contest.TYPE_TEST)
    c1, c2, c3 = sorted(contests, key=lambda x: x.contest_id)
    assert ApplicantFactory(campaign=campaign).online_test.compute_contest_id(Contest.TYPE_TEST, group_size=3) == c1.contest_id
    a = ApplicantFactory(campaign=campaign)
    assert a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=3) == c1.contest_id
    assert a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=1) == c2.contest_id
    a = ApplicantFactory(campaign=campaign)
    assert a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=3) == c1.contest_id
    assert a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=1) == c3.contest_id
    assert ApplicantFactory(campaign=campaign).online_test.compute_contest_id(Contest.TYPE_TEST, group_size=3) == c2.contest_id


@pytest.mark.django_db
def test_interview_invitation_create():
    """Make sure Applicant status auto updated"""
    a = ApplicantFactory(status=Applicant.PERMIT_TO_EXAM)
    invitation = InterviewInvitationFactory(applicant=a, interview=None)
    a.refresh_from_db()
    assert a.status == Applicant.INTERVIEW_TOBE_SCHEDULED
    invitation = InterviewInvitationFactory(applicant=a, interview__section=InterviewSections.ALL_IN_ONE)
    assert invitation.interview_id is not None
    a.refresh_from_db()
    assert a.status == Applicant.INTERVIEW_SCHEDULED
    a.status = Applicant.PENDING
    a.interview.delete()
    a.save()
    invitation = InterviewInvitationFactory(applicant=a, interview=None)
    a.refresh_from_db()
    assert a.status == Applicant.PENDING
