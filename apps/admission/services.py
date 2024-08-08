from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timedelta
from operator import attrgetter
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytz
from post_office import mail
from post_office.models import STATUS as EMAIL_STATUS
from post_office.models import Email, EmailTemplate
from post_office.utils import get_email_template
from rest_framework.exceptions import APIException, NotFound

from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import models, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from admission.constants import (
    EMAIL_VERIFICATION_CODE_TEMPLATE,
    INVITATION_EXPIRED_IN_HOURS,
    ContestTypes,
    InterviewFormats,
    InterviewInvitationStatuses, ApplicantStatuses, ApplicantInterviewFormats,
)
# from admission.filters import InterviewStreamFilter
from admission.models import (
    Acceptance,
    Applicant,
    Campaign,
    Exam,
    Interview,
    InterviewInvitation,
    InterviewSlot,
    InterviewStream,
)
from admission.selectors import get_acceptance
from admission.tokens import email_code_generator
from admission.utils import logger
from core.timezone import get_now_utc
from core.timezone.constants import DATE_FORMAT_RU
from core.utils import bucketize
from grading.api.yandex_contest import YandexContestAPI
from tasks.models import Task
from users.constants import GenderTypes
from users.models import StudentProfile, StudentTypes, User
from users.services import (
    create_account,
    create_student_profile,
    generate_username_from_email,
    get_student_profile,
)


def get_email_from(campaign: Campaign):
    # TODO: add email to Campaign model?
    return campaign.branch.default_email_from


def get_ongoing_interview_streams() -> models.QuerySet[InterviewStream]:
    """
    Returns interview streams to which participants can be invited.
    """
    # XXX: It could return streams that already expired since
    # we get time zone from the venue, e.g. venue time zone is NSK,
    # if create invitation at June 15 22:00 MSK it will expire at June 16 00:00
    # or 15 June 17:00 in UTC time zone (or 15 June 21 MSK)
    return InterviewStream.objects.filter(date__gt=get_now_utc().date())


def get_applicants_for_invitation(
    *, campaign: Campaign, section: str, format=None, last_name=None, track=None, way_to_interview=None,
    number_of_misses=None
) -> models.QuerySet[Applicant]:
    """
    Returns all campaign participants available for invitation to the interview
    of the target section.
    """
    # Waiting for participant response to the sent invitation
    with_active_invitation = (
        InterviewInvitation.objects.filter(
            expired_at__gt=get_now_utc(),
            status=InterviewInvitationStatuses.NO_RESPONSE,
            applicant__campaign=campaign,
            streams__section=section,
        )
        .values("applicant_id")
        .distinct()
    )
    # Participants with scheduled interview
    with_interview = (Interview.objects.filter(
        applicant__campaign=campaign, section=section)
                      .exclude(status__in=[Interview.DEFERRED, Interview.CANCELED])
                      .values("applicant_id"))

    format_filter = Q()
    if format:
        format_filter = Q(interview_format=format) | Q(interview_format=ApplicantInterviewFormats.ANY)

    last_name_filter = Q()
    if last_name:
        last_name_filter = Q(last_name__icontains=last_name)

    track_filter = Q()
    if track:
        track_filter = Q(new_track=(track == "alternative"))

    way_filter = Q()
    if way_to_interview:
        if way_to_interview == "exam":
            way_filter = Q(status=ApplicantStatuses.PASSED_EXAM)
        elif way_to_interview == "olympiad":
            way_filter = Q(status=ApplicantStatuses.PASSED_OLYMPIAD)
        elif way_to_interview == "golden_ticket":
            way_filter = Q(status=ApplicantStatuses.GOLDEN_TICKET)
        else:
            raise ValueError(f"Unsupported value {way_to_interview}")

    miss_filter = Q()
    if number_of_misses or number_of_misses == 0:
        if number_of_misses in range(0, 4):
            miss_filter = Q(miss_count=number_of_misses)
        elif number_of_misses == 4:
            miss_filter = Q(miss_count__gt=3)
        else:
            raise ValueError(f"Unsupported value {number_of_misses}")

    queryset = (
        Applicant.objects.filter(
            format_filter,
            track_filter,
            way_filter,
            miss_filter,
            last_name_filter,
            campaign=campaign,
            status__in=ApplicantStatuses.RIGHT_BEFORE_INTERVIEW,
        )
        .exclude(pk__in=with_active_invitation)
        .exclude(pk__in=with_interview)
    )
    return queryset


