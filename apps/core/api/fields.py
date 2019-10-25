from rest_framework.fields import DecimalField


class ScoreField(DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 6)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("min_value", 3)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        """Allow using `1.23` and `1,23` string values"""
        if data and hasattr(data, "replace"):
            data = data.replace(",", ".")
        return super().to_internal_value(data)
