from typing import List

from django.apps import apps
from django.conf import settings

from django.db import models
from django.db.models import query, Subquery, Q, Prefetch, Count, Case, When, \
    Value, IntegerField

from core.utils import is_club_site
from core.settings.base import CENTER_FOUNDATION_YEAR
from courses.settings import SemesterTypes
from courses.utils import get_term_index, get_boundaries


class CourseTeacherQuerySet(query.QuerySet):
    def for_course(self, course_slug):
        course_pks = (self.model.course.field.related_model.objects
                         .filter(meta_course__slug=course_slug)
                         # Note: can't reset default ordering in a Subquery
                         .order_by("pk")
                         .values("pk"))
        return self.filter(course__in=Subquery(course_pks))


CourseTeacherManager = models.Manager.from_queryset(CourseTeacherQuerySet)


class AssignmentQuerySet(query.QuerySet):
    def prefetch_student_scores(self, student):
        """
        For each assignment prefetch requested student's score and comments
        count. Later on iterating over assignment we can get this data
        by calling `studentassignment_set.all()[0]`
        """
        StudentAssignment = self.model.studentassignment_set.field.model
        student_comments = Case(
            When(assignmentcomment__author_id=student.pk, then=Value(1)),
            output_field=IntegerField()
        )
        qs = (StudentAssignment.objects
              .only("pk", "assignment_id", "score")
              .filter(student=student)
              .annotate(student_comments_cnt=Count(student_comments))
              .order_by("pk"))  # optimize by overriding default order
        return self.prefetch_related(
            Prefetch("studentassignment_set", queryset=qs))


AssignmentManager = models.Manager.from_queryset(AssignmentQuerySet)


class CourseClassQuerySet(query.QuerySet):
    def for_calendar(self):
        return (self
                .select_related('course', 'course__meta_course',
                                'course__semester')
                .order_by('date', 'starts_at'))

    def for_timetable(self):
        return self.for_calendar().select_related('venue')

    def in_city(self, city_code):
        return self.in_cities([city_code])

    def in_cities(self, city_codes: List[str]):
        return self.filter(Q(course__city_id__in=city_codes,
                             course__is_correspondence=False) |
                           Q(course__is_correspondence=True))

    def in_month(self, year, month):
        date_start, date_end = get_boundaries(year, month)
        return self.filter(date__gte=date_start, date__lte=date_end)

    def for_student(self, user):
        return self.filter(course__enrollment__student_id=user.pk,
                           course__enrollment__is_deleted=False)

    def for_teacher(self, user):
        return self.filter(course__teachers=user)


class _CourseClassManager(models.Manager):
    def get_queryset(self):
        if is_club_site():
            return super().get_queryset().filter(course__is_open=True)
        else:
            return super().get_queryset()


CourseClassManager = _CourseClassManager.from_queryset(CourseClassQuerySet)


class _CourseDefaultManager(models.Manager):
    """On compsciclub.ru always restrict selection by open readings"""
    def get_queryset(self):
        # TODO: add test
        if is_club_site():
            return super().get_queryset().filter(is_open=True)
        else:
            return super().get_queryset()


class CourseQuerySet(models.QuerySet):
    def in_city(self, city_code):
        _q = {"is_correspondence": False}
        if isinstance(city_code, (list, tuple)):
            _q["city_id__in"] = city_code
        else:
            _q["city_id__exact"] = city_code
        return self.filter(Q(**_q) | Q(is_correspondence=True))

    # FIXME: remove
    def in_center_branches(self):
        return self.filter(city_id__in=settings.CENTER_BRANCHES_CITY_CODES)

    def for_teacher(self, user):
        return self.filter(teachers=user)

    # TODO: relocate
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


CourseDefaultManager = _CourseDefaultManager.from_queryset(CourseQuerySet)
