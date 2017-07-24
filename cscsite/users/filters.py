from __future__ import unicode_literals, absolute_import

import django_filters
from django.db.models import Count, Case, When, Q, Value, F
from django.http import QueryDict

from learning.models import Enrollment
from users.models import CSCUser, SHADCourseRecord


class ListFilter(django_filters.Filter):
    """key=value1,value2,value3 filter for django_filters"""
    def filter(self, qs, value):
        value_list = value.split(u',')
        value_list = filter(None, value_list)
        return super(ListFilter, self).filter(qs, django_filters.fields.Lookup(
            value_list, 'in'))


class CSCUserFilter(django_filters.FilterSet):
    FILTERING_GROUPS = [CSCUser.group.VOLUNTEER,
                        CSCUser.group.STUDENT_CENTER,
                        CSCUser.group.GRADUATE_CENTER,
                        CSCUser.group.MASTERS_DEGREE]

    ENROLLMENTS_CNT_LIMIT = 12

    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

    name = django_filters.CharFilter(method='name_filter')
    cnt_enrollments = django_filters.CharFilter(method='cnt_enrollments_filter')
    # FIXME: replace with range?
    curriculum_year = ListFilter(name='curriculum_year')
    # TODO: TypedChoiceFilter?
    status = django_filters.CharFilter(method='status_filter')
    status_log = django_filters.CharFilter(method='status_log_filter')
    # FIXME: set cscuserstatuslog__created_0 and cscuserstatuslog__created_1 EXAMPLE: 2015-01-01%208:00
    cscuserstatuslog__created = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = CSCUser
        fields = ["name", "curriculum_year", "groups", "status",
                  "cnt_enrollments", "cscuserstatuslog__created"]

    def __init__(self, *args, **kwargs):
        self.empty_query = False
        super(CSCUserFilter, self).__init__(*args, **kwargs)
        # Remove empty values
        cleaned_data = QueryDict(mutable=True)
        if self.data:
            for filter_name in self.data:
                filter_values = self.data.getlist(filter_name)
                if not isinstance(filter_values, list):
                    filter_values = [filter_values]
                values = [v for v in filter_values if v]
                if values:
                    cleaned_data.setlist(filter_name, set(values))
        self.data = cleaned_data
        if "groups" not in self.data:
            if not self.data:
                self.empty_query = True
            groups = self.FILTERING_GROUPS[:]
            if "status" in self.data and "studying" in self.data["status"]:
                groups.remove(CSCUser.group.GRADUATE_CENTER)
            self.data.setlist("groups", groups)

    def cnt_enrollments_filter(self, queryset, name, value):
        value_list = value.split(u',')
        try:
            value_list = [int(v) for v in value_list if v]
            if not value_list:
                return queryset
        except ValueError:
            return queryset

        queryset = queryset.annotate(
            courses_cnt=
            # Remove unsuccessful grades, then distinctly count by pk
            Count(Case(
                When(Q(enrollment__grade=Enrollment.GRADES.not_graded) |
                     Q(enrollment__grade=Enrollment.GRADES.unsatisfactory),
                     then=Value(None)),
                default=F("enrollment__course_offering__course_id")
            ), distinct=True) +
            Count(Case(
                When(Q(shadcourserecord__grade=SHADCourseRecord.GRADES.not_graded) |
                     Q(shadcourserecord__grade=SHADCourseRecord.GRADES.unsatisfactory),
                     then=Value(None)),
                default=F("shadcourserecord")
            ), distinct=True) +
            # No need to filter online courses by grade
            Count("onlinecourserecord", distinct=True)
        )

        condition = Q(courses_cnt__in=value_list)
        if any(value > self.ENROLLMENTS_CNT_LIMIT for value in value_list):
            condition |= Q(courses_cnt__gt=self.ENROLLMENTS_CNT_LIMIT)

        return queryset.filter(condition)

    def status_filter(self, queryset, name, value):
        value_list = value.split(u',')
        value_list = [v for v in value_list if v]
        if "studying" in value_list and CSCUser.STATUS.expelled in value_list:
            return queryset
        elif "studying" in value_list:
            return queryset.exclude(status=CSCUser.STATUS.expelled)
        for value in value_list:
            if value not in CSCUser.STATUS:
                raise ValueError(
                    "CSCUserFilter: unrecognized status_filter choice")
        return queryset.filter(status__in=value_list).distinct()

    # FIXME: Difficult and unpredictable
    def name_filter(self, queryset, name, value):
        qstr = value.strip()
        tsquery = self._form_name_tsquery(qstr)
        if tsquery is None:
            return queryset
        else:
            return (queryset
                    .extra(where=["to_tsvector(first_name || ' ' || last_name) "
                                  "@@ to_tsquery(%s)"],
                           params=[tsquery])
                    .exclude(first_name__exact='',
                             last_name__exact=''))

    def _form_name_tsquery(self, qstr):
        if qstr is None or not (2 < len(qstr) < 100):
            return
        lexems = []
        for s in qstr.split(' '):
            lexeme = s.translate(self._lexeme_trans_map).strip()
            if len(lexeme) > 0:
                lexems.append(lexeme)
        if len(lexems) > 3:
            return
        return " & ".join("{}:*".format(l) for l in lexems)
