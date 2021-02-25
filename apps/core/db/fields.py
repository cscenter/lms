from django.core.validators import MinValueValidator
from django.db.models import DecimalField, JSONField

from core import forms
from core.db.models import normalize_score


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
