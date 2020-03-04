from datetime import datetime, timedelta
from operator import attrgetter
from typing import List, Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.formats import date_format
from post_office import mail
from post_office.models import EmailTemplate, Email, STATUS as EMAIL_STATUS

from admission.constants import INVITATION_EXPIRED_IN_HOURS, \
    INTERVIEW_FEEDBACK_TEMPLATE
from admission.models import InterviewStream, InterviewInvitation, \
    Applicant
from admission.utils import logger
from core.timezone.constants import DATE_FORMAT_RU
from learning.roles import Roles
from users.models import User


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


class UsernameError(Exception):
    """Raise this exception if fail to create a unique username"""
    pass


def create_student_from_applicant(applicant):
    """
    Create new model or override existent with data from applicant form.
    """
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
                                        password=random_password,
                                        branch=applicant.campaign.branch)
    if applicant.status == Applicant.VOLUNTEER:
        user.add_group(Roles.VOLUNTEER)
    else:
        user.add_group(Roles.STUDENT)
    user.add_group(Roles.STUDENT, site_id=settings.CLUB_SITE_ID)
    # Copy data from application form to the user profile
    same_attrs = [
        "first_name",
        "phone"
    ]
    for attr_name in same_attrs:
        setattr(user, attr_name, getattr(applicant, attr_name))
    try:
        user.stepic_id = int(applicant.stepic_id)
    except (TypeError, ValueError):
        pass
    user.last_name = applicant.surname
    user.patronymic = applicant.patronymic if applicant.patronymic else ""
    user.enrollment_year = user.curriculum_year = timezone.now().year
    # Looks like the same fields below
    user.yandex_login = applicant.yandex_login if applicant.yandex_login else ""
    # For github store part after github.com/
    if applicant.github_login:
        user.github_login = applicant.github_login.split("github.com/",
                                                      maxsplit=1)[-1]
    user.workplace = applicant.workplace if applicant.workplace else ""
    user.uni_year_at_enrollment = applicant.level_of_education
    user.branch = applicant.campaign.branch
    user.university = applicant.university.name
    user.save()
    return user


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
    def generate_interview_invitation(interview_invitation) -> Email:
        streams = []
        for stream in interview_invitation.streams.select_related("venue").all():
            s = {
                "city": stream.venue.city.name,
                "date": date_format(stream.date, "j E"),
                "office": stream.venue.name,
                "with_assignments": stream.with_assignments,
                "directions": stream.venue.directions,
            }
            streams.append(s)
        context = {
            "BRANCH": interview_invitation.applicant.campaign.branch.name,
            "SECRET_LINK": interview_invitation.get_absolute_url(),
            "STREAMS": streams
        }
        return mail.send(
            [interview_invitation.applicant.email],
            sender='CS центр <info@compscicenter.ru>',
            template=interview_invitation.applicant.campaign.template_appointment,
            context=context,
            render_on_delivery=False,
            backend='ses',
        )

    @staticmethod
    def generate_interview_reminder(interview, slot) -> Optional[Email]:
        today = timezone.now()
        if interview.date - today > timedelta(days=1):
            campaign = interview.applicant.campaign
            meeting_at = interview.date_local()
            # Give them time to solve some assignments before interview part
            if slot.stream.with_assignments:
                meeting_at -= timedelta(minutes=30)
            scheduled_time = interview.date - timedelta(days=1)
            return mail.send(
                [interview.applicant.email],
                scheduled_time=scheduled_time,
                sender='info@compscicenter.ru',
                template=campaign.template_interview_reminder,
                context={
                    "BRANCH": campaign.branch.name,
                    "DATE": meeting_at.strftime(DATE_FORMAT_RU),
                    "TIME": meeting_at.strftime("%H:%M"),
                    "DIRECTIONS": slot.stream.venue.directions
                },
                # Render on delivery, we have no really big amount of
                # emails to think about saving CPU time
                render_on_delivery=True,
                backend='ses',
            )

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