def create_invitation(
    streams: List[InterviewStream], applicant: Applicant
) -> InterviewInvitation:
    first_stream = min(streams, key=attrgetter("date"))
    tz = first_stream.get_timezone()
    first_day_interview_naive = datetime.combine(first_stream.date, datetime.min.time())
    first_day_interview = tz.localize(first_day_interview_naive)
    # Calculate deadline for invitation. It can't be later than 00:00
    # of the first interview day
    expired_in_hours = INVITATION_EXPIRED_IN_HOURS
    now_utc = get_now_utc()
    expired_at = now_utc + timedelta(hours=expired_in_hours)
    expired_at = min(expired_at, first_day_interview)
    # FIXME: add test
    if expired_at <= now_utc:
        raise ValidationError("Invitation already expired", code="expired")
    invitation = InterviewInvitation(applicant=applicant, expired_at=expired_at)
    invitation.save()
    invitation.streams.add(*streams)
    return invitation


@dataclass
class CampaignContestsImportState:
    campaign: Campaign
    contest_type: str
    latest_task: Optional[Task] = None


IMPORT_CONTEST_RESULTS_TASK_NAME = "admission.tasks.import_campaign_contest_results"


# TODO: add tests
def create_contest_results_import_task(
    campaign: int, contest_type: int, author: User
) -> Task:
    # Don't save a new record if an unprocessed task with the same
    # parameters exists
    task = Task.build(
        task_name=IMPORT_CONTEST_RESULTS_TASK_NAME,
        kwargs={"campaign_id": campaign, "contest_type": contest_type},
        creator=author,
    )
    same_task_in_a_queue = (
        Task.objects.unlocked(get_now_utc())
        .filter(
            processed_at__isnull=True,
            task_name=task.task_name,
            task_params=task.task_params,
            task_hash=task.task_hash,
        )
        .order_by("-id")
        .first()
    )
    if same_task_in_a_queue is None:
        task.save()
    else:
        task = same_task_in_a_queue
    return task


# TODO: add test
def get_latest_contest_results_task(
    campaign: Campaign, contest_type: int
) -> Optional[Task]:
    if contest_type not in ContestTypes.values:
        raise ValidationError("Unknown contest type", code="invalid")
    return (
        Task.objects.get_task(
            IMPORT_CONTEST_RESULTS_TASK_NAME,
            kwargs={"campaign_id": campaign.pk, "contest_type": contest_type},
        )
        .order_by("-id")
        .first()
    )


def import_campaign_contest_results(*, campaign: Campaign, model_class):
    api = YandexContestAPI(access_token=campaign.access_token)
    on_scoreboard_total = 0
    updated_total = 0
    for contest in campaign.contests.filter(type=model_class.CONTEST_TYPE):
        logger.debug(f"Starting processing contest {contest.pk}")
        on_scoreboard, updated = model_class.import_scores(api=api, contest=contest)
        on_scoreboard_total += on_scoreboard
        updated_total += updated
        logger.debug(f"Scoreboard total = {on_scoreboard}")
        logger.debug(f"Updated = {updated}")
    return on_scoreboard_total, updated_total


def import_exam_results(*, campaign: Campaign):
    import_campaign_contest_results(campaign=campaign, model_class=Exam)


def get_streams(
    invitation: InterviewInvitation,
) -> Dict[InterviewStream, List[InterviewSlot]]:
    """
    Returns streams related to the invitation where
    slots are sorted by time in ASC order.
    """
    slots = (
        InterviewSlot.objects.filter(stream__interview_invitations=invitation)
        .select_related("stream__interview_format", "stream__venue__city")
        .order_by("stream__date", "start_at")
    )
    bucket = bucketize(slots, key=lambda s: s.stream)

    return {stream: slots for stream, slots in bucket.items() if stream.slots_free_count != 0}


# TODO: change exception type
class InterviewCreateError(APIException):
    pass


def decline_interview_invitation(invitation: InterviewInvitation):
    if invitation.is_expired:
        raise ValidationError("Interview Invitation is expired", code="expired")
    is_unprocessed_invitation = (
        invitation.status == InterviewInvitationStatuses.NO_RESPONSE
    )
    if not is_unprocessed_invitation:
        raise ValidationError("Status transition is not supported", code="malformed")
    invitation.status = InterviewInvitationStatuses.DECLINED
    invitation.save(update_fields=["status"])


