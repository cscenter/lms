import logging

from django.apps import apps
from django_rq import job

logger = logging.getLogger('auth')


@job('high')
def update_password_in_gerrit(user_id: int):
    """
    Update LDAP password hash in review.compscicenter.ru when user
    successfully changed his password with reset or change form.
    """
    from code_reviews.api.ldap import connection
    from code_reviews.ldap import get_ldap_username
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