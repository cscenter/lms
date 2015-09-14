from __future__ import absolute_import, unicode_literals

import posixpath
import itertools

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from slides import yandex_disk, slideshare
from .models import Assignment, AssignmentStudent, Enrollment, \
    AssignmentComment, AssignmentNotification, \
    CourseOfferingNews, CourseOfferingNewsNotification, CourseClass


@receiver(post_save, sender=CourseClass)
def maybe_upload_slides(sender, instance, **kwargs):
    # XXX we might want to delegate this to cron or Celery.
    # TODO: We want to update slides_url if slides have changed
    if instance.slides and not instance.slides_url:
        course_offering = instance.course_offering
        course = course_offering.course

        # a) Yandex.Disk
        yandex_disk.upload_slides(
            instance.slides.file,
            posixpath.join(course.slug, instance.slides_file_name))

        # b) SlideShare
        instance.slides_url = slideshare.upload_slides(
            instance.slides.file,
            "{0}: {1}".format(course_offering, instance),
            instance.description, tags=[course.slug])
        instance.save()


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
    for a in assignments:
        (AssignmentStudent.objects
         .get_or_create(assignment=a,
                        student=instance.student))


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
        is_about_passed = not ((a_s.assignmentcomment_set
                                .exclude(pk=instance.pk)
                                .filter(author__groups__name='Student [CENTER]')
                                .exists()) and
                               a_s.assignment.is_online)
        # this loop can be optimized using bulk_create at the expence of
        # pre/post_save signals on AssigmentNotification
        for teacher in teachers:
            (AssignmentNotification(user=teacher,
                                    assignment_student=a_s,
                                    is_about_passed=is_about_passed)
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


@receiver(models.signals.post_save, sender=AssignmentComment)
def mark_assignment_passed(sender, instance, created,
                           *args, **kwargs):
    if not created:
        return
    a_s = instance.assignment_student
    if not a_s.is_passed\
       and instance.author.pk == a_s.student.pk\
       and a_s.assignment.is_online:
        a_s.is_passed = True
        a_s.save()
