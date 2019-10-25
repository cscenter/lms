from typing import List

from django.db import models
from django.db.models import query, Subquery, Q, Prefetch, Count, Case, When, \
    Value, IntegerField

from core.utils import is_club_site
from courses.utils import get_boundaries


class CourseTeacherQuerySet(query.QuerySet):
    # FIXME: do I need subquery here?
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
                                'course__semester', 'course__branch')
                .order_by('course__pk', 'date', 'starts_at', 'pk'))

    def for_timetable(self):
        return self.for_calendar().select_related('venue', 'venue__location')

    def in_branches(self, *branches: List[int]):
        return (self.filter(Q(course__branch_id__in=branches) |
                            Q(course__additional_branches__in=branches))
                .distinct('date', 'starts_at', 'course__pk', 'pk')
                .order_by('date', 'starts_at', 'course__pk', 'pk'))

    # FIXME: rename?
    def in_month(self, year, month):
        """
        Get boundaries for the month with complete weeks and return classes
        in this range.
        """
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
    def available_in(self, branch: int):
        return (self.filter(Q(branch_id=branch) |
                            Q(additional_branches=branch))
                .distinct('semester__index', 'meta_course__name', 'pk')
                .order_by('-semester__index', 'meta_course__name', 'pk'))

    def for_teacher(self, user):
        return self.filter(teachers=user)


CourseDefaultManager = _CourseDefaultManager.from_queryset(CourseQuerySet)
