import datetime

from django.conf import settings
from django.utils import timezone

from core.timezone.models import TimezoneAwareModel
from core.timezone.typing import Timezone


def aware_to_naive(value, instance: TimezoneAwareModel):
    """
    Make an aware datetime.datetime naive in a time zone of the given instance
    """
    if settings.USE_TZ and value is not None and timezone.is_aware(value):
        instance_timezone = instance.get_timezone()
        return timezone.make_naive(value, instance_timezone)
    return value


def now_local(tz: Timezone) -> datetime.datetime:
    return timezone.localtime(timezone.now(), timezone=tz)
