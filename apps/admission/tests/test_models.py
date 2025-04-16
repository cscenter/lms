import datetime

import pytest

from django.core.exceptions import ValidationError

from admission.constants import InterviewSections, InterviewInvitationStatuses, ApplicantStatuses
from admission.models import Applicant, Contest, Interview
from admission.tests.factories import (
    ApplicantFactory,
    CampaignFactory,
    ContestFactory,
    InterviewFactory,
    InterviewInvitationFactory,
    InterviewSlotFactory,
    InterviewStreamFactory,
)


@pytest.mark.django_db
def test_compute_contest_id():
    campaign = CampaignFactory.create()
    ContestFactory(campaign=campaign, type=Contest.TYPE_EXAM)
    contests = ContestFactory.create_batch(3, campaign=campaign, type=Contest.TYPE_TEST)
    c1, c2, c3 = sorted(contests, key=lambda x: x.contest_id)
    assert (
        ApplicantFactory(campaign=campaign).online_test.compute_contest_id(
            Contest.TYPE_TEST, group_size=3
        )
        == c1.contest_id
    )
    a = ApplicantFactory(campaign=campaign)
    assert (
        a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=3)
        == c1.contest_id
    )
    assert (
        a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=1)
        == c2.contest_id
    )
    a = ApplicantFactory(campaign=campaign)
    assert (
        a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=3)
        == c1.contest_id
    )
    assert (
        a.online_test.compute_contest_id(Contest.TYPE_TEST, group_size=1)
        == c3.contest_id
    )
    assert (
        ApplicantFactory(campaign=campaign).online_test.compute_contest_id(
            Contest.TYPE_TEST, group_size=3
        )
        == c2.contest_id
    )


@pytest.mark.django_db
def test_unique_interview_section_per_applicant():
    applicant = ApplicantFactory()
    InterviewFactory(applicant=applicant, section=InterviewSections.MATH)
    interview = Interview(applicant=applicant, section=InterviewSections.MATH)
    with pytest.raises(ValidationError):
        interview.full_clean()

@pytest.mark.django_db
def test_interview_invitation_create():
    for status in ApplicantStatuses.values:
        applicant = ApplicantFactory(status=status)
        interview = InterviewFactory(
            applicant=applicant, section=InterviewSections.ALL_IN_ONE,
        )
        if status in ApplicantStatuses.RIGHT_BEFORE_INTERVIEW:
            assert InterviewInvitationFactory(applicant=applicant, interview=interview)
        else:
            with pytest.raises(ValidationError):
                InterviewInvitationFactory(applicant=applicant, interview=interview)


@pytest.mark.django_db
def test_applicant_miss_count():
    """Make sure Applicant miss_count is incremented after status change"""
    interview = InterviewFactory(status=Interview.APPROVED, section=InterviewSections.ALL_IN_ONE)
    a = interview.applicant
    invitation = InterviewInvitationFactory(applicant=a, interview=interview)
    assert a.miss_count == 0
    invitation.status = InterviewInvitationStatuses.DECLINED
    invitation.save()
    a.refresh_from_db()
    assert a.miss_count == 1
    invitation.status = InterviewInvitationStatuses.NO_RESPONSE
    invitation.save()
    a.refresh_from_db()
    assert a.miss_count == 1
    invitation.status = InterviewInvitationStatuses.EXPIRED
    invitation.save()
    a.refresh_from_db()
    assert a.miss_count == 2
    interview.status = interview.CANCELED
    interview.save()
    a.refresh_from_db()
    assert a.miss_count == 3


@pytest.mark.django_db
def test_interview_stream_slots_count():
    stream = InterviewStreamFactory(
        start_at=datetime.time(14, 10), end_at=datetime.time(14, 50), duration=20
    )
    assert stream.slots_count == 2
    slot = InterviewSlotFactory(
        interview=None,
        stream=stream,
        start_at=datetime.time(15, 0),
        end_at=datetime.time(16, 0),
    )
    stream.refresh_from_db()
    assert stream.slots_count == 3
    slot.delete()
    stream.refresh_from_db()
    assert stream.slots_count == 2


