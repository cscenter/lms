from django.db import transaction
from django.db.models import Q, OuterRef, Value, F, TextField
from django.db.models.functions import Concat

from core.constants import DATE_FORMAT_RU
from core.db.expressions import SubqueryCount
from core.timezone import now_local
from courses.models import Course
from django.utils.translation import ugettext_lazy as _
from learning.models import Enrollment
from learning.utils import populate_assignments_for_student, \
    update_course_learners_count
from users.models import User


class EnrollmentError(Exception):
    pass


class AlreadyEnrolled(EnrollmentError):
    pass


class CourseCapacityFull(EnrollmentError):
    pass


class EnrollmentService:
    @staticmethod
    def enroll(user: User, course: Course, **attrs):
        reason_entry = attrs.pop("reason_entry", None)
        if reason_entry:
            timezone = course.get_city_timezone()
            today = now_local(timezone).strftime(DATE_FORMAT_RU)
            reason_entry = Concat(Value(f'{today}\n{reason_entry}\n\n'),
                                  F('reason_entry'),
                                  output_field=TextField())
        with transaction.atomic():
            enrollment, created = (Enrollment.objects.get_or_create(
                student=user, course=course,
                defaults={'is_deleted': True}))
            if not enrollment.is_deleted:
                raise AlreadyEnrolled
            # This is a sharable lock for concurrent enrollments if needs to
            # control participants number. A blocking operation since `nowait`
            # is not used.
            if course.is_capacity_limited:
                locked = Course.objects.select_for_update().get(pk=course.pk)
            # Try to update state of the enrollment record to `active`
            filters = [Q(pk=enrollment.pk), Q(is_deleted=True)]
            if course.is_capacity_limited:
                learners_count = SubqueryCount(
                    Enrollment.active
                    .filter(course_id=OuterRef('course_id')))
                filters.append(Q(course__capacity__gt=learners_count))
            updated = (Enrollment.objects
                       .filter(*filters)
                       .update(**attrs,
                               is_deleted=False,
                               reason_entry=reason_entry))
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
                if not created:
                    populate_assignments_for_student(enrollment)
                update_course_learners_count(course.pk)

    @staticmethod
    def leave(enrollment: Enrollment, reason_leave=''):
        update_fields = ['is_deleted']
        enrollment.is_deleted = True
        if reason_leave:
            timezone = enrollment.course.get_city_timezone()
            today = now_local(timezone).strftime(DATE_FORMAT_RU)
            enrollment.reason_leave = Concat(
                Value(f'{today}\n{reason_leave}\n\n'),
                F('reason_leave'),
                output_field=TextField())
            update_fields.append('reason_leave')
        with transaction.atomic():
            enrollment.save(update_fields=update_fields)
