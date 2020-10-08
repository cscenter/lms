from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.models import Semester, CourseTeacher, Assignment
from learning.models import EnrollmentPeriod


@receiver(post_save, sender=Semester)
def create_enrollment_period_for_compsciclub_ru(sender, instance: Semester,
                                                created, *args, **kwargs):
    """Side effect for compsciclub.ru creates predefined enrollment period"""
    if not created:
        return
    ends_on = instance.ends_at.date()
    EnrollmentPeriod.objects.get_or_create(site_id=settings.CLUB_SITE_ID,
                                           semester=instance,
                                           defaults={"ends_on": ends_on})


@receiver(post_save, sender=CourseTeacher)
def assign_new_homework_reviewer(sender, instance: CourseTeacher,
                                 created, *args, **kwargs):
    """Add new course teacher with a reviewer role to assignment assignees"""
    if not created:
        return
    course_teacher = instance
    if not course_teacher.roles.reviewer:
        return
    for assignment in Assignment.objects.filter(course=course_teacher.course):
        assignment.assignees.add(instance)
