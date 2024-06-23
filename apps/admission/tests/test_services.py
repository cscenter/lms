import dataclasses
import datetime
import io
import itertools
from typing import BinaryIO, cast

import pytest
import pytz
from rest_framework.exceptions import NotFound

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q
from django.utils import timezone

from admission.constants import (
    INVITATION_EXPIRED_IN_HOURS,
    ChallengeStatuses,
    InterviewFormats,
    InterviewInvitationStatuses,
    InterviewSections, ApplicantStatuses, ApplicantInterviewFormats,
)
from admission.models import Acceptance, Applicant, Exam, Interview, InterviewSlot
from admission.services import (
    AccountData,
    EmailQueueService,
    StudentProfileData,
    accept_interview_invitation,
    create_student,
    create_student_from_applicant,
    decline_interview_invitation,
    get_acceptance_ready_to_confirm,
    get_applicants_for_invitation,
    get_meeting_time,
    get_ongoing_interview_streams,
    get_or_create_student_profile,
    get_streams,
)
from admission.tests.factories import (
    AcceptanceFactory,
    ApplicantFactory,
    CampaignFactory,
    ExamFactory,
    InterviewFactory,
    InterviewFormatFactory,
    InterviewInvitationFactory,
    InterviewSlotFactory,
    InterviewStreamFactory,
)
from core.models import Branch
from core.tests.factories import BranchFactory, EmailTemplateFactory, SiteFactory
from core.timezone import get_now_utc
from core.urls import reverse
from users.constants import GenderTypes
from users.models import StudentTypes
from users.services import get_student_profile
from users.tests.factories import StudentProfileFactory, UserFactory, CuratorFactory


@pytest.mark.django_db
def test_new_exam_invitation_email():
    email_template = EmailTemplateFactory()
    campaign = CampaignFactory(template_exam_invitation=email_template.name)
    applicant = ApplicantFactory(campaign=campaign)
    with pytest.raises(Exam.DoesNotExist):
        EmailQueueService.new_exam_invitation(applicant)
    exam = ExamFactory(
        applicant=applicant, status=ChallengeStatuses.REGISTERED, yandex_contest_id="42"
    )
    email, created = EmailQueueService.new_exam_invitation(applicant)
    assert created
    assert email.template == email_template
    assert email.to == [applicant.email]
    # Render on delivery
    assert not email.subject
    assert not email.message
    assert not email.html_message
    assert "YANDEX_LOGIN" in email.context
    assert email.context["YANDEX_LOGIN"] == applicant.yandex_login
    assert "CONTEST_ID" in email.context
    assert email.context["CONTEST_ID"] == "42"
    email2, created = EmailQueueService.new_exam_invitation(applicant)
    assert not created
    assert email2 == email
    email3, created = EmailQueueService.new_exam_invitation(
        applicant, allow_duplicates=True
    )
    assert created
    assert email3.pk > email2.pk


@pytest.mark.django_db
def test_create_student_from_applicant(settings):
    branch = BranchFactory(time_zone=pytz.timezone("Asia/Yekaterinburg"))
    campaign = CampaignFactory(branch=branch)
    applicant = ApplicantFactory(campaign=campaign)
    user = create_student_from_applicant(applicant)
    student_profile = user.get_student_profile(settings.SITE_ID)
    assert student_profile.branch == branch
    assert student_profile.year_of_admission == applicant.campaign.year
    assert student_profile.type == StudentTypes.REGULAR
    assert user.time_zone == branch.time_zone


