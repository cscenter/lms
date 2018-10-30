from typing import List

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import query, Prefetch, Q, Count, Case, When, Value, \
    IntegerField, Subquery

from core.utils import is_club_site
from learning.calendar import get_bounds_for_calendar_month
from learning.settings import SEMESTER_TYPES, CENTER_FOUNDATION_YEAR
from learning.utils import get_term_index


class CourseOfferingTeacherQuerySet(query.QuerySet):
    def for_course(self, course_slug):
        offerings_ids = (self.model.course_offering.field.related_model.objects
                         .filter(meta_course__slug=course_slug)
                         # Note: can't reset default ordering in a Subquery
                         .order_by("pk")
                         .values("pk"))
        return self.filter(course_offering__in=Subquery(offerings_ids))


CourseOfferingTeacherManager = models.Manager.from_queryset(
    CourseOfferingTeacherQuerySet)


class AssignmentQuerySet(query.QuerySet):
    def list(self):
        return (self
                .only("title", "course_offering_id", "is_online", "deadline_at")
                .prefetch_related("assignmentattachment_set")
                .order_by('deadline_at', 'title'))

    def with_progress(self, student):
        """Prefetch progress on assignments for student"""
        from learning.models import StudentAssignment
        qs = (StudentAssignment.objects
              .only("pk", "assignment_id", "grade")
              .filter(student=student)
              .annotate(student_comments_cnt=Count(
                Case(When(assignmentcomment__author_id=student.pk,
                          then=Value(1)),
                     output_field=IntegerField())))
              .order_by("pk"))  # optimize by overriding default order
        return self.prefetch_related(
            Prefetch("studentassignment_set", queryset=qs))


AssignmentManager = models.Manager.from_queryset(AssignmentQuerySet)


class StudentAssignmentQuerySet(query.QuerySet):
    def for_user(self, user):
        related = ['assignment',
                   'assignment__course_offering',
                   'assignment__course_offering__meta_course',
                   'assignment__course_offering__semester']
        return (self
                .filter(student=user)
                .select_related(*related)
                .order_by('assignment__course_offering__meta_course__name',
                          'assignment__deadline_at',
                          'assignment__title'))

    def in_term(self, term):
        return self.filter(assignment__course_offering__semester_id=term.id)


class _StudentAssignmentDefaultManager(models.Manager):
    """On compsciclub.ru always restrict selection by open reading"""
    def get_queryset(self):
        if is_club_site():
            return super().get_queryset().filter(
                assignment__course_offering__is_open=True)
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


class CourseClassQuerySet(query.QuerySet):
    # FIXME: Tests for club part!!!
    def for_calendar(self, user):
        q = (self
             .select_related('venue',
                             'course_offering',
                             'course_offering__meta_course',
                             'course_offering__semester')
             .order_by('date', 'starts_at'))
        # Hide summer classes on compsciclub.ru if user not enrolled in
        # FIXME: Performance issue.
        if is_club_site():
            # XXX: On join enrollment table we get a lot of duplicates.
            # Clean them with right `.order` and `.distinct()`!
            summer_classes_enrolled_in = Q(
                course_offering__is_open=True,
                course_offering__semester__type=SEMESTER_TYPES.summer,
                course_offering__enrollment__student_id=user.pk,
                course_offering__enrollment__is_deleted=False)
            others = (Q(course_offering__is_open=True) &
                      ~Q(course_offering__semester__type=SEMESTER_TYPES.summer))
            q = q.filter(others)
        return q

    def in_city(self, city_code):
        return self.filter(Q(course_offering__city_id=city_code,
                             course_offering__is_correspondence=False) |
                           Q(course_offering__is_correspondence=True))

    def in_cities(self, city_codes: List[str]):
        return self.filter(course_offering__city_id__in=city_codes)

    def in_month(self, year, month):
        date_start, date_end = get_bounds_for_calendar_month(year, month)
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

    def in_cities(self, city_codes: List[str]):
        return self.filter(venue__city_id__in=city_codes)

    def in_month(self, year, month):
        date_start, date_end = get_bounds_for_calendar_month(year, month)
        return self.filter(date__gte=date_start, date__lte=date_end)


class CourseOfferingQuerySet(models.QuerySet):
    def in_city(self, city_code):
        _q = {"is_correspondence": False}
        if isinstance(city_code, (list, tuple)):
            _q["city_id__in"] = city_code
        else:
            _q["city_id__exact"] = city_code
        return self.filter(Q(**_q) | Q(is_correspondence=True))

    def in_center_branches(self):
        return self.filter(city_id__in=settings.CENTER_BRANCHES_CITY_CODES)

    def for_teacher(self, user):
        return self.filter(teachers=user)

    def from_center_foundation(self):
        Semester = apps.get_model('learning', 'Semester')
        center_foundation_term_index = get_term_index(CENTER_FOUNDATION_YEAR,
                                                      Semester.TYPES.autumn)
        return self.filter(semester__index__gte=center_foundation_term_index)

    def get_offerings_base_queryset(self):
        """Returns list of available courses for CS Center"""
        User = apps.get_model('users', 'User')
        prefetch_teachers = Prefetch(
            'teachers',
            queryset=User.objects.only("id", "first_name", "last_name",
                                       "patronymic"))
        return (self
                .select_related('meta_course', 'semester')
                .only("pk", "city_id", "is_open",
                      "materials_video", "materials_slides", "materials_files",
                      "meta_course__name", "meta_course__slug",
                      "semester__year", "semester__index", "semester__type")
                .from_center_foundation()
                .prefetch_related(prefetch_teachers)
                .order_by('-semester__year', '-semester__index',
                          'meta_course__name'))

    def reviews_for_course(self, co):
        return (self
                .defer("description")
                .select_related("semester")
                .filter(meta_course_id=co.meta_course_id,
                        semester__index__lte=co.semester.index)
                .in_city(co.get_city())
                .exclude(reviews__isnull=True)
                .exclude(reviews__exact='')
                .order_by("-semester__index"))


class _CourseOfferingDefaultManager(models.Manager):
    """On compsciclub.ru always restrict selection by open reading"""
    def get_queryset(self):
        # TODO: add test
        if is_club_site():
            return super().get_queryset().filter(is_open=True)
        else:
            return super().get_queryset()


CourseOfferingDefaultManager = _CourseOfferingDefaultManager.from_queryset(
    CourseOfferingQuerySet)


class _EnrollmentDefaultManager(models.Manager):
    """On compsciclub.ru always restrict selection by open reading"""
    def get_queryset(self):
        if is_club_site():
            return super().get_queryset().filter(course_offering__is_open=True)
        else:
            return super().get_queryset()


class _EnrollmentActiveManager(models.Manager):
    def get_queryset(self):
        if is_club_site():
            return super().get_queryset().filter(course_offering__is_open=True,
                                                 is_deleted=False)
        else:
            return super().get_queryset().filter(is_deleted=False)


class EnrollmentQuerySet(models.QuerySet):
    pass


EnrollmentDefaultManager = _EnrollmentDefaultManager.from_queryset(
    EnrollmentQuerySet)
EnrollmentActiveManager = _EnrollmentActiveManager.from_queryset(
    EnrollmentQuerySet)
