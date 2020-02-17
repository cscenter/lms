from typing import Set

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from core.models import Branch
from courses.models import Assignment, CourseNews, CourseTeacher, Course, \
    StudentGroupTypes
from learning.models import AssignmentNotification, \
    StudentAssignment, Enrollment, CourseNewsNotification, AssignmentGroup, \
    StudentGroup
from learning.services import StudentGroupService, AssignmentService, \
    update_course_learners_count


# FIXME: post_delete нужен? Что лучше - удалять StudentGroup + SET_NULL у Enrollment или делать soft-delete?
# FIXME: группу лучше удалить, т.к. она будет предлагаться для новых заданий, хотя типа уже удалена.
@receiver(post_save, sender=Course)
def add_student_group_for_course_root_branch(sender, instance, created,
                                             **kwargs):
    # FIXME: Как взять предыдущее значение? Нужно ли его удалять?
    if created:
        if instance.group_mode == StudentGroupTypes.BRANCH:
            StudentGroupService.add(instance, instance.branch)
    # TODO: What if a root branch were changed?


@receiver(m2m_changed, sender=Course.additional_branches.through)
def manage_student_group_for_course_additional_branch(sender, **kwargs):
    action = kwargs.pop("action")
    if action not in ("post_add", "post_remove"):
        return
    course = kwargs.pop("instance")
    branches: Set[int] = kwargs.pop("pk_set", set())
    if action == "post_add":
        if course.group_mode == StudentGroupTypes.BRANCH:
            for branch_id in branches:
                branch = Branch.objects.get_by_pk(branch_id)
                StudentGroupService.add(course, branch)
    elif action == "post_remove":
        if course.group_mode == StudentGroupTypes.BRANCH:
            for branch_id in branches:
                branch = Branch.objects.get_by_pk(branch_id)
                StudentGroupService.remove(course, branch)


@receiver(post_save, sender=Enrollment)
def compute_course_learners_count(sender, instance: Enrollment, created,
                                  *args, **kwargs):
    if created and instance.is_deleted:
        return
    update_course_learners_count(instance.course_id)


@receiver(post_save, sender=CourseNews)
def create_notifications_about_course_news(sender, instance: CourseNews,
                                           created, *args, **kwargs):
    if not created:
        return
    co_id = instance.course_id
    notifications = []
    active_enrollments = Enrollment.active.filter(course_id=co_id)
    for e in active_enrollments.iterator():
        notifications.append(
            CourseNewsNotification(user_id=e.student_id,
                                   course_offering_news_id=instance.pk))
    teachers = CourseTeacher.objects.filter(course_id=co_id)
    for co_t in teachers.iterator():
        notifications.append(
            CourseNewsNotification(user_id=co_t.teacher_id,
                                   course_offering_news_id=instance.pk))
    CourseNewsNotification.objects.bulk_create(notifications)


@receiver(post_save, sender=Assignment)
def create_deadline_change_notification(sender, instance, created,
                                        *args, **kwargs):
    if created:
        return
    if 'deadline_at' in instance.tracker.changed():
        active_enrollments = Enrollment.active.filter(course=instance.course)
        for e in active_enrollments:
            try:
                sa = (StudentAssignment.objects
                      .only('pk')
                      .get(student_id=e.student_id,
                           assignment=instance))
                (AssignmentNotification(user_id=e.student_id,
                                        student_assignment_id=sa.pk,
                                        is_about_deadline=True)
                 .save())
            except StudentAssignment.DoesNotExist:
                # It can occur for student with inactive status
                continue
