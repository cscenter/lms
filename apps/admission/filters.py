import datetime

import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Row, Submit

from django import forms
from django.conf import settings
from django.db.models import Q
from django.forms import SelectMultiple
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from admission.constants import InterviewInvitationStatuses, InterviewSections
from admission.forms import ResultsModelForm
from admission.models import (
    Applicant, Campaign, Interview, InterviewInvitation, InterviewStream
)
from core.models import University
from core.widgets import DateTimeRangeWidget


# Fields
class ApplicantStatusFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        if value == Applicant.PERMIT_TO_EXAM:
            return qs.exclude(**{
                f"{self.field_name}__exact": Applicant.REJECTED_BY_TEST
            })
        return super().filter(qs, value)


class InterviewStatusFilter(django_filters.ChoiceFilter):
    AGREED = "agreed"
    AGREED_CHOICE = (AGREED, _('Approved and completed'))
    AGREED_STATUSES = [Interview.COMPLETED, Interview.APPROVED]

    def __init__(self, *args, choices, **kwargs):
        choices = (self.AGREED_CHOICE,) + choices
        super().__init__(*args, choices=choices, **kwargs)

    def filter(self, qs, value):
        if value == self.AGREED:
            return self.get_method(qs)(**{
                f"{self.field_name}__in": self.AGREED_STATUSES
            })
        return super().filter(qs, value)


class InterviewInvitationStatusFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        if value == InterviewInvitationStatuses.EXPIRED:
            return self.get_method(qs)(
                Q(status=value) |
                (Q(status=InterviewInvitationStatuses.NO_RESPONSE) & Q(expired_at__lte=timezone.now()))
            )
        return super().filter(qs, value)


# Filters
class ApplicantFilter(django_filters.FilterSet):
    campaign = django_filters.ModelChoiceFilter(
        label=_("Campaign"),
        queryset=(Campaign.objects
                  .filter(branch__site_id=settings.SITE_ID)
                  .select_related("branch")
                  .order_by("-year", "branch__order").all()),
        required=True,
        empty_label=None)
    status = django_filters.ChoiceFilter(
        label=_("Status"),
        choices=Applicant.STATUS)
    last_name = django_filters.CharFilter(
        label=_("Surname"),
        lookup_expr='icontains')

    class Meta:
        model = Applicant
        fields = ['status']

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super(ApplicantFilter, self).form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("campaign", css_class="col-xs-3"),
                    Div("status", css_class="col-xs-3"),
                    Div("last_name", css_class="col-xs-4"),
                    Div(Submit('', _('Filter'),
                               css_class="btn-block -inline-submit"),
                        css_class="col-xs-2"),
                ))
        return self._form


class InterviewStreamFilter(django_filters.FilterSet):
    campaign = django_filters.ModelChoiceFilter(
        label=_("Campaign"),
        queryset=(Campaign.objects
                  .filter(branch__site_id=settings.SITE_ID)
                  .select_related("branch")
                  .order_by("-year", "branch__order").all()),
        empty_label=None)
    section = django_filters.ChoiceFilter(
        label=_("Interview Section"),
        choices=InterviewSections.choices)

    class Meta:
        model = InterviewStream
        fields = ['campaign', 'section']

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super(InterviewStreamFilter, self).form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("campaign", css_class="col-xs-3"),
                    Div("section", css_class="col-xs-3"),
                    Div(Submit('', _('Filter'),
                               css_class="btn-block -inline-submit"),
                        css_class="col-xs-2"),
                ))
        return self._form


class RequiredSectionInterviewStreamFilter(InterviewStreamFilter):
    section = django_filters.ChoiceFilter(
        label=_("Interview Section"),
        choices=InterviewSections.choices,
        empty_label=None)


