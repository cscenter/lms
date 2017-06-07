# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import django_filters
from crispy_forms.bootstrap import FormActions, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Row, Field
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from core.filters import FilterEmptyChoiceMixin
from learning.admission.models import Applicant, Interview, Campaign


class ApplicantStatusFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        if value == Applicant.PERMIT_TO_EXAM:
            return qs.exclude(**{
                '%s__%s' % (self.name, "exact"): Applicant.REJECTED_BY_TEST
            })
        return super().filter(qs, value)


class ApplicantFilter(FilterEmptyChoiceMixin, django_filters.FilterSet):
    campaign = django_filters.ModelChoiceFilter(
        label=_("Campaign"),
        queryset=(Campaign.objects
                  .select_related("city")
                  .order_by("-city__name", "-year").all()))
    status = ApplicantStatusFilter(choices=Applicant.STATUS,
                                   label=_("Status"))
    surname = django_filters.CharFilter(lookup_type='icontains',
                                        label=_("Surname"))

    class Meta:
        model = Applicant
        fields = ['status']

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super(ApplicantFilter, self).form
            self._form.fields["campaign"].help_text = ""
            self._form.fields["status"].help_text = ""
            self._form.fields["surname"].help_text = ""
            self._form.helper = FormHelper()
            # Looks like I disable it due to GET method
            self._form.helper.disable_csrf = True
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("campaign", css_class="col-xs-4"),
                    Div("status", css_class="col-xs-4"),
                    Div("surname", css_class="col-xs-4"),
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
                '%s__%s' % (self.name, "in"): [Interview.COMPLETED, Interview.APPROVED]})
            return qs
        return super(InterviewStatusFilter, self).filter(qs, value)


class InterviewsBaseFilter(FilterEmptyChoiceMixin, django_filters.FilterSet):
    status = InterviewStatusFilter(choices=Interview.STATUSES,
                                   label=_("Status"),
                                   help_text="")
    date = django_filters.MethodFilter(action='filter_by_date',
                                       name="date",
                                       label=_("Date"),
                                       help_text="")

    class Meta:
        model = Interview

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
            self._form = super().form
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


class InterviewsFilter(InterviewsBaseFilter):
    class Meta(InterviewsBaseFilter.Meta):
        fields = ['status', 'date']


class InterviewsCuratorFilter(InterviewsBaseFilter):
    campaign = django_filters.ModelChoiceFilter(
        name="applicant__campaign",
        label=_("Campaign"),
        queryset=(Campaign.objects
                  .select_related("city")
                  .order_by("-city__name", "-year").all()),
        help_text="")

    class Meta(InterviewsBaseFilter.Meta):
        fields = ['campaign', 'status', 'date']

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super(InterviewsCuratorFilter, self).form
            self._form.helper.layout = Layout(
                Row(
                    Div(Field('campaign'),
                        css_class="col-xs-4"),
                    Div('status', css_class="col-xs-4"),
                    Div(PrependedText('date', '<i class="fa fa-calendar"></i>'),
                        css_class="col-xs-4"),
                ),
                Row(
                    FormActions(Div(Submit('', _('Filter')),
                                    css_class="col-xs-4"))
                )
            )
        return self._form
