import datetime

import pytest
import pytz
from rest_framework.exceptions import NotFound

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from admission.constants import (
    INVITATION_EXPIRED_IN_HOURS, ChallengeStatuses, InterviewFormats,
    InterviewInvitationStatuses, InterviewSections
)
from admission.models import Acceptance, Applicant, Exam, Interview
from admission.services import (
    EmailQueueService, accept_interview_invitation, create_student_from_applicant,
    decline_interview_invitation, get_acceptance_ready_to_confirm,
    get_applicants_for_invitation, get_meeting_time, get_ongoing_interview_streams,
    get_streams
)
from admission.tests.factories import (
    AcceptanceFactory, ApplicantFactory, CampaignFactory, ExamFactory, InterviewFactory,
    InterviewFormatFactory, InterviewInvitationFactory, InterviewSlotFactory,
    InterviewStreamFactory
)
from core.models import Branch
from core.tests.factories import BranchFactory, EmailTemplateFactory, SiteFactory
from core.timezone import get_now_utc
from users.models import StudentTypes
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_new_exam_invitation_email():
    email_template = EmailTemplateFactory()
    campaign = CampaignFactory(template_exam_invitation=email_template.name)
    applicant = ApplicantFactory(campaign=campaign)
    with pytest.raises(Exam.DoesNotExist):
        EmailQueueService.new_exam_invitation(applicant)
    exam = ExamFactory(applicant=applicant, status=ChallengeStatuses.REGISTERED,
                       yandex_contest_id='42')
    email, created = EmailQueueService.new_exam_invitation(applicant)
    assert created
    assert email.template == email_template
    assert email.to == [applicant.email]
    # Render on delivery
    assert not email.subject
    assert not email.message
    assert not email.html_message
    assert 'YANDEX_LOGIN' in email.context
    assert email.context['YANDEX_LOGIN'] == applicant.yandex_login
    assert 'CONTEST_ID' in email.context
    assert email.context['CONTEST_ID'] == '42'
    email2, created = EmailQueueService.new_exam_invitation(applicant)
    assert not created
    assert email2 == email
    email3, created = EmailQueueService.new_exam_invitation(applicant,
                                                            allow_duplicates=True)
    assert created
    assert email3.pk > email2.pk


@pytest.mark.django_db
def test_create_student_from_applicant(settings):
    branch = BranchFactory(time_zone='Asia/Yekaterinburg')
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
    with pytest.raises(NotFound) as e:
        accept_interview_invitation(invitation1, slot_id=0)
    with pytest.raises(ValidationError) as e:
        accept_interview_invitation(invitation2, slot_id=slot.pk)
    assert "not associated" in e.value.message
    interview1 = InterviewFactory(section=InterviewSections.ALL_IN_ONE)
    invitation1.interview = interview1
    with pytest.raises(ValidationError) as e:
        accept_interview_invitation(invitation1, slot_id=slot.pk)
    assert e.value.code == 'corrupted'
    interview2 = InterviewFactory(section=InterviewSections.ALL_IN_ONE,
                                  applicant=invitation1.applicant)
    invitation1.interview = interview2
    with pytest.raises(ValidationError) as e:
        accept_interview_invitation(invitation1, slot_id=slot.pk)
    assert e.value.code == 'accepted'
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
        date=(timezone.now() + datetime.timedelta(days=3)).date())
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
    assert e.value.code == 'expired'


@pytest.mark.django_db
def test_get_streams():
    campaign = CampaignFactory(current=True,
                               branch__time_zone=pytz.timezone('Europe/Moscow'))
    # Make sure invitation is active
    dt = timezone.now() + datetime.timedelta(hours=INVITATION_EXPIRED_IN_HOURS)
    stream = InterviewStreamFactory(start_at=datetime.time(14, 10),
                                    end_at=datetime.time(15, 10),
                                    duration=20,
                                    date=dt.date(),
                                    with_assignments=False,
                                    campaign=campaign,
                                    section=InterviewSections.ALL_IN_ONE,
                                    format=InterviewFormats.OFFLINE)
    assert stream.slots.count() == 3
    invitation = InterviewInvitationFactory(
        expired_at=dt,
        applicant__campaign=stream.campaign,
        interview=None,
        streams=[stream])
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
    campaign = CampaignFactory(current=True,
                               branch__time_zone=pytz.timezone('Europe/Moscow'))
    # Make sure invitation is active
    stream = InterviewStreamFactory(start_at=datetime.time(14, 10),
                                    end_at=datetime.time(14, 30),
                                    duration=20,
                                    date=dt.date(),
                                    with_assignments=False,
                                    campaign=campaign,
                                    section=InterviewSections.ALL_IN_ONE,
                                    format=InterviewFormats.OFFLINE)
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
    stream = InterviewStreamFactory(start_at=datetime.time(14, 10),
                                    end_at=datetime.time(14, 30),
                                    duration=20,
                                    date=today_utc.date())
    stream = InterviewStreamFactory(start_at=datetime.time(14, 10),
                                    end_at=datetime.time(14, 30),
                                    duration=20,
                                    date=tomorrow.date())
    assert get_ongoing_interview_streams().count() == 1


