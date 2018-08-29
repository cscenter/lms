from __future__ import absolute_import, unicode_literals

from captcha.fields import ReCaptchaField
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _

from registration.forms import RegistrationFormUniqueEmail
from users.models import CSCUser


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
        group = Group.objects.get(pk=CSCUser.group.STUDENT_CLUB)
        user.groups.add(group)
        return user
