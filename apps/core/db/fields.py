from datetime import timedelta

import pytz
from django.core import checks
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import DecimalField, JSONField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core import forms
from core.db.utils import normalize_score
from core.timezone import get_now_utc


class ScoreField(DecimalField):
    default_validators = [MinValueValidator(0)]
    """Stores positive value with 2 decimal places"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 6)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return normalize_score(value)

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", forms.ScoreField)
        return super().formfield(**kwargs)


class PrettyJSONField(JSONField):
    def formfield(self, **kwargs):
        return super(JSONField, self).formfield(**{
            'form_class': forms.PrettyJSONField,
            **kwargs,
        })


def parse_timezone_string(value) -> pytz.tzinfo.BaseTzInfo:
    try:
        return pytz.timezone(value)
    except pytz.UnknownTimeZoneError:
        raise ValidationError(_("Invalid timezone identifier"))


class TimeZoneField(models.Field):
    empty_strings_allowed = False
    description = _("A pytz timezone instance")

    def __init__(self, verbose_name=None, choices=None, **kwargs):
        # The time zones have unique names in the form "Area/Location".
        # The Area and Location names have a maximum length of 14 characters.
        # In some cases the Location is itself represented as a compound name, so max_length is 42 characters
        kwargs['max_length'] = 42
        self._default_choices = not choices
        if not choices:
            # `pytz.common_timezones` is a list of useful, current timezones.
            # It doesn't contain deprecated zones or historical zones.
            values = pytz.common_timezones
            choices_ = []
            now_utc = get_now_utc()
            zero_ = timedelta(0)
            for tz_name in values:
                # TODO: use babel.dates.get_timezone_gmt instead?
                offset = now_utc.astimezone(pytz.timezone(tz_name)).utcoffset()
                sign = "+" if offset >= zero_ else "-"
                hh_mm = str(abs(offset)).zfill(8)[:-3]
                label = f"GMT{sign}{hh_mm} {tz_name.replace('_', ' ')}"
                choices_.append((tz_name, offset, label))
            choices_.sort(key=lambda x: x[1])
            choices = [(value, label) for value, _, label in choices_]
        kwargs['choices'] = choices
        super().__init__(verbose_name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        if self._default_choices:
            del kwargs['choices']
        else:
            kwargs['choices'] = [(str(tz), name) for tz, name in kwargs['choices']]
        return name, path, args, kwargs

    def get_internal_type(self):
        return "CharField"

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return parse_timezone_string(value)

    def to_python(self, value):
        if isinstance(value, pytz.tzinfo.BaseTzInfo):
            return value
        if value is None or value == '':
            return None
        return parse_timezone_string(value)

    def get_prep_value(self, value):
        if value is None or value == '':
            return None
        if isinstance(value, pytz.tzinfo.BaseTzInfo):
            return value.zone
        return str(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def validate(self, value, model_instance):
        value_str = str(value) if value else ''
        super().validate(value_str, model_instance)

    def _check_choices(self):
        errors = super()._check_choices()
        if not errors:
            for value, label in self.choices:
                if value not in pytz.all_timezones_set:
                    return [checks.Error(
                        "'choices' contains value %s that is not a valid timezone identifier" % value,
                        obj=self,
                        id='fields.E201',
                    )]
        return errors
