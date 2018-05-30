from django.core.validators import MinValueValidator
from django.db.models import DecimalField


class GradeField(DecimalField):
    """Stores positive value with 2 decimal places"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 6)
        kwargs.setdefault("decimal_places", 2)
        validators = kwargs.pop("validators", [])
        validators.append(MinValueValidator(0))
        kwargs["validators"] = validators
        super(GradeField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        decimal_as_int = value.to_integral_value()
        if value == decimal_as_int:
            return decimal_as_int
        return value.normalize()
