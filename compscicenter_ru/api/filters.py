from django import forms
from django.conf import settings
from django.db.models import Q
from django.http import QueryDict
from django_filters import FilterSet, Filter
from django_filters.constants import EMPTY_VALUES

from courses.constants import SemesterTypes
from courses.models import Course
from courses.utils import get_term_index
from learning.settings import Branches
from lms.filters import BranchChoiceFilter


class IntegerFilter(Filter):
    field_class = forms.IntegerField


class AcademicYearFilter(IntegerFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()
        term_index = get_term_index(value, SemesterTypes.AUTUMN)
        return self.get_method(qs)(Q(semester__index=term_index) |
                                   Q(semester__index=term_index + 1))


class CourseFilter(FilterSet):
    branch = BranchChoiceFilter(field_name="branch__code", empty_label=None,
                                choices=Branches.choices)
    # TODO: restrict max value
    academic_year = AcademicYearFilter(label='Academic Year',
                                       min_value=settings.CENTER_FOUNDATION_YEAR)

    class Meta:
        model = Course
        fields = ('branch', 'academic_year')

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
