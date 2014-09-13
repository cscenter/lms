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
    for student in students:
        a_s = AssignmentStudent.objects.create(assignment=instance,
                                               student=student)
        # Note(Dmitry): we create notifications here instead of a separate
        #               receiver because it's much more efficient than getting
        #               AssignmentStudent objects back one by one. It seems
        #               reasonable that 2*N INSERTs are better than bulk_create
        #               + N SELECTs + N INSERTs.
        (AssignmentNotification(user=student,
                                assignment_student=a_s,
                                is_about_creation=True)
         .save())


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
def create_assignment_comment_notification(sender, instance, created,
                                           *args, **kwargs):
    if not created:
        return
    a_s = instance.assignment_student
    if instance.author.pk == a_s.student.pk:
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
    else:
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
                .all())
    # this loop can be optimized using bulk_create at the expence of
    # pre/post_save signals on CourseOfferingNewsNotification
    for user in itertools.chain(students, teachers):
        (CourseOfferingNewsNotification(
            user=user,
            course_offering_news=instance)
         .save())


@receiver(models.signals.post_save, sender=Assignment)
def create_deadline_change_notification(sender, instance, created,
                                        *args, **kwargs):
    if created:
        return
    if 'deadline_at' in instance.tracker.changed():
        students = instance.course_offering.enrolled_students.all()
        for student in students:
            a_s = AssignmentStudent.objects.get(student=student,
                                                assignment=instance)
            (AssignmentNotification(user=student,
                                    assignment_student=a_s,
                                    is_about_deadline=True)
             .save())
