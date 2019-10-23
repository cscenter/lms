from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.models import Assignment, CourseNews, CourseTeacher
from learning.models import AssignmentNotification, \
    StudentAssignment, Enrollment, CourseNewsNotification
from learning.settings import StudentStatuses
from learning.utils import update_course_learners_count


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
