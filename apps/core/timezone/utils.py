from datetime import datetime
from typing import Optional

from babel.dates import get_timezone_gmt

from django.conf import settings
from django.utils import timezone

from core.timezone.typing import Timezone

__all__ = ['now_local', 'get_now_utc', 'get_gmt']


# TODO: Does None actually make sense as a value here?
def now_local(tz: Optional[Timezone]) -> datetime:
    return timezone.localtime(timezone.now(), timezone=tz)


def get_now_utc() -> datetime:
    """Returns current time in UTC"""
    return datetime.now(timezone.utc)


def get_gmt(tz: Timezone) -> str:
    """
    Returns string indicating current offset from GMT for the timezone
    associated with the given `datetime` object.
    """
    dt = get_now_utc()
    return get_timezone_gmt(dt.astimezone(tz), locale=settings.LANGUAGE_CODE)
