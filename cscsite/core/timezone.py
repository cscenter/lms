import datetime
from typing import NewType, Union

import pytz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


def city_aware_to_naive(value, instance):
    """
    Convert aware datetime to naive in the timezone of the city for display.
    """
    if settings.USE_TZ and value is not None and timezone.is_aware(value):
        if not hasattr(instance, "get_city_timezone"):
            raise NotImplementedError("Implement `get_city_timezone` method "
                                      "for %s model" % str(instance.__class__))
        city_timezone = instance.get_city_timezone()
        return timezone.make_naive(value, city_timezone)
    return value


def naive_to_city_aware(value, instance):
    """
    When time zone support is enabled, convert naive datetime to aware.
    """
    if settings.USE_TZ and value is not None and timezone.is_naive(value):
        try:
            city_timezone = instance.get_city_timezone()
        except ObjectDoesNotExist:
            # Until city aware field is empty, we can't determine timezone
            city_timezone = pytz.UTC
        try:
            return timezone.make_aware(value, city_timezone)
        except Exception as exc:
            msg = _(
                '%(datetime)s couldn\'t be interpreted in time zone '
                '%(city_timezone)s; it may be ambiguous or it may not exist.'
            )
            params = {'datetime': value, 'city_timezone': city_timezone}
            raise ValidationError(
                msg,
                code='ambiguous_timezone',
                params=params) from exc
    return value


CityCode = NewType('CityCode', str)
Timezone = NewType('Timezone', datetime.tzinfo)


def now_local(tz_aware: Union[Timezone, CityCode]) -> datetime.datetime:
    if not isinstance(tz_aware, datetime.tzinfo):
        tz_aware = settings.TIME_ZONES[tz_aware]
    return timezone.localtime(timezone.now(), timezone=tz_aware)