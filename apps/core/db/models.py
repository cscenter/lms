from decimal import Decimal
from typing import Optional, Union

from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator
from django.db.models import DecimalField

from core import forms


def normalize_score(value: Optional[Decimal]) -> Optional[Union[int, Decimal]]:
    """
    This method used for humanizing score value - we want to show `5`
    instead of `5.00` when it's possible.

    When decimal is provided cast it to integer. If the result is exact
    as decimal value returns integer instead of the original decimal.
    """
    if value is None:
        return value
    decimal_as_int = value.to_integral_value()
    if value == decimal_as_int:
        return decimal_as_int
    return value.normalize()


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
