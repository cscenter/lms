from typing import List

import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Row, Submit, Column
from django.conf import settings
from django.contrib.admin import SimpleListFilter

from django.utils.translation import gettext_lazy as _

from core.models import Branch
from courses.models import Semester, Course
from courses.utils import get_current_term_pair
from learning.models import Invitation
from learning.settings import InvitationCategories, StudentStatuses
from study_programs.models import AcademicDiscipline
from users.models import StudentProfile, StudentTypes, StudentAcademicDisciplineLog, StudentStatusLog


class StudentProfileFilter(django_filters.FilterSet):
    branch = django_filters.ChoiceFilter(
        label="Отделение",
        required=True,
        empty_label=None,
        choices=())
    year = django_filters.TypedChoiceFilter(
        label="Год поступления",
        field_name="year_of_admission",
        required=True,
        coerce=int)
    type = django_filters.ChoiceFilter(
        label="Тип профиля",
        required=False,
        choices=StudentTypes.choices)

    class Meta:
        model = StudentProfile
        fields = ['year', 'branch', 'type']

    def __init__(self, site_branches: List[Branch], data=None, **kwargs):
        assert len(site_branches) > 0
        super().__init__(data=data, **kwargs)
        self.filters['branch'].extra["choices"] = [(b.pk, b.name) for b in site_branches]
        if self.is_bound:
            branch_id = data.get('branch')
            branch = next((b for b in site_branches if str(b.pk) == branch_id), site_branches[0])
            current_term = get_current_term_pair(branch.get_timezone())
            year_range = range(branch.established, current_term.year + 1)
            self.filters['year'].extra["choices"] = [(y, y) for y in reversed(year_range)]

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super().form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("branch", css_class="col-xs-3"),
                    Div("year", css_class="col-xs-3"),
                    Div("type", css_class="col-xs-3"),
                    Div(Submit('', _('Filter'), css_class="btn-block -inline-submit"),
                        css_class="col-xs-3"),
                ))
        return self._form

    @property
    def qs(self):
        # Prevents returning all records
        if not self.is_bound or not self.is_valid():
            return self.queryset.none()
        return super().qs


# class InvitationCourseFilter(SimpleListFilter):
#     title = _('Course')
#     parameter_name = 'course'
#     template = 'admin/dropdown_listfilter.html'

#     def lookups(self, request, model_admin):
#         # Get courses from the invitation
#         invitation_id = request.GET.get('id')
#         if invitation_id:
#             try:
#                 invitation = Invitation.objects.get(pk=invitation_id)
#                 courses = invitation.courses.all().order_by('-pk').select_related('meta_course', 'semester')
#                 return [(course.pk, str(course)) for course in courses]
#             except Invitation.DoesNotExist:
#                 pass
#         return []

#     def queryset(self, request, queryset):
#         if self.value():
#             return queryset.filter(courses__pk=self.value())
#         return queryset


class EnrollmentInvitationFilter(django_filters.FilterSet):
    branches = django_filters.ChoiceFilter(
        label="Отделение",
        required=True,
        empty_label=None,
        choices=())
    semester = django_filters.ChoiceFilter(
        label="Семестр",
        choices=())
    category = django_filters.ChoiceFilter(
        label="Категория",
        choices=InvitationCategories.choices)
    name = django_filters.CharFilter(
        label="Название",
        lookup_expr='icontains')
    course = django_filters.ChoiceFilter(
        label=_('Course'),
        choices=(),
        method='filter_by_course')

    class Meta:
        model = Invitation
        fields = ['branches', 'name', 'semester', 'category', 'course']

    def __init__(self, site_branches: List[Branch], site_semesters: List[Semester], data=None, **kwargs):
        assert len(site_branches) > 0
        invitations = kwargs.get("queryset")
        super().__init__(data=data, **kwargs)
        self.filters['branches'].extra["choices"] = [(b.pk, b.name) for b in site_branches]
        self.filters['semester'].extra["choices"] = [(s.pk, s.name) for s in site_semesters]
        
        courses_choices = []
        if invitations:
            invitation_ids = invitations.values_list('id', flat=True)
            courses = Course.objects.filter(
                courseinvitation__invitation_id__in=invitation_ids
            ).select_related('meta_course', 'semester').distinct()
            courses_choices = [(course.pk, str(course)) for course in courses]
        self.filters['course'].extra["choices"] = courses_choices

    def filter_by_course(self, queryset, name, value):
        if value:
            return queryset.filter(courses__pk=value)
        return queryset

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super().form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("branches", css_class="col-xs-3"),
                    Div("name", css_class="col-xs-6"),
                    Div(Submit('', _('Filter'), css_class="btn-block -inline-submit"),
                        css_class="col-xs-3"),
                ),
                Row(
                    Div("semester", css_class="col-xs-3"),
                    Div("course", css_class="col-xs-3"),
                ),
                Row(
                    Div("category", css_class="col-xs-3"),
                ))
        return self._form

    @property
    def qs(self):
        # Do not return all records by default
        if not self.is_bound or not self.is_valid():
            return self.queryset.none()
        return super().qs

