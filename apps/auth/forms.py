from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from core.urls import reverse
from users import tasks
from users.constants import CSCENTER_ACCESS_ALLOWED


class UserPasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        ctx = {
            'site_name': context['site_name'],
            'email': context['email'],
            'protocol': context['protocol'],
            'domain': context['domain'],
            'uid': context['uid'],
            'token': context['token'],
        }
        tasks.send_restore_password_email.delay(
            from_email=from_email,
            to_email=to_email,
            context=ctx,
            language_code=translation.get_language())


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        required=True,
        label=_("Username"),
        widget=forms.TextInput(attrs={'autofocus': 'autofocus'}))
    password = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Password"))

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        # NOTE(Dmitry): this should be done after Users app is loaded
        # because of URL name resolutions quirks
        self.fields['password'].help_text = (
            _("You can also <a href=\"{0}\">restore your password</a>")
            .format(reverse('password_reset')))
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-xs-2'
        self.helper.field_class = 'col-xs-7'
        self.helper.layout = Layout(
            'username',
            'password',
            FormActions(Div(Submit('submit', _("Login")),
                            css_class="pull-right")))

    def is_valid(self):
        is_valid = super(LoginForm, self).is_valid()
        # Prevent login for club students on compscicenter.ru
        # FIXME: remove?
        if is_valid and settings.SITE_ID == settings.CENTER_SITE_ID:
            user = self.get_user()
            if user.is_curator:
                return is_valid
            user_roles = set(g.role for g
                             in user.groups.filter(site_id=settings.SITE_ID))
            if not user_roles.intersection(CSCENTER_ACCESS_ALLOWED):
                is_valid = False
                no_access_msg = _("You haven't enough access rights to login "
                                  "on this site. Contact curators if you think "
                                  "this is wrong.")
                self.add_error(None, ValidationError(no_access_msg))
        return is_valid
