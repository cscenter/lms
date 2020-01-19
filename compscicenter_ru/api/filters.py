from django import forms
from django.conf import settings
from django.db.models import Q
from django.http import QueryDict
from django_filters import FilterSet, Filter
from django_filters.constants import EMPTY_VALUES

from core.models import Branch
from courses.constants import SemesterTypes
from courses.models import Course
from courses.utils import get_term_index
from learning.settings import Branches
from lms.filters import BranchCodeFilter, CoursesFilter


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


class CoursesPublicFilter(CoursesFilter):
    branch = BranchCodeFilter(field_name="branch__code", empty_label=None,
                              choices=Branch.objects.none())
    # TODO: restrict max value
    academic_year = AcademicYearFilter(label='Academic Year')

    class Meta(CoursesFilter.Meta):
        fields = ('branch', 'academic_year')
