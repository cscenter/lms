from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from code_reviews.constants import GROUPS_IMPORT_TO_GERRIT
from code_reviews.tasks import create_account_in_gerrit, \
    update_password_in_gerrit
from users.models import User


@receiver(post_save, sender=User)
def post_save_user(sender, instance: User, created, *args, **kwargs):
    """
    Add task to the queue for creating user account in a hdb database used
    by gerrit if user does not exist, otherwise sync user password.
    """
    gerrit_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
    if not gerrit_sync_enabled:
        return
    user = instance
    password_has_changed = user._password is not None
    if created:
        # FIXME: в момент создания аккаунта у пользователя ещё не может быть ролей, поэтому ldap аккаунт не будет создан (даже если не добавить проверку на пересечение с IMPORT_TO_GERRIT) => нужно вызывать в других местах
        return
        create_account_in_gerrit.delay(user_id=user.pk)
    elif password_has_changed:
        # XXX: Avoid caching user.roles here since this signal could be
        # called multiple times (at least in tests because of
        # post generation hooks)
        # FIXME: mute signals instead? Kinda suck edit code to fix tests :<
        site_id = settings.SITE_ID
        roles = {g.role for g in user.groups.all() if g.site_id == site_id}
        if not roles.intersection(GROUPS_IMPORT_TO_GERRIT):
            return
        update_password_in_gerrit.delay(user_id=user.pk)
