from typing import List, Union

from django.db import models
from django.db.models import query, Subquery, Q, Prefetch, Count, Case, When, \
    Value, IntegerField, F
from django.utils import timezone

from core.utils import is_club_site
from courses.constants import MaterialVisibilityTypes


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
    def with_future_deadline(self):
        """
        Returns assignments with unexpired deadlines.
        """
        return self.filter(deadline_at__gt=timezone.now())

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
    def select_calendar_data(self):
        return (self
                .select_related('course',
                                'course__meta_course',
                                'course__semester',
                                'course__main_branch')
                .defer('course__description',
                       'course__description_en',
                       'course__description_ru',
                       'course__main_branch__description',
                       'course__meta_course__description',
                       'course__meta_course__description_en',
                       'course__meta_course__description_ru',
                       'course__meta_course__short_description',
                       'course__meta_course__short_description_en',
                       'course__meta_course__short_description_ru'))

    # FIXME: possible duplicates. Add tests
    def in_branches(self, *branches):
        if not branches:
            return self
        return (self.filter(Q(course__main_branch__in=branches) |
                            Q(course__additional_branches__in=branches)))

    def for_student(self, user):
        # Get common courses classes and restricted to the student group
        common_classes = Q(courseclassgroup__isnull=True)
        restricted_to_student_group = Q(courseclassgroup__group_id=F('course__enrollment__student_group_id'))
        return (self.filter(common_classes | restricted_to_student_group,
                            course__enrollment__student_id=user.pk,
                            course__enrollment__is_deleted=False))

    def for_teacher(self, user):
        return self.filter(course__teachers=user)

    def with_public_materials(self):
        return self.filter(materials_visibility=MaterialVisibilityTypes.VISIBLE)


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
        if is_club_site():
            return super().get_queryset().filter(is_open=True)
        else:
            return super().get_queryset()


class CourseQuerySet(models.QuerySet):
    def available_in(self, branch):
        branches = [branch]
        return (self.filter(Q(main_branch__in=branches) |
                            Q(additional_branches__in=branches))
                .distinct('semester__index', 'meta_course__name', 'pk')
                .order_by('-semester__index', 'meta_course__name', 'pk'))

    def in_branches(self, branches: List[int]):
        return (self.filter(Q(main_branch__in=branches) |
                            Q(additional_branches__in=branches))
                .distinct('semester__index', 'meta_course__name', 'pk')
                .order_by('-semester__index', 'meta_course__name', 'pk'))

    def for_teacher(self, user):
        return self.filter(teachers=user)


CourseDefaultManager = _CourseDefaultManager.from_queryset(CourseQuerySet)
