import logging
from typing import NamedTuple

from django_rq import job

from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template import loader
from django.utils import translation

from auth.settings import (
    EMAIL_ACTIVATION_BODY, EMAIL_ACTIVATION_SUBJECT, EMAIL_RESTORE_PASSWORD_BODY,
    EMAIL_RESTORE_PASSWORD_SUBJECT
)
from core.urls import replace_hostname, reverse

logger = logging.getLogger(__name__)


@job('high')
def send_restore_password_email(context, from_email, to_email, language_code):
    translation.activate(language_code)
    # Email subject *must not* contain newlines
    reset_url = reverse('auth:password_reset_confirm', kwargs={
        'uidb64': context['uid'],
        'token': context['token']
    })
    reset_url = replace_hostname(reset_url, context['domain'])
    context['reset_url'] = reset_url
    subject = loader.render_to_string(EMAIL_RESTORE_PASSWORD_SUBJECT, context)
    subject = ''.join(subject.splitlines())
    body = loader.render_to_string(EMAIL_RESTORE_PASSWORD_BODY, context)
    connection = get_connection(settings.POST_OFFICE['BACKENDS']['ses'])
    email_message = EmailMultiAlternatives(subject, body, from_email, [to_email],
                                           connection=connection)
    email_message.send()


class ActivationEmailContext(NamedTuple):
    site_name: str
    activation_url: str
    language_code: str


@job('high')
def send_activation_email(context: ActivationEmailContext,
                          registration_profile_id) -> None:
    RegistrationProfile = apps.get_model('registration', 'RegistrationProfile')
    translation.activate(context.language_code)

    reg_profile = (RegistrationProfile.objects
                   .select_related("user")
                   .get(pk=registration_profile_id))
    site_name, site_domain, activation_url, *_ = context
    email_context = {
        'user': reg_profile.user,
        'activation_key': reg_profile.activation_key,
        'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
        'site_name': context.site_name,
        'activation_url': context.activation_url,
    }
    # Email subject *must not* contain newlines
    subject = loader.render_to_string(EMAIL_ACTIVATION_SUBJECT, email_context)
    subject = ''.join(subject.splitlines())
    body = loader.render_to_string(EMAIL_ACTIVATION_BODY, email_context)
    connection = get_connection(settings.POST_OFFICE['BACKENDS']['ses'])
    email_message = EmailMultiAlternatives(subject, body,
                                           settings.DEFAULT_FROM_EMAIL,
                                           [reg_profile.user.email],
                                           connection=connection)
    email_message.send()
