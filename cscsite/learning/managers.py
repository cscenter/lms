from django.conf import settings
from django.db import models
from django.db.models import query, Manager, Prefetch
from django.utils.timezone import now


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
