from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from code_reviews.tasks import update_password_in_gerrit
from users.constants import Roles
from users.models import User


GROUPS_IMPORT_TO_GERRIT = [
    Roles.STUDENT,
    Roles.VOLUNTEER,
    Roles.TEACHER,
    Roles.GRADUATE
]


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
    password_changed = user._password is not None
    if created:
        # create or update user in a hdb
        pass
    elif password_changed:
        if user.roles.intersection(GROUPS_IMPORT_TO_GERRIT):
            update_password_in_gerrit.delay(user_id=user.pk)
