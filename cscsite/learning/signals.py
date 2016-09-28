from __future__ import absolute_import, unicode_literals

import itertools

from django.apps import apps

import django_rq

from learning.tasks import (maybe_upload_slides_yandex,
                            maybe_upload_slides_slideshare)


def create_student_assignments_for_new_assignment(sender, instance, created,
                                                  *args, **kwargs):
    if not created:
        return
    AssignmentNotification = apps.get_model('learning', 'AssignmentNotification')
    StudentAssignment = apps.get_model('learning', 'StudentAssignment')
    students = instance.course_offering.enrolled_students.all()
    for student in students:
        a_s = StudentAssignment.objects.create(assignment=instance,
                                               student=student)
        # Note(Dmitry): we create notifications here instead of a separate
        #               receiver because it's much more efficient than getting
        #               StudentAssignment objects back one by one. It seems
        #               reasonable that 2*N INSERTs are better than bulk_create
        #               + N SELECTs + N INSERTs.
        (AssignmentNotification(user=student,
                                student_assignment=a_s,
                                is_about_creation=True)
         .save())


def create_deadline_change_notification(sender, instance, created,
                                        *args, **kwargs):
    if created:
        return
    StudentAssignment = apps.get_model('learning', 'StudentAssignment')
    AssignmentNotification = apps.get_model('learning', 'AssignmentNotification')
    if 'deadline_at' in instance.tracker.changed():
        students = instance.course_offering.enrolled_students.all()
        for student in students:
            a_s = StudentAssignment.objects.get(student=student,
                                                assignment=instance)
            (AssignmentNotification(user=student,
                                    student_assignment=a_s,
                                    is_about_deadline=True)
             .save())


def create_assignment_comment_notification(sender, instance, created,
                                           *args, **kwargs):
    """Send notification to teachers if student leave a comment, otherwise to student"""
    if not created:
        return
    AssignmentNotification = apps.get_model('learning', 'AssignmentNotification')
    s_a = instance.student_assignment
    if instance.author.pk == s_a.student.pk:
        is_about_passed = not ((s_a.assignmentcomment_set
                                .exclude(pk=instance.pk)
                                .filter(author__groups__name='Student [CENTER]')
                                .exists()) and
                               s_a.assignment.is_online)

        teachers = instance.student_assignment.assignment.notify_teachers.all()
        # this loop can be optimized using bulk_create at the expence of
        # pre/post_save signals on AssigmentNotification
        for teacher in teachers:
            (AssignmentNotification(user=teacher.teacher,
                                    student_assignment=s_a,
                                    is_about_passed=is_about_passed)
             .save())
    else:
        student = instance.student_assignment.student
        AssignmentNotification(user=student, student_assignment=s_a).save()


def update_last_comment_info_on_student_assignment(sender, instance,
                                                   created,
                                                   *args, **kwargs):
    if not created:
        return

    sa = instance.student_assignment
    if instance.author_id == sa.student_id:
        sa.last_comment_from = sa.LAST_COMMENT_STUDENT
    else:
        sa.last_comment_from = sa.LAST_COMMENT_TEACHER

    sa.__class__.objects.filter(pk=sa.pk).update(
        last_comment_from=sa.last_comment_from)


def mark_assignment_passed(sender, instance, created,
                           *args, **kwargs):
    if not created:
        return
    a_s = instance.student_assignment
    if not a_s.is_passed\
       and instance.author.pk == a_s.student.pk\
       and a_s.assignment.is_online:
        a_s.is_passed = True
        a_s.save()


def track_fields_post_init(sender, instance, **kwargs):
    instance.__class__.update_track_fields(instance)


def add_upload_slides_job(sender, instance, **kwargs):
    if instance.slides and not instance.slides_url:
        queue = django_rq.get_queue('default')
        queue.enqueue(maybe_upload_slides_yandex, instance.pk)
        queue.enqueue(maybe_upload_slides_slideshare, instance.pk)


def create_course_offering_news_notification(sender, instance, created,
                                             *args, **kwargs):
    if not created:
        return

    students = (instance.course_offering.enrolled_students.all())
    teachers = (instance.course_offering.teachers.all())

    CourseOfferingNewsNotification = apps.get_model('learning',
                                                    'CourseOfferingNewsNotification')
    # this loop can be optimized using bulk_create at the expence of
    # pre/post_save signals on CourseOfferingNewsNotification
    for user in itertools.chain(students, teachers):
        (CourseOfferingNewsNotification(
            user=user,
            course_offering_news=instance)
         .save())


def populate_assignments_for_new_enrolled_student(sender, instance, created,
                                                  *args, **kwargs):
    if not created:
        return
    StudentAssignment = apps.get_model('learning', 'StudentAssignment')
    assignments = instance.course_offering.assignment_set.all()
    for a in assignments:
        (StudentAssignment.objects.get_or_create(assignment=a,
                                                 student=instance.student))
