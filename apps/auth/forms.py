from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from auth.tasks import send_restore_password_email
from core.urls import reverse


class AsyncPasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        # XXX: separate configuration for public domain and lms (they
        # should have different SITE_ID), then it should be possible to
        # remove logic below
        domain = context['domain']
        if (settings.LMS_SUBDOMAIN and settings.RESTRICT_LOGIN_TO_LMS and
                not domain.startswith(settings.LMS_SUBDOMAIN)):
            domain = f"{settings.LMS_SUBDOMAIN}.{domain}"
        ctx = {
            'site_name': context['site_name'],
            'email': context['email'],
            'protocol': context['protocol'],
            'domain': domain,
            'uid': context['uid'],
            'token': context['token'],
        }
        send_restore_password_email.delay(
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
            .format(reverse('auth:password_reset')))
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
        is_valid = super().is_valid()
        if is_valid:
            user = self.get_user()
            # FIXME: replace with permission `can_login_on_site`
            if user.is_curator:
                return is_valid
            # User without any role doesn't have any permission to the site,
            # even with account (it could be created for the purposes
            # of another site)
            if not user.roles:
                is_valid = False
                no_access_msg = _("You haven't enough access rights to login "
                                  "on this site. Contact curators if you think "
                                  "this is wrong.")
                self.add_error(None, ValidationError(no_access_msg))
        return is_valid
