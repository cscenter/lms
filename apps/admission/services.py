from datetime import datetime, timedelta
from operator import attrgetter
from typing import List, Optional, Tuple

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone, formats, translation
from django.utils.formats import date_format
from post_office import mail
from post_office.models import EmailTemplate, Email, STATUS as EMAIL_STATUS
from post_office.utils import get_email_template

from admission.constants import INVITATION_EXPIRED_IN_HOURS, \
    INTERVIEW_FEEDBACK_TEMPLATE, InterviewFormats
from admission.models import InterviewStream, InterviewInvitation, \
    Applicant, Campaign, Exam, Interview, InterviewSlot
from admission.utils import logger
from api.providers.yandex_contest import YandexContestAPI
from core.timezone.constants import DATE_FORMAT_RU
from learning.services import create_student_profile, get_student_profile
from users.models import User, StudentProfile, StudentTypes


def get_email_from(campaign: Campaign, default=None):
    if campaign.branch.site.domain == 'compscicenter.ru':
        return 'CS центр <info@compscicenter.ru>'
    return default or settings.DEFAULT_FROM_EMAIL


def create_invitation(streams: List[InterviewStream], applicant: Applicant):
    """Create invitation and send email to applicant."""
    streams = list(streams)  # Queryset -> list
    first_stream = min(streams, key=attrgetter('date'))
    tz = first_stream.get_timezone()
    first_day_interview_naive = datetime.combine(first_stream.date,
                                                 datetime.min.time())
    first_day_interview = tz.localize(first_day_interview_naive)
    # Calculate deadline for invitation. It can't be later than 00:00
    # of the first interview day
    expired_in_hours = INVITATION_EXPIRED_IN_HOURS
    expired_at = timezone.now() + timedelta(hours=expired_in_hours)
    expired_at = min(expired_at, first_day_interview)
    invitation = InterviewInvitation(applicant=applicant,
                                     expired_at=expired_at)
    with transaction.atomic():
        invitation.save()
        invitation.streams.add(*streams)
        EmailQueueService.generate_interview_invitation(invitation)


def import_campaign_contest_results(*, campaign: Campaign, model_class):
    api = YandexContestAPI(access_token=campaign.access_token)
    on_scoreboard_total = 0
    updated_total = 0
    for contest in campaign.contests.filter(type=model_class.CONTEST_TYPE):
        logger.debug(f"Starting processing contest {contest.pk}")
        on_scoreboard, updated = model_class.import_results(api, contest)
        on_scoreboard_total += on_scoreboard
        updated_total += updated
        logger.debug(f"Scoreboard total = {on_scoreboard}")
        logger.debug(f"Updated = {updated}")
    return on_scoreboard_total, updated_total


def import_exam_results(*, campaign: Campaign):
    import_campaign_contest_results(campaign=campaign, model_class=Exam)


class UsernameError(Exception):
    """Raise this exception if fail to create a unique username"""
    pass


def create_student_from_applicant(applicant):
    """
    Creates new model or override existent with data from application form.
    """
    branch = applicant.campaign.branch
    try:
        user = User.objects.get(email=applicant.email)
    except User.DoesNotExist:
        username = applicant.email.split("@", maxsplit=1)[0]
        if User.objects.filter(username=username).exists():
            username = User.generate_random_username(attempts=5)
        if not username:
            raise UsernameError(f"Имя {username} уже занято. "
                                f"Cлучайное имя сгенерировать не удалось")
        random_password = User.objects.make_random_password()
        user = User.objects.create_user(username=username,
                                        email=applicant.email,
                                        time_zone=branch.time_zone,
                                        password=random_password)
    campaign_year = applicant.campaign.year
    student_profile = get_student_profile(
        user=user, site=branch.site,
        profile_type=StudentTypes.REGULAR,
        filters=[Q(year_of_admission=campaign_year)])
    # Don't override existing student profile for this campaign since it could
    # be already changed
    if student_profile is None:
        create_student_profile(
            user=user, branch=branch,
            profile_type=StudentTypes.REGULAR,
            year_of_admission=campaign_year,
            year_of_curriculum=campaign_year,
            level_of_education_on_admission=applicant.level_of_education,
            university=applicant.university.name)
    user.first_name = applicant.first_name
    user.last_name = applicant.surname
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
        user.github_login = applicant.github_login.split("github.com/",
                                                         maxsplit=1)[-1]
    user.save()
    return user


