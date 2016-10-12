# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import django_filters
from crispy_forms.bootstrap import FormActions, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Row
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from core.widgets import DateTimeRangeWidget
from learning.admission.models import Applicant, Interview, Campaign

EMPTY_CHOICE = ('', _('Any'))


class FilterEmptyChoiceMixin(object):
    """add empty choice to all choice fields"""
    def __init__(self, *args, **kwargs):
        super(FilterEmptyChoiceMixin, self).__init__(*args, **kwargs)

        choices = filter(
            lambda f: isinstance(self.filters[f], django_filters.ChoiceFilter),
            self.filters)
        for field_name in choices:
            extended_choices = ((EMPTY_CHOICE,) +
                                self.filters[field_name].extra['choices'])
            self.filters[field_name].extra['choices'] = extended_choices


class ApplicantFilter(FilterEmptyChoiceMixin, django_filters.FilterSet):
    campaign = django_filters.ModelChoiceFilter(
        label=_("Campaign"),
        queryset=Campaign.objects.order_by("-code").all())
    second_name = django_filters.CharFilter(lookup_type='icontains',
                                            label=_("Second name"))

    class Meta:
        model = Applicant
        fields = ['status']

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super(ApplicantFilter, self).form
            self._form.fields["campaign"].help_text = ""
            self._form.fields["status"].help_text = ""
            self._form.fields["second_name"].help_text = ""
            self._form.helper = FormHelper()
            # Looks like I disable it due to GET method
            self._form.helper.disable_csrf = True
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("campaign", css_class="col-xs-4"),
                    Div("status", css_class="col-xs-4"),
                    Div("second_name", css_class="col-xs-4"),
                ),
                FormActions(Submit('', _('Filter'))))
        return self._form


class InterviewStatusFilter(django_filters.ChoiceFilter):
    AGREED = "agreed"
    AGREED_CHOICE = (AGREED, _('Agreed'))

    def __init__(self, *args, **kwargs):
        super(InterviewStatusFilter, self).__init__(*args, **kwargs)
        self.extra['choices'] = (self.AGREED_CHOICE,) + self.extra['choices']

    def filter(self, qs, value):
        if value == self.AGREED:
            qs = self.get_method(qs)(**{
                '%s__%s' % (self.name, "in"): [Interview.COMPLETED, Interview.WAITING]})
            return qs
        return super(InterviewStatusFilter, self).filter(qs, value)


class InterviewsFilter(FilterEmptyChoiceMixin, django_filters.FilterSet):
    status = InterviewStatusFilter(choices=Interview.STATUSES, label=_("Status"),
                                   help_text="")
    date = django_filters.MethodFilter(action='filter_by_date', label=_("Date"),
                                       help_text="", name="date")

    class Meta:
        model = Interview
        fields = ['status', 'date']

    def filter_by_date(self, queryset, value):
        try:
            day_start = datetime.datetime.strptime(value, '%d.%m.%Y')
        except ValueError:
            return queryset
        day_end = day_start + datetime.timedelta(days=1)
        return queryset.filter(
            date__range=(day_start, day_end)
        )

    @property
    def form(self):
        if not hasattr(self, '_form'):
            today = now().date()
            self._form = super(InterviewsFilter, self).form
            self._form.fields["status"].initial = InterviewStatusFilter.AGREED
            self._form.fields["date"].initial = today.strftime("%d.%m.%Y")
            self._form.helper = FormHelper(self._form)
            self._form.helper.disable_csrf = True
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div('status', css_class="col-xs-6"),
                    Div(PrependedText('date', '<i class="fa fa-calendar"></i>'),
                        css_class="col-xs-6"),
                ),
                Row(
                    FormActions(Div(Submit('', _('Filter')),
                                    css_class="col-xs-4"))
                )
            )
        return self._form