from captcha.fields import ReCaptchaField
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.utils.translation import ugettext_lazy as _
from registration.forms import RegistrationFormUniqueEmail

from auth.forms import LoginForm
from users.models import User


class InvitationLoginForm(LoginForm):
    """
    Basic LoginForm prevent log in for users without any role.
    This form removes this restriction.
    """
    def is_valid(self):
        return super(LoginForm, self).is_valid()


class InvitationRegistrationForm(RegistrationFormUniqueEmail):
    captcha = ReCaptchaField()

    class Meta:
        model = User
        fields = ("email", "last_name", "first_name", "patronymic", "gender")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit('submit', _('Submit')))
        )

    def clean(self):
        cleaned_data = super().clean()
        if "email" in cleaned_data:
            email = cleaned_data["email"]
            username = email.split("@", maxsplit=1)[0]
            if User.objects.filter(username=username).exists():
                username = User.generate_random_username(attempts=5)
            if not username:
                raise forms.ValidationError("Username is not unique")
            self.instance.username = username
        return cleaned_data


class CompleteProfileForm(forms.ModelForm):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    class Meta:
        model = User
        fields = ("first_name", "last_name", "patronymic")