def accept_interview_invitation(
    invitation: InterviewInvitation, slot_id: int
) -> Interview:
    """
    Creates interview, occupies slot and sends confirmation via email.

    It is allowed to accept only ongoing unprocessed invitation.
    """
    # Checks for more detailed errors
    if invitation.is_accepted:
        # Interview was created but reassigned to another participant
        if invitation.applicant_id != invitation.interview.applicant_id:
            code = "corrupted"
        else:
            code = "accepted"  # by invited participant
        raise ValidationError("Приглашение уже принято", code=code)
    elif invitation.is_expired:
        raise ValidationError("Приглашение больше не актуально", code="expired")
    is_unprocessed_invitation = (
        invitation.status == InterviewInvitationStatuses.NO_RESPONSE
    )
    if not is_unprocessed_invitation:
        raise ValidationError(
            f"You can't accept invitation with {invitation.status} status",
            code="malformed",
        )

    try:
        slot = InterviewSlot.objects.get(pk=slot_id)
    except InterviewSlot.DoesNotExist:
        raise NotFound(_("Interview slot not found"))
    # TODO: What if slot is occupied
    if slot.stream_id not in (s.id for s in invitation.streams.all()):
        raise ValidationError(_("Interview slot is not associated with the invitation"))

    interview = Interview(
        applicant=invitation.applicant,
        status=Interview.APPROVED,
        section=slot.stream.section,
        format=slot.stream.format,
        venue=slot.stream.venue,
        date=slot.datetime_local,
        duration=slot.stream.duration
    )
    with transaction.atomic():
        sid = transaction.savepoint()
        interview.save()
        is_slot_has_taken = InterviewSlot.objects.lock(slot, interview)
        if not is_slot_has_taken:
            transaction.savepoint_rollback(sid)
            raise InterviewCreateError(
                "Извините, но слот уже был занят другим участником. "
                "Выберите другое время и повторите попытку.",
                code="slot_occupied",
            )
        interview.interviewers.set(slot.stream.interviewers.all())
        # FIXME: delay or remove .on_commit
        transaction.on_commit(
            lambda: slot.stream.compute_fields("slots_occupied_count")
        )
        EmailQueueService.generate_interview_confirmation(interview, slot.stream)
        EmailQueueService.generate_interview_reminder(interview, slot.stream)
        # Mark invitation as accepted
        (
            InterviewInvitation.objects.filter(pk=invitation.pk).update(
                interview_id=interview.id,
                status=InterviewInvitationStatuses.ACCEPTED,
                modified=timezone.now(),
            )
        )
        transaction.savepoint_commit(sid)
        return interview


def get_meeting_time(meeting_at: datetime, stream: InterviewStream):
    if stream.interview_format.format == InterviewFormats.OFFLINE:
        # Applicants have to solve some assignments before interview part
        if stream.with_assignments:
            meeting_at -= timedelta(minutes=30)
    return meeting_at


def get_acceptance_ready_to_confirm(
    *, year: int, access_key: str, filters: Optional[List[Q]] = None
) -> Optional[Acceptance]:
    """Returns acceptance object ready for confirmation by participant."""
    acceptance = get_acceptance(year=year, access_key=access_key, filters=filters)
    if not acceptance:
        return None
    if acceptance.is_expired:
        raise ValidationError(
            "Deadline for confirmation has been exceeded", code="expired"
        )
    # If acceptance is already confirmed, no need to proceed
    is_ready_for_confirmation = acceptance.status == acceptance.WAITING
    if not is_ready_for_confirmation:
        msg = (
            f"You can't confirm acceptance for studies with {acceptance.status} status"
        )
        raise ValidationError(msg, code="malformed")
    # Student profile have been created manually (e.g. by curator)
    is_student_profile_created = acceptance.applicant.user_id is not None
    if is_student_profile_created:
        raise ValidationError(
            f"Acceptance for studies is already confirmed", code="confirmed"
        )
    return acceptance


def send_email_verification_code(
    *, email_to: str, site: Site, applicant: Applicant
) -> Email:
    campaign = applicant.campaign
    plain_text = render_to_string(
        EMAIL_VERIFICATION_CODE_TEMPLATE,
        context={
            "SITE_NAME": site.name,
            "VERIFICATION_CODE": generate_verification_code(email_to, applicant),
        },
    )
    return mail.send(
        [email_to],
        sender=get_email_from(campaign),
        # TODO: replace subject/message with template
        subject="Подтверждение электронной почты",
        message=plain_text,
        render_on_delivery=False,
        priority="now",  # send immediately
        backend="ses",
    )


