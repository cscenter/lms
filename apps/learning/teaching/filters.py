from django_filters import ChoiceFilter, FilterSet

from django.utils.translation import gettext_lazy as _

from learning.models import Enrollment, StudentAssignment, StudentGroup
from learning.services import StudentGroupService

filter_by_score = (
    ("any", _("All")),  # Default
    ("no", _("Without score")),
    ("yes", _("With grade")),
)


filter_by_comments = (
    ("any", _("No matter")),
    ("student", _("From student")),
    ("teacher", _("From teacher")),
    ("empty", _("Without comments")),
)


class ScoreFilter(ChoiceFilter):
    def filter(self, qs, value):
        if value == self.null_value:
            value = None
        if value == "no":
            return qs.filter(score__isnull=True)
        elif value == "yes":
            return qs.filter(score__isnull=False)
        else:
            return qs


class CommentFilter(ChoiceFilter):
    def filter(self, qs, value):
        if value == self.null_value:
            value = None
        types_ = StudentAssignment.CommentAuthorTypes
        if value == "student":
            return qs.filter(last_comment_from=types_.STUDENT)
        elif value == "teacher":
            return qs.filter(last_comment_from=types_.TEACHER)
        elif value == "empty":
            return qs.filter(last_comment_from=types_.NOBODY)
        else:
            return qs


class StudentGroupFilter(ChoiceFilter):
    def filter(self, qs, value):
        if value == self.null_value or value == "any":
            value = None
        if value:
            group_students = (Enrollment.objects
                              .filter(course=self.parent.course,
                                      student_group_id=value)
                              .values_list('student_id', flat=True))
            return qs.filter(student_id__in=group_students)
        else:
            return qs


class AssignmentStudentsFilter(FilterSet):
    score = ScoreFilter(empty_label=None, choices=filter_by_score)
    comment = CommentFilter(empty_label=None, choices=filter_by_comments)
    student_group = StudentGroupFilter(empty_label=None, choices=StudentGroup.objects.none())

    class Meta:
        model = StudentAssignment
        fields = ('student_group', 'score', 'comment')

    def __init__(self, course, data=None, queryset=None, request=None, **kwargs):
        super().__init__(data=data, queryset=queryset, request=request, **kwargs)
        self.course = course
        student_group_choices = StudentGroupService.get_choices(course)
        student_group_choices.insert(0, ('any', _('All')))
        self.form['student_group'].field.choices = student_group_choices
