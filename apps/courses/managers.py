from typing import List

from django.db import models
from django.db.models import (
    Case, Count, F, IntegerField, Prefetch, Q, Subquery, Value, When, query
)
from django.utils import timezone

from courses.constants import MaterialVisibilityTypes


class CourseTeacherQuerySet(query.QuerySet):
    # FIXME: do I need subquery here?
    def for_meta_course(self, meta_course):
        course_pks = (self
                      .model.course.field.related_model.objects
                      .filter(meta_course=meta_course)
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
        from learning.models import AssignmentSubmissionTypes, StudentAssignment

        # FIXME: get solutions count from meta['stats']['solutions'] instead of joining all submissions
        solutions_total = Case(
            When(Q(assignmentcomment__author_id=student.pk) &
                 Q(assignmentcomment__type=AssignmentSubmissionTypes.SOLUTION),
                 then=Value(1)),
            output_field=IntegerField()
        )
        qs = (StudentAssignment.objects
              .only("pk", "assignment_id", "score")
              .filter(student=student)
              .annotate(solutions_total=Count(solutions_total))
              .order_by("pk"))  # optimize by overriding default order
        return self.prefetch_related(
            Prefetch("studentassignment_set", queryset=qs)
        )


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

    def in_branches(self, *branches):
        """
        Returns distinct course classes for a given list of branches
        """
        if not branches:
            return self
        return self.filter(course__coursebranch__branch__in=branches).distinct()

    def for_student(self, user):
        # Get common courses classes and restricted to the student group
        common_classes = Q(courseclassgroup__isnull=True)
        restricted_to_student_group = Q(courseclassgroup__group_id=F('course__enrollment__student_group_id'))
        return (self.filter(common_classes | restricted_to_student_group,
                            course__enrollment__student_id=user.pk,
                            course__enrollment__is_deleted=False))

    def for_teacher(self, user):
        from courses.models import CourseTeacher
        spectator = CourseTeacher.roles.spectator
        return self.filter(course__teachers=user,
                           course__course_teachers__roles=~spectator)

    def with_public_materials(self):
        return self.filter(materials_visibility=MaterialVisibilityTypes.PUBLIC)


CourseClassManager = models.Manager.from_queryset(CourseClassQuerySet)


class CourseQuerySet(models.QuerySet):
    def available_in(self, branch):
        return self.filter(coursebranch__branch=branch)

    def available_on_site(self, site):
        return self.filter(coursebranch__branch__site=site).distinct()

    def made_by(self, branches: List):
        return self.filter(main_branch__in=branches)

    def in_branches(self, branches: List[int]):
        return (self.filter(coursebranch__branch__in=branches)
                .distinct('semester__index', 'meta_course__name', 'pk')
                .order_by('-semester__index', 'meta_course__name', 'pk'))

    def for_teacher(self, user):
        return self.filter(teachers=user)


CourseDefaultManager = models.Manager.from_queryset(CourseQuerySet)