@pytest.mark.django_db
def test_accept_interview_invitation():
    dt = timezone.now() + datetime.timedelta(days=3)
    slot = InterviewSlotFactory(
        interview=None,
        stream__section=InterviewSections.MATH,
        stream__date=dt.date(),
        start_at=datetime.time(14, 0),
        end_at=datetime.time(16, 0),
    )
    invitation1 = InterviewInvitationFactory(interview=None, streams=[slot.stream])
    invitation2 = InterviewInvitationFactory(interview=None)
    with pytest.raises(NotFound) as e:  # type: ExceptionInfo[Any]
        accept_interview_invitation(invitation1, slot_id=0)
    with pytest.raises(ValidationError) as e:
        accept_interview_invitation(invitation2, slot_id=slot.pk)
    assert "not associated" in e.value.message
    interview1 = InterviewFactory(section=InterviewSections.ALL_IN_ONE)
    invitation1.interview = interview1
    with pytest.raises(ValidationError) as e:
        accept_interview_invitation(invitation1, slot_id=slot.pk)
    assert e.value.code == "corrupted"
    interview2 = InterviewFactory(
        section=InterviewSections.ALL_IN_ONE, applicant=invitation1.applicant
    )
    invitation1.interview = interview2
    with pytest.raises(ValidationError) as e:
        accept_interview_invitation(invitation1, slot_id=slot.pk)
    assert e.value.code == "accepted"
    invitation1.interview = None
    accept_interview_invitation(invitation1, slot_id=slot.pk)
    assert Interview.objects.count() == 3
    interview = Interview.objects.exclude(pk__in=[interview1.pk, interview2.pk]).get()
    assert interview.date.date() == dt.date()
    assert interview.date_local().hour == 14
    assert interview.section == slot.stream.section
    invitation1.refresh_from_db()
    assert invitation1.interview_id == interview.id
    # TODO: occupy slot


@pytest.mark.django_db(transaction=True)
def test_accept_interview_invitation_slots_occupied():
    stream = InterviewStreamFactory(
        section=InterviewSections.MATH,
        start_at=datetime.time(14, 10),
        end_at=datetime.time(14, 30),
        duration=20,
        date=(timezone.now() + datetime.timedelta(days=3)).date(),
    )
    slot = InterviewSlotFactory(
        interview=None,
        stream=stream,
        start_at=datetime.time(14, 0),
        end_at=datetime.time(16, 0),
    )
    stream.refresh_from_db()
    assert stream.slots_occupied_count == 0
    invitation = InterviewInvitationFactory(interview=None, streams=[slot.stream])
    accept_interview_invitation(invitation, slot_id=slot.pk)
    stream.refresh_from_db()
    assert stream.slots_occupied_count == 1


@pytest.mark.django_db
def test_decline_interview_invitation():
    dt = timezone.now() + datetime.timedelta(days=3)
    slot = InterviewSlotFactory(
        interview=None,
        stream__section=InterviewSections.MATH,
        stream__date=dt.date(),
        start_at=datetime.time(14, 0),
        end_at=datetime.time(16, 0),
    )
    invitation = InterviewInvitationFactory(interview=None, streams=[slot.stream])
    assert invitation.status == InterviewInvitationStatuses.NO_RESPONSE
    decline_interview_invitation(invitation)
    invitation.refresh_from_db()
    assert invitation.status == InterviewInvitationStatuses.DECLINED
    # Invite is expired but status is not synced yet
    invitation.expired_at = timezone.now() - datetime.timedelta(days=3)
    invitation.status = InterviewInvitationStatuses.NO_RESPONSE
    invitation.save()
    with pytest.raises(ValidationError) as e:
        decline_interview_invitation(invitation)
    assert e.value.code == "expired"


@pytest.mark.django_db
def test_get_streams():
    campaign = CampaignFactory(
        current=True, branch__time_zone=pytz.timezone("Europe/Moscow")
    )
    # Make sure invitation is active
    dt = timezone.now() + datetime.timedelta(hours=INVITATION_EXPIRED_IN_HOURS)
    stream = InterviewStreamFactory(
        start_at=datetime.time(14, 10),
        end_at=datetime.time(15, 10),
        duration=20,
        date=dt.date(),
        with_assignments=False,
        campaign=campaign,
        section=InterviewSections.ALL_IN_ONE,
        format=InterviewFormats.OFFLINE,
    )
    assert stream.slots.count() == 3
    invitation = InterviewInvitationFactory(
        expired_at=dt,
        applicant__campaign=stream.campaign,
        interview=None,
        streams=[stream],
    )
    streams = get_streams(invitation)
    assert len(streams) == 1
    assert stream in streams
    slots = streams[stream]
    assert len(slots) == 3
    slot1, slot2, slot3 = slots
    assert slot1.start_at == datetime.time(hour=14, minute=10)
    assert slot2.start_at == datetime.time(hour=14, minute=30)
    assert slot3.start_at == datetime.time(hour=14, minute=50)


