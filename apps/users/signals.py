from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from lms.utils import PublicRoute
from users.constants import Roles

from .models import StudentProfile, StudentTypes, User, UserGroup
from .services import get_student_profile, maybe_unassign_student_role


@receiver(post_save, sender=UserGroup)
def post_save_user_group(sender, instance: UserGroup, *args, **kwargs):
    """Copy branch value from the student profile"""
    # FIXME: What if multiple profiles from different branches were found?
    if instance.role in {Roles.STUDENT, Roles.VOLUNTEER, Roles.PARTNER, Roles.INVITED}:
        profile_type = StudentTypes.from_permission_role(instance.role)
        student_profile = get_student_profile(instance.user, instance.site_id,
                                              profile_type=profile_type)
        (UserGroup.objects
         .filter(pk=instance.pk)
         .update(branch_id=student_profile.branch_id))


@receiver(post_delete, sender=UserGroup)
def post_delete_user_group(sender, instance: UserGroup, *args, **kwargs):
    """Restore redirect defaults in case user is not a student anymore"""
    # FIXME: remove redirect at all or sync PublicRoute codes with `view_*_menu` permissions and check permissions intead
    if (instance.role == Roles.STUDENT and
            instance.user.index_redirect == PublicRoute.LEARNING.code):
        User.objects.filter(pk=instance.user_id).update(index_redirect='')


# FIXME: move to the service method
@receiver(post_delete, sender=StudentProfile)
def post_delete_student_profile(sender, instance: StudentProfile, **kwargs):
    deleted_profile = instance
    role = StudentTypes.to_permission_role(deleted_profile.type)
    maybe_unassign_student_role(role=role, account=deleted_profile.user,
                                site=deleted_profile.site)
