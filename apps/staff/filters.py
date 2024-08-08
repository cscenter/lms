from typing import List

import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Row, Submit

from django.utils.translation import gettext_lazy as _

from core.models import Branch
from courses.utils import get_current_term_pair
from users.models import StudentProfile, StudentTypes


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


class EnrollmentInvitationFilter(django_filters.FilterSet):
    branch = django_filters.ChoiceFilter(
        label="Отделение",
        required=True,
        empty_label=None,
        choices=())
    name = django_filters.CharFilter(
        label="Название",
        lookup_expr='icontains')

    class Meta:
        model = StudentProfile
        fields = ['branch', 'name']

    def __init__(self, site_branches: List[Branch], data=None, **kwargs):
        assert len(site_branches) > 0
        super().__init__(data=data, **kwargs)
        self.filters['branch'].extra["choices"] = [(b.pk, b.name) for b in site_branches]

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super().form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("branch", css_class="col-xs-3"),
                    Div("name", css_class="col-xs-6"),
                    Div(Submit('', _('Filter'), css_class="btn-block -inline-submit"),
                        css_class="col-xs-3"),
                ))
        return self._form

    @property
    def qs(self):
        # Do not return all records by default
        if not self.is_bound or not self.is_valid():
            return self.queryset.none()
        return super().qs
