from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from code_reviews.constants import GROUPS_IMPORT_TO_GERRIT
from code_reviews.tasks import create_account_in_gerrit, \
    update_password_in_gerrit, add_student_to_project_in_gerrit
from courses.models import CourseTeacher
from learning.models import Enrollment
from users.models import User, UserGroup


@receiver(post_save, sender=User)
def post_save_user(sender, instance: User, created, *args, **kwargs):
    """
    Add task to the queue for syncing user password.
    """
    gerrit_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
    if not gerrit_sync_enabled:
        return
    user = instance
    password_has_changed = user._password is not None
    if password_has_changed:
        # XXX: Avoid caching user.roles here since this signal could be
        # called multiple times (at least in tests because of
        # post generation hooks)
        # FIXME: mute signals instead? Kinda suck edit code to fix tests :<
        site_id = settings.SITE_ID
        roles = {g.role for g in user.groups.all() if g.site_id == site_id}
        if not roles.intersection(GROUPS_IMPORT_TO_GERRIT):
            return
        update_password_in_gerrit.delay(user_id=user.pk)


@receiver(post_save, sender=UserGroup)
def post_save_user_group(sender, instance: UserGroup, created, *args, **kwargs):
    """
    Add task to the queue for creating user account in hdb database used
    by gerrit if one of the roles from GROUPS_IMPORT_TO_GERRIT was added.
    """
    gerrit_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
    if not gerrit_sync_enabled:
        return
    if created:
        user = instance.user
        role = instance.role
        if role in GROUPS_IMPORT_TO_GERRIT:
            create_account_in_gerrit.delay(user_id=user.pk)


@receiver(post_save, sender=Enrollment)
def add_student_to_gerrit_project(sender, instance: Enrollment,
                                  created, *args, **kwargs):
    """
    Add task to the queue for adding student to the course project in Gerrit.
    User account should already exist when student role was added.
    """
    gerrit_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
    if not gerrit_sync_enabled:
        return
    course = instance.course
    if not course.is_code_review_system_used:
        return
    if created:
        add_student_to_project_in_gerrit.delay(enrollment_id=instance.pk)


@receiver(post_save, sender=CourseTeacher)
def add_reviewer_to_gerrit_project(sender, instance: CourseTeacher,
                                   created, *args, **kwargs):
    """
    Add task to the queue for adding reviewer to the course project in Gerrit.
    """
    gerrit_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
    if not gerrit_sync_enabled:
        return
    course = instance.course
    if not course.is_code_review_system_used:
        return
    is_reviewer = bool(instance.roles.reviewer)
    if created:
        # Ensure that teacher account exists, because he/she can be added to a
        # course before adding the teacher role
        create_account_in_gerrit.delay(user_id=instance.teacher.pk)
    if is_reviewer:
        add_student_to_project_in_gerrit.delay(enrollment_id=instance.pk)


@receiver(post_save, sender=UserGroup)
def post_save_user_group(sender, instance: UserGroup, created, *args, **kwargs):
    """
    Add task to the queue for creating user account in hdb database used
    by gerrit if one of the roles from GROUPS_IMPORT_TO_GERRIT was added.
    """
    gerrit_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
    if not gerrit_sync_enabled:
        return
    user = instance.user
    role = instance.role
    if role in GROUPS_IMPORT_TO_GERRIT:
        create_account_in_gerrit.delay(user_id=user.pk)