@pytest.mark.django_db
def test_get_meeting_time():
    dt = timezone.now() + datetime.timedelta(hours=INVITATION_EXPIRED_IN_HOURS)
    campaign = CampaignFactory(
        current=True, branch__time_zone=pytz.timezone("Europe/Moscow")
    )
    # Make sure invitation is active
    stream = InterviewStreamFactory(
        start_at=datetime.time(14, 10),
        end_at=datetime.time(14, 30),
        duration=20,
        date=dt.date(),
        with_assignments=False,
        campaign=campaign,
        section=InterviewSections.ALL_IN_ONE,
        format=InterviewFormats.OFFLINE,
    )
    assert stream.slots.count() == 1
    slot = stream.slots.first()
    meeting_at = get_meeting_time(slot.datetime_local, stream)
    assert meeting_at.time() == datetime.time(hour=14, minute=10)
    # 30 min diff if stream with assignments
    stream.with_assignments = True
    stream.save()
    meeting_at = get_meeting_time(slot.datetime_local, stream)
    assert meeting_at.time() == datetime.time(hour=13, minute=40)
    # Don't adjust time for online interview format
    InterviewFormatFactory(campaign=campaign, format=InterviewFormats.ONLINE)
    stream.format = InterviewFormats.ONLINE
    stream.save()
    meeting_at = get_meeting_time(slot.datetime_local, stream)
    assert meeting_at.time() == datetime.time(hour=14, minute=10)


@pytest.mark.django_db
def test_ongoing_interview_streams():
    today_utc = get_now_utc()
    tomorrow = today_utc + datetime.timedelta(days=1)
    assert get_ongoing_interview_streams().count() == 0
    stream = InterviewStreamFactory(
        start_at=datetime.time(14, 10),
        end_at=datetime.time(14, 30),
        duration=20,
        date=today_utc.date(),
    )
    stream = InterviewStreamFactory(
        start_at=datetime.time(14, 10),
        end_at=datetime.time(14, 30),
        duration=20,
        date=tomorrow.date(),
    )
    assert get_ongoing_interview_streams().count() == 1


@pytest.mark.django_db
def test_get_applicants_for_invitation():
    campaign1, campaign2 = CampaignFactory.create_batch(2)
    applicant1 = ApplicantFactory(campaign=campaign1)
    applicant2 = ApplicantFactory(campaign=campaign2)
    assert (
        get_applicants_for_invitation(
            campaign=campaign1, section=InterviewSections.ALL_IN_ONE
        ).count()
        == 0
    )
    applicant3 = ApplicantFactory(
        campaign=campaign1, status=ApplicantStatuses.PASSED_EXAM
    )
    assert (
        get_applicants_for_invitation(
            campaign=campaign1, section=InterviewSections.ALL_IN_ONE
        ).count()
        == 1
    )
    # Participant is already interviewed on another section
    InterviewFactory(applicant=applicant3, section=InterviewSections.MATH)
    assert (
        get_applicants_for_invitation(
            campaign=campaign1, section=InterviewSections.ALL_IN_ONE
        ).count()
        == 1
    )
    InterviewFactory(applicant=applicant3, section=InterviewSections.ALL_IN_ONE)
    assert (
        get_applicants_for_invitation(
            campaign=campaign1, section=InterviewSections.ALL_IN_ONE
        ).count()
        == 0
    )
    # Expired invitation for target section
    applicant4 = ApplicantFactory(
        campaign=campaign1, status=ApplicantStatuses.PASSED_EXAM
    )
    yesterday_utc = get_now_utc() - datetime.timedelta(days=1)
    next_week_utc = get_now_utc() + datetime.timedelta(weeks=1)
    stream = InterviewStreamFactory(
        section=InterviewSections.ALL_IN_ONE,
        start_at=datetime.time(14, 10),
        end_at=datetime.time(14, 30),
        duration=20,
        date=yesterday_utc.date(),
    )
    invitation = InterviewInvitationFactory(
        interview=None, applicant=applicant4, expired_at=yesterday_utc, streams=[stream]
    )
    assert (
        get_applicants_for_invitation(
            campaign=campaign1, section=InterviewSections.ALL_IN_ONE
        ).count()
        == 1
    )
    # Active invitation for another section
    stream = InterviewStreamFactory(
        section=InterviewSections.MATH,
        start_at=datetime.time(14, 10),
        end_at=datetime.time(14, 30),
        duration=20,
        date=next_week_utc.date(),
    )
    invitation = InterviewInvitationFactory(
        interview=None, applicant=applicant4, expired_at=next_week_utc, streams=[stream]
    )
    assert (
        get_applicants_for_invitation(
            campaign=campaign1, section=InterviewSections.ALL_IN_ONE
        ).count()
        == 1
    )
    # Active invitation
    stream = InterviewStreamFactory(
        section=InterviewSections.ALL_IN_ONE,
        start_at=datetime.time(14, 10),
        end_at=datetime.time(14, 30),
        duration=20,
        date=next_week_utc.date(),
    )
    invitation = InterviewInvitationFactory(
        interview=None, applicant=applicant4, expired_at=next_week_utc, streams=[stream]
    )
    assert (
        get_applicants_for_invitation(
            campaign=campaign1, section=InterviewSections.ALL_IN_ONE
        ).count()
        == 0
    )
