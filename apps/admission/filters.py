import datetime

import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Row, Submit

from django import forms
from django.conf import settings
from django.db.models import Q, QuerySet
from django.forms import SelectMultiple
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from admission.constants import InterviewInvitationStatuses, InterviewSections, InterviewFormats
from admission.forms import ApplicantFinalStatusForm
from admission.models import (
    Applicant,
    Campaign,
    Interview,
    InterviewInvitation,
    InterviewStream,
)
from core.models import University
from core.widgets import DateTimeRangeWidget


# Fields
class ApplicantStatusFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        if value == Applicant.PERMIT_TO_EXAM:
            return qs.exclude(
                **{f"{self.field_name}__exact": Applicant.REJECTED_BY_TEST}
            )
        return super().filter(qs, value)


class InterviewStatusFilter(django_filters.ChoiceFilter):
    AGREED = "agreed"
    AGREED_CHOICE = (AGREED, _("Approved and completed"))
    AGREED_STATUSES = [Interview.COMPLETED, Interview.APPROVED]

    def __init__(self, *args, choices, **kwargs):
        choices = (self.AGREED_CHOICE,) + choices
        super().__init__(*args, choices=choices, **kwargs)

    def filter(self, qs, value):
        if value == self.AGREED:
            return self.get_method(qs)(
                **{f"{self.field_name}__in": self.AGREED_STATUSES}
            )
        return super().filter(qs, value)


class InterviewInvitationStatusFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        if value == InterviewInvitationStatuses.EXPIRED:
            return self.get_method(qs)(
                Q(status=value)
                | (
                    Q(status=InterviewInvitationStatuses.NO_RESPONSE)
                    & Q(expired_at__lte=timezone.now())
                )
            )
        return super().filter(qs, value)


# Filters
class ApplicantFilter(django_filters.FilterSet):
    campaign = django_filters.ModelChoiceFilter(
        label=_("Campaign"),
        queryset=(
            Campaign.objects.filter(branch__site_id=settings.SITE_ID)
            .select_related("branch")
            .order_by("-year", "branch__order")
            .all()
        ),
        required=True,
        empty_label=None,
    )
    status = django_filters.ChoiceFilter(label=_("Status"), choices=Applicant.STATUS)
    last_name = django_filters.CharFilter(label=_("Surname"), lookup_expr="icontains")

    class Meta:
        model = Applicant
        fields = ["status"]

    @property
    def form(self):
        if not hasattr(self, "_form"):
            self._form = super(ApplicantFilter, self).form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("campaign", css_class="col-xs-3"),
                    Div("status", css_class="col-xs-3"),
                    Div("last_name", css_class="col-xs-4"),
                    Div(
                        Submit("", _("Filter"), css_class="btn-block -inline-submit"),
                        css_class="col-xs-2",
                    ),
                )
            )
        return self._form


class InterviewStreamFilter(django_filters.FilterSet):
    campaign = django_filters.ModelChoiceFilter(
        label=_("Campaign"),
        queryset=(
            Campaign.objects.filter(branch__site_id=settings.SITE_ID)
            .select_related("branch")
            .order_by("-year", "branch__order")
            .all()
        ),
        empty_label=None,
    )
    section = django_filters.ChoiceFilter(
        label=_("Interview Section"), choices=InterviewSections.choices
    )

    class Meta:
        model = InterviewStream
        fields = ["campaign", "section", "format"]

    @property
    def form(self):
        if not hasattr(self, "_form"):
            self._form = super(InterviewStreamFilter, self).form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("campaign", css_class="col-xs-3"), Div("section", css_class="col-xs-3"),
                       Div(Submit("", _("Filter"), css_class="btn-block -inline-submit"), css_class="col-xs-2"),
                )
            )
        return self._form


