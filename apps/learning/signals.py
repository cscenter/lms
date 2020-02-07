from typing import Set

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from core.models import Branch
from courses.models import Assignment, CourseNews, CourseTeacher, Course, \
    StudentGroupTypes
from learning.models import AssignmentNotification, \
    StudentAssignment, Enrollment, CourseNewsNotification, StudentGroup
from learning.settings import StudentStatuses
from learning.utils import update_course_learners_count


def add_student_group(course: Course, branch):
    group, _ = (StudentGroup.objects.get_or_create(
        course_id=course.pk,
        type=StudentGroupTypes.BRANCH,
        branch_id=branch.pk,
        defaults={
            "name": str(branch),
            "name_en": f"{branch.name_en} [{branch.site}]"
        }))

"""
TODO:
1. Сделать привязку Assignment к StudentGroup (если групп > 1 ???). Кого-то это может начать путать, особенно суффиксы [compsciclub.ru]
Возможно, надо делать явный вариант "все", т.к. возможны студенты без привязки к группе. Тогда если в UI выбрать все группы - им не будут видны 
2. Генерировать StudentAssignment на основе StudentGroup. Как матчить необходимость? Если type == manual, то просто по StudentGroup.pk. Если type == branch, то по StudentGroup.branch_id
3. При записи студента на курс - добавлять его в группу по возможности. [optional Enrollment.student_group]. Если записывают студента, для которого нет группы - его всё равно надо как-то добавить.
"""


# FIXME: post_delete нужен? Что лучше - удалять StudentGroup + SET_NULL у Enrollment или делать soft-delete?
# FIXME: группу лучше удалить, т.к. она будет предлагаться для новых заданий, хотя типа уже удалена.
@receiver(post_save, sender=Course)
def manage_student_group_for_course_root_branch(sender, instance, created,
                                                **kwargs):
    # FIXME: Как взять предыдущее значение? Нужно ли его удалять?
    if instance.group_mode == StudentGroupTypes.BRANCH:
        add_student_group(instance, instance.branch)


@receiver(m2m_changed, sender=Course.additional_branches.through)
def manage_student_group_for_course_additional_branch(sender, **kwargs):
    action = kwargs.pop("action")
    if action != "post_add":
        return
    instance = kwargs.pop("instance")
    if instance.group_mode == StudentGroupTypes.BRANCH:
        branches: Set[int] = kwargs.pop("pk_set", set())
        for branch_id in branches:
            branch = Branch.objects.get(pk=branch_id)
            add_student_group(instance, branch)


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


# TODO: send notification to other teachers
@receiver(post_save, sender=Assignment)
def create_student_assignments_for_new_assignment(sender, instance, created,
                                                  *args, **kwargs):
    if not created:
        return
    course = instance.course
    # Skip expelled students or in academic leave
    active_students = (Enrollment.active
                       .filter(course=course)
                       # FIXME: move to `active` manager?
                       .exclude(student__status__in=StudentStatuses.inactive_statuses)
                       .values_list("student_id", flat=True))
    for student_id in active_students:
        a_s = StudentAssignment.objects.create(assignment=instance,
                                               student_id=student_id)
        # Note(Dmitry): we create notifications here instead of a separate
        #               receiver because it's much more efficient than getting
        #               StudentAssignment objects back one by one. It seems
        #               reasonable that 2*N INSERTs are better than bulk_create
        #               + N SELECTs + N INSERTs.
        # bulk_create doesn't return pks, that's the main reason
        (AssignmentNotification(user_id=student_id,
                                student_assignment=a_s,
                                is_about_creation=True)
         .save())


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