@pytest.mark.django_db
def test_get_applicants_for_invitation_with_filters(client, settings):
    campaign = CampaignFactory(current=True)
    formats = [ApplicantInterviewFormats.ONLINE, ApplicantInterviewFormats.OFFLINE, ApplicantInterviewFormats.ANY]
    tracks = [False, True]
    statuses = [ApplicantStatuses.PASSED_EXAM, ApplicantStatuses.PASSED_OLYMPIAD, ApplicantStatuses.GOLDEN_TICKET]
    miss_counts = range(0, 6)
    combinations = list(
        itertools.product(statuses, formats, tracks, miss_counts))
    applicants = [
        ApplicantFactory(
            status=status,
            campaign=campaign,
            interview_format=interview_format,
            new_track=new_track,
            miss_count=miss_count
        )
        for status, interview_format, new_track, miss_count in combinations
    ]

    for format in ['online', 'offline']:
        qs = get_applicants_for_invitation(
            campaign=campaign, section=InterviewSections.ALL_IN_ONE, format=format
        )
        for applicant in applicants:
            if applicant.interview_format == ApplicantInterviewFormats.ONLINE and format == 'online':
                assert applicant in qs
            elif applicant.interview_format == ApplicantInterviewFormats.OFFLINE and format == 'offline':
                assert applicant in qs
            elif applicant.interview_format == ApplicantInterviewFormats.ANY:
                assert applicant in qs
            else:
                assert applicant not in qs

    for track in ['regular', 'alternative']:
        qs = get_applicants_for_invitation(
            campaign=campaign, section=InterviewSections.ALL_IN_ONE, track=track
        )
        for applicant in applicants:
            if applicant.new_track is True and track == 'alternative':
                assert applicant in qs
            elif applicant.new_track is False and track == 'regular':
                assert applicant in qs
            else:
                assert applicant not in qs

    for way_to_interview in ['exam', 'olympiad', 'golden_ticket']:
        qs = get_applicants_for_invitation(
            campaign=campaign, section=InterviewSections.ALL_IN_ONE, way_to_interview=way_to_interview
        )
        for applicant in applicants:
            if applicant.status == ApplicantStatuses.PASSED_EXAM and way_to_interview == 'exam':
                assert applicant in qs
            elif applicant.status == ApplicantStatuses.PASSED_OLYMPIAD and way_to_interview == 'olympiad':
                assert applicant in qs
            elif applicant.status == ApplicantStatuses.GOLDEN_TICKET and way_to_interview == 'golden_ticket':
                assert applicant in qs
            else:
                assert applicant not in qs

    for miss_count in range(0,5):
        qs = get_applicants_for_invitation(
            campaign=campaign, section=InterviewSections.ALL_IN_ONE, number_of_misses=miss_count
        )
        for applicant in applicants:
            if applicant.miss_count == miss_count and miss_count in range(0,4):
                assert applicant in qs
            elif applicant.miss_count > 3 and miss_count == 4:
                assert applicant in qs
            else:
                assert applicant not in qs, f'{applicant=}, {applicant.miss_count=}, {miss_count=}'

