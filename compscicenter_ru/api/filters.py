from django import forms
from django.conf import settings
from django.http import QueryDict
from django_filters import FilterSet, Filter, ChoiceFilter

from courses.models import Course
from learning.settings import Branches
from my_compscicenter_ru.filters import BranchChoiceFilter
from study_programs.models import StudyProgramCourseGroup


class IntegerFilter(Filter):
    field_class = forms.IntegerField


class CoreCourseFilter(FilterSet):
    branch = ChoiceFilter(
        field_name="studyprogramcoursegroup__study_program__branch__code",
        empty_label=None,
        choices=Branches.choices)
    year = IntegerFilter(
        field_name='studyprogramcoursegroup__study_program__year',
        min_value=settings.CENTER_FOUNDATION_YEAR)

    class Meta:
        model = StudyProgramCourseGroup.courses.through
        fields = ('branch', 'year',)


class CourseFilter(FilterSet):
    branch = BranchChoiceFilter(field_name="branch__code", empty_label=None,
                                choices=Branches.choices)
    # TODO: restrict max value
    year = IntegerFilter(field_name='semester__year',
                         min_value=settings.CENTER_FOUNDATION_YEAR)

    class Meta:
        model = Course
        fields = ('branch', 'year')

    def __init__(self, data=None, queryset=None, request=None, **kwargs):
        """
        Resolves `branch` value in the next order:
            * query value
            * valid branch code from user settings
            * default branch code
        """
        if data is not None:
            data = data.copy()  # get a mutable copy of the QueryDict
        else:
            data = QueryDict(mutable=True)
        branch_code = data.pop("branch", None)
        if not branch_code and hasattr(request.user, "branch"):
            branch_code = [request.user.branch.code]
        # For unauthenticated users or users without valid branch code
        if not branch_code:
            branch_code = [settings.DEFAULT_BRANCH_CODE]
        data.setlist("branch", branch_code)
        super().__init__(data=data, queryset=queryset, request=request, **kwargs)
