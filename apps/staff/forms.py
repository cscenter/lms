from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Row, Submit

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.urls import reverse
from core.widgets import DateInputTextWidget
from users.models import User


class GraduationForm(forms.Form):
    graduated_on = forms.DateField(
        label=_("Date of Graduation"),
        widget=DateInputTextWidget(attrs={'class': 'datepicker'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Div('graduated_on', css_class="col-xs-4"),
            ),
            FormActions(Submit('submit', 'Сгенерировать профили'))
        )


class MergeUsersForm(forms.Form):
    major_email = forms.EmailField(
        label=_("Major User email")
    )
    minor_email = forms.EmailField(
        label=_("Minor User email")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_action = reverse("staff:merge_users")
        self.helper.layout = Layout(
            Row(
                Div('major_email', css_class="col-xs-4"),
                Div('minor_email', css_class="col-xs-4"),
            ),
            FormActions(Submit('submit', _('Merge Users'),
                               onclick="return confirm('Вы уверены? Это действие нельзя обратить');"))
        )

    def clean_major_email(self):
        major_email = self.cleaned_data.get('major_email')
        if not User.objects.filter(email__iexact=major_email).exists():
            raise ValidationError(_("There is no User with this email"))
        return major_email

    def clean_minor_email(self):
        minor_email = self.cleaned_data.get('minor_email')
        if not User.objects.filter(email__iexact=minor_email).exists():
            raise ValidationError(_("There is no User with this email"))
        return minor_email

    def clean(self):
        major_email = self.cleaned_data.get('major_email')
        minor_email = self.cleaned_data.get('minor_email')
        if major_email == minor_email:
            raise ValidationError(_("Emails must not be the same"))