@pytest.mark.django_db
def test_interview_stream_slots_occupied():
    stream = InterviewStreamFactory(
        start_at=datetime.time(14, 10), end_at=datetime.time(14, 50), duration=20
    )
    slot = InterviewSlotFactory(
        interview__section=InterviewSections.MATH,
        stream=stream,
        start_at=datetime.time(15, 0),
        end_at=datetime.time(16, 0),
    )
    stream.refresh_from_db()
    assert stream.slots_count == 3
    assert stream.slots_occupied_count == 1
    slot.interview = None
    slot.save()
    stream.refresh_from_db()
    assert stream.slots_count == 3
    assert stream.slots_occupied_count == 0


@pytest.mark.django_db
def test_applicant_status_log_creation():
    """Test that ApplicantStatusLog is created when applicant status changes."""
    applicant = ApplicantFactory(status=ApplicantStatuses.PENDING)
    
    # Initially there should be no logs, even if status is set on creation
    assert not applicant.status_logs.count()
    
    # Change the status and save
    applicant.status = ApplicantStatuses.PASSED_EXAM
    applicant.save()
    
    # Check that a log was created
    assert applicant.status_logs.count() == 1
    log = applicant.status_logs.first()
    assert log.former_status == ApplicantStatuses.PENDING
    assert log.status == ApplicantStatuses.PASSED_EXAM
    assert log.entry_author is None  # No user specified


@pytest.mark.django_db
def test_applicant_status_log_no_change():
    """Test that ApplicantStatusLog is not created when status doesn't change."""
    applicant = ApplicantFactory(status=ApplicantStatuses.PENDING)
    
    # Initially there should be no logs
    assert applicant.status_logs.count() == 0
    
    # Change something else but not status
    applicant.first_name = "New Name"
    applicant.save()
    
    # Check that still no log was created
    assert applicant.status_logs.count() == 0


@pytest.mark.django_db
def test_applicant_email_uniqueness_with_ununique_email_status():
    """Test that applicants with the same email can exist when one has a ununique email status."""
    campaign = CampaignFactory()
    email = "same_email@example.com"
    ApplicantFactory(
        campaign=campaign,
        email=email,
        status=ApplicantStatuses.REJECTED_BY_EXAM_PRESELECT
    ).full_clean()
    ApplicantFactory(
        campaign=campaign,
        email=email,
        status=ApplicantStatuses.PENDING
    ).full_clean()
    assert Applicant.objects.filter(email=email, campaign=campaign).count() == 2


@pytest.mark.django_db
def test_applicant_email_uniqueness_with_active_applicant():
    """Test that creating an applicant with the same email as an active applicant is prevented."""
    campaign = CampaignFactory()
    email = "same_email@example.com"
    ApplicantFactory(
        campaign=campaign,
        email=email,
        status=ApplicantStatuses.PENDING
    ).full_clean()
    
    applicant2 = ApplicantFactory.build(
        campaign=campaign,
        email=email,
        status=ApplicantStatuses.PENDING
    )
    
    with pytest.raises(ValidationError) as excinfo:
        applicant2.full_clean()
    assert 'email' in excinfo.value.error_dict


@pytest.mark.django_db
def test_applicant_status_change_from_special_to_non_special_allowed():
    """Test that changing status from special to non-special is allowed when no active applicant exists."""
    campaign = CampaignFactory()
    email = "same_email@example.com"
    ApplicantFactory(
        campaign=campaign,
        email=email,
        status=ApplicantStatuses.REJECTED_BY_EXAM_PRESELECT
    )
    applicant = ApplicantFactory(
        campaign=campaign,
        email=email,
        status=ApplicantStatuses.REJECTED_BY_EXAM_PRESELECT
    )
    applicant.status = ApplicantStatuses.PENDING
    applicant.full_clean()
    applicant.save()
    applicant.refresh_from_db()
    assert applicant.status == ApplicantStatuses.PENDING


@pytest.mark.django_db
def test_applicant_status_change_from_special_to_non_special_prevented():
    """Test that changing status from special to non-special is prevented when an active applicant exists."""
    campaign = CampaignFactory()
    email = "same_email@example.com"

    applicant = ApplicantFactory(
        campaign=campaign,
        email=email,
        status=ApplicantStatuses.REJECTED_BY_EXAM_PRESELECT
    )
    ApplicantFactory(
        campaign=campaign,
        email=email,
        status=ApplicantStatuses.PENDING
    ).full_clean()
    
    applicant.status = ApplicantStatuses.PASSED_EXAM
    with pytest.raises(ValidationError) as excinfo:
        applicant.full_clean()
    assert 'status' in excinfo.value.error_dict
