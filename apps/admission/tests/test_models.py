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
