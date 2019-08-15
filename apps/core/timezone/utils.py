import datetime

import pytz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

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


# FIXME: not generic, move to admin.py
def naive_to_aware(value, instance: TimezoneAwareModel):
    """
    Make a naive datetime.datetime in a given instance time zone aware.
    """
    if settings.USE_TZ and value is not None and timezone.is_naive(value):
        try:
            instance_tz = instance.get_timezone()
        except ObjectDoesNotExist:
            # Can't retrieve timezone until timezone aware field is empty
            instance_tz = pytz.UTC
        try:
            return timezone.make_aware(value, instance_tz)
        except Exception as exc:
            msg = _(
                '%(datetime)s couldn\'t be interpreted in time zone '
                '%(instance_tz)s; it may be ambiguous or it may not exist.'
            )
            params = {'datetime': value, 'instance_tz': instance_tz}
            raise ValidationError(
                msg,
                code='ambiguous_timezone',
                params=params) from exc
    return value


def now_local(tz: Timezone) -> datetime.datetime:
    return timezone.localtime(timezone.now(), timezone=tz)
