# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import django_filters
from crispy_forms.bootstrap import FormActions, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Row
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from learning.projects.models import Project
from learning.settings import PARTICIPANT_GROUPS
from users.models import CSCUser

EMPTY_CHOICE = ('', _('Any'))


class ProjectsFilter(django_filters.FilterSet):
    students = django_filters.ModelChoiceFilter(
        label=_("Student"),
        queryset=(CSCUser.objects
            .filter(
                groups__in=[PARTICIPANT_GROUPS.STUDENT_CENTER,
                            PARTICIPANT_GROUPS.GRADUATE_CENTER])
            .distinct()
            .all())
    )

    def filter_by_score(self, queryset, value):
        return queryset

    class Meta:
        model = Project
        fields = ['semester', 'project_type', 'supervisor', 'students',
                  'projectstudent__final_grade']

    @property
    def form(self):
        if not hasattr(self, '_form'):
            today = now().date()
            self._form = super(ProjectsFilter, self).form
            self._form.helper = FormHelper(self._form)
            self._form.helper.disable_csrf = True
            self._form.helper.form_method = "GET"
            for attr in self.Meta.fields:
                self._form.fields[attr].help_text = ""
            self._form.helper.layout = Layout(
                Row(
                    Div('semester', css_class="col-xs-4"),
                    Div('project_type', css_class="col-xs-4"),
                    Div('supervisor', css_class="col-xs-4"),
                ),
                Row(
                    Div('students', css_class="col-xs-4"),
                    Div('projectstudent__final_grade', css_class="col-xs-4"),
                ),
                Row(
                    Div(Submit('', _('Filter')), css_class="col-xs-4")
                )
            )
        return self._form

    # TODO: 1. Submit вровень со 2й строкой.
    # TODO: 2. Empty choice для типов практик. Переделать на Внешний/Внутренний и итоговую оценку тоже там добавить. Руководитель - ILIKE поиск
    # TODO: 3. Фильтр по оценке из связанных моделей. Хотя бы 1?