class StudentAcademicDisciplineLogFilter(django_filters.FilterSet):
    academic_discipline = django_filters.ModelChoiceFilter(
        label=_('Field of study'),
        queryset=AcademicDiscipline.objects.all(),
        required=False
    )
    former_academic_discipline = django_filters.ModelChoiceFilter(
        label=_('Former field of study'),
        queryset=AcademicDiscipline.objects.all(),
        required=False
    )
    is_processed = django_filters.BooleanFilter(
        label=_('Is processed'),
        required=False
    )
    branch = django_filters.ModelChoiceFilter(
        label=_('Branch'),
        queryset=Branch.objects.filter(site_id=settings.SITE_ID, active=True),
        field_name='student_profile__branch'
    )
    type = django_filters.ChoiceFilter(
        label=_("Type"),
        choices=StudentTypes.choices,
        field_name='student_profile__type'
    )

    class Meta:
        model = StudentAcademicDisciplineLog
        fields = ['academic_discipline', 'former_academic_discipline', 'is_processed', 'branch', 'type']

    @property
    def qs(self):
        queryset = super().qs
        return queryset.select_related(
            'academic_discipline',
            'former_academic_discipline',
            'student_profile__branch',
            'student_profile__user'
        )


    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super().form

            self._form.fields['branch'].label_from_instance=lambda obj: obj.name

            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Column(
                        "former_academic_discipline",
                        "academic_discipline",
                        css_class="col-xs-5"
                    ),
                    Column(
                        Column("type", "branch", css_class="col-xs-7"),
                        Column("is_processed", css_class="col-xs-5"),
                        css_class="col-xs-5"
                    ),
                    Column(
                        Submit("", _("Filter"), css_class="btn-block -inline-submit"),
                        Submit("download_csv", _('Download'), css_class="btn-block -inline-submit"),
                        Submit("mark_processed", _('Mark processed'), css_class="btn-block -inline-submit"),
                        css_class="col-xs-2",
                    )
                )
            )
        return self._form

class StudentStatusLogFilter(django_filters.FilterSet):
    STATUS_CHOICES = (("empty", _("Studying")),) + StudentStatuses.choices
    status = django_filters.ChoiceFilter(
        label=_('Status'),
        choices=STATUS_CHOICES,
        required=False,
        method='filter_by_status'
    )
    former_status = django_filters.ChoiceFilter(
        label=_('Former status'),
        choices=STATUS_CHOICES,
        required=False,
        method='filter_by_former_status'
    )
    is_processed = django_filters.BooleanFilter(
        label=_('Is processed'),
        required=False
    )
    branch = django_filters.ModelChoiceFilter(
        label=_('Branch'),
        queryset=Branch.objects.filter(site_id=settings.SITE_ID, active=True),
        field_name='student_profile__branch'
    )
    type = django_filters.ChoiceFilter(
        label=_("Type"),
        choices=StudentTypes.choices,
        field_name='student_profile__type',
        required=False
    )

    class Meta:
        model = StudentStatusLog
        fields = ['status', 'former_status', 'is_processed', 'branch', 'type']

    def filter_by_status(self, queryset, name, value):
        if value == "empty":
            return queryset.filter(status="")
        return queryset.filter(**{name: value})

    def filter_by_former_status(self, queryset, name, value):
        if value == "empty":
            return queryset.filter(former_status="")
        return queryset.filter(**{name: value})

    @property
    def qs(self):
        queryset = super().qs
        return queryset.select_related(
            'student_profile__branch',
            'student_profile__user'
        )

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super().form

            self._form.fields['branch'].label_from_instance=lambda obj: obj.name

            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Column(
                        "former_status",
                        "status",
                        css_class="col-xs-5"
                    ),
                    Column(
                        Column("type", "branch", css_class="col-xs-7"),
                        Column("is_processed", css_class="col-xs-5"),
                        css_class="col-xs-5"
                    ),
                    Column(
                        Submit("", _("Filter"), css_class="btn-block -inline-submit"),
                        Submit("download_csv", _('Download'), css_class="btn-block -inline-submit"),
                        Submit("mark_processed", _('Mark processed'), css_class="btn-block -inline-submit"),
                        css_class="col-xs-2",
                    )
                )
            )
        return self._form
