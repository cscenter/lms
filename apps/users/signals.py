from django.db.models.signals import post_delete
from django.dispatch import receiver

from my_compscicenter_ru.utils import PublicRoute
from users.constants import Roles
from .models import UserGroup, User


@receiver(post_delete, sender=UserGroup)
def post_delete_user_role(sender, instance: UserGroup, *args, **kwargs):
    """Restore redirect defaults in case user is not a student anymore"""
    # FIXME: remove redirect at all or sync PublicRoute codes with `view_*_menu` permissions and check permissions intead
    if (instance.role == Roles.STUDENT and
            instance.user.index_redirect == PublicRoute.LEARNING.code):
        User.objects.filter(pk=instance.user_id).update(index_redirect='')
