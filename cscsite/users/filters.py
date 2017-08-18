from __future__ import unicode_literals, absolute_import

from django.db.models import Count, Case, When, Q, Value, F
from django.http import QueryDict
from django_filters import BaseInFilter, NumberFilter, FilterSet, CharFilter, \
    DateTimeFromToRangeFilter

from learning.models import Enrollment
from users.models import CSCUser, SHADCourseRecord


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass


# TODO: Rewrite with DRF
class UserFilter(FilterSet):
    FILTERING_GROUPS = [CSCUser.group.VOLUNTEER,
                        CSCUser.group.STUDENT_CENTER,
                        CSCUser.group.GRADUATE_CENTER,
                        CSCUser.group.MASTERS_DEGREE]

    ENROLLMENTS_MAX = 12

    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

    name = CharFilter(method='name_filter')
    cnt_enrollments = CharFilter(method='cnt_enrollments_filter')
    curriculum_year = NumberInFilter(name='curriculum_year')
    cities = CharInFilter(name='city_id')
    # TODO: Restrict choices
    groups = NumberInFilter(name='groups', distinct=True)
    # TODO: TypedChoiceFilter?
    status = CharFilter(method='status_filter')
    status_log = CharFilter(method='status_log_filter')
    # FIXME: set cscuserstatuslog__created_0 and cscuserstatuslog__created_1 EXAMPLE: 2015-01-01%208:00
    cscuserstatuslog__created = DateTimeFromToRangeFilter()

    class Meta:
        model = CSCUser
        fields = ["name", "cities", "curriculum_year", "groups", "status",
                  "cnt_enrollments", "cscuserstatuslog__created"]

    def __init__(self, *args, **kwargs):
        self.empty_query = False
        super().__init__(*args, **kwargs)
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
        # Set default groups
        if "groups" not in self.data:
            if not self.data:
                self.empty_query = True
            groups = self.FILTERING_GROUPS[:]
            if "status" in self.data and "studying" in self.data["status"]:
                groups.remove(CSCUser.group.GRADUATE_CENTER)
            # FIXME: BaseInFilter don't understand foo[]=&foo[]=
            self.data.setlist("groups", [",".join(str(g) for g in groups)])

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
        if any(value > self.ENROLLMENTS_MAX for value in value_list):
            condition |= Q(courses_cnt__gt=self.ENROLLMENTS_MAX)

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

    # FIXME: Can I rewrite it with new __search lookup expr?
    def name_filter(self, queryset, name, value):
        qstr = value.strip()
        tsquery = self._form_name_tsquery(qstr)
        if tsquery is None:
            return queryset
        else:
            qs = (queryset
                    .extra(where=["to_tsvector(first_name || ' ' || last_name) "
                                  "@@ to_tsquery(%s)"],
                           params=[tsquery])
                    .exclude(first_name__exact='',
                             last_name__exact=''))
            return qs

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