@pytest.mark.django_db
def test_get_streams(client, settings):
    campaign = CampaignFactory(current=True)
    stream_1 = InterviewStreamFactory(
        campaign=campaign, section=InterviewSections.ALL_IN_ONE, interviewers_max=2,
        start_at=datetime.datetime(2011, 1, 1, 13, 0, 0), end_at=datetime.datetime(2011, 1, 1, 15, 0, 0)
    )
    stream_2 = InterviewStreamFactory(
        campaign=campaign, section=InterviewSections.ALL_IN_ONE,
        start_at=datetime.datetime(2011, 1, 1, 13, 0, 0), end_at=datetime.datetime(2011, 1, 1, 14, 0, 0)
    )
    invitation = InterviewInvitationFactory(streams=[stream_1,stream_2],
                                            interview__section=InterviewSections.ALL_IN_ONE)
    assert stream_1 in get_streams(invitation).keys()
    assert stream_2 in get_streams(invitation).keys()
    for _ in range(2):
        slot = InterviewSlot.objects.filter(stream=stream_1, interview__isnull=True).first()
        interview = InterviewFactory(section=InterviewSections.ALL_IN_ONE)
        slot.interview = interview
        slot.save()
    # stream is not present if no more free slots left or occupied_slots are more than interviewers_max
    assert stream_1 not in get_streams(invitation).keys()
    assert stream_2 in get_streams(invitation).keys()

@pytest.mark.django_db
def test_get_acceptance_ready_to_confirm(settings):
    branch1 = BranchFactory(site__domain="test.domain1")
    future_dt = get_now_utc() + datetime.timedelta(days=5)
    campaign1 = CampaignFactory(
        year=2011, branch=branch1, confirmation_ends_at=future_dt
    )
    campaign2 = CampaignFactory(
        year=2011,
        branch=BranchFactory(site=SiteFactory(pk=settings.SITE_ID)),
        confirmation_ends_at=future_dt,
    )
    acceptance1 = AcceptanceFactory(
        status=Acceptance.WAITING, applicant__campaign=campaign1
    )
    acceptance2 = AcceptanceFactory(
        status=Acceptance.WAITING, applicant__campaign=campaign2
    )
    branches = Branch.objects.for_site(site_id=settings.SITE_ID)
    assert (
        get_acceptance_ready_to_confirm(
            year=2011,
            access_key=acceptance1.access_key,
            filters=[Q(applicant__campaign__branch__in=branches)],
        )
        is None
    )
    assert (
        get_acceptance_ready_to_confirm(
            year=2011,
            access_key=acceptance2.access_key,
            filters=[Q(applicant__campaign__branch__in=branches)],
        )
        == acceptance2
    )
    # Test deadline
    acceptance2.applicant.campaign.confirmation_ends_at = None
    acceptance2.applicant.campaign.save()
    with pytest.raises(ValidationError) as e:
        get_acceptance_ready_to_confirm(
            year=2011,
            access_key=acceptance2.access_key,
            filters=[Q(applicant__campaign__branch__in=branches)],
        )
    assert e.value.code == "expired"
    # Already confirmed
    acceptance2.applicant.campaign.confirmation_ends_at = future_dt
    acceptance2.applicant.campaign.save()
    acceptance2.status = Acceptance.CONFIRMED
    acceptance2.save()
    with pytest.raises(ValidationError) as e:
        get_acceptance_ready_to_confirm(
            year=2011,
            access_key=acceptance2.access_key,
            filters=[Q(applicant__campaign__branch__in=branches)],
        )
    assert e.value.code == "malformed"
    # Applicant is associated with a user account
    acceptance2.status = Acceptance.WAITING
    acceptance2.save()
    acceptance2.applicant.user_id = UserFactory()
    acceptance2.applicant.save()
    with pytest.raises(ValidationError) as e:
        get_acceptance_ready_to_confirm(
            year=2011,
            access_key=acceptance2.access_key,
            filters=[Q(applicant__campaign__branch__in=branches)],
        )
    assert e.value.code == "confirmed"


