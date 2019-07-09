from django.conf import settings
from django.db.models import Count, Case, When, Q, Value, F
from django_filters.rest_framework import BaseInFilter, NumberFilter, \
    FilterSet, CharFilter

from learning.settings import StudentStatuses, GradeTypes
from users.constants import AcademicRoles
from users.models import User


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class RolesInFilter(NumberInFilter):
    def filter(self, qs, value):
        qs = super().filter(qs, value)
        return qs.filter(group__site_id=settings.SITE_ID)


class CharInFilter(BaseInFilter, CharFilter):
    pass


class UserFilter(FilterSet):
    FILTERING_GROUPS = [
        AcademicRoles.VOLUNTEER,
        AcademicRoles.STUDENT,
        AcademicRoles.GRADUATE,
        AcademicRoles.MASTERS_DEGREE,
    ]

    ENROLLMENTS_MAX = 12

    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

    name = CharFilter(method='name_filter')
    cities = CharInFilter(field_name='city_id')
    curriculum_year = NumberInFilter(field_name='curriculum_year')
    # TODO: Restrict choices
    groups = RolesInFilter(field_name='group__role', distinct=True)
    # TODO: TypedChoiceFilter?
    status = CharFilter(method='status_filter')
    cnt_enrollments = CharFilter(method='cnt_enrollments_filter')

    class Meta:
        model = User
        fields = ("name", "cities", "curriculum_year", "groups", "status",
                  "cnt_enrollments",)

    def __init__(self, data, **kwargs):
        self.empty_query = not data or all(not v for v in data.values())
        # FIXME: what about groups[] ?
        if not self.empty_query and data:
            data = data.copy()
            # Skip invalid values
            query = {int(g) for g in data.get("groups", "").split(",") if g}
            # Note: can failed with ValueError. Should validate values first
            groups = set(self.FILTERING_GROUPS) & query
            # Specify superset for `groups` filter field if no values provided
            if not groups:
                groups = self.FILTERING_GROUPS[:]
                if "studying" in data.get("status", []):
                    groups.remove(AcademicRoles.GRADUATE)
            # Special case - show `studying` among graduated
            only_graduate_selected = (groups == {AcademicRoles.GRADUATE})
            if "studying" in data.get("status", []) and only_graduate_selected:
                self.empty_query = True
            else:
                # FIXME: BaseInFilter doesn't understand foo[]=&foo[]=
                data.setlist("groups", [",".join(str(g) for g in groups)])
        super().__init__(data, **kwargs)

    @property
    def qs(self):
        if self.empty_query:
            return self.queryset.none()
        return super().qs

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
                When(Q(enrollment__grade=GradeTypes.NOT_GRADED) |
                     Q(enrollment__grade=GradeTypes.UNSATISFACTORY),
                     then=Value(None)),
                default=F("enrollment__course__meta_course_id")
            ), distinct=True) +
            Count(Case(
                When(Q(shadcourserecord__grade=GradeTypes.NOT_GRADED) |
                     Q(shadcourserecord__grade=GradeTypes.UNSATISFACTORY),
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
        if "studying" in value_list and StudentStatuses.EXPELLED in value_list:
            return queryset
        elif "studying" in value_list:
            return queryset.exclude(status=StudentStatuses.EXPELLED)
        for value in value_list:
            if value not in StudentStatuses.values:
                raise ValueError(
                    "UserFilter: unrecognized status_filter choice")
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
