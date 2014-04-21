from __future__ import absolute_import, unicode_literals

from django.db import models
from django.dispatch import receiver

from .models import Assignment, AssignmentStudent, Enrollment

# pylint: disable=unused-argument


@receiver(models.signals.post_save, sender=Assignment)
def populate_assignment_students(sender, instance, created,
                                 *args, **kwargs):
    if not created:
        return
    students = instance.course_offering.enrolled_students.all()
    AssignmentStudent.objects.bulk_create(
        AssignmentStudent(assignment=instance, student=student)
        for student in students)


@receiver(models.signals.post_save, sender=Enrollment)
def populate_student_assignments(sender, instance, created,
                                 *args, **kwargs):
    if not created:
        return
    assignments = instance.course_offering.assignment_set.all()
    AssignmentStudent.objects.bulk_create(
        AssignmentStudent(assignment=assignment, student=instance.student)
        for assignment in assignments)


@receiver(models.signals.post_delete, sender=Enrollment)
def delete_student_assignments(sender, instance, *args, **kwargs):
    (AssignmentStudent.objects
     .filter(assignment__course_offering=instance.course_offering,
             student=instance.student)
     .delete())
