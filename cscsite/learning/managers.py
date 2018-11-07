from typing import List

from django.db import models
from django.db.models import query, Prefetch

from core.utils import is_club_site
from learning.calendar import get_bounds_for_calendar_month


class StudentAssignmentQuerySet(query.QuerySet):
    def for_user(self, user):
        related = ['assignment',
                   'assignment__course',
                   'assignment__course__meta_course',
                   'assignment__course__semester']
        return (self
                .filter(student=user)
                .select_related(*related)
                .order_by('assignment__course__meta_course__name',
                          'assignment__deadline_at',
                          'assignment__title'))

    def in_term(self, term):
        return self.filter(assignment__course__semester_id=term.id)


class _StudentAssignmentDefaultManager(models.Manager):
    """On compsciclub.ru always restrict selection by open reading"""
    def get_queryset(self):
        if is_club_site():
            return super().get_queryset().filter(
                assignment__course__is_open=True)
        else:
            return super().get_queryset()


StudentAssignmentManager = _StudentAssignmentDefaultManager.from_queryset(
    StudentAssignmentQuerySet)


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


class NonCourseEventQuerySet(query.QuerySet):
    def for_calendar(self):
        if is_club_site():
            return self.none()
        return (self
                .select_related('venue')
                .order_by('date', 'starts_at'))

    def for_city(self, city_code):
        return self.filter(venue__city_id=city_code)

    def in_cities(self, city_codes: List[str]):
        return self.filter(venue__city_id__in=city_codes)

    def in_month(self, year, month):
        date_start, date_end = get_bounds_for_calendar_month(year, month)
        return self.filter(date__gte=date_start, date__lte=date_end)


class _EnrollmentDefaultManager(models.Manager):
    """On compsciclub.ru always restrict selection by open reading"""
    def get_queryset(self):
        if is_club_site():
            return super().get_queryset().filter(course__is_open=True)
        else:
            return super().get_queryset()


class _EnrollmentActiveManager(models.Manager):
    def get_queryset(self):
        if is_club_site():
            return super().get_queryset().filter(course__is_open=True,
                                                 is_deleted=False)
        else:
            return super().get_queryset().filter(is_deleted=False)


class EnrollmentQuerySet(models.QuerySet):
    pass


EnrollmentDefaultManager = _EnrollmentDefaultManager.from_queryset(
    EnrollmentQuerySet)
EnrollmentActiveManager = _EnrollmentActiveManager.from_queryset(
    EnrollmentQuerySet)
