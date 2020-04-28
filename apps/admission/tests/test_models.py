import pytest

from admission.models import Contest, Applicant
from admission.tests.factories import CampaignFactory, ContestFactory, \
    ApplicantFactory, InterviewInvitationFactory


@pytest.mark.django_db
def test_compute_contest_id():
    campaign = CampaignFactory.create()
    ContestFactory(campaign=campaign, type=Contest.TYPE_EXAM)
    contests = ContestFactory.create_batch(3, campaign=campaign,
                                           type=Contest.TYPE_TEST)
    c1, c2, c3 = sorted(contests, key=lambda x: x.contest_id)
    a = ApplicantFactory(campaign=campaign)
    a.id = 1
    assert a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=5) == c1.contest_id
    a.id = 2
    assert a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=5) == c1.contest_id
    a.id = 6
    assert a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=5) == c2.contest_id
    a.id = 8
    assert a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=5) == c2.contest_id


@pytest.mark.django_db
def test_interview_invitation_create():
    """Make sure Applicant status autoupdated"""
    a = ApplicantFactory(status=Applicant.PERMIT_TO_EXAM)
    invitation = InterviewInvitationFactory(applicant=a, interview=None)
    a.refresh_from_db()
    assert a.status == Applicant.INTERVIEW_TOBE_SCHEDULED
    invitation = InterviewInvitationFactory(applicant=a)
    assert invitation.interview_id is not None
    a.refresh_from_db()
    assert a.status == Applicant.INTERVIEW_SCHEDULED
    a.status = Applicant.PENDING
    a.interview.delete()
    a.save()
    invitation = InterviewInvitationFactory(applicant=a, interview=None)
    a.refresh_from_db()
    assert a.status == Applicant.PENDING
