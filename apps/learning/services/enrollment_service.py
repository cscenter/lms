from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, Func, OuterRef, Q, Subquery, TextField, Value
from django.db.models.functions import Coalesce, Concat
from django.db.models.signals import post_save

from core.timezone import now_local
from core.timezone.constants import DATE_FORMAT_RU
from courses.constants import AssignmentFormat
from courses.models import Course, CourseGroupModes
from learning.models import Enrollment, StudentGroup
from learning.services import AssignmentService
from learning.services.notification_service import (
    remove_course_notifications_for_student
)
from users.models import StudentProfile, User


class EnrollmentError(Exception):
    pass


class AlreadyEnrolled(EnrollmentError):
    pass


class CourseCapacityFull(EnrollmentError):
    pass


class EnrollmentService:
    @staticmethod
    def _format_reason_record(reason_text: str, course: Course) -> str:
        """Append date to the enter/leave reason text"""
        timezone = course.get_timezone()
        today = now_local(timezone).strftime(DATE_FORMAT_RU)
        return f'{today}\n{reason_text}\n\n'

    @classmethod
    def enroll(cls, student_profile: StudentProfile, course: Course,
               reason_entry: str = '',
               student_group: Optional[StudentGroup] = None, **attrs: Any) -> Enrollment:
        if course.group_mode != CourseGroupModes.NO_GROUPS and not student_group:
            raise ValidationError("Provide student group value")
        elif course.group_mode == CourseGroupModes.NO_GROUPS and student_group:
            raise ValidationError(f"Course {course} does not support student groups")
        if student_group and student_group.course_id != course.pk:
            raise ValueError(f"Student group {student_group.pk} is not "
                             f"associated with the course {course.pk}")
        if reason_entry:
            new_record = cls._format_reason_record(reason_entry, course)
            reason_entry = Concat(Value(new_record),
                                  F('reason_entry'),
                                  output_field=TextField())
        with transaction.atomic():
            # At this moment enrollment instance not in a consistent state
            enrollment, created = (Enrollment.objects.get_or_create(
                student=student_profile.user, course=course,
                defaults={'is_deleted': True,
                          'student_profile': student_profile,
                          'student_group': student_group}))
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
                "student_group": student_group,
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
    def leave(cls, enrollment: Enrollment, reason_leave: str = '') -> None:
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


def get_learners_count_subquery(outer_ref: OuterRef) -> Func:
    from learning.models import Enrollment
    return Coalesce(Subquery(
        (Enrollment.active
         .filter(course_id=outer_ref)
         .order_by()
         .values('course')  # group by
         .annotate(total=Count("*"))
         .values("total"))
    ), Value(0))


def update_course_learners_count(course_id: int) -> None:
    Course.objects.filter(id=course_id).update(
        learners_count=get_learners_count_subquery(outer_ref=OuterRef('id'))
    )


def recreate_assignments_for_student(enrollment: Enrollment) -> None:
    """
    Resets progress for existing and creates missing assignments
    Adds a student to the gerrit project if the course has code review assignments
    """
    has_code_review = False
    for a in enrollment.course.assignment_set.all():
        AssignmentService.create_or_restore_student_assignment(a, enrollment)
        if a.submission_type == AssignmentFormat.CODE_REVIEW:
            has_code_review = True
    if has_code_review:
        from code_reviews.gerrit.tasks import add_student_to_gerrit_project
        transaction.on_commit(lambda: add_student_to_gerrit_project.delay(enrollment.pk))


def is_course_failed_by_student(course: Course, student: User,
                                enrollment: Optional[Enrollment] = None) -> bool:
    """Checks that student didn't fail the completed course"""
    from learning.models import Enrollment
    if course.is_club_course or not course.is_completed:
        return False
    bad_grades = (Enrollment.GRADES.UNSATISFACTORY,
                  Enrollment.GRADES.NOT_GRADED)
    if enrollment:
        return enrollment.grade in bad_grades
    return (Enrollment.active
            .filter(student=student,
                    course=course,
                    grade__in=bad_grades)
            .exists())
