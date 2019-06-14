from typing import List

from django.db import models
from django.db.models import query, Prefetch

from core.utils import is_club_site
from courses.utils import get_boundaries


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
    """On compsciclub.ru always restrict by open readings"""
    def get_queryset(self):
        qs = super().get_queryset()
        if is_club_site():
            return qs.filter(assignment__course__is_open=True)
        return qs


StudentAssignmentManager = _StudentAssignmentDefaultManager.from_queryset(
    StudentAssignmentQuerySet)


class EventQuerySet(query.QuerySet):
    def for_calendar(self):
        if is_club_site():
            return self.none()
        return (self
                .order_by('date', 'starts_at'))

    def for_city(self, city_code):
        return self.filter(venue__city_id=city_code)

    def in_cities(self, city_codes: List[str]):
        return self.filter(venue__city_id__in=city_codes)

    def in_month(self, year, month):
        date_start, date_end = get_boundaries(year, month)
        return self.filter(date__gte=date_start, date__lte=date_end)


class _EnrollmentDefaultManager(models.Manager):
    """On compsciclub.ru always restrict selection by open readings"""
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


class _GraduateProfileActiveManager(models.Manager):
    def get_queryset(self):
        return (super().get_queryset()
                .filter(is_active=True)
                .select_related("student")
                .only("pk",
                      "modified",
                      "graduation_year",
                      "photo",
                      "testimonial",
                      "student__city_id",
                      "student__photo",
                      "student__cropbox_data",
                      "student__first_name",
                      "student__last_name",
                      "student__patronymic",
                      "student__gender",))


class GraduateProfileQuerySet(models.QuerySet):
    def with_testimonial(self):
        return self.exclude(testimonial='')


GraduateProfileActiveManager = _GraduateProfileActiveManager.from_queryset(
    GraduateProfileQuerySet)