@pytest.mark.django_db
def test_get_applicants_for_invitation():
    campaign1, campaign2 = CampaignFactory.create_batch(2)
    applicant1 = ApplicantFactory(campaign=campaign1)
    applicant2 = ApplicantFactory(campaign=campaign2)
    assert get_applicants_for_invitation(campaign=campaign1,
                                         section=InterviewSections.ALL_IN_ONE).count() == 0
    applicant3 = ApplicantFactory(campaign=campaign1, status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    assert get_applicants_for_invitation(campaign=campaign1,
                                         section=InterviewSections.ALL_IN_ONE).count() == 1
    # Participant is already interviewed on another section
    InterviewFactory(applicant=applicant3, section=InterviewSections.MATH)
    assert get_applicants_for_invitation(campaign=campaign1,
                                         section=InterviewSections.ALL_IN_ONE).count() == 1
    InterviewFactory(applicant=applicant3, section=InterviewSections.ALL_IN_ONE)
    assert get_applicants_for_invitation(campaign=campaign1,
                                         section=InterviewSections.ALL_IN_ONE).count() == 0
    # Expired invitation for target section
    applicant4 = ApplicantFactory(campaign=campaign1, status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    yesterday_utc = get_now_utc() - datetime.timedelta(days=1)
    next_week_utc = get_now_utc() + datetime.timedelta(weeks=1)
    stream = InterviewStreamFactory(section=InterviewSections.ALL_IN_ONE,
                                    start_at=datetime.time(14, 10),
                                    end_at=datetime.time(14, 30),
                                    duration=20,
                                    date=yesterday_utc.date())
    invitation = InterviewInvitationFactory(interview=None,
                                            applicant=applicant4,
                                            expired_at=yesterday_utc,
                                            streams=[stream])
    assert get_applicants_for_invitation(campaign=campaign1,
                                         section=InterviewSections.ALL_IN_ONE).count() == 1
    # Active invitation for another section
    stream = InterviewStreamFactory(section=InterviewSections.MATH,
                                    start_at=datetime.time(14, 10),
                                    end_at=datetime.time(14, 30),
                                    duration=20,
                                    date=next_week_utc.date())
    invitation = InterviewInvitationFactory(interview=None,
                                            applicant=applicant4,
                                            expired_at=next_week_utc,
                                            streams=[stream])
    assert get_applicants_for_invitation(campaign=campaign1,
                                         section=InterviewSections.ALL_IN_ONE).count() == 1
    # Active invitation
    stream = InterviewStreamFactory(section=InterviewSections.ALL_IN_ONE,
                                    start_at=datetime.time(14, 10),
                                    end_at=datetime.time(14, 30),
                                    duration=20,
                                    date=next_week_utc.date())
    invitation = InterviewInvitationFactory(interview=None,
                                            applicant=applicant4,
                                            expired_at=next_week_utc,
                                            streams=[stream])
    assert get_applicants_for_invitation(campaign=campaign1,
                                         section=InterviewSections.ALL_IN_ONE).count() == 0


@pytest.mark.django_db
def test_get_acceptance_ready_to_confirm(settings):
    branch1 = BranchFactory(site__domain='test.domain1')
    future_dt = get_now_utc() + datetime.timedelta(days=5)
    campaign1 = CampaignFactory(year=2011, branch=branch1,
                                confirmation_ends_at=future_dt)
    campaign2 = CampaignFactory(year=2011,
                                branch=BranchFactory(site=SiteFactory(pk=settings.SITE_ID)),
                                confirmation_ends_at=future_dt)
    acceptance1 = AcceptanceFactory(status=Acceptance.WAITING, applicant__campaign=campaign1)
    acceptance2 = AcceptanceFactory(status=Acceptance.WAITING, applicant__campaign=campaign2)
    branches = Branch.objects.for_site(site_id=settings.SITE_ID)
    assert get_acceptance_ready_to_confirm(year=2011, access_key=acceptance1.access_key,
                                           filters=[Q(applicant__campaign__branch__in=branches)]) is None
    assert get_acceptance_ready_to_confirm(year=2011, access_key=acceptance2.access_key,
                                           filters=[Q(applicant__campaign__branch__in=branches)]) == acceptance2
    # Test deadline
    acceptance2.applicant.campaign.confirmation_ends_at = None
    acceptance2.applicant.campaign.save()
    with pytest.raises(ValidationError) as e:
        get_acceptance_ready_to_confirm(year=2011, access_key=acceptance2.access_key,
                                        filters=[Q(applicant__campaign__branch__in=branches)])
    assert e.value.code == "expired"
    # Already confirmed
    acceptance2.applicant.campaign.confirmation_ends_at = future_dt
    acceptance2.applicant.campaign.save()
    acceptance2.status = Acceptance.CONFIRMED
    acceptance2.save()
    with pytest.raises(ValidationError) as e:
        get_acceptance_ready_to_confirm(year=2011, access_key=acceptance2.access_key,
                                        filters=[Q(applicant__campaign__branch__in=branches)])
    assert e.value.code == "malformed"
    # Applicant is associated with a user account
    acceptance2.status = Acceptance.WAITING
    acceptance2.save()
    acceptance2.applicant.user_id = UserFactory()
    acceptance2.applicant.save()
    with pytest.raises(ValidationError) as e:
        get_acceptance_ready_to_confirm(year=2011, access_key=acceptance2.access_key,
                                        filters=[Q(applicant__campaign__branch__in=branches)])
    assert e.value.code == "confirmed"
