from captcha.fields import ReCaptchaField
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ChoiceField
from django.utils.translation import gettext_lazy as _
from registration.forms import RegistrationFormUniqueEmail

from users.constants import GenderTypes


class RegistrationUniqueEmailAndUsernameForm(RegistrationFormUniqueEmail):
    gender = ChoiceField(label=_("Gender"),
                         choices=[('', '---------'), *GenderTypes.choices])
    captcha = ReCaptchaField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit('submit', _('Submit')))
        )
