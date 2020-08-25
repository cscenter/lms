import logging

from django.apps import apps
from django_rq import job

from code_reviews.api.ldap import init_client
from code_reviews.ldap import get_ldap_username, user_to_ldap_entry, \
    get_password_hash
from users.models import User

logger = logging.getLogger('auth')


@job('high')
def create_account_in_gerrit(*, user_id: int):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning(f"User with id={user_id} not found")
        return
    uid = get_ldap_username(user)
    with init_client() as ldap_client:
        results = ldap_client.search_users(uid)
        if results:
            logger.info(f"User with id={user_id} already has an account")
            return
        else:
            entry = user_to_ldap_entry(user)
            ldap_client.add_entry(entry)


@job('high')
def update_password_in_gerrit(*, user_id: int):
    """
    Update LDAP password hash in review.compscicenter.ru when user
    successfully changed his password with reset or change form.
    """
    User = apps.get_model('users', 'User')
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning(f"User with id={user_id} not found")
        return
    password_hash = get_password_hash(user)
    if not password_hash:
        logger.error(f"Empty hash for user_id={user_id}")
        return
    username = get_ldap_username(user)
    # TODO: What if connection fail when code review system is not available?
    with init_client() as client:
        changed = client.set_password_hash(username, password_hash)
        if not changed:
            logger.error(f"Password hash for user {user_id} wasn't changed")