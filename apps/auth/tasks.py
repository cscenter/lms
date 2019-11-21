import logging
from typing import NamedTuple

from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils import translation
from django_rq import job

from auth.settings import EMAIL_RESTORE_PASSWORD_SUBJECT, \
    EMAIL_RESTORE_PASSWORD_BODY, EMAIL_ACTIVATION_SUBJECT, EMAIL_ACTIVATION_BODY
from core.urls import reverse, replace_hostname

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
    email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
    email_message.send()


@job('high')
def update_password_in_gerrit(user_id: int):
    """
    Update LDAP password hash in review.compscicenter.ru when user
    successfully changed his password with reset or change form.
    """
    from api.providers.ldap import connection
    from users.ldap import get_ldap_username
    User = apps.get_model('users', 'User')
    try:
        user = User.objects.get(pk=user_id)
        if not user.password_hash_ldap:
            logger.error(f"Empty hash for user_id={user_id}")
            return
    except User.DoesNotExist:
        logger.warning(f"User with id={user_id} not found")
        return
    username = get_ldap_username(user)
    # TODO: What if connection fail when code review system is not available?
    with connection() as c:
        changed = c.set_password_hash(username, user.password_hash_ldap)
        if not changed:
            logger.error(f"Password hash for user {user_id} wasn't changed")


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
    email_message = EmailMultiAlternatives(subject, body,
                                           settings.DEFAULT_FROM_EMAIL,
                                           [reg_profile.user.email])
    email_message.send()
