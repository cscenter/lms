from datetime import datetime, timedelta

from django.utils import timezone
from post_office import mail


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


def generate_interview_reminder(interview, slot):
    today = timezone.now()
    if interview.date - today > timedelta(days=1):
        meeting_at = interview.date_local()
        # Give them some time to solve proposed tasks
        if slot.stream.with_assignments:
            meeting_at -= timedelta(minutes=30)
        scheduled_time = interview.date - timedelta(days=1)
        mail.send(
            [interview.applicant.email],
            scheduled_time=scheduled_time,
            sender='info@compscicenter.ru',
            template=interview.REMINDER_TEMPLATE,
            context={
                "SUBJECT_CITY": interview.applicant.campaign.city.name,
                "DATE": meeting_at.strftime("%d.%m.%Y"),
                "TIME": meeting_at.strftime("%H:%M"),
                "DIRECTIONS": slot.stream.venue.directions
            },
            # Render on delivery, we have no really big amount of
            # emails to think about saving CPU time
            render_on_delivery=True,
            backend='ses',
        )
