from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from code_reviews.gerrit.tasks import update_password_in_gerrit
from users.models import User


@receiver(post_save, sender=User)
def post_save_user(sender, instance: User, created, *args, **kwargs):
    """
    Sync Django's user and Gerrit LDAP user hash password.
    """
    is_gerrit_ldap_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
    if is_gerrit_ldap_sync_enabled:
        is_password_has_changed = instance._password is not None
        if not created and is_password_has_changed:
            update_password_in_gerrit.delay(user_id=instance.pk)