def generate_verification_code(email: str, applicant: Applicant) -> str:
    return email_code_generator.make_token(email, applicant)


def validate_verification_code(
    applicant: Applicant, email: str, verification_code: str
):
    return email_code_generator.check_token(email, applicant, verification_code)


@dataclass(frozen=True)
class AccountData:
    has_no_patronymic: bool
    email: str
    gender: str
    birth_date: date
    living_place: str
    phone: str
    yandex_login: str
    telegram_username: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        field_types = {field.name: field.type for field in fields(cls)}
        valid_data = {k: v for k, v in data.items() if k in field_types}
        return cls(**valid_data)


@dataclass(frozen=True)
class StudentProfileData:
    comment: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        field_types = {field.name: field.type for field in fields(cls)}
        valid_data = {k: v for k, v in data.items() if k in field_types}
        return cls(**valid_data)


def get_or_create_student_profile(
    campaign: Campaign, user: User, data: Optional[Dict[str, Any]] = None
) -> StudentProfile:
    branch = campaign.branch
    campaign_year = campaign.year
    student_profile = get_student_profile(
        user=user,
        site=branch.site,
        profile_type=StudentTypes.REGULAR,
        filters=[Q(year_of_admission=campaign_year)],
    )
    # Don't override existing student profile for this campaign since it could
    # be already changed
    if student_profile is None:
        profile_fields = {
            "profile_type": StudentTypes.REGULAR,
            "year_of_curriculum": campaign_year,
            **(data or {}),
            # Fields below are not allowed to be overwritten
            "user": user,
            "branch": branch,
            "year_of_admission": campaign_year,
        }
        student_profile = create_student_profile(**profile_fields)
    return student_profile


def create_student(
    acceptance: Acceptance,
    account_data: AccountData,
    profile_data: StudentProfileData
) -> User:
    """
    Creates new user account or merges with the existing one, then creates
    student profile.

    Make sure email is verified since merging operation overwrites
    data for existing account.
    """
    email = account_data.email
    applicant: Applicant = acceptance.applicant
    branch = applicant.campaign.branch
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        user = create_account(
            username=generate_username_from_email(email),
            # User can't reset password if it's set to `None`
            password=User.objects.make_random_password(),
            email=email,
            gender=account_data.gender,
            time_zone=branch.time_zone,
            is_active=True
        )
    user.workplace = applicant.workplace or ""
    user.branch = branch
    user.first_name = applicant.first_name
    user.last_name = applicant.last_name
    user.patronymic = "" if account_data.has_no_patronymic else applicant.patronymic
    user.photo = applicant.photo
    user.gave_permission_at = user.date_joined
    # dataclasses.asdict raises `cannot pickle '_io.BufferedRandom' object`
    account_fields = {field.name for field in fields(AccountData)}
    for name in account_fields:
        setattr(user, name, getattr(account_data, name))
    user.save()
    student_data = {
        "level_of_education_on_admission": applicant.level_of_education,
        "level_of_education_on_admission_other": applicant.level_of_education_other,
        "university": applicant.get_university_display() if applicant.university else applicant.university_other,
        "faculty": applicant.faculty,
        "diploma_degree": applicant.diploma_degree,
        "graduation_year": applicant.year_of_graduation,
        "new_track": applicant.new_track,
        **asdict(profile_data)
    }
    get_or_create_student_profile(applicant.campaign, user, data=student_data)
    applicant.user = user
    applicant.save(update_fields=["user"])
    acceptance.status = Acceptance.CONFIRMED
    acceptance.save(update_fields=["status"])
    return user


def create_student_from_applicant(applicant: Applicant):
    """
    Creates new model or override existent with data from application form.
    """
    branch = applicant.campaign.branch
    try:
        user = User.objects.get(email=applicant.email)
    except User.DoesNotExist:
        user = create_account(
            username=generate_username_from_email(applicant.email),
            # User can't reset password if it's set to `None`
            password=User.objects.make_random_password(),
            email=applicant.email,
            gender=GenderTypes.OTHER,
            time_zone=branch.time_zone,
            is_active=True,
        )
    user.first_name = applicant.first_name
    user.last_name = applicant.last_name
    user.patronymic = applicant.patronymic if applicant.patronymic else ""
    user.phone = applicant.phone
    user.workplace = applicant.workplace if applicant.workplace else ""
    # Social accounts info
    try:
        user.stepic_id = int(applicant.stepic_id)
    except (TypeError, ValueError):
        pass
    user.yandex_login = applicant.yandex_login if applicant.yandex_login else ""
    # For github.com store part after github.com/
    if applicant.github_login:
        user.github_login = applicant.github_login.split("github.com/", maxsplit=1)[-1]
    user.save()
    student_data = {
        "year_of_curriculum": applicant.campaign.year,
        "level_of_education_on_admission": applicant.level_of_education,
        "university": applicant.get_university_display(),
    }
    get_or_create_student_profile(applicant.campaign, user, data=student_data)
    return user


