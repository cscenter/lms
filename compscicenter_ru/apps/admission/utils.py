import logging
from datetime import datetime, timedelta
from itertools import groupby

from django.utils import timezone
from post_office import mail

from admission.constants import INTERVIEW_FEEDBACK_TEMPLATE
from core.constants import DATE_FORMAT_RU

logger = logging.getLogger(__name__)


def slot_range(start_at, end_at, step):
    current = timedelta(hours=start_at.hour, minutes=start_at.minute)
    end_at = timedelta(hours=end_at.hour, minutes=end_at.minute)
    while current < end_at:
        in_datetime = datetime.min + current
        # (start_at : datetime.time, end_at: datetime.time)
        yield in_datetime.time(), (in_datetime + step).time()
        current += step


def calculate_time(time, timedelta):
    """
    We can't directly use `datetime.timedelta` with `datetime.time` object,
    convert it to `datetime.datetime` object first and after calculation
    return `time`.
    """
    return (datetime.combine(timezone.now(), time) - timedelta).time()


def generate_interview_reminder(interview, slot) -> None:
    today = timezone.now()
    if interview.date - today > timedelta(days=1):
        campaign = interview.applicant.campaign
        meeting_at = interview.date_local()
        # Give them time to solve some assignments before interview part
        if slot.stream.with_assignments:
            meeting_at -= timedelta(minutes=30)
        scheduled_time = interview.date - timedelta(days=1)
        mail.send(
            [interview.applicant.email],
            scheduled_time=scheduled_time,
            sender='info@compscicenter.ru',
            template=campaign.template_interview_reminder,
            context={
                "SUBJECT_CITY": campaign.branch.name,
                "DATE": meeting_at.strftime(DATE_FORMAT_RU),
                "TIME": meeting_at.strftime("%H:%M"),
                "DIRECTIONS": slot.stream.venue.directions
            },
            # Render on delivery, we have no really big amount of
            # emails to think about saving CPU time
            render_on_delivery=True,
            backend='ses',
        )


def generate_interview_feedback_email(interview) -> None:
    from post_office.models import EmailTemplate, Email, STATUS as EMAIL_STATUS
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
        # Update scheduled_time if feedback task in a queue and not completed
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
        mail.send(
            recipients,
            scheduled_time=scheduled_time,
            sender='info@compscicenter.ru',
            template=template,
            context={
                "SUBJECT_CITY": interview.applicant.campaign.branch.name,
            },
            # Render on delivery, we have no really big amount of
            # emails to think about saving CPU time
            render_on_delivery=True,
            backend='ses',
        )
