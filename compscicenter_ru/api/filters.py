from django import forms
from django.conf import settings
from django.db.models import Q
from django_filters import Filter, ChoiceFilter
from django_filters.constants import EMPTY_VALUES
from django_filters.rest_framework import FilterSet

from core.models import Branch
from courses.constants import SemesterTypes
from courses.utils import get_term_index
from lms.filters import CoursesFilter


class IntegerFilter(Filter):
    field_class = forms.IntegerField


class BranchCodeFilter(ChoiceFilter):
    def filter(self, qs, value):
        """
        Return courses made by compscicenter.ru that are available in the
        target branch.
        """
        if value == self.null_value:
            value = None
        branch = next(b for b in self.parent.site_branches if b.code == value)
        term_index = get_term_index(branch.established, SemesterTypes.AUTUMN)
        qs = (qs
              .available_in(branch.pk)
              .filter(main_branch__site_id=settings.SITE_ID,
                      main_branch__active=True,
                      semester__index__gte=term_index))
        return qs


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
    branch = BranchCodeFilter(empty_label=None, null_label=None)
    academic_year = AcademicYearFilter(label='Academic Year')

    class Meta(CoursesFilter.Meta):
        fields = ('branch', 'academic_year')


class AlumniFilter(FilterSet):
    # TODO: We could avoid left join with `core_branch` table
    #  by using `branch__in=Branch.objects.for_site()` on filtering by site
    site = IntegerFilter(label='Site',
                         field_name='student_profile__branch__site',
                         min_value=1, max_value=1)

    def __init__(self, data=None, *args, **kwargs):
        if data is not None and 'site' not in data:
            data = data.copy()
            data['site'] = settings.SITE_ID
        super().__init__(data, *args, **kwargs)
