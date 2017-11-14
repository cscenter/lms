from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now

from learning.settings import STUDENT_STATUS
from learning.models import AssignmentComment, AssignmentNotification, \
    Assignment, StudentAssignment, Enrollment


# TODO: send notification to other teachers
@receiver(post_save, sender=Assignment)
def create_student_assignments_for_new_assignment(sender, instance, created,
                                                  *args, **kwargs):
    if not created:
        return
    course_offering = instance.course_offering
    # Skip those who already been expelled
    active_students = (Enrollment.active
                       .filter(course_offering=course_offering)
                       .exclude(student__status=STUDENT_STATUS.expelled)
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
