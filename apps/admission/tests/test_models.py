import datetime

import pytest

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError

from admission.constants import InterviewSections, InterviewInvitationStatuses, ApplicantStatuses, ChallengeStatuses
from admission.models import Contest, Interview, Olympiad
from admission.tests.factories import (
    ApplicantFactory,
    CampaignFactory,
    ContestFactory,
    InterviewFactory,
    InterviewInvitationFactory,
    InterviewSlotFactory,
    InterviewStreamFactory,
    OlympiadFactory,
    LocationFactory,
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
def test_olympiad_lifecycle():
    applicant = ApplicantFactory()
    olympiad = Olympiad.objects.create(applicant=applicant)
    assert olympiad.pk is not None
    assert olympiad.score is None
    assert olympiad.math_score is None
    
    location = LocationFactory()
    olympiad_full = Olympiad.objects.create(
        applicant=ApplicantFactory(),
        score=8,
        math_score=7,
        location=location,
        details={"scores": [3, 2, 3]}
    )
    assert olympiad_full.total_score() == 15
    
    olympiad.score = 5
    olympiad.math_score = 4
    olympiad.save()
    olympiad.refresh_from_db()
    assert olympiad.score == 5
    assert olympiad.math_score == 4
    assert olympiad.total_score() == 9
    
    olympiad_id = olympiad.id
    olympiad.delete()
    assert not Olympiad.objects.filter(id=olympiad_id).exists()


@pytest.mark.django_db
def test_olympiad_validation():
    applicant = ApplicantFactory()
    Olympiad.objects.create(applicant=applicant)
    
    with pytest.raises(ValidationError):
        duplicate = Olympiad(applicant=applicant)
        duplicate.full_clean()
    
    olympiad = Olympiad(
        applicant=ApplicantFactory(),
        score=-1
    )
    with pytest.raises(ValidationError):
        olympiad.full_clean()
    
    olympiad = Olympiad(
        applicant=ApplicantFactory(),
        math_score=-1
    )
    with pytest.raises(ValidationError):
        olympiad.full_clean()
    
    olympiad = Olympiad(
        applicant=ApplicantFactory(),
        status="invalid_status"
    )
    with pytest.raises(ValidationError):
        olympiad.full_clean()


@pytest.mark.django_db
def test_olympiad_score_methods():
    olympiad = OlympiadFactory(score=8, math_score=7)
    assert olympiad.score_display() == 8
    assert olympiad.total_score() == 15
    assert olympiad.total_score_display() == 15
    
    olympiad = OlympiadFactory(score=5, math_score=None)
    assert olympiad.score_display() == 5
    assert olympiad.total_score() == 5
    assert olympiad.total_score_display() == 5
    
    olympiad = OlympiadFactory(score=None, math_score=6)
    assert olympiad.score_display() == "-"
    assert olympiad.total_score() == 6
    assert olympiad.total_score_display() == 6
    
    olympiad = OlympiadFactory(score=None, math_score=None)
    assert olympiad.score_display() == "-"
    assert olympiad.total_score() == 0
    assert olympiad.total_score_display() == "-"


@pytest.mark.django_db
def test_olympiad_applicant_integration():
    applicant = ApplicantFactory(status=ApplicantStatuses.PERMIT_TO_OLYMPIAD)
    olympiad = OlympiadFactory(
        applicant=applicant,
        score=8,
        math_score=7
    )
    
    assert olympiad.applicant == applicant
    assert hasattr(applicant, 'olympiad')
    assert applicant.olympiad == olympiad
    assert applicant.get_olympiad_record() == olympiad
    
    applicant.status = ApplicantStatuses.PASSED_OLYMPIAD
    applicant.save()
    applicant.refresh_from_db()
    
    assert hasattr(applicant, 'olympiad')
    assert applicant.olympiad == olympiad
    with pytest.raises(ProtectedError):
        applicant.delete()