class InvitationCreateInterviewStreamFilter(InterviewStreamFilter):
    ApplicantTrack = [
        ("regular", _("Regular")),
        ("alternative", _("Alternative"))
    ]
    ApplicantWayToInterview = [
        ("exam", _("Exam")),
        ("olympiad", _("Olympiad")),
        ("golden_ticket", _("Golden ticket"))
    ]
    ApplicantMisses = [
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 3),
        (4, ">3")
    ]
    section = django_filters.ChoiceFilter(
        label=_("Interview Section"),
        choices=InterviewSections.choices,
        empty_label=None,
    )
    format = django_filters.ChoiceFilter(
        label=_("Interview format"), choices=InterviewFormats.choices
    )
    track = django_filters.ChoiceFilter(
        label=_("Applicant track"), choices=ApplicantTrack
    )
    way_to_interview = django_filters.ChoiceFilter(
        label=_("Applicant way to interview"), choices=ApplicantWayToInterview
    )
    number_of_misses = django_filters.ChoiceFilter(
        label=_("Applicant number of missed interviews"), choices=ApplicantMisses
    )
    last_name = django_filters.CharFilter(label=_("Last Name"))

    @property
    def form(self):
        if not hasattr(self, "_form"):
            self._form = super(InvitationCreateInterviewStreamFilter, self).form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("campaign", css_class="col-xs-3"), Div("section", css_class="col-xs-3"),
                        Div("format", css_class="col-xs-3"), Div("last_name", css_class="col-xs-3")),
                Row(
                    Div("track", css_class="col-xs-3"), Div("way_to_interview", css_class="col-xs-3"),
                        Div("number_of_misses", css_class="col-xs-3"),
                        Div(Submit("", _("Filter"), css_class="btn-block -inline-submit"), css_class="col-xs-2"),
                )
            )
        return self._form

    def filter_queryset(self, queryset):
        """
        Filter the queryset with the underlying form's `cleaned_data`. You must
        call `is_valid()` or `errors` before calling this method.

        This method should be overridden if additional filtering needs to be
        applied to the queryset before it is cached.
        """
        for name, value in self.form.cleaned_data.items():
            if name not in self.Meta.fields:
                continue
            queryset = self.filters[name].filter(queryset, value)
            assert isinstance(queryset, QuerySet), \
                "Expected '%s.%s' to return a QuerySet, but got a %s instead." \
                % (type(self).__name__, name, type(queryset).__name__)
        return queryset


class InterviewInvitationFilter(django_filters.FilterSet):
    last_name = django_filters.CharFilter(
        label=_("Last Name"),
        required=False,
        field_name="applicant__last_name",
        lookup_expr="icontains",
    )
    streams = django_filters.ModelMultipleChoiceFilter(
        label=_("Interview Streams"),
        queryset=InterviewStream.objects.get_queryset(),
        widget=SelectMultiple(
            attrs={"size": 1, "class": "multiple-select bs-select-hidden"}
        ),
        required=False,
    )
    status = InterviewInvitationStatusFilter(
        label=_("Status"), choices=InterviewInvitationStatuses.choices, required=False
    )

    class Meta:
        model = InterviewInvitation
        fields = ["last_name", "streams", "status"]

    def __init__(self, streams, **kwargs):
        super().__init__(**kwargs)
        self.filters["streams"].queryset = streams.prefetch_related("interviewers")

    @property
    def form(self):
        if not hasattr(self, "_form"):
            self._form = super().form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "POST"
            self._form.helper.layout = Layout(
                Row(
                    Div("last_name", css_class="col-xs-3"),
                    Div("streams", css_class="col-xs-4"),
                    Div("status", css_class="col-xs-3"),
                    Div(
                        Submit(
                            "filter-interview-invitation",
                            _("Show"),
                            css_class="btn btn-primary btn-outline btn-block -inline-submit",
                        ),
                        css_class="col-xs-2",
                    ),
                )
            )
        return self._form


class InterviewsFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.layout = Layout(
            Row(
                Div("status", css_class="col-xs-4"),
                Div("date", css_class="col-xs-5"),
                Div(
                    Submit("", _("Filter"), css_class="btn-block -inline-submit"),
                    css_class="col-xs-3",
                ),
            ),
        )
        super().__init__(*args, **kwargs)


class InterviewsCuratorFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.layout = Layout(
            Row(
                Div(Field("campaign"), css_class="col-xs-3"),
                Div("status", css_class="col-xs-3"),
                Div("date", css_class="col-xs-4"),
                Div(
                    Submit("", _("Filter"), css_class="btn-block -inline-submit"),
                    Submit(
                        "download_csv", "Скачать", css_class="btn-block -inline-primary"
                    ),
                    css_class="col-xs-2",
                ),
            ),
            Row(Div("my_interviews", css_class="col-xs-3")),
        )
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        campaign = cleaned_data.get("campaign")
        if campaign and cleaned_data.get("date"):
            tz = campaign.get_timezone()
            date_slice = cleaned_data["date"]
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
            cleaned_data["date"] = slice(start, stop, date_slice.step)


class InterviewsBaseFilter(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(
        field_name="date",
        label="Период собеседований",
        help_text="",
        widget=DateTimeRangeWidget,
    )
    status = django_filters.MultipleChoiceFilter(
        choices=Interview.STATUSES,
        label=_("Status"),
        help_text="",
        widget=SelectMultiple(
            attrs={"size": 1, "class": "multiple-select bs-select-hidden"}
        ),
    )

    class Meta:
        model = Interview
        fields = []


class InterviewsFilter(InterviewsBaseFilter):
    class Meta(InterviewsBaseFilter.Meta):
        form = InterviewsFilterForm
        fields = ["status", "date"]


class InterviewsCuratorFilter(InterviewsBaseFilter):
    campaign = django_filters.ModelChoiceFilter(
        field_name="applicant__campaign",
        label=_("Campaign"),
        queryset=(
            Campaign.objects.filter(branch__site_id=settings.SITE_ID)
            .select_related("branch")
            .order_by("-branch_id", "-year")
            .all()
        ),
        help_text="",
    )

    my_interviews = django_filters.ChoiceFilter(
        label="Показать",
        empty_label=None,  # hide empty choice
        choices=[
            ("1", "Мои собеседования"),
            ("", "Все собеседования"),
        ],
        method="display_own_interviews",
    )

    class Meta(InterviewsBaseFilter.Meta):
        form = InterviewsCuratorFilterForm
        fields = ["campaign", "status", "date"]

    def display_own_interviews(self, queryset, name, value):
        if value == "1":
            return queryset.filter(interviewers=self.request.user)
        return queryset


class ResultsFilter(django_filters.FilterSet):
    status = ApplicantStatusFilter(
        empty_label=None,
        choices=ApplicantFinalStatusForm.FINAL_CHOICES,
        label=_("Status"),
    )
    university_legacy = django_filters.ChoiceFilter(label=_("University"))

    class Meta:
        model = Applicant
        fields = ["status", "university_legacy", "level_of_education"]

    def __init__(self, *args, branch_code, **kwargs):
        super().__init__(*args, **kwargs)
        # Get universities based on requested branch
        qs = University.objects.order_by("name")
        university_choices = [(u.id, u.name) for u in qs.all()]
        self.filters["university_legacy"].extra["choices"] = university_choices

    @property
    def form(self):
        if not hasattr(self, "_form"):
            self._form = super().form
            self._form.helper = FormHelper()
            self._form.helper.form_method = "GET"
            self._form.helper.layout = Layout(
                Row(
                    Div("status", css_class="col-xs-3"),
                    Div("university_legacy", css_class="col-xs-3"),
                    Div("level_of_education", css_class="col-xs-3"),
                    Div(
                        Submit("", _("Filter"), css_class="btn-block -inline-submit"),
                        css_class="col-xs-3",
                    ),
                )
            )
        return self._form
