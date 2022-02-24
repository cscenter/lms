from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from courses.models import (
    Assignment, Course, CourseBranch, CourseGroupModes, CourseNews, CourseTeacher,
    StudentGroupTypes
)
from learning.models import (
    AssignmentComment, AssignmentNotification, AssignmentSubmissionTypes,
    CourseNewsNotification, Enrollment, StudentAssignment, StudentGroup
)
from learning.services import StudentGroupService
from learning.services.enrollment_service import update_course_learners_count
# FIXME: post_delete нужен? Что лучше - удалять StudentGroup + SET_NULL у Enrollment или делать soft-delete?
# FIXME: группу лучше удалить, т.к. она будет предлагаться для новых заданий, хотя типа уже удалена.
from learning.tasks import convert_assignment_submission_ipynb_file_to_html


@receiver(post_save, sender=Course)
def manage_student_group_for_course_root_branch(sender, instance, created,
                                                **kwargs):
    # TODO: What if a root branch were changed?
    pass


@receiver(post_save, sender=CourseBranch)
def create_student_group_from_course_branch(sender, instance: CourseBranch,
                                            created, *args, **kwargs):
    if created and instance.course.group_mode == CourseGroupModes.BRANCH:
        StudentGroupService.create(instance.course,
                                   group_type=StudentGroupTypes.BRANCH,
                                   branch=instance.branch)


@receiver(post_delete, sender=CourseBranch)
def delete_student_group_if_course_branch_deleted(sender, instance: CourseBranch,
                                                  *args, **kwargs):
    student_groups = (StudentGroup.objects
                      .filter(course=instance.course,
                              branch=instance.branch,
                              type=StudentGroupTypes.BRANCH))
    for student_group in student_groups:
        StudentGroupService.remove(student_group)


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


@receiver(post_save, sender=AssignmentComment)
def convert_ipynb_files(sender, instance: AssignmentComment, *args, **kwargs):
    # TODO: convert for solutions only? both?
    if not instance.attached_file:
        return
    if instance.attached_file_name.endswith('.ipynb'):
        kwargs = {'assignment_submission_id': instance.pk}
        # FIXME: add transaction.on_commit
        convert_assignment_submission_ipynb_file_to_html.delay(**kwargs)


# TODO: move to the create_assignment_solution service method
@receiver(post_save, sender=AssignmentComment)
def save_student_solution(sender, instance: AssignmentComment, *args, **kwargs):
    """Updates aggregated execution time value on StudentAssignment model"""
    if instance.type != AssignmentSubmissionTypes.SOLUTION:
        return
    instance.student_assignment.compute_fields('execution_time')


@receiver(post_delete, sender=AssignmentComment)
def delete_student_solution(sender, instance: AssignmentComment,
                            *args, **kwargs):
    """Updates aggregated execution time value on StudentAssignment model"""
    if instance.type != AssignmentSubmissionTypes.SOLUTION:
        return
    instance.student_assignment.compute_fields('execution_time')
