from datetime import datetime, timedelta, timezone

from django.utils.timezone import localtime, now
from post_office import mail

from core.settings.base import TIME_ZONES


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
    return (datetime.combine(now(), time) - timedelta).time()


def generate_interview_reminder(interview, slot):
    """
    Сейчас этот метод работает только для таймзоны MSK!!! Сначала нужно научиться
    хранить данные из Новосибирска с учетом часового пояса. В противном
    случае мы напоминание будем отправлять с лагом в 4 часа.
    Хотя для напоминалки за 24 часа вроде не сильно критично...
    """
    if slot.stream.venue.city_id != 'spb':
        return
    # FIXME: respect timezone
    today = now()
    when = interview.date  # should be correct utc
    if when - today > timedelta(days=1):
        if slot.stream.with_assignments:
            when -= timedelta(minutes=30)

        city_code = interview.applicant.campaign.city_id
        when = localtime(when, TIME_ZONES[city_code])  # uses `normalize` inside
        scheduled_time = when - timedelta(days=1)
        mail.send(
            [interview.applicant.email],
            scheduled_time=scheduled_time,
            sender='info@compscicenter.ru',
            template=interview.REMINDER_TEMPLATE,
            context={
                "SUBJECT_CITY": interview.applicant.campaign.city.name,
                "DATE": when.strftime("%d.%m.%Y"),  # TODO: move this to template?
                "TIME": when.strftime("%H:%M"),
                "DIRECTIONS": slot.stream.venue.directions
            },
            # Render on delivery, we have no really big amount of
            # emails to think about saving CPU time
            render_on_delivery=True,
            backend='ses',
        )