class InterviewInvitationFilter(django_filters.FilterSet):
    last_name = django_filters.CharFilter(
        label=_("Last Name"),
        required=False,
        field_name='applicant__last_name',
        lookup_expr='icontains')
    streams = django_filters.ModelMultipleChoiceFilter(
        label=_("Interview Streams"),
        queryset=InterviewStream.objects.get_queryset(),
        widget=SelectMultiple(attrs={"size": 1,
                                     "class": "multiple-select bs-select-hidden"
                                     }),
        required=False)
    status = InterviewInvitationStatusFilter(
        label=_("Status"),
        choices=InterviewInvitationStatuses.choices,
        required=False
    )

    class Meta:
        model = InterviewInvitation
        fields = ['last_name', 'streams', 'status']

    def __init__(self, streams, **kwargs):
        super().__init__(**kwargs)
        self.filters['streams'].queryset = streams

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super().form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "POST"
            self._form.helper.layout = Layout(
                Row(
                    Div("last_name", css_class="col-xs-3"),
                    Div("streams", css_class="col-xs-4"),
                    Div("status", css_class="col-xs-3"),
                    Div(Submit('filter-interview-invitation', _('Show'),
                               css_class="btn btn-primary btn-outline btn-block -inline-submit"),
                        css_class="col-xs-2"),
                ))
        return self._form


class InterviewsFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.layout = Layout(
            Row(
                Div('status', css_class="col-xs-4"),
                Div('date', css_class="col-xs-5"),
                Div(Submit('', _('Filter'),
                           css_class="btn-block -inline-submit"),
                    css_class="col-xs-3"),
            ),
        )
        super().__init__(*args, **kwargs)


class InterviewsCuratorFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.layout = Layout(
            Row(
                Div(Field('campaign'), css_class="col-xs-3"),
                Div('status', css_class="col-xs-3"),
                Div('date', css_class="col-xs-4"),
                Div(Submit('', _('Filter'),
                           css_class="btn-block -inline-submit"),
                    css_class="col-xs-2"),
            ),
        )
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        campaign = cleaned_data.get('campaign')
        if campaign and cleaned_data.get('date'):
            tz = campaign.get_timezone()
            date_slice = cleaned_data['date']
            start = date_slice.start
            stop = date_slice.stop
            # Make sure campaign timezone has correct offset and replace
            # tzinfo with campaign timezone
            if isinstance(start, datetime.datetime):
                start_naive = timezone.make_naive(start)
                start = tz.localize(start_naive)
            if isinstance(stop, datetime.datetime):
                stop_naive = timezone.make_naive(stop)
                stop = tz.localize(stop_naive)
            cleaned_data['date'] = slice(start, stop, date_slice.step)


class InterviewsBaseFilter(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(
        field_name="date",
        label="Период собеседований",
        help_text="",
        widget=DateTimeRangeWidget)
    status = django_filters.MultipleChoiceFilter(
        choices=Interview.STATUSES,
        label=_("Status"),
        help_text="",
        widget=SelectMultiple(attrs={"size": 1, "class": "multiple-select bs-select-hidden"}))

    class Meta:
        model = Interview
        fields = []


class InterviewsFilter(InterviewsBaseFilter):
    class Meta(InterviewsBaseFilter.Meta):
        form = InterviewsFilterForm
        fields = ['status', 'date']


class InterviewsCuratorFilter(InterviewsBaseFilter):
    campaign = django_filters.ModelChoiceFilter(
        field_name="applicant__campaign",
        label=_("Campaign"),
        queryset=(Campaign.objects
                  .filter(branch__site_id=settings.SITE_ID)
                  .select_related("branch")
                  .order_by("-branch_id", "-year").all()),
        help_text="")

    class Meta(InterviewsBaseFilter.Meta):
        form = InterviewsCuratorFilterForm
        fields = ['campaign', 'status', 'date']


class ResultsFilter(django_filters.FilterSet):
    status = ApplicantStatusFilter(empty_label=None,
                                   choices=ResultsModelForm.FINAL_CHOICES,
                                   label=_("Status"))
    university = django_filters.ChoiceFilter(label=_("University"))

    class Meta:
        model = Applicant
        fields = ['status', 'university', 'level_of_education']

    def __init__(self, *args, branch_code, **kwargs):
        super().__init__(*args, **kwargs)
        # Get universities based on requested branch
        qs = University.objects.order_by("name")
        university_choices = [(u.id, u.name) for u in qs.all()]
        self.filters['university'].extra["choices"] = university_choices

    @property
    def form(self):
        if not hasattr(self, '_form'):
            self._form = super().form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("status", css_class="col-xs-3"),
                    Div("university", css_class="col-xs-3"),
                    Div("level_of_education", css_class="col-xs-3"),
                    Div(Submit('', _('Filter'),
                               css_class="btn-block -inline-submit"),
                        css_class="col-xs-3"),
                ))
        return self._form