def get_meeting_time(meeting_at: datetime, stream: InterviewStream):
    if stream.interview_format.format == InterviewFormats.OFFLINE:
        # Applicants have to solve some assignments before interview part
        if stream.with_assignments:
            meeting_at -= timedelta(minutes=30)
    return meeting_at


class EmailQueueService:
    """
    Adds email to the db queue instead of sending email directly.
    """
    @staticmethod
    def new_registration(applicant: Applicant) -> Email:
        return mail.send(
            [applicant.email],
            sender='CS центр <info@compscicenter.ru>',
            template=applicant.campaign.template_registration,
            context={
                'FIRST_NAME': applicant.first_name,
                'SURNAME': applicant.surname,
                'PATRONYMIC': applicant.patronymic if applicant.patronymic else "",
                'EMAIL': applicant.email,
                'BRANCH': applicant.campaign.branch.name,
                'PHONE': applicant.phone,
                'CONTEST_ID': applicant.online_test.yandex_contest_id,
                'YANDEX_LOGIN': applicant.yandex_login,
            },
            render_on_delivery=False,
            backend='ses',
        )

    @staticmethod
    def new_exam_invitation(applicant: Applicant,
                            allow_duplicates=False) -> Tuple[Email, bool]:
        recipient = applicant.email
        template_name = applicant.campaign.template_exam_invitation
        template = get_email_template(template_name)
        if not allow_duplicates:
            latest_email = (Email.objects
                            .filter(to=recipient, template=template)
                            .order_by('-pk')
                            .first())
            if latest_email:
                return latest_email, False
        return mail.send(
            [recipient],
            sender=get_email_from(applicant.campaign),
            template=template,
            context={
                'CONTEST_ID': applicant.exam.yandex_contest_id,
                'YANDEX_LOGIN': applicant.yandex_login,
            },
            render_on_delivery=True,
            backend='ses',
        ), True

    @staticmethod
    def generate_interview_invitation(interview_invitation) -> Email:
        streams = []
        for stream in interview_invitation.streams.select_related("venue").all():
            with translation.override('ru'):
                date = date_format(stream.date, "j E")
            s = {
                "CITY": stream.venue.city.name,
                "FORMAT": stream.format,
                "DATE": date,
                "VENUE": stream.venue.name,
                "WITH_ASSIGNMENTS": stream.with_assignments,
                "DIRECTIONS": stream.venue.directions,
            }
            streams.append(s)
        campaign = interview_invitation.applicant.campaign
        context = {
            "BRANCH": campaign.branch.name,
            "SECRET_LINK": interview_invitation.get_absolute_url(),
            "STREAMS": streams
        }
        return mail.send(
            [interview_invitation.applicant.email],
            sender=get_email_from(campaign),
            template=campaign.template_appointment,
            context=context,
            render_on_delivery=False,
            backend='ses',
        )

    # noinspection DuplicatedCode
    @staticmethod
    def generate_interview_confirmation(interview: Interview,
                                        stream: InterviewStream):
        interview_format = stream.interview_format
        if interview_format.confirmation_template_id is None:
            return
        campaign = interview.applicant.campaign
        meeting_at = get_meeting_time(interview.date_local(), stream)
        with translation.override('ru'):
            date = date_format(meeting_at, "j E")
        context = {
            "BRANCH": campaign.branch.name,
            "DATE": date,
            "TIME": meeting_at.strftime("%H:%M"),
            "DIRECTIONS": stream.venue.directions
        }
        is_online = (stream.format == InterviewFormats.ONLINE)
        if stream.with_assignments and is_online:
            public_url = interview.get_public_assignments_url()
            context['ASSIGNMENTS_LINK'] = public_url
        return mail.send(
            [interview.applicant.email],
            sender=get_email_from(campaign),
            template=interview_format.confirmation_template,
            context=context,
            render_on_delivery=False,
            backend='ses',
        )

    @staticmethod
    def generate_interview_reminder(interview: Interview,
                                    stream: InterviewStream) -> Optional[Email]:
        today = timezone.now()
        interview_format = stream.interview_format
        scheduled_time = interview.date - interview_format.remind_before_start
        # It's not late to send a reminder
        if scheduled_time > today:
            campaign = interview.applicant.campaign
            meeting_at = get_meeting_time(interview.date_local(), stream)
            context = {
                "BRANCH": campaign.branch.name,
                "DATE": meeting_at.strftime(DATE_FORMAT_RU),
                "TIME": meeting_at.strftime("%H:%M"),
                "DIRECTIONS": stream.venue.directions
            }
            is_online = (stream.format == InterviewFormats.ONLINE)
            if stream.with_assignments and is_online:
                public_url = interview.get_public_assignments_url()
                context['ASSIGNMENTS_LINK'] = public_url
            return mail.send(
                [interview.applicant.email],
                scheduled_time=scheduled_time,
                sender=get_email_from(campaign),
                template=interview_format.reminder_template,
                context=context,
                # Rendering on delivery stores template id and allowing
                # filtering emails in the future
                render_on_delivery=True,
                backend='ses',
            )

    @staticmethod
    def remove_interview_reminder(interview: Interview):
        slots = (InterviewSlot.objects
                 .filter(interview=interview)
                 .select_related('stream', 'stream__interview_format'))
        for slot in slots:
            interview_format = slot.stream.interview_format
            (Email.objects
             .filter(template_id=interview_format.reminder_template_id,
                     to=interview.applicant.email)
             .exclude(status=EMAIL_STATUS.sent)
             .delete())

    @staticmethod
    def generate_interview_feedback_email(interview) -> Optional[Email]:
        if interview.status != interview.COMPLETED:
            return
        # Fail silently if template not found
        template_name = INTERVIEW_FEEDBACK_TEMPLATE
        try:
            template = EmailTemplate.objects.get(name=template_name)
        except EmailTemplate.DoesNotExist:
            logger.error("Template with name {} not found".format(template_name))
            return
        interview_date = interview.date_local()
        # It will be send immediately if time is expired
        scheduled_time = interview_date.replace(hour=21, minute=0, second=0,
                                                microsecond=0)
        recipients = [interview.applicant.email]
        try:
            # Update scheduled_time if a feedback task in a queue is
            # not completed
            email_identifiers = {
                "template__name": INTERVIEW_FEEDBACK_TEMPLATE,
                "to": recipients
            }
            email = Email.objects.get(**email_identifiers)
            if email.status != EMAIL_STATUS.sent:
                (Email.objects
                 .filter(**email_identifiers)
                 .update(scheduled_time=scheduled_time))
        except Email.DoesNotExist:
            return mail.send(
                recipients,
                scheduled_time=scheduled_time,
                sender='info@compscicenter.ru',
                template=template,
                context={
                    "BRANCH": interview.applicant.campaign.branch.name,
                },
                # Render on delivery, we have no really big amount of
                # emails to think about saving CPU time
                render_on_delivery=True,
                backend='ses',
            )

    @staticmethod
    def remove_interview_feedback_emails(interview):
        (Email.objects
         .filter(template__name=INTERVIEW_FEEDBACK_TEMPLATE,
                 to=interview.applicant.email)
         .exclude(status=EMAIL_STATUS.sent)
         .delete())
