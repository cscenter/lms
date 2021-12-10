from typing import Optional

from rest_framework import serializers


class ScoreField(serializers.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 6)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("min_value", 0)
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        """Allow using `1.23` and `1,23` string values"""
        if data and hasattr(data, "replace"):
            data = data.replace(",", ".")
        return super().to_internal_value(data)


class CharSeparatedField(serializers.CharField):
    def __init__(self, separator: Optional[str] = None, **kwargs):
        self.separator = separator or ","
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        return [s for s in super().to_internal_value(data).split(self.separator) if s]

    def to_representation(self, data):
        if isinstance(data, list):
            return self.separator.join(data)
        return super().to_representation(data)
