from __future__ import absolute_import, unicode_literals

import itertools

from django.apps import apps

import django_rq
from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from django.utils import timezone
from django.utils.timezone import now

from learning.models import AssignmentComment, AssignmentNotification, \
    Assignment, CourseClass, CourseOfferingNews, Enrollment, \
    CourseOfferingTeacher
from learning.tasks import (maybe_upload_slides_yandex,
                            maybe_upload_slides_slideshare)


@receiver(post_save, sender=Assignment)
def create_student_assignments_for_new_assignment(sender, instance, created,
                                                  *args, **kwargs):
    if not created:
        return
    AssignmentNotification = apps.get_model('learning', 'AssignmentNotification')
    StudentAssignment = apps.get_model('learning', 'StudentAssignment')
    course_offering = instance.course_offering
    active_enrollments = Enrollment.active.filter(
        course_offering=course_offering)
    for e in active_enrollments:
        a_s = StudentAssignment.objects.create(assignment=instance,
                                               student_id=e.student_id)
        # Note(Dmitry): we create notifications here instead of a separate
        #               receiver because it's much more efficient than getting
        #               StudentAssignment objects back one by one. It seems
        #               reasonable that 2*N INSERTs are better than bulk_create
        #               + N SELECTs + N INSERTs.
        # bulk_create doesn't return pks, that's the main reason
        (AssignmentNotification(user_id=e.student_id,
                                student_assignment=a_s,
                                is_about_creation=True)
         .save())


@receiver(post_save, sender=Assignment)
def create_deadline_change_notification(sender, instance, created,
                                        *args, **kwargs):
    if created:
        return
    StudentAssignment = apps.get_model('learning', 'StudentAssignment')
    AssignmentNotification = apps.get_model('learning', 'AssignmentNotification')
    if 'deadline_at' in instance.tracker.changed():
        active_enrollments = Enrollment.active.filter(
            course_offering=instance.course_offering)
        for e in active_enrollments:
            a_s = StudentAssignment.objects.get(student_id=e.student_id,
                                                assignment=instance)
            (AssignmentNotification(user_id=e.student_id,
                                    student_assignment=a_s,
                                    is_about_deadline=True)
             .save())


@receiver(post_save, sender=AssignmentComment)
def assignment_comment_post_save(sender, instance, created, *args, **kwargs):
    """
    * Notify teachers if student leave a comment, otherwise notify student.
    * Update StudentAssignment model:
        1. Set `first_submission_at` if it's the first comment from the student.
        2. Set `last_comment_from` field
        Note:
            Can be essential for future signals but it doesn't update
            model attributes.
    """
    if not created:
        return

    comment = instance
    sa = comment.student_assignment
    notifications = []
    sa_update_dict = {"modified": now()}
    if comment.author_id == sa.student_id:
        other_comments = (sa.assignmentcomment_set
                          .filter(author_id=comment.author_id)
                          .exclude(pk=comment.pk))
        is_first_submission = (sa.assignment.is_online and
                               not other_comments.exists())

        teachers = comment.student_assignment.assignment.notify_teachers.all()
        for t in teachers:
            notifications.append(
                AssignmentNotification(user_id=t.teacher_id,
                                       student_assignment=sa,
                                       is_about_passed=is_first_submission))

        if is_first_submission:
            sa_update_dict["first_submission_at"] = comment.created
        sa_update_dict["last_comment_from"] = sa.LAST_COMMENT_STUDENT
    else:
        sa_update_dict["last_comment_from"] = sa.LAST_COMMENT_TEACHER
        student_id = comment.student_assignment.student_id
        notifications.append(
            AssignmentNotification(user_id=student_id, student_assignment=sa)
        )
    AssignmentNotification.objects.bulk_create(notifications)
    sa.__class__.objects.filter(pk=sa.pk).update(**sa_update_dict)
    for attr_name in sa_update_dict:
        setattr(sa, attr_name, sa_update_dict[attr_name])


# FIXME: redesign with `from_db` method!
@receiver(post_init,
          sender=CourseClass,
          dispatch_uid='learning.signals.course_class_post_init')
def track_fields_post_init(sender, instance, **kwargs):
    instance.__class__.update_track_fields(instance)


@receiver(post_save,
          sender=CourseClass,
          dispatch_uid='learning.signals.course_class_add_upload_slides_job')
def add_upload_slides_job(sender, instance, **kwargs):
    if instance.slides and not instance.slides_url:
        queue = django_rq.get_queue('default')
        queue.enqueue(maybe_upload_slides_yandex, instance.pk)
        queue.enqueue(maybe_upload_slides_slideshare, instance.pk)


@receiver(post_save, sender=CourseOfferingNews)
def create_course_offering_news_notification(sender, instance, created,
                                             *args, **kwargs):
    if not created:
        return

    co = instance.course_offering
    CourseOfferingNewsNotification = apps.get_model(
        'learning', 'CourseOfferingNewsNotification')
    active_enrollments = Enrollment.active.filter(course_offering=co)
    teachers = CourseOfferingTeacher.objects.filter(course_offering=co)

    for e in active_enrollments:
        (CourseOfferingNewsNotification(user_id=e.student_id,
                                        course_offering_news=instance)
         .save())
    for co_t in teachers:
        (CourseOfferingNewsNotification(user_id=co_t.teacher_id,
                                        course_offering_news=instance)
         .save())


@receiver(post_save, sender=Enrollment)
def populate_assignments_for_new_enrolled_student(sender, instance, created,
                                                  *args, **kwargs):
    if not created:
        return
    StudentAssignment = apps.get_model('learning', 'StudentAssignment')
    assignments = instance.course_offering.assignment_set.all()
    for a in assignments:
        (StudentAssignment.objects.get_or_create(assignment=a,
                                                 student=instance.student))
