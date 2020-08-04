from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from learning.services import get_student_profile
from lms.utils import PublicRoute
from users.constants import Roles
from .models import UserGroup, User, StudentProfile, StudentTypes


@receiver(post_save, sender=UserGroup)
def post_save_user_group(sender, instance: UserGroup, *args, **kwargs):
    """Copy branch value from the student profile"""
    if instance.role in {Roles.STUDENT, Roles.VOLUNTEER, Roles.INVITED}:
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


@receiver(post_delete, sender=StudentProfile)
def post_delete_student_profile(sender, instance: StudentProfile, **kwargs):
    deleted_profile = instance
    # Other student profiles on the same site of the same type
    other_profiles = (StudentProfile.objects
                      .filter(user_id=deleted_profile.user_id,
                              type=deleted_profile.type,
                              site_id=deleted_profile.site_id))
    # It is safe to remove permission group if all other profiles are inactive
    if all(not p.is_active for p in other_profiles):
        permission_role = StudentTypes.to_permission_role(deleted_profile.type)
        (UserGroup.objects
         .filter(user_id=instance.user_id,
                 site_id=instance.site_id,
                 role=permission_role)
         .delete())


@receiver(post_save, sender=StudentProfile)
def post_save_student_profile(sender, instance: StudentProfile, **kwargs):
    permission_role = StudentTypes.to_permission_role(instance.type)
    UserGroup.objects.update_or_create(user_id=instance.user_id,
                                       site_id=instance.site_id,
                                       role=permission_role,
                                       defaults={"branch": instance.branch})
