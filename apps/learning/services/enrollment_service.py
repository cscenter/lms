from django.db import transaction
from django.db.models import Count, F, OuterRef, Q, Subquery, TextField, Value
from django.db.models.functions import Coalesce, Concat
from django.db.models.signals import post_save

from core.timezone import now_local
from core.timezone.constants import DATE_FORMAT_RU
from courses.models import Course
from learning.models import Enrollment
from learning.services import AssignmentService
from learning.services.notification_service import (
    remove_course_notifications_for_student
)
from users.models import StudentProfile


class EnrollmentError(Exception):
    pass


class AlreadyEnrolled(EnrollmentError):
    pass


class CourseCapacityFull(EnrollmentError):
    pass


class EnrollmentService:
    @staticmethod
    def _format_reason_record(reason_text: str, course: Course):
        """Append date to the enter/leave reason text"""
        timezone = course.get_timezone()
        today = now_local(timezone).strftime(DATE_FORMAT_RU)
        return f'{today}\n{reason_text}\n\n'

    @classmethod
    def enroll(cls, student_profile: StudentProfile, course: Course,
               reason_entry='', **attrs):
        if reason_entry:
            new_record = cls._format_reason_record(reason_entry, course)
            reason_entry = Concat(Value(new_record),
                                  F('reason_entry'),
                                  output_field=TextField())
        with transaction.atomic():
            # At this moment enrollment instance not in a consistent state -
            # it has no student group, etc
            enrollment, created = (Enrollment.objects.get_or_create(
                student=student_profile.user, course=course,
                defaults={'is_deleted': True, 'student_profile': student_profile}))
            if not enrollment.is_deleted:
                raise AlreadyEnrolled
            # Use sharable lock for concurrent enrollments if necessary to
            # control participants number. A blocking operation since `nowait`
            # is not used.
            if course.is_capacity_limited:
                locked = Course.objects.select_for_update().get(pk=course.pk)
            # Try to update enrollment to the `active` state
            filters = [Q(pk=enrollment.pk), Q(is_deleted=True)]
            if course.is_capacity_limited:
                learners_count = get_learners_count_subquery(
                    outer_ref=OuterRef('course_id')
                )
                filters.append(Q(course__capacity__gt=learners_count))
            attrs.update({
                "is_deleted": False,
                "student_profile": student_profile,
                "reason_entry": reason_entry
            })
            updated = (Enrollment.objects
                       .filter(*filters)
                       .update(**attrs))
            if not updated:
                # At this point we don't know the exact reason why row wasn't
                # updated. It could happen if the enrollment state was
                # `is_deleted=False` or no places left or both.
                # The first one is quit impossible (user should do concurrent
                # requests) and still should be considered as success, so
                # let's take into account only the second case.
                if course.is_capacity_limited:
                    raise CourseCapacityFull
            else:
                enrollment.refresh_from_db()
                # Send signal to trigger callbacks:
                # - update learners count
                post_save.send(Enrollment, instance=enrollment, created=created)
                recreate_assignments_for_student(enrollment)
        return enrollment

    @classmethod
    def leave(cls, enrollment: Enrollment, reason_leave=''):
        update_fields = ['is_deleted']
        enrollment.is_deleted = True
        if reason_leave:
            new_record = cls._format_reason_record(reason_leave,
                                                   enrollment.course)
            enrollment.reason_leave = Concat(
                Value(new_record),
                F('reason_leave'),
                output_field=TextField())
            update_fields.append('reason_leave')
        with transaction.atomic():
            enrollment.save(update_fields=update_fields)
            remove_course_notifications_for_student(enrollment)


def get_learners_count_subquery(outer_ref: OuterRef):
    from learning.models import Enrollment
    return Coalesce(Subquery(
        (Enrollment.active
         .filter(course_id=outer_ref)
         .order_by()
         .values('course')  # group by
         .annotate(total=Count("*"))
         .values("total"))
    ), Value(0))


def update_course_learners_count(course_id):
    Course.objects.filter(id=course_id).update(
        learners_count=get_learners_count_subquery(outer_ref=OuterRef('id'))
    )


def recreate_assignments_for_student(enrollment):
    """Resets progress for existing and creates missing assignments"""
    for a in enrollment.course.assignment_set.all():
        AssignmentService.recreate_student_assignment(a, enrollment)


def is_course_failed_by_student(course: Course, student, enrollment=None) -> bool:
    """Checks that student didn't fail the completed course"""
    from learning.models import Enrollment
    if course.is_club_course or not course.is_completed:
        return False
    bad_grades = (Enrollment.GRADES.UNSATISFACTORY,
                  Enrollment.GRADES.NOT_GRADED)
    if enrollment:
        return enrollment.grade in bad_grades
    return (Enrollment.active
            .filter(student_id=student.id,
                    course_id=course.id,
                    grade__in=bad_grades)
            .exists())
