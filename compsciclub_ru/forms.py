from captcha.fields import ReCaptchaField
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.utils.translation import ugettext_lazy as _
from registration.forms import RegistrationFormUniqueEmail

from users.constants import AcademicRoles


class RegistrationUniqueEmailAndUsernameForm(RegistrationFormUniqueEmail):
    captcha = ReCaptchaField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit('submit', _('Submit')))
        )

    def save(self, commit=True):
        user = super().save(commit)
        user.add_group(AcademicRoles.STUDENT)
        return user
