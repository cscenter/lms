import logging
from datetime import datetime, timedelta

from django.utils import timezone

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
