# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import django_filters
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from django.utils.translation import ugettext_lazy as _

from core.widgets import DateTimeRangeWidget
from learning.admission.models import Applicant, Interview

EMPTY_CHOICE = ('', '---------')


class ApplicantFilter(django_filters.FilterSet):
    second_name = django_filters.CharFilter(lookup_type='icontains',
                                            label=_("Second name"))

    class Meta:
        model = Applicant
        fields = ['campaign', 'status']

    def __init__(self, *args, **kwargs):
        super(ApplicantFilter, self).__init__(*args, **kwargs)
        # add empty choice to all choice fields:
        choices = filter(
            lambda f: isinstance(self.filters[f], django_filters.ChoiceFilter),
            self.filters)
        for field_name in choices:
            extended_choices = ((EMPTY_CHOICE,) +
                                self.filters[field_name].extra['choices'])
            self.filters[field_name].extra['choices'] = extended_choices

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super(ApplicantFilter, self).form
            self._form.fields["campaign"].help_text = ""
            self._form.fields["status"].help_text = ""
            self._form.fields["second_name"].help_text = ""
            self._form.helper = FormHelper()
            self._form.helper.disable_csrf = True
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Div('campaign', 'status', 'second_name'),
                FormActions(Submit('', _('Filter'))))
        return self._form


class InterviewsFilter(django_filters.FilterSet):
    date = django_filters.DateTimeFromToRangeFilter(name='date',
                                                    label=_("Date"),
                                                    widget=DateTimeRangeWidget)

    class Meta:
        model = Interview
        fields = ['decision']

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super(InterviewsFilter, self).form
            self._form.fields["decision"].initial = Interview.WAITING
            self._form.fields["decision"].help_text = ""
            self._form.fields["date"].help_text = ""
            self._form.helper = FormHelper(self._form)
            self._form.helper.disable_csrf = True
            self._form.helper.form_method = "GET"
            self._form.helper.layout.append(
                FormActions(Submit('', _('Filter'))))
        return self._form