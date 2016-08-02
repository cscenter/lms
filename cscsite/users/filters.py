from __future__ import unicode_literals, absolute_import

import django_filters
from django.db.models import Count, Case, When, Q, Value, F
from django.http import QueryDict

from learning.models import Enrollment
from users.models import CSCUser, ListFilter


class CSCUserFilter(django_filters.FilterSet):
    FILTERING_GROUPS = [CSCUser.group_pks.VOLUNTEER,
                        CSCUser.group_pks.STUDENT_CENTER,
                        CSCUser.group_pks.GRADUATE_CENTER,
                        CSCUser.group_pks.MASTERS_DEGREE]

    ENROLLMENTS_CNT_LIMIT = 12

    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

    name = django_filters.MethodFilter(action='name_filter')
    cnt_enrollments = django_filters.MethodFilter(action='cnt_enrollments_filter')
    # FIXME: replace with range?
    enrollment_year = ListFilter(name='enrollment_year')
    status = django_filters.MethodFilter(action='status_filter')
    status_log = django_filters.MethodFilter(action='status_log_filter')
    # FIXME: set cscuserstatuslog__created_0 and cscuserstatuslog__created_1 EXAMPLE: 2015-01-01%208:00
    cscuserstatuslog__created = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = CSCUser
        fields = ["name", "enrollment_year", "groups", "status",
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
                groups.remove(CSCUser.group_pks.GRADUATE_CENTER)
            self.data.setlist("groups", groups)

    def cnt_enrollments_filter(self, queryset, value):
        value_list = value.split(u',')
        value_list = [v for v in value_list if v]
        if not value_list:
            return queryset
        try:
            value_list = map(int, value_list)
        except ValueError:
            return queryset

        queryset = queryset.annotate(
            courses_cnt=
            Count(Case(
                When(Q(enrollment__grade=Enrollment.GRADES.not_graded) | Q(
                    enrollment__grade=Enrollment.GRADES.unsatisfactory),
                     then=Value(None)),
                default=F("enrollment")
            ), distinct=True) +
            Count("shadcourserecord", distinct=True) +
            Count("onlinecourserecord", distinct=True)
        )

        condition = Q(courses_cnt__in=value_list)
        if any(value > self.ENROLLMENTS_CNT_LIMIT for value in value_list):
            condition |= Q(courses_cnt__gt=self.ENROLLMENTS_CNT_LIMIT)

        return queryset.filter(condition)

    def status_filter(self, queryset, value):
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
    def name_filter(self, queryset, value):
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