ACCOUNT_DATA = AccountData(
    email="test@example.com",
    time_zone=pytz.timezone("Europe/Moscow"),
    gender=GenderTypes.FEMALE,
    photo=SimpleUploadedFile("test.txt", b"content"),
    telegram_username="username",
    phone="+71234567",
    workplace="vk",
    private_contacts="tiktok.com/git_lover",
    codeforces_login="handle1",
    stepic_id="42",
    github_login="git_lover",
    birth_date=datetime.date(2000, 1, 1),
)
STUDENT_PROFILE_DATA = StudentProfileData(university="University1")


@pytest.mark.django_db
def test_create_student(settings, get_test_image):
    future_dt = get_now_utc() + datetime.timedelta(days=5)
    campaign = CampaignFactory(
        year=2011,
        branch=BranchFactory(site=SiteFactory(pk=settings.SITE_ID)),
        confirmation_ends_at=future_dt,
    )
    acceptance = AcceptanceFactory(
        status=Acceptance.WAITING,
        applicant__campaign=campaign,
        applicant__yandex_login="login1",
        applicant__university_other="University2",
    )
    applicant = acceptance.applicant
    user = create_student(acceptance, ACCOUNT_DATA, STUDENT_PROFILE_DATA)
    assert user.pk
    applicant.refresh_from_db()
    assert user.first_name == applicant.first_name
    assert user.last_name == applicant.last_name
    assert user.patronymic == applicant.patronymic
    assert user.gender == ACCOUNT_DATA.gender
    assert user.yandex_login == "login1"
    assert user.birth_date == ACCOUNT_DATA.birth_date
    assert applicant.user == user
    acceptance.refresh_from_db()
    assert acceptance.status == Acceptance.CONFIRMED
    student_profile = get_student_profile(
        user=user,
        site=campaign.branch.site,
        profile_type=StudentTypes.REGULAR,
        filters=[Q(year_of_admission=campaign.year)],
    )
    assert student_profile is not None
    assert student_profile.university == STUDENT_PROFILE_DATA.university
    assert student_profile.year_of_admission == campaign.year
    assert student_profile.type == StudentTypes.REGULAR


@pytest.mark.django_db
def test_get_or_create_student_profile(settings, get_test_image):
    branch = BranchFactory(site=SiteFactory(pk=settings.SITE_ID))
    campaign1 = CampaignFactory(year=2011, branch=branch)
    campaign2 = CampaignFactory(year=2012, branch=branch)
    student_profile = StudentProfileFactory(
        type=StudentTypes.REGULAR,
        branch=campaign1.branch,
        year_of_admission=campaign1.year,
    )
    user = student_profile.user
    sp1 = get_or_create_student_profile(campaign1, user)
    assert sp1 == student_profile
    sp2 = get_or_create_student_profile(campaign2, user)
    assert sp2 != sp1
    # Don't allow overwrite data relative to campaign
    sp2.delete()
    branch1 = BranchFactory()
    sp2 = get_or_create_student_profile(
        campaign2,
        user,
        data={
            "year_of_admission": 1998,
            "branch": branch1,
            "user": UserFactory(),
            "profile_type": StudentTypes.VOLUNTEER,
        },
    )
    assert sp2.year_of_admission == campaign2.year
    assert sp2.branch == campaign2.branch
    assert sp2.user == user
    assert sp2.type == StudentTypes.VOLUNTEER


@pytest.mark.django_db
def test_create_student_email_case_insensitive(settings, get_test_image):
    future_dt = get_now_utc() + datetime.timedelta(days=5)
    campaign = CampaignFactory(
        year=2011,
        branch=BranchFactory(site=SiteFactory(pk=settings.SITE_ID)),
        confirmation_ends_at=future_dt,
    )
    acceptance = AcceptanceFactory(
        status=Acceptance.WAITING,
        applicant__campaign=campaign,
        applicant__yandex_login="login1",
    )
    user1 = UserFactory(email=ACCOUNT_DATA.email)
    assert user1.email == "test@example.com"
    # Merging data into existing account since email address must be case insensitive
    account_data1 = dataclasses.replace(ACCOUNT_DATA, email="TEST@example.com")
    user2 = create_student(acceptance, account_data1, STUDENT_PROFILE_DATA)
    assert user2.pk == user1.pk
