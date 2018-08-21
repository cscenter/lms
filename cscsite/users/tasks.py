import logging

from django.apps import apps
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils import translation
from django_rq import job

logger = logging.getLogger(__name__)

html_email_template_name = None
email_template_name = 'emails/password_reset.html'
subject_template_name = 'registration/password_reset_subject.txt'


@job('high')
def send_restore_password_email(context, from_email, to_email, language_code):
    """
    Sends a django.core.mail.EmailMultiAlternatives to `to_email`.
    """
    translation.activate(language_code)
    subject = loader.render_to_string(subject_template_name, context)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    body = loader.render_to_string(email_template_name, context)
    email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
    if html_email_template_name is not None:
        html_email = loader.render_to_string(html_email_template_name, context)
        email_message.attach_alternative(html_email, 'text/html')
    email_message.send()


@job('high')
def update_password_in_gerrit(user_id: int):
    """
    Update LDAP password hash in review.compscicenter.ru when user
    successfully changed his password with reset or change form.
    """
    from api.providers.ldap import connection
    from users.ldap import get_ldap_username
    CSCUser = apps.get_model('users', 'CSCUser')
    try:
        user = CSCUser.objects.get(pk=user_id)
        if not user.password_hash_ldap:
            logger.error(f"Empty hash for user_id={user_id}")
            return
    except CSCUser.DoesNotExist:
        logger.warning(f"User with id={user_id} not found")
        return
    username = get_ldap_username(user)
    # TODO: What if connection failed when code review system is not available?
    with connection() as c:
        changed = c.set_password_hash(username, user.password_hash_ldap)
        if not changed:
            logger.error(f"Password hash for user {user_id} wasn't changed")
