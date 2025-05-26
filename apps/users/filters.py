from django_filters.fields import MultipleChoiceField
from django_filters.rest_framework import CharFilter, FilterSet

from django.db.models import Case, Count, F, Q, Value, When
from django.forms import SelectMultiple
from django.conf import settings
from django.contrib.sites.models import Site

from core.filters import CharInFilter, NumberInFilter
from learning.settings import GradeTypes, StudentStatuses
from users.models import StudentProfile


class SelectMultipleCSVSupport(SelectMultiple):
    """
    1. Values can be provided as csv string:  ?foo=bar,baz
    2. Values can be provided as query array: ?foo=bar&foo=baz

    Note: Duplicate and empty values are skipped from results
    """

    def value_from_datadict(self, data, files, name):
        value = super().value_from_datadict(data, files, name)
        if isinstance(value, str):
            ret = {x.strip() for x in value.rstrip(',').split(',') if x}
        elif value is not None and len(value) > 0:
            ret = set()
            for csv in value:
                ret.update({x.strip() for x in
                           csv.rstrip(',').split(',') if x})
        else:
            ret = []
        return list(ret)


class MultipleChoiceCSVField(MultipleChoiceField):
    widget = SelectMultipleCSVSupport


def replace_single_quotes(column_name):
    """Returns `replace` postgres function call that removes single quotes"""
    return f"replace({column_name}, '''', '')"


class StudentFilter(FilterSet):
    ENROLLMENTS_MAX = 12

    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

    name = CharFilter(method='name_filter')
    branches = CharInFilter(field_name='branch_id')
    profile_types = CharInFilter(field_name='type')
    year_of_curriculum = NumberInFilter(field_name='year_of_curriculum')
    year_of_admission = NumberInFilter(field_name='year_of_admission')
    types = CharInFilter(field_name='type')
    # FIXME: choice validation
    status = CharFilter(label='Student Status', method='status_filter')
    cnt_enrollments = CharFilter(label='Enrollments',
                                 method='courses_filter')
    academic_disciplines = CharInFilter(field_name='academic_disciplines', distinct=True)
    partners = NumberInFilter(field_name='partner')
    is_paid_basis = NumberInFilter(field_name='is_paid_basis')
    uni_graduation_year = NumberInFilter(label='University graduation year',
                                        method='uni_graduation_year_filter')

    class Meta:
        model = StudentProfile
        fields = ("name", "branches", "profile_types", "year_of_curriculum",
                  "year_of_admission", "types", "status", "cnt_enrollments",
                  "academic_disciplines", "partners", "is_paid_basis", "uni_graduation_year")

    @property
    def qs(self):
        if not self.form.changed_data:
            return self.queryset.none()

        return super().qs.filter(site=Site.objects.get(pk=settings.SITE_ID))

    def courses_filter(self, queryset, name, value):
        value_list = value.split(u',')
        try:
            value_list = [int(v) for v in value_list if v]
            if not value_list:
                return queryset
        except ValueError:
            return queryset

        queryset = queryset.annotate(
            courses_total=
            # Remove unsuccessful grades, then distinctly count by pk
            Count(Case(
                When(user__enrollment__grade__in=[*GradeTypes.unsatisfactory_grades, *GradeTypes.unset_grades],
                     then=Value(None)),
                default=F("user__enrollment__course__meta_course_id")
            ), distinct=True) +
            Count(Case(
                When(user__shadcourserecord__grade__in=[*GradeTypes.unsatisfactory_grades, *GradeTypes.unset_grades],
                     then=Value(None)),
                default=F("user__shadcourserecord")
            ), distinct=True) +
            # No need to filter online courses by grade
            Count("user__onlinecourserecord", distinct=True)
        )
        condition = Q(courses_total__in=[v for v in value_list
                                         if v <= self.ENROLLMENTS_MAX])
        if any(value > self.ENROLLMENTS_MAX for value in value_list):
            condition |= Q(courses_total__gt=self.ENROLLMENTS_MAX)
        return queryset.filter(condition)

    def uni_graduation_year_filter(self, queryset, name, value):
        condition = Q(graduate_without_diploma=True) & Q(graduation_year__isnull=False) & Q(graduation_year__in=[year                                                                                                          for year in value if year != 0])
        if any(year == 0 for year in value):
            condition |= Q(graduate_without_diploma=True)
        return queryset.filter(condition)

    def status_filter(self, queryset, name, value):
        value_list = value.split(u',')
        value_list = [v for v in value_list if v]
        if "studying" in value_list:
            value_list.append('')
        for value in value_list:
            # TODO: remove after adding explicit status
            if not value or value == "studying":
                continue
            if value not in StudentStatuses.values:
                raise ValueError("StudentFilter: unrecognized status")
        return queryset.filter(status__in=value_list).distinct()

    def name_filter(self, queryset, name, value):
        qstr = value.strip()
        tsquery = self._form_name_tsquery(qstr)
        if tsquery is None:
            return queryset
        else:
            tsvector_text = (f"{replace_single_quotes('users_user.first_name')}"
                             f" || ' ' || "
                             f"{replace_single_quotes('users_user.last_name')}")
            qs = (queryset
                  .extra(where=[f"to_tsvector({tsvector_text}) @@ to_tsquery({replace_single_quotes('%s')})"],
                         params=[tsquery])
                  .exclude(user__first_name__exact='',
                           user__last_name__exact=''))
            return qs

    def _form_name_tsquery(self, qstr):
        if qstr is None or not (2 <= len(qstr) < 100):
            return
        lexems = []
        for s in qstr.split(' '):
            lexeme = s.translate(self._lexeme_trans_map).strip()
            if len(lexeme) > 0:
                lexems.append(lexeme)
        if len(lexems) > 3:
            return
        return " & ".join("{}:*".format(l) for l in lexems)
