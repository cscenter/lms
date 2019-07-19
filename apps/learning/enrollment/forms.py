from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.utils.translation import ugettext_lazy as _


class CourseEnrollmentForm(forms.Form):
    reason = forms.CharField(
        label=_("Почему вы выбрали этот курс?"),
        widget=forms.Textarea(),
        required=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit('enroll', 'Записаться на курс'))
