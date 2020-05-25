from django.db import models
from django.db.models import query
from django.utils import timezone

from core.models import LiveManager
from core.utils import is_club_site


class StudentAssignmentQuerySet(query.QuerySet):
    def for_user(self, user):
        return (self.filter(student=user)
                .select_related('assignment',
                                'assignment__course',
                                'assignment__course__main_branch',
                                'assignment__course__meta_course',
                                'assignment__course__semester'))

    def in_term(self, term):
        return self.filter(assignment__course__semester_id=term.id)

    def with_future_deadline(self):
        """
        Returns individual assignments with unexpired deadlines.
        """
        return self.filter(assignment__deadline_at__gt=timezone.now())


class _StudentAssignmentDefaultManager(LiveManager):
    """On compsciclub.ru always restrict by open readings"""
    def get_queryset(self):
        qs = super().get_queryset()
        if is_club_site():
            return qs.filter(assignment__course__is_open=True)
        return qs


StudentAssignmentManager = _StudentAssignmentDefaultManager.from_queryset(
    StudentAssignmentQuerySet)


class EventQuerySet(query.QuerySet):
    pass


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
        return super().get_queryset().filter(is_active=True)


class GraduateProfileQuerySet(models.QuerySet):
    def with_testimonial(self):
        return self.exclude(testimonial='')

    def get_only_required_fields(self):
        return (self.select_related("student_profile",
                                    "student_profile__branch",
                                    "student_profile__user", )
                .only("pk",
                      "student_profile_id",
                      "modified",
                      "graduation_year",
                      "photo",
                      "testimonial",
                      "student_profile__user_id",
                      "student_profile__branch__code",
                      "student_profile__user__photo",
                      "student_profile__user__cropbox_data",
                      "student_profile__user__first_name",
                      "student_profile__user__last_name",
                      "student_profile__user__patronymic",
                      "student_profile__user__gender", ))


GraduateProfileActiveManager = _GraduateProfileActiveManager.from_queryset(
    GraduateProfileQuerySet)


class AssignmentCommentQuerySet(models.QuerySet):
    pass


class _AssignmentCommentPublishedManager(LiveManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


AssignmentCommentPublishedManager = _AssignmentCommentPublishedManager.from_queryset(
    AssignmentCommentQuerySet)