class EmailQueueService:
    @staticmethod
    def new_registration(applicant: Applicant) -> Email:
        campaign = applicant.campaign
        return mail.send(
            [applicant.email],
            sender=get_email_from(campaign),
            template=campaign.template_registration,
            context={
                "FIRST_NAME": applicant.first_name,
                "SURNAME": applicant.last_name,
                "PATRONYMIC": applicant.patronymic if applicant.patronymic else "",
                "EMAIL": applicant.email,
                "BRANCH": campaign.branch.name,
                "PHONE": applicant.phone,
                "CONTEST_ID": applicant.online_test.yandex_contest_id,
                "YANDEX_LOGIN": applicant.yandex_login,
            },
            render_on_delivery=False,
            backend="ses",
        )

    @staticmethod
    def new_exam_invitation(
        applicant: Applicant, allow_duplicates=False
    ) -> Tuple[Email, bool]:
        recipient = applicant.email
        template_name = applicant.campaign.template_exam_invitation
        template = get_email_template(template_name)
        if not allow_duplicates:
            latest_email = (
                Email.objects.filter(to=recipient, template=template)
                .order_by("-pk")
                .first()
            )
            if latest_email:
                return latest_email, False
        return (
            mail.send(
                [recipient],
                sender=get_email_from(applicant.campaign),
                template=template,
                context={
                    "CONTEST_ID": applicant.exam.yandex_contest_id,
                    "YANDEX_LOGIN": applicant.yandex_login,
                },
                render_on_delivery=True,
                backend="ses",
            ),
            True,
        )

    @staticmethod
    def generate_interview_invitation(
        interview_invitation: InterviewInvitation,
        streams: List[InterviewStream],
        url_builder: Callable[[str], str] = None,
    ) -> Email:
        streams_context = []
        for stream in streams:
            with translation.override("ru"):
                date = date_format(stream.date, "j E")
            s = {
                "CITY": stream.venue.city.name,
                "FORMAT": stream.format,
                "SECTION": stream.get_section_display(),
                "DATE": date,
                "VENUE": stream.venue.name,
                "WITH_ASSIGNMENTS": stream.with_assignments,
                "DIRECTIONS": stream.venue.directions,
            }
            streams_context.append(s)
        campaign = interview_invitation.applicant.campaign
        secret_link = interview_invitation.get_absolute_url()
        if url_builder:
            secret_link = url_builder(secret_link)
        context = {
            "BRANCH": campaign.branch.name,
            "SECRET_LINK": secret_link,
            "STREAMS": streams_context,
        }
        return mail.send(
            [interview_invitation.applicant.email],
            sender=get_email_from(campaign),
            template=campaign.template_appointment,
            context=context,
            render_on_delivery=False,
            backend="ses",
        )

    # noinspection DuplicatedCode
    @staticmethod
    def generate_interview_confirmation(
        interview: Interview, stream: InterviewStream
    ) -> Optional[Email]:
        interview_format = stream.interview_format
        if interview_format.confirmation_template_id is None:
            return None
        campaign = interview.applicant.campaign
        meeting_at = get_meeting_time(interview.date_local(), stream)
        with translation.override("ru"):
            date = date_format(meeting_at, "j E")
        context = {
            "BRANCH": campaign.branch.name,
            "SECTION": interview.get_section_display(),
            "DATE": date,
            "TIME": meeting_at.strftime("%H:%M"),
            "DIRECTIONS": stream.venue.directions,
        }
        is_online = stream.format == InterviewFormats.ONLINE
        if stream.with_assignments and is_online:
            public_url = interview.get_public_assignments_url()
            context["ASSIGNMENTS_LINK"] = public_url
        return mail.send(
            [interview.applicant.email],
            sender=get_email_from(campaign),
            template=interview_format.confirmation_template,
            context=context,
            render_on_delivery=False,
            backend="ses",
        )

    @staticmethod
    def generate_interview_reminder(
        interview: Interview, stream: InterviewStream
    ) -> None:
        today = timezone.now()
        interview_format = stream.interview_format
        scheduled_time = interview.date - interview_format.remind_before_start
        # It's not late to send a reminder
        if scheduled_time > today:
            campaign = interview.applicant.campaign
            meeting_at = get_meeting_time(interview.date_local(), stream)
            context = {
                "BRANCH": campaign.branch.name,
                "SECTION": interview.get_section_display(),
                "DATE": meeting_at.strftime(DATE_FORMAT_RU),
                "TIME": meeting_at.strftime("%H:%M"),
                "DIRECTIONS": stream.venue.directions,
            }
            is_online = stream.format == InterviewFormats.ONLINE
            if stream.with_assignments and is_online:
                public_url = interview.get_public_assignments_url()
                context["ASSIGNMENTS_LINK"] = public_url
            mail.send(
                [interview.applicant.email],
                scheduled_time=scheduled_time,
                sender=get_email_from(campaign),
                template=interview_format.reminder_template,
                context=context,
                # Rendering on delivery stores template id and allowing
                # filtering emails in the future
                render_on_delivery=True,
                backend="ses",
            )

    @staticmethod
    def remove_interview_reminder(interview: Interview) -> None:
        slots = InterviewSlot.objects.filter(interview=interview).select_related(
            "stream", "stream__interview_format"
        )
        for slot in slots:
            campaign = interview.applicant.campaign
            interview_format = slot.stream.interview_format
            stream = slot.stream
            meeting_at = get_meeting_time(interview.date_local(), stream)
            expected_context_json = {
                "BRANCH": campaign.branch.name,
                "SECTION": interview.get_section_display(),
                "DATE": meeting_at.strftime(DATE_FORMAT_RU),
                "TIME": meeting_at.strftime("%H:%M"),
                "DIRECTIONS": stream.venue.directions,
            }
            (
                Email.objects.filter(
                    template_id=interview_format.reminder_template_id,
                    to=interview.applicant.email,
                    context=expected_context_json,
                )
                .exclude(status=EMAIL_STATUS.sent)
                .delete()
            )

    @staticmethod
    def generate_interview_feedback_email(interview: Interview) -> None:
        if interview.status != interview.COMPLETED:
            return
        campaign = interview.applicant.campaign
        if not campaign.template_interview_feedback_id:
            return
        interview_date = interview.date_local()
        # It will be send immediately if time is expired
        scheduled_time = interview_date.replace(
            hour=21, minute=0, second=0, microsecond=0
        )
        recipients = [interview.applicant.email]
        try:
            # Update scheduled_time if a feedback task in a queue is
            # not completed
            email_identifiers = {
                "template_id": campaign.template_interview_feedback_id,
                "to": recipients,
            }
            email = Email.objects.get(**email_identifiers)
            if email.status != EMAIL_STATUS.sent:
                (
                    Email.objects.filter(**email_identifiers).update(
                        scheduled_time=scheduled_time
                    )
                )
        except Email.DoesNotExist:
            email_from = get_email_from(campaign)
            mail.send(
                recipients,
                scheduled_time=scheduled_time,
                sender=email_from,
                template=campaign.template_interview_feedback,
                context={
                    "BRANCH": interview.applicant.campaign.branch.name,
                    "SECTION": interview.get_section_display(),
                },
                # Render on delivery, we have no really big amount of
                # emails to think about saving CPU time
                render_on_delivery=True,
                backend="ses",
            )

    @staticmethod
    def remove_interview_feedback_emails(interview: Interview):
        campaign = interview.applicant.campaign
        (
            Email.objects.filter(
                template_id=campaign.template_interview_feedback_id,
                to=interview.applicant.email,
            )
            .exclude(status=EMAIL_STATUS.sent)
            .delete()
        )

    @staticmethod
    def time_to_start_yandex_contest(
        *, campaign: Campaign, template: EmailTemplate, participants
    ):
        email_from = get_email_from(campaign)
        generated = 0
        for participant in participants:
            recipients = [participant["applicant__email"]]
            if not Email.objects.filter(to=recipients, template=template).exists():
                mail.send(
                    recipients,
                    sender=email_from,
                    template=template,
                    context={
                        "CONTEST_ID": participant["yandex_contest_id"],
                        "YANDEX_LOGIN": participant["applicant__yandex_login"],
                    },
                    render_on_delivery=True,
                    backend="ses",
                )
                generated += 1
        return generated
