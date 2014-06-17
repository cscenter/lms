from __future__ import absolute_import, unicode_literals

import itertools

from django.db import models
from django.dispatch import receiver

from .models import Assignment, AssignmentStudent, Enrollment, \
    AssignmentComment, AssignmentNotification, \
    CourseOfferingNews, CourseOfferingNewsNotification


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


@receiver(models.signals.post_save, sender=AssignmentComment)
def create_assignment_notification(sender, instance, created,
                                   *args, **kwargs):
    if not created:
        return
    a_s = instance.assignment_student
    if instance.author.is_student:
        teachers = (instance
                    .assignment_student
                    .assignment
                    .course_offering
                    .teachers
                    .all())
        is_passed = not instance.assignment_student.has_passes()
        # this loop can be optimized using bulk_create at the expence of
        # pre/post_save signals on AssigmentNotification
        for teacher in teachers:
            (AssignmentNotification(user=teacher,
                                    assignment_student=a_s,
                                    is_passed=is_passed)
             .save())
    elif instance.author.is_teacher:
        student = instance.assignment_student.student
        (AssignmentNotification(user=student,
                                assignment_student=a_s)
         .save())


@receiver(models.signals.post_save, sender=CourseOfferingNews)
def create_course_offering_news_notification(sender, instance, created,
                                             *args, **kwargs):
    if not created:
        return

    students = (instance
                .course_offering
                .enrolled_students
                .all())
    teachers = (instance
                .course_offering
                .teachers
                .exclude(pk=instance.author.pk))
    # this loop can be optimized using bulk_create at the expence of
    # pre/post_save signals on CourseOfferingNewsNotification
    for user in itertools.chain(students, teachers):
        (CourseOfferingNewsNotification(
            user=user,
            course_offering_news=instance)
         .save())
