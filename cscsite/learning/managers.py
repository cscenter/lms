from django.conf import settings
from django.db import models
from django.db.models import query, Manager, Prefetch, Q
from django.utils.timezone import now

from core.utils import is_club_site
from learning.calendar import EventsCalendar, get_bounds_for_month
from learning.settings import SEMESTER_TYPES


class StudentAssignmentQuerySet(query.QuerySet):
    def for_user(self, user):
        related = ['assignment',
                   'assignment__course_offering',
                   'assignment__course_offering__course',
                   'assignment__course_offering__semester']
        return (self
                .filter(student=user)
                .select_related(*related)
                .order_by('assignment__course_offering__course__name',
                          'assignment__deadline_at',
                          'assignment__title'))

    def in_term(self, term):
        return self.filter(assignment__course_offering__semester_id=term.id)


class StudyProgramQuerySet(query.QuerySet):
    def syllabus(self):
        from learning.models import StudyProgramCourseGroup
        return (self.select_related("area")
                    .prefetch_related(
                        Prefetch(
                            'course_groups',
                            queryset=(StudyProgramCourseGroup
                                      .objects
                                      .prefetch_related("courses")),
                        )))


class CourseClassQuerySet(query.QuerySet):
    def for_calendar(self, user=None):
        q = (self
             .select_related('venue',
                             'course_offering',
                             'course_offering__course',
                             'course_offering__semester')
             .order_by('date', 'starts_at'))
        # Hide summer classes on compsciclub.ru if user not enrolled in
        if is_club_site() and user:
            active_summer_enrollments = Q(
                course_offering__is_open=True,
                course_offering__semester__type=SEMESTER_TYPES.summer,
                course_offering__enrollment__student_id=user.pk,
                course_offering__enrollment__is_deleted=False)
            others = ~Q(course_offering__semester__type=SEMESTER_TYPES.summer)
            q = self.filter(active_summer_enrollments | others)
        return q

    def for_city(self, city_code):
        return self.filter(course_offering__city_id=city_code)

    def in_month(self, year, month):
        date_start, date_end = get_bounds_for_month(year, month)
        return self.filter(date__gte=date_start, date__lte=date_end)

    def open_only(self):
        return self.filter(course_offering__is_open=True)

    def for_student(self, user):
        """More strict than in `.for_calendar`. Let DB optimize it later."""
        return self.filter(course_offering__enrollment__student_id=user.pk,
                           course_offering__enrollment__is_deleted=False)

    def for_teacher(self, user):
        return self.filter(course_offering__teachers=user)


class NonCourseEventQuerySet(query.QuerySet):
    def for_calendar(self):
        if is_club_site():
            return self.none()
        return (self
                .select_related('venue')
                .order_by('date', 'starts_at'))

    def for_city(self, city_code):
        return self.filter(venue__city_id=city_code)

    def in_month(self, year, month):
        date_start, date_end = get_bounds_for_month(year, month)
        return self.filter(date__gte=date_start, date__lte=date_end)


class CustomCourseOfferingQuerySet(models.QuerySet):
    def site_related(self, request):
        qs = self.filter(city__pk=request.city_code)
        if request.site.domain == settings.CLUB_DOMAIN:
            qs = qs.filter(is_open=True,)
        return qs

    # FIXME: respect timezones!
    def completed(self, is_completed):
        if is_completed:
            return self.filter(completed_at__lte=now().date())
        else:
            return self.filter(completed_at__gt=now().date())


class _EnrollmentDefaultManager(models.Manager):
    pass


class _EnrollmentActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class EnrollmentDefaultQuerySet(models.QuerySet):
    def site_related(self, request):
        qs = (self.select_related("course_offering")
                  .filter(course_offering__city_id=request.city_code))
        if request.site.domain == settings.CLUB_DOMAIN:
            qs = qs.filter(course_offering__is_open=True)
        return qs


EnrollmentDefaultManager = _EnrollmentDefaultManager.from_queryset(
    EnrollmentDefaultQuerySet)
EnrollmentActiveManager = _EnrollmentActiveManager.from_queryset(
    EnrollmentDefaultQuerySet)
