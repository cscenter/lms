from django.contrib.auth import get_user_model
from django.db import models
from django.dispatch import receiver

from models import Assignment, AssignmentStudent, CourseOffering, Enrollment


@receiver(models.signals.post_save, sender=Assignment)
def populate_assignment_students(sender, instance, created,
                                 *args, **kwargs):
    if not created:
        return
    students = instance.course_offering.enrolled_students.all()
    AssignmentStudent.objects.bulk_create(
            AssignmentStudent(assignment=instance, student=student)
            for student in students)

# TODO: should we delete assignments on unenrolling?
@receiver(models.signals.post_save, sender=Enrollment)
def populate_student_assignments(sender, instance, created,
                                 *args, **kwargs):
    if not created:
        return
    assignments = instance.course_offering.assignment_set.all()
    AssignmentStudent.objects.bulk_create(
        AssignmentStudent(assignment=assignment, student=instance.student)
        for assignment in assignments)
