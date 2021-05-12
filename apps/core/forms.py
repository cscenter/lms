from crispy_forms.layout import Button, Div, Submit
from prettyjson import PrettyJSONWidget

from django import forms
from django.utils.translation import gettext_lazy as _

CANCEL_BUTTON = Button('cancel', _('Cancel'),
                       onclick='history.go(-1);',
                       css_class="btn btn-default")
SUBMIT_BUTTON = Submit('save', _('Save'))
CANCEL_SAVE_PAIR = Div(CANCEL_BUTTON, SUBMIT_BUTTON, css_class="pull-right")


class ScoreField(forms.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("min_value", 0)
        kwargs.setdefault("max_digits", 6)
        kwargs.setdefault("decimal_places", 2)
        widget = forms.NumberInput(attrs={'min': 0, 'step': 0.01})
        kwargs.setdefault("widget", widget)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        """Allow using `1.23` and `1,23` string values"""
        if value not in self.empty_values and hasattr(value, "replace"):
            value = value.replace(",", ".")
        return super().clean(value)


class PrettyJSONField(forms.JSONField):
    widget = PrettyJSONWidget
