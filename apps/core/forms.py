from crispy_forms.layout import Button, Submit, Div
from django import forms
from django.contrib.postgres.forms import JSONField
from django.utils.translation import ugettext_lazy as _
from prettyjson import PrettyJSONWidget

CANCEL_BUTTON = Button('cancel', _('Cancel'),
                       onclick='history.go(-1);',
                       css_class="btn btn-default")
SUBMIT_BUTTON = Submit('save', _('Save'))
CANCEL_SAVE_PAIR = Div(CANCEL_BUTTON, SUBMIT_BUTTON, css_class="pull-right")


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


class PrettyJSONField(JSONField):
    widget = PrettyJSONWidget
