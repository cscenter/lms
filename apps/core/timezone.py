import datetime
from typing import NewType, Union

import pytz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


def city_aware_to_naive(value, instance):
    """
    Convert aware datetime to naive for display.
    """
    if settings.USE_TZ and value is not None and timezone.is_aware(value):
        if not hasattr(instance, "get_timezone"):
            raise NotImplementedError("Implement `get_timezone` method "
                                      "for %s model" % str(instance.__class__))
        instance_timezone = instance.get_timezone()
        return timezone.make_naive(value, instance_timezone)
    return value


def naive_to_city_aware(value, instance):
    """
    When time zone support is enabled, convert naive datetime to aware.
    """
    if settings.USE_TZ and value is not None and timezone.is_naive(value):
        try:
            instance_tz = instance.get_timezone()
        except ObjectDoesNotExist:
            # Until city aware field is empty, we can't determine timezone
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


CityCode = NewType('CityCode', str)
Timezone = NewType('Timezone', datetime.tzinfo)
TzAware = Union[Timezone, CityCode]


def now_local(tz_aware: TzAware) -> datetime.datetime:
    if not isinstance(tz_aware, datetime.tzinfo):
        tz_aware = settings.TIME_ZONES[tz_aware]
    return timezone.localtime(timezone.now(), timezone=tz_aware)
