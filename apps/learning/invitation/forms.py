from captcha.fields import ReCaptchaField
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from registration.forms import RegistrationFormUniqueEmail

from django import forms
from django.utils.translation import gettext_lazy as _

from auth.forms import LoginForm
from users.models import User
from users.services import UniqueUsernameError, generate_username_from_email


class InvitationLoginForm(LoginForm):
    """
    Basic LoginForm prevent log in for users without any role.
    This form removes this restriction.
    """
    def is_valid(self):
        return super(LoginForm, self).is_valid()


class InvitationRegistrationForm(RegistrationFormUniqueEmail):
    captcha = ReCaptchaField()
    not_required = [
        "patronymic"
    ]
    class Meta:
        model = User
        fields = ("email", "branch", "last_name", "first_name", "patronymic", "gender", "telegram_username", "birth_date")


    def __init__(self, *args, invitation, **kwargs):
        super().__init__(*args, **kwargs)
        for name, value in self.fields.items():
            if name not in self.not_required:
                value.required = True

        self.fields['branch'].queryset = invitation.branches
        self.fields['telegram_username'].help_text = "@&lt;<b>username</b>&gt; в настройках профиля Telegram."\
                                                     "<br>Поставьте прочерк «-», если аккаунт отсутствует."
        self.fields['birth_date'].help_text = "Введите дату в формате DD.MM.YYYY"
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit('submit', _('Submit')))
        )

    def clean_telegram_username(self):
        telegram_username = self.cleaned_data.get("telegram_username")
        telegram_username = telegram_username.replace("@", "")
        return "" if len(telegram_username) == 1 else telegram_username

    def clean(self):
        cleaned_data = super().clean()
        if "email" in cleaned_data:
            try:
                username = generate_username_from_email(cleaned_data["email"], attempts=5)
            except UniqueUsernameError:
                raise forms.ValidationError("Username is not unique")
            cleaned_data['username'] = username
            self.instance.username = username
        return cleaned_data


class CompleteAccountForm(forms.ModelForm):
    def __init__(self, *args, invitation, **kwargs):
        instance: User = kwargs["instance"]
        kwargs["initial"] = {
            **kwargs.get("initial", {}),
            "branch": instance.branch,
        }
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        self.fields['branch'].required = True
        self.fields['branch'].queryset = invitation.branches
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit('continue', _('Continue')))
        )

    class Meta:
        model = User
        fields = ("branch", "first_name", "last_name", "patronymic")
