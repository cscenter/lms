from django import forms


class GradeField(forms.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("min_value", 0)
        widget = forms.NumberInput(attrs={'min': 0, 'step': 0.01})
        kwargs.setdefault("widget", widget)
        super(GradeField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """Allow using `1.23` and `1,23` string values"""
        if value not in self.empty_values and hasattr(value, "replace"):
            value = value.replace(",", ".")
        return super().to_python(value)
