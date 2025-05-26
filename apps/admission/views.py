import csv
import logging
import uuid
import zoneinfo
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib import parse

import pytz
from braces.views import UserPassesTestMixin
from django_filters.views import BaseFilterView, FilterMixin
from extra_views.formsets import BaseModelFormSetView
from rest_framework import serializers
from vanilla import GenericModelView, TemplateView

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Case, Count, Prefetch, Q, Value, When, Subquery, F
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.http.response import Http404, HttpResponseForbidden
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse as django_reverse
from django.utils import formats, timezone
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.generic.base import RedirectView, TemplateResponseMixin
from django.views.generic.edit import BaseCreateView, ModelFormMixin
from django.views.generic.list import BaseListView

from admission.filters import (
    ApplicantFilter,
    InterviewInvitationFilter,
    InterviewsCuratorFilter,
    InterviewsFilter,
    InterviewStreamFilter,
    InvitationCreateInterviewStreamFilter,
    ResultsFilter,
)
from admission.forms import (
    ApplicantFinalStatusForm,
    ApplicantForm,
    ApplicantReadOnlyForm,
    ConfirmationAuthorizationForm,
    ConfirmationForm,
    InterviewAssignmentsForm,
    InterviewCommentForm,
    InterviewForm,
    InterviewFromStreamForm,
    InterviewStreamInvitationForm,
)
from admission.models import (
    Acceptance,
    Applicant,
    ApplicantStatusLog,
    Campaign,
    Comment,
    Contest,
    Interview,
    InterviewAssignment,
    InterviewInvitation,
    InterviewSlot,
    InterviewStream,
    Olympiad,
)
from admission.services import (
    CampaignContestsImportState,
    EmailQueueService,
    create_applicant_status_log,
    create_invitation,
    create_student_from_applicant,
    get_acceptance_ready_to_confirm,
    get_applicants_for_invitation,
    get_latest_contest_results_task,
    get_meeting_time,
    get_ongoing_interview_streams,
    get_streams,
    manual_status_change
)
from core.db.fields import ScoreField
from core.http import AuthenticatedHttpRequest, HttpRequest
from core.models import Branch
from core.timezone import get_now_utc, now_local
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.urls import reverse
from core.utils import bucketize, render_markdown
from grading.api.yandex_contest import YandexContestAPI
from users.api.serializers import PhotoSerializerField
from users.mixins import CuratorOnlyMixin
from users.models import User
from users.services import UniqueUsernameError

from .constants import (
    SESSION_CONFIRMATION_CODE_KEY,
    ApplicantStatuses,
    ChallengeStatuses,
    ContestTypes,
    InterviewInvitationStatuses,
    InterviewSections, InterviewFormats,
)
from .selectors import get_interview_invitation, get_occupied_slot

logger = logging.getLogger(__name__)


def get_applicant_context(request, applicant_id) -> Dict[str, Any]:
    branches = Branch.objects.for_site(site_id=settings.SITE_ID)
    qs = Applicant.objects.select_related(
        "exam", "campaign__branch__site", "online_test", "olympiad", "university_legacy"
    ).prefetch_related(
        Prefetch("status_logs", queryset=ApplicantStatusLog.objects.select_related("entry_author"))
    ).filter(campaign__branch__in=branches, pk=applicant_id)
    applicant = get_object_or_404(qs)
    online_test = applicant.get_testing_record()
    exam = applicant.get_exam_record()
    olympiad = applicant.get_olympiad_record()
    # Fetch contest records
    contest_pks = []
    if online_test and online_test.yandex_contest_id:
        contest_pks.append(online_test.yandex_contest_id)
    if exam and exam.yandex_contest_id:
        contest_pks.append(exam.yandex_contest_id)
    if olympiad and olympiad.yandex_contest_id:
        contest_pks.append(olympiad.yandex_contest_id)
    contests = {}
    if contest_pks:
        filters = [Q(contest_id__in=contest_pks), Q(campaign_id=applicant.campaign_id)]
        queryset = Contest.objects.filter(*filters)
        contests = bucketize(queryset, key=lambda o: o.type)
    context = {
        "applicant": applicant,
        "applicant_form": ApplicantReadOnlyForm(request=request, instance=applicant),
        "campaign": applicant.campaign,
        "contests": contests,
        "ContestTypes": ContestTypes,
        "exam": exam,
        "online_test": online_test,
        "olympiad": olympiad,
        "similar_applicants": applicant.get_similar().select_related("campaign__branch__site"),
    }
    return context


class InterviewerOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_interviewer or user.is_curator


def get_interview_invitation_sections(invitation: InterviewInvitation):
    occupied = invitation.interview.section if invitation.interview_id else None
    sections = set()
    for stream in invitation.streams.all():
        sections.add(stream.section)
    return [
        {"name": InterviewSections.values[s], "occupied": s == occupied}
        for s in sections
    ]


class InterviewerSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="user_detail")
    full_name = serializers.CharField(source="get_full_name")
    last_name = serializers.CharField()
    photo = PhotoSerializerField(
        User.ThumbnailSize.INTERVIEW_LIST, thumbnail_options={"use_stab": False}
    )

    class Meta:
        model = User
        fields = ("url", "full_name", "last_name", "photo")


class InterviewSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    interviewers = InterviewerSerializer(many=True)

    class Meta:
        model = Interview
        fields = ("date", "time", "interviewers")

    def get_date(self, obj: Interview):
        """
        Returns date part in a local time zone.

        Note:
            serializers.DateTimeField enforces time zone to the UTC.
        """
        return obj.date_local().strftime(DATE_FORMAT_RU)

    def get_time(self, obj: Interview):
        """
        Returns time part in a local time zone.

        Note:
            serializers.DateTimeField enforces time zone to the UTC.
        """
        return obj.date_local().strftime(TIME_FORMAT_RU)


def get_interview_stream_filterset(input_serializer: serializers.Serializer):
    filters = {"campaign": input_serializer.validated_data["campaign"]}
    if input_serializer.validated_data["section"]:
        filters["section"] = input_serializer.validated_data["section"]
    interview_stream_filterset = InterviewStreamFilter(
        data=input_serializer.validated_data,
        queryset=(
            InterviewStream.objects.filter(**filters).order_by(
                "-date", "-start_at", "pk"
            )
        ),
    )
    return interview_stream_filterset


class InterviewInvitationCreateView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "lms/admission/send_interview_invitations.html"

    # page number validation is not included
    class FilterSerializer(serializers.Serializer):
        campaign = serializers.PrimaryKeyRelatedField(
            required=True,
            queryset=(
                Campaign.objects.filter(
                    branch__site_id=settings.SITE_ID
                ).select_related("branch")
            ),
        )
        section = serializers.ChoiceField(
            choices=InterviewSections.choices, required=True
        )
        format = serializers.ChoiceField(
            choices=InterviewFormats.choices, required=False
        )
        track = serializers.ChoiceField(
            choices=InvitationCreateInterviewStreamFilter.ApplicantTrack, required=False
        )
        way_to_interview = serializers.ChoiceField(
            choices=InvitationCreateInterviewStreamFilter.ApplicantWayToInterview, required=False
        )
        number_of_misses = serializers.ChoiceField(
            choices=InvitationCreateInterviewStreamFilter.ApplicantMisses, required=False
        )
        last_name = serializers.CharField(required=False)

    class InputSerializer(serializers.Serializer):
        streams = serializers.ListField(
            child=serializers.IntegerField(min_value=1), min_length=1, allow_empty=False
        )
        ids = serializers.ListField(
            label="List of participant identifiers",
            child=serializers.IntegerField(min_value=1),
            min_length=1,
            allow_empty=False,
        )

    def get(self, request, *args, **kwargs):
        serializer = self.FilterSerializer(data=request.GET)
        if not serializer.is_valid(raise_exception=False):
            campaign = get_default_campaign_for_user(request.user)
            campaign_id = campaign.id if campaign else ""
            section = InterviewSections.ALL_IN_ONE
            url = reverse("admission:interviews:invitations:send")
            url = f"{url}?campaign={campaign_id}&section={section}"
            return HttpResponseRedirect(redirect_to=url)
        context = self.get_context_data(filter_serializer=serializer, **kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        filter_serializer = self.FilterSerializer(data=request.GET)
        if not filter_serializer.is_valid(raise_exception=False):
            messages.error(self.request, "Приглашения не были созданы.")
            context = self.get_context_data(
                filter_serializer=filter_serializer, **kwargs
            )
            return self.render_to_response(context)

        input_serializer = self.InputSerializer(data=request.POST)
        if not input_serializer.is_valid(raise_exception=False):
            messages.error(self.request, "Выберите поступающих перед отправкой формы.")
            context = self.get_context_data(
                filter_serializer=filter_serializer, **kwargs
            )
            return self.render_to_response(context)

        interview_stream_filterset = self.get_interview_stream_filterset(
            filter_serializer
        )
        streams = list(
            interview_stream_filterset.qs.filter(
                pk__in=input_serializer.validated_data["streams"]
            )
            # location data used in email context)
            .select_related("venue__city")
        )

        # Create interview invitations
        campaign = filter_serializer.validated_data["campaign"]
        section = filter_serializer.validated_data["section"]
        format = filter_serializer.validated_data.get("format", "")
        track = filter_serializer.validated_data.get("track", "")
        way_to_interview = filter_serializer.validated_data.get("way_to_interview", "")
        number_of_misses = filter_serializer.validated_data.get("number_of_misses", "")
        last_name = filter_serializer.validated_data.get("last_name", "")
        applicants = get_applicants_for_invitation(campaign=campaign, section=section, format=format,
                                                   last_name=last_name, track=track, way_to_interview=way_to_interview,
                                                   number_of_misses=number_of_misses)
        applicants = applicants.filter(pk__in=input_serializer.validated_data["ids"])
        free_slots = sum(stream.slots_free_count for stream in streams)
        if free_slots < len(applicants):
            messages.error(self.request, "Суммарное количество слотов выбранных потоков меньше, чем количество "
                                         "выбранных абитуриентов.")
            context = self.get_context_data(
                filter_serializer=filter_serializer, **kwargs
            )
            return self.render_to_response(context)
        with transaction.atomic():
            for applicant in applicants:
                applicant.campaign = campaign
                invitation = create_invitation(streams, applicant)
                EmailQueueService.generate_interview_invitation(
                    invitation, streams, url_builder=request.build_absolute_uri
                )
        messages.success(request, "Приглашения успешно созданы", extra_tags="timeout")
        url = reverse("admission:interviews:invitations:send")
        redirect_to = f"{url}?campaign={campaign.id}&section={section}&format={format}" \
                        f"&last_name={last_name}&track={track}&way_to_interview={way_to_interview}" \
                        f"&number_of_misses={number_of_misses}"
        return HttpResponseRedirect(redirect_to)

    @staticmethod
    def get_interview_stream_filterset(serializer: serializers.Serializer):
        invitations_waiting_for_response = Count(
            Case(
                When(
                    interview_invitations__expired_at__lte=get_now_utc(),
                    then=Value(None),
                ),
                When(
                    interview_invitations__status=InterviewInvitationStatuses.NO_RESPONSE,
                    then=Value(1),
                ),
                default=Value(None),
            )
        )
        slots_and_invitations = F('slots_occupied_count') + F('invitations')
        is_interviewers_max_ok = Q(interviewers_max__gt=slots_and_invitations) | Q(interviewers_max__isnull=True)
        is_slots_count_ok = Q(slots_count__gt=slots_and_invitations)
        return InvitationCreateInterviewStreamFilter(
            data=serializer.validated_data,
            queryset=(
                get_ongoing_interview_streams()
                .annotate(invitations=invitations_waiting_for_response)
                .filter(is_interviewers_max_ok, is_slots_count_ok)
                .order_by("-date", "-start_at", "pk")
            ),
        )

    def get_context_data(self, **kwargs):
        filter_serializer = kwargs["filter_serializer"]
        campaign = filter_serializer.validated_data["campaign"]
        section = filter_serializer.validated_data["section"]
        format = filter_serializer.validated_data.get("format", "")
        track = filter_serializer.validated_data.get("track", "")
        way_to_interview = filter_serializer.validated_data.get("way_to_interview", "")
        number_of_misses = filter_serializer.validated_data.get("number_of_misses", "")
        last_name = filter_serializer.validated_data.get("last_name", "")
        interview_stream_filterset = self.get_interview_stream_filterset(
            filter_serializer
        )

        applicants = (
            get_applicants_for_invitation(campaign=campaign, section=section, format=format, last_name=last_name,
                                          track=track,
                                          way_to_interview=way_to_interview, number_of_misses=number_of_misses)
            .select_related(
                "exam",
                "online_test",
                "campaign",
                "university_legacy",
                "campaign__branch",
            )
            .annotate(
                exam__score_coalesce=Coalesce(
                    "exam__score", Value(-1, output_field=ScoreField())
                ),
                test__score_coalesce=Coalesce("online_test__score", Value(-1)),
            )
            .order_by("-exam__score_coalesce", "-test__score_coalesce", "-pk")
        )

        paginator = Paginator(applicants, 50)
        page_number = self.request.GET.get("page")
        page = paginator.get_page(page_number)
        paginator_url = reverse("admission:interviews:invitations:send")
        paginator_url = f"{paginator_url}?campaign={campaign.id}&section={section}&format={format}" \
                        f"&last_name={last_name}&track={track}&way_to_interview={way_to_interview}" \
                        f"&number_of_misses={number_of_misses}"
        context = {
            "stream_filter_form": interview_stream_filterset.form,
            "stream_form": InterviewStreamInvitationForm(
                streams=interview_stream_filterset.qs
            ),
            "applicants": page.object_list,
            "paginator_url": paginator_url,
            "paginator": paginator,
            "page": page,
        }
        return context


class InterviewInvitationListView(
    CuratorOnlyMixin, TemplateResponseMixin, BaseListView
):
    model = InterviewStream
    template_name = "lms/admission/interview_invitation_list.html"
    paginate_by = 50

    class InputSerializer(serializers.Serializer):
        campaign = serializers.PrimaryKeyRelatedField(
            required=True,
            queryset=(Campaign.objects.filter(branch__site_id=settings.SITE_ID)),
        )
        section = serializers.ChoiceField(
            choices=InterviewSections.choices, required=True, allow_blank=True
        )

    def get(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.GET)
        if not serializer.is_valid(raise_exception=False):
            campaign = get_default_campaign_for_user(request.user)
            campaign_id = campaign.id if campaign else ""
            url = reverse("admission:interviews:invitations:list")
            url = f"{url}?campaign={campaign_id}&section="
            return HttpResponseRedirect(redirect_to=url)
        context = self.get_context_data(input_serializer=serializer, **kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        input_serializer = kwargs["input_serializer"]
        interview_stream_filterset = get_interview_stream_filterset(input_serializer)
        invitations_waiting_for_response = Count(
            Case(
                When(
                    interview_invitations__expired_at__lte=get_now_utc(),
                    then=Value(None),
                ),
                When(
                    interview_invitations__status=InterviewInvitationStatuses.NO_RESPONSE,
                    then=Value(1),
                ),
                default=Value(None),
            )
        )
        interview_streams = (
            interview_stream_filterset.qs.select_related("venue")
            .annotate(invitations_total=invitations_waiting_for_response)
            .defer("venue__description", "venue__directions")
            .prefetch_related("interviewers")
        )
        # Fetch filtered invitations
        filters = {"applicant__campaign": input_serializer.validated_data["campaign"]}
        if input_serializer.validated_data["section"]:
            filters["streams__section"] = input_serializer.validated_data["section"]
        invitation_queryset = (
            InterviewInvitation.objects.select_related(
                "interview__venue__city", "applicant"
            )
            .filter(**filters)
            .prefetch_related("streams", "interview__interviewers")
            .order_by("applicant__last_name", "applicant_id", "pk")
        )
        interview_filterset = InterviewInvitationFilter(
            interview_stream_filterset.qs,
            data=self.request.POST or None,
            prefix="interview-invitation",
            queryset=invitation_queryset,
        )

        paginator = Paginator(interview_filterset.qs.distinct(), 50)
        page_number = self.request.GET.get("page")
        page = paginator.get_page(page_number)
        campaign = input_serializer.validated_data["campaign"]
        section = input_serializer.validated_data["section"]
        paginator_url = reverse("admission:interviews:invitations:list")
        paginator_url = f"{paginator_url}?campaign={campaign.id}&section={section}"

        interview_invitations = []
        for invitation in page.object_list:
            applicant = invitation.applicant
            interview = invitation.interview
            # Avoid additional queries on fetching time zone
            if invitation.interview_id:
                interview.applicant = applicant
                interview.applicant.campaign = input_serializer.validated_data[
                    "campaign"
                ]
            # TODO: add serializer
            student_invitation = {
                "applicant": applicant,
                "sections": get_interview_invitation_sections(invitation),
                "interview": InterviewSerializer(
                    interview, context={"request": self.request}
                ).data,
                "status": {
                    "value": invitation.status,
                    "label": invitation.get_status_display(),
                    "code": InterviewInvitationStatuses.get_code(invitation.status),
                },
            }
            interview_invitations.append(student_invitation)

        context = {
            "interview_stream_filter_form": interview_stream_filterset.form,
            "interview_invitation_filter_form": interview_filterset.form,
            "interview_invitations": interview_invitations,
            "paginator_url": paginator_url,
            "paginator": paginator,
            "page": page,
            "interview_streams": interview_streams,
        }
        return context


def get_contest_results_import_info(
    campaign: Campaign,
) -> Dict[str, CampaignContestsImportState]:
    data = {}
    contest_types = [ContestTypes.TEST, ContestTypes.EXAM, ContestTypes.OLYMPIAD]
    for contest_type in contest_types:
        task = get_latest_contest_results_task(campaign, contest_type)
        info = CampaignContestsImportState(
            campaign=campaign, contest_type=contest_type, latest_task=task
        )
        data[contest_type] = info
    return data


class ApplicantListView(CuratorOnlyMixin, FilterMixin, generic.ListView):
    request: AuthenticatedHttpRequest
    context_object_name = "applicants"
    model = Applicant
    template_name = "lms/admission/applicant_list.html"
    filterset_class = ApplicantFilter
    paginate_by = 50

    def get_queryset(self):
        branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        return (
            Applicant.objects.filter(campaign__branch__in=branches)
            .select_related(
                "exam",
                "online_test",
                "olympiad",
                "campaign",
                "university_legacy",
                "campaign__branch",
            )
            .prefetch_related("interviews")
            .annotate(
                exam__score_coalesce=Coalesce(
                    "exam__score", Value(-1, output_field=ScoreField())
                ),
                test__score_coalesce=Coalesce("online_test__score", Value(-1)),
                olympiad__total_score_coalesce=Coalesce(
                    F("olympiad__score") + F("olympiad__math_score"),
                    Value(-1, output_field=ScoreField())
                ),
            )
            .order_by("-exam__score_coalesce", "-olympiad__total_score_coalesce", "-test__score_coalesce", "-pk")
        )

    def get(self, request: AuthenticatedHttpRequest, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)

        if not self.filterset.is_valid():
            campaign = get_default_campaign_for_user(request.user)
            if not campaign:
                messages.info(request, "No active campaigns")
                return HttpResponseRedirect(redirect_to="/")
            url = reverse("admission:applicants:list")
            url = f"{url}?campaign={campaign.pk}&status="
            return HttpResponseRedirect(redirect_to=url)

        self.object_list = self.filterset.qs
        context = self.get_context_data(
            filter=self.filterset, object_list=self.object_list
        )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = context["filter"].form.cleaned_data.get("campaign")
        if campaign and campaign.current and self.request.user.is_curator:
            context["import_tasks"] = get_contest_results_import_info(campaign)
            context["ContestTypes"] = ContestTypes
            context["show_register_for_olympiad"] = True
            context["campaign"] = campaign
        return context


class RegisterApplicantsForOlympiadView(CuratorOnlyMixin, generic.View):
    """
    Register applicants with status PERMIT_TO_OLYMPIAD in the olympiad contest.
    """

    def get_campaign(self, campaign_id):
        """Get campaign by ID."""
        return get_object_or_404(Campaign, pk=campaign_id)

    def get_applicants(self, campaign):
        """Get applicants with status PERMIT_TO_OLYMPIAD."""
        return Applicant.objects.filter(
            campaign=campaign,
            status=ApplicantStatuses.PERMIT_TO_OLYMPIAD
        )

    def create_olympiad_records(self, applicants):
        """Create Olympiad records for applicants who don't have one."""
        created_count = 0
        with transaction.atomic():
            for applicant in applicants:
                try:
                    Olympiad.objects.get(applicant=applicant)
                except Olympiad.DoesNotExist:
                    Olympiad.objects.create(applicant=applicant)
                    created_count += 1
        return created_count

    def register_in_contest(self, api, applicants, request):
        """Register applicants in the contest."""
        registered_count = 0
        for olympiad in Olympiad.objects.filter(
            applicant__in=applicants,
            status=ChallengeStatuses.NEW
        ):
            try:
                olympiad.register_in_contest(api)
                registered_count += 1
            except Exception as e:
                logger.error(f"Error registering applicant {olympiad.applicant_id} in olympiad contest: {e}")
                messages.error(
                    request,
                    f"Error registering applicant {olympiad.applicant_id} in olympiad contest: {e}"
                )
        return registered_count

    def get(self, request, campaign_id):
        campaign = self.get_campaign(campaign_id)

        # Get applicants and create Olympiad records
        applicants = self.get_applicants(campaign)
        created_count = self.create_olympiad_records(applicants)

        # Register applicants in the contest
        api = YandexContestAPI(access_token=campaign.access_token, refresh_token=campaign.refresh_token)
        registered_count = self.register_in_contest(api, applicants, request)

        # Add success message
        messages.success(
            request,
            _("Created {} olympiad records and registered {} applicants in the contest.").format(created_count, registered_count)
        )

        return redirect("admission:applicants:list")


class ApplicantDetailView(CuratorOnlyMixin, TemplateResponseMixin, BaseCreateView):
    form_class = InterviewForm
    template_name = "admission/applicant_detail.html"

    def get_context_data(self, **kwargs):
        applicant_id = self.kwargs[self.pk_url_kwarg]
        context = kwargs
        context.update(get_applicant_context(self.request, applicant_id))
        applicant = context["applicant"]
        context["status_form"] = ApplicantForm(instance=applicant)
        if "form" not in kwargs:
            invitation = InterviewInvitation.objects.for_applicant(applicant)
            if (
                not invitation
                or invitation.status == InterviewInvitationStatuses.DECLINED
            ):
                branch = applicant.campaign.branch
                context["form"] = InterviewFromStreamForm(branch=branch)
            else:
                context["invitation"] = invitation
        return context

    def post(self, request, *args, **kwargs):
        """Get data for interview from stream form"""
        if not request.user.is_curator:
            return self.handle_no_permission(request)
        applicant_id = self.kwargs.get(self.pk_url_kwarg)
        applicant = get_object_or_404(
            Applicant.objects.filter(pk=applicant_id).select_related("campaign")
        )
        self.object = None
        stream_form = InterviewFromStreamForm(
            branch=applicant.campaign.branch, data=self.request.POST
        )
        if not stream_form.is_valid():
            msg = "Действие было отменено"
            messages.error(self.request, msg, extra_tags="timeout")
            return self.form_invalid(stream_form)
        slot = stream_form.cleaned_data.get("slot")
        if slot:
            response = self.create_interview_from_slot(applicant, stream_form, slot)
        else:
            response = self.create_invitation(applicant, stream_form)
        return response

    def get_success_url(self):
        messages.success(
            self.request, "Собеседование успешно добавлено", extra_tags="timeout"
        )
        return reverse("admission:interviews:detail", args=[self.object.pk])

    def create_interview_from_slot(self, applicant, stream_form, slot):
        data = InterviewForm.build_data(applicant, slot)
        form = InterviewForm(data=data)
        if form.is_valid():
            with transaction.atomic():
                sid = transaction.savepoint()
                interview = self.object = form.save()
                slot_has_taken = InterviewSlot.objects.lock(slot, interview)
                EmailQueueService.generate_interview_reminder(interview, slot.stream)
                if not slot_has_taken:
                    transaction.savepoint_rollback(sid)
                    messages.error(
                        self.request,
                        "Cлот уже был занят другим участником! Нужно вручную "
                        "разобраться в ситуации.<br><a target='_blank' "
                        "href='{}'>Перейти в админ-панель</a>".format(
                            reverse(
                                "admin:admission_interviewstream_change",
                                args=[slot.stream.pk],
                            )
                        ),
                    )
                    return self.form_invalid(stream_form)
                else:
                    transaction.savepoint_commit(sid)
            return super(ModelFormMixin, self).form_valid(form)
        else:
            # It never happens until user trying to change data by hand.
            messages.error(
                self.request,
                "Unknown error. Repeat your "
                "request or tell everyone about "
                "this disaster.",
            )
            return self.form_invalid(stream_form)

    def create_invitation(self, applicant, stream_form):
        streams = stream_form.cleaned_data["streams"]
        try:
            with transaction.atomic():
                invitation = create_invitation(list(streams), applicant)
                EmailQueueService.generate_interview_invitation(
                    invitation, streams, url_builder=self.request.build_absolute_uri
                )
            messages.success(
                self.request,
                "Приглашение успешно создано и должно быть отправлено в "
                "течение 5 минут.",
                extra_tags="timeout",
            )
        except IntegrityError:
            messages.error(self.request, "Приглашение не было создано.")
        url = applicant.get_absolute_url()
        return HttpResponseRedirect("{}#create".format(url))


class ApplicantStatusUpdateView(CuratorOnlyMixin, generic.UpdateView):
    form_class = ApplicantForm
    model = Applicant

    def form_valid(self, form):
        if 'status' in form.changed_data:
            with manual_status_change():
                create_applicant_status_log(
                    applicant=self.object,
                    new_status=form.cleaned_data['status'],
                    editor=self.request.user
                )
                response = super().form_valid(form)
                return response
        else:
            return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Статус успешно обновлён", extra_tags="timeout")
        return reverse("admission:applicants:detail", args=[self.object.pk])


# FIXME: rewrite with rest framework
class InterviewAssignmentDetailView(CuratorOnlyMixin, generic.DetailView):
    def get(self, request, **kwargs):
        assignment_id = self.kwargs["pk"]
        assignment = get_object_or_404(
            InterviewAssignment.objects.filter(pk=assignment_id)
        )
        rendered_text = render_markdown(assignment.description)
        return JsonResponse(
            {"id": assignment_id, "name": assignment.name, "description": rendered_text}
        )


def get_default_campaign_for_user(user: User) -> Optional[Campaign]:
    active_campaigns = list(
        Campaign.objects.filter(current=True, branch__site_id=settings.SITE_ID)
        .only("pk", "branch_id")
        .order_by("branch__order")
    )
    try:
        campaign = next(c for c in active_campaigns if c.branch_id == user.branch_id)
    except StopIteration:
        # Get any campaign if no active campaign found for the user branch
        campaign = next((c for c in active_campaigns), None)
    return campaign


# FIXME: For interviewers filterset form use user timezone instead of UTC?
class InterviewListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
    """
    XXX: Filter by date uses UTC time zone
    """

    context_object_name = "interviews"
    model = Interview
    paginate_by = 50
    template_name = "admission/interview_list.html"

    def get(self, request, *args, **kwargs):
        """
        Redirects curator to page with appropriate parameters for correct work of 'download_csv'.
        """
        user = self.request.user
        is_param_lost = any(param not in self.request.GET for param in ["status", "date_from", "date_to"])
        if is_param_lost:
            if user.branch:
                local_timezone = user.branch.get_timezone()
            else:
                campaign = get_default_campaign_for_user(user)
                local_timezone = campaign.branch.get_timezone()
            local_time = now_local(local_timezone)
            today = formats.date_format(local_time, "SHORT_DATE_FORMAT")
            date_to = datetime(local_time.year, 8, 1)
            date_to = formats.date_format(date_to, "SHORT_DATE_FORMAT")
            params = {
                    "status": [Interview.COMPLETED, Interview.APPROVED],
                    "date_from": today,
                    "date_to": date_to,
                }
            if user.is_curator and "campaign" not in self.request.GET:
                params.update({"campaign": ""})
            params = parse.urlencode(params, doseq=True)
            url = "{}?{}".format(reverse("admission:interviews:list"), params)
            return HttpResponseRedirect(redirect_to=url)
        if "download_csv" in request.GET:
            campaign = request.GET.get("campaign")
            date_from = request.GET.get("date_from")
            date_to = request.GET.get("date_to")
            return redirect(
                reverse("admission:interviews:csv_list") + f"?campaign={campaign}"
                f"&date_from={date_from}"
                f"&date_to={date_to}"
            )
        return super().get(request, *args, **kwargs)

    def get_filterset_class(self):
        if self.request.user.is_curator:
            return InterviewsCuratorFilter
        return InterviewsFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset
        # Choose results list title for selected campaign
        context["results_title"] = _("Current campaign")
        # TODO: Move to appropriate place?
        if "campaign" in self.filterset.form.declared_fields:
            try:
                campaign_filter_value = int(self.filterset.data.get("campaign"))
                campaign_field = self.filterset.form.declared_fields["campaign"]
                for campaign_id, name in campaign_field.choices:
                    if campaign_id == campaign_filter_value:
                        context["results_title"] = name
            except ValueError:
                context["results_title"] = _("All campaigns")
        return context

    def get_queryset(self):
        branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        q = (
            Interview.objects.filter(applicant__campaign__branch__in=branches)
            .select_related("applicant__campaign__branch", "venue__city")
            .prefetch_related("interviewers", "slot__stream")
            .annotate(average=Coalesce(Avg("comments__score"), Value(0.0)))
            .order_by("date", "pk")
        )
        if not self.request.user.is_curator:
            # To interviewers show interviews from current campaigns where
            # they participate.
            try:
                current_campaigns = list(
                    Campaign.objects.filter(
                        current=True, branch__site_id=settings.SITE_ID
                    ).values_list("pk", flat=True)
                )
            except Campaign.DoesNotExist:
                messages.error(self.request, "Нет активных кампаний по набору.")
                return Interview.objects.none()
            q = q.filter(
                applicant__campaign_id__in=current_campaigns,
                interviewers=self.request.user,
            )
        return q


class InterviewListCSVView(CuratorOnlyMixin, generic.base.View):
    def get(self, request, *args, **kwargs):
        date_from = datetime.strptime(request.GET.get("date_from"), "%d.%m.%Y")
        date_to = datetime.strptime(request.GET.get("date_to"), "%d.%m.%Y")
        campaign = request.GET.get("campaign")
        campaign = int(campaign) if campaign else None
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        filename = f"interviews_{date_from.strftime('%d.%m.%Y')}_{date_to.strftime('%d.%m.%Y')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        headers = [
            _("Date"),
            _("Time"),
            _("Section"),
            _("Applicant"),
            _("Interviewer"),
            _("Status"),
            _("Format")
        ]
        campaign_filter = Q(applicant__campaign=campaign) if campaign else Q()
        writer.writerow(headers)
        interviews = (
            Interview.objects.select_related("applicant", "slot__stream")
            .prefetch_related("interviewers")
            .filter(
                campaign_filter,
                date__date__gte=date_from.strftime("%Y-%m-%d"),
                date__date__lte=date_to.strftime("%Y-%m-%d"),
            )
            .order_by("date")
        )
        for interview in interviews:
            dt = interview.date_local()
            interview_format = value if (value := interview.get_format_display()) is not None else '<не указан>'
            writer.writerow(
                [
                    dt.date().strftime("%d.%m.%Y"),
                    dt.time().strftime("%H:%M"),
                    interview.get_section_display(),
                    interview.applicant.full_name,
                    ", ".join(
                        map(
                            lambda u: u.get_full_name(last_name_first=True),
                            interview.interviewers.all(),
                        )
                    ),
                    interview.get_status_display(),
                    interview_format
                ]
            )
        return response


class InterviewDetailView(InterviewerOnlyMixin, generic.TemplateView):
    template_name = "admission/interview_detail.html"

    def get_queryset(self):
        branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        return Interview.objects.filter(
            pk=self.kwargs["pk"], applicant__campaign__branch__in=branches
        )

    def get_context_data(self, **kwargs):
        qs = self.get_queryset().prefetch_related(
            "interviewers",
            "assignments",
            Prefetch(
                "comments", queryset=(Comment.objects.select_related("interviewer"))
            ),
            "slot__stream"
        )
        interview = get_object_or_404(qs)
        context = get_applicant_context(self.request, interview.applicant_id)
        interview.applicant = context["applicant"]
        show_all_comments = self.request.user.is_curator
        form_kwargs = {"interview": interview, "interviewer": self.request.user}
        for comment in interview.comments.all():
            if comment.interviewer == self.request.user:
                show_all_comments = True
                form_kwargs["instance"] = comment
        context.update(
            {
                "interview": interview,
                "assignments_form": InterviewAssignmentsForm(instance=interview),
            }
        )
        context["show_all_comments"] = show_all_comments
        context["comment_form"] = InterviewCommentForm(**form_kwargs)
        return context

    def post(self, request, *args, **kwargs):
        """Update list of assignments"""
        if not request.user.is_curator:
            return HttpResponseForbidden()
        interview = get_object_or_404(self.get_queryset())
        form = InterviewAssignmentsForm(instance=interview, data=self.request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                self.request, "Список заданий успешно обновлён", extra_tags="timeout"
            )
        url = "{}#assignments".format(interview.get_absolute_url())
        return HttpResponseRedirect(url)


# FIXME: rewrite as API view
class InterviewCommentUpsertView(InterviewerOnlyMixin, GenericModelView):
    """Update/Insert view for interview comment"""

    http_method_names = ["post", "put"]

    def post(self, request, *args, **kwargs):
        qs = Interview.objects.select_related(
            "applicant__campaign__branch__site"
        ).filter(pk=self.kwargs["pk"])
        interview = get_object_or_404(qs)
        comment = self.object = self.get_object()
        form = InterviewCommentForm(
            data=request.POST,
            instance=comment,
            interview=interview,
            interviewer=self._get_interviewer(),
        )
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_object(self, queryset=None):
        try:
            return Comment.objects.get(
                interview=self.kwargs["pk"], interviewer=self.request.user
            )
        except Comment.DoesNotExist:
            return None

    @transaction.atomic
    def form_valid(self, form):
        _ = form.save()
        return JsonResponse({"success": "true"})

    def form_invalid(self, form):
        msg = "<br>".join(m for ms in form.errors.values() for m in ms)
        r = JsonResponse({"errors": msg})
        r.status_code = 400
        return r

    def get_success_url(self):
        messages.success(
            self.request, "Комментарий успешно сохранён", extra_tags="timeout"
        )
        return reverse("admission:interviews:detail", args=[self.object.interview_id])

    def _get_interviewer(self):
        interview_id = self.kwargs["pk"]
        interview = get_object_or_404(
            Interview.objects.filter(pk=interview_id).prefetch_related("interviewers")
        )
        if self.request.user.is_curator:
            return self.request.user
        for i in interview.interviewers.all():
            if i.pk == self.request.user.pk:
                return i
        return None


class InterviewResultsDispatchView(CuratorOnlyMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        """Based on user settings, get preferred page address and redirect"""
        branches = Campaign.objects.filter(
            current=True, branch__site_id=settings.SITE_ID
        ).values_list("branch__code", flat=True)
        if self.request.user.branch_id is not None:
            branch_code = self.request.user.branch.code
        else:
            branch_code = settings.DEFAULT_BRANCH_CODE
        if branch_code not in branches:
            branch_code = next(branches.iterator(), settings.DEFAULT_BRANCH_CODE)
        return reverse(
            "admission:results:list",
            kwargs={
                "branch_code": branch_code,
            },
        )


class BranchFromURLViewMixin:
    """
    This view mixin sets `branch` attribute to the request object based on
    `settings.SITE_ID` and non-empty `branch_code` url named argument
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        branch_code = kwargs.get("branch_code", None)
        if not branch_code:
            raise ImproperlyConfigured(
                f"{self.__class__} is subclass of {self.__class__.__name__} but "
                f"`branch_code` view keyword argument is not specified or empty"
            )
        request.branch = Branch.objects.get_by_natural_key(branch_code, settings.SITE_ID)


class InterviewResultsView(
    CuratorOnlyMixin,
    FilterMixin,
    BranchFromURLViewMixin,
    TemplateResponseMixin,
    BaseModelFormSetView,
):
    context_object_name = "interviews"
    template_name = "lms/admission/admission_results.html"
    model = Applicant
    form_class = ApplicantFinalStatusForm
    filterset_class = ResultsFilter

    def dispatch(self, request, *args, **kwargs):
        self.active_campaigns = Campaign.objects.filter(
            current=True, branch__site_id=settings.SITE_ID
        ).select_related("branch")
        try:
            self.selected_campaign = next(
                c for c in self.active_campaigns if c.branch_id == request.branch.pk
            )
        except StopIteration:
            messages.error(self.request, "Активная кампания по набору не найдена")
            return HttpResponseRedirect(reverse("admission:applicants:list"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        formset = self.construct_formset()
        context = self.get_context_data(filter=self.filterset, formset=formset)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        formset = self.construct_formset()
        if formset.is_valid():
            return self.formset_valid(formset)
        else:
            return self.formset_invalid(formset)

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs["extra"] = 0
        return kwargs

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        kwargs["branch_code"] = self.kwargs["branch_code"]
        return kwargs

    def get_formset_kwargs(self):
        """Overrides queryset for instantiating the formset."""
        kwargs = super().get_formset_kwargs()
        kwargs["queryset"] = self.filterset.qs
        return kwargs

    def get_queryset(self):
        return (
            Applicant.objects.filter(
                campaign=self.selected_campaign,
                status__in=ApplicantStatuses.RESULTS_STATUSES,
            )
            .select_related("exam", "online_test", "university_legacy")
            .prefetch_related(
                Prefetch(
                    "interviews",
                    queryset=(
                        Interview.objects.select_related("venue__city").annotate(
                            _average_score=Avg("comments__score")
                        )
                    ),
                ),
            )
        )

    def get_context_data(self, filter, formset, **kwargs):
        stats = Counter()
        final_statuses = {
            Applicant.ACCEPT,
            Applicant.ACCEPT_IF,
            Applicant.ACCEPT_PAID,
        }
        received = 0
        for form in formset.forms:
            applicant = form.instance
            stats.update((applicant.status,))
            if applicant.status in final_statuses:
                received += 1
        stats = [
            (Applicant.get_name_by_status_code(s), cnt) for s, cnt in stats.items()
        ]
        if received:
            stats.append(("Планируем принять всего", received))

        def cpm_interviews_score_sum(form):
            a = form.instance
            exam_score = a.exam.score if hasattr(a, "exam") and a.exam.score else -1
            interviews_average_score_sum = 0
            for interview in a.interviews.all():
                if interview.average_score is not None:
                    interviews_average_score_sum += interview.average_score
            return interviews_average_score_sum, exam_score

        formset.forms.sort(key=cpm_interviews_score_sum, reverse=True)

        context = {
            "filter": filter,
            "formset": formset,
            "stats": stats,
            "active_campaigns": self.active_campaigns,
            "selected_campaign": self.selected_campaign,
        }
        return context


class ApplicantCreateStudentView(CuratorOnlyMixin, generic.View):
    http_method_names = ["post"]

    @atomic
    def post(self, request, *args, **kwargs):
        applicant_pk = kwargs.get("pk")
        back_url = reverse("admission:applicants:list")
        try:
            applicant = Applicant.objects.get(pk=applicant_pk)
        except Applicant.DoesNotExist:
            messages.error(self.request, "Анкета не найдена", extra_tags="timeout")
            return HttpResponseRedirect(reverse("admission:applicants:list"))
        try:
            user = create_student_from_applicant(applicant)
        except User.MultipleObjectsReturned:
            messages.error(
                self.request,
                f"Найдено несколько пользователей с email {applicant.email}",
            )
            return HttpResponseRedirect(back_url)
        except UniqueUsernameError as e:
            messages.error(self.request, e.args[0])
            return HttpResponseRedirect(back_url)
        # Link applicant and user
        applicant.user = user
        applicant.save()
        url = reverse("admin:users_user_change", args=[user.pk])
        return HttpResponseRedirect(url)


class AppointmentSlotSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source="pk")
    label = serializers.SerializerMethodField()
    available = serializers.BooleanField(source="is_empty")

    class Meta:
        model = InterviewSlot
        fields = ("value", "label", "available")

    def get_label(self, obj):
        meeting_at = get_meeting_time(obj.datetime_local, obj.stream)
        return meeting_at.strftime("%H:%M")


def get_slot_occupation_url(invitation: InterviewInvitation):
    """`use-http` on client waits for relative path."""
    url = django_reverse(
        "appointment:api:interview_appointment_slots",
        kwargs={
            "year": invitation.applicant.campaign.year,
            "secret_code": invitation.secret_code.hex,
            "slot_id": 42,
        },
    )
    endpoint, _ = url.rsplit("42", 1)
    return endpoint + "{slotId}/"


class InterviewAppointmentView(TemplateView):
    template_name = "lms/admission/interview_appointment.html"

    class InputSerializer(serializers.Serializer):
        secret_code = serializers.UUIDField(format="hex_verbose")
        year = serializers.IntegerField()

    def get(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=kwargs)
        if not serializer.is_valid(raise_exception=False):
            return HttpResponseNotFound()

        invitation = get_interview_invitation(**serializer.validated_data)
        if not invitation or invitation.is_expired or invitation.is_declined:
            raise Http404

        tz_msk = pytz.timezone("Europe/Moscow")
        invitation_deadline = formats.date_format(
            invitation.expired_at.astimezone(tz_msk), "j E H:i"
        )
        decline_invitation_url = django_reverse(
            "appointment:api:interview_appointment",
            kwargs={
                "year": invitation.applicant.campaign.year,
                "secret_code": invitation.secret_code.hex,
            },
        )

        context: Dict[str, Any] = {
            "invitation": invitation,
            "interview": None,
            "app_data": {
                "props": {
                    "invitationDeadline": invitation_deadline,
                    "endpointSlotOccupation": get_slot_occupation_url(invitation),
                    "endpointDeclineInvitation": decline_invitation_url,
                    "csrfToken": get_token(request),
                }
            },
        }
        if invitation.is_accepted:
            slot = get_occupied_slot(invitation=invitation)
            interview = slot.interview
            interview.date = get_meeting_time(interview.date, slot.stream)
            context["interview"] = interview
        else:
            # TODO: what if all slots were occupied?
            streams = get_streams(invitation)
            days = []
            for stream, slots in streams.items():
                day = {
                    "id": str(stream.pk),
                    "date": f"{stream.date}",
                    "format": stream.format,
                    "section": {
                        "value": stream.section,
                        "label": stream.get_section_display(),
                    },
                    "venue": {
                        "name": stream.venue.name,
                        "address": stream.venue.address,
                        "description": stream.venue.description,
                    },
                    "slots": [
                        AppointmentSlotSerializer(instance=s).data for s in slots
                    ],
                }
                days.append(day)
            context["app_data"]["props"]["days"] = days
        return self.render_to_response(context)


class InterviewAppointmentAssignmentsView(generic.TemplateView):
    template_name = "admission/interview_appointment_assignments.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            secret_code = uuid.UUID(self.kwargs["secret_code"], version=4)
        except ValueError:
            raise Http404
        campaign_year = self.kwargs["year"]
        interview = get_object_or_404(
            Interview.objects.filter(
                secret_code=secret_code, applicant__campaign__year=campaign_year
            )
            .select_related("applicant")
            .prefetch_related("assignments")
        )
        if interview.status != interview.APPROVED:
            raise Http404
        today = timezone.now()
        # Close access in 2 hours after interview started
        ends_at = interview.date_local() + timedelta(hours=2)
        if today > ends_at:
            raise Http404
        self.interview = interview

    def get_context_data(self, **kwargs):
        today = timezone.now()
        # Open assignments 5 minutes earlier than we notify students
        starts_at = self.interview.date_local() - timedelta(minutes=35)
        ends_at = self.interview.date_local() + timedelta(hours=2)
        context = {
            "interview": self.interview,
            "is_open": starts_at <= today <= ends_at,
        }
        return context


class ConfirmationOfAcceptanceForStudiesView(TemplateView):
    """
    After sending Confirmation of Acceptance for Studies to participant
    we expect they confirm it from their side and complete registration on site.
    """

    acceptance: Acceptance
    template_name = "lms/admission/confirmation_of_acceptance.html"

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        campaign_year: int = kwargs["year"]
        access_key: str = kwargs["access_key"]
        try:
            branches = Branch.objects.for_site(site_id=settings.SITE_ID)
            acceptance = get_acceptance_ready_to_confirm(
                year=campaign_year,
                access_key=access_key,
                filters=[Q(applicant__campaign__branch__in=branches)],
            )
        except ValidationError:
            raise Http404
        if not acceptance:
            raise Http404
        self.acceptance = acceptance

    def get(self, request: HttpRequest, *args, **kwargs):
        context: Dict[str, Any]
        confirmation_code = request.session.get(SESSION_CONFIRMATION_CODE_KEY)
        is_authorized = (
            confirmation_code and self.acceptance.confirmation_code == confirmation_code
        )
        if not is_authorized:
            authorization_form = ConfirmationAuthorizationForm(instance=self.acceptance)
            context = {"authorization_form": authorization_form}
        else:
            confirmation_form = ConfirmationForm(acceptance=self.acceptance)
            context = {
                "confirmation_form": confirmation_form,
                "contact_email": settings.LMS_CURATOR_EMAIL
            }
        return self.render_to_response(context)

    def post(self, request: HttpRequest, *args, **kwargs):
        context: Dict[str, Any]
        confirmation_code = request.session.get(SESSION_CONFIRMATION_CODE_KEY)
        is_authorized = (
            confirmation_code and self.acceptance.confirmation_code == confirmation_code
        )
        if not is_authorized:
            # Check authorization form
            authorization_form = ConfirmationAuthorizationForm(
                instance=self.acceptance, data=request.POST
            )
            if authorization_form.is_valid():
                # Save confirmation code in user session and redirect
                request.session[
                    SESSION_CONFIRMATION_CODE_KEY
                ] = authorization_form.cleaned_data["authorization_code"]
                return HttpResponseRedirect(redirect_to=request.path_info)
            else:
                context = {"authorization_form": authorization_form}
                return self.render_to_response(context)
        else:
            confirmation_form = ConfirmationForm(
                acceptance=self.acceptance, data=request.POST, files=request.FILES
            )
            if confirmation_form.is_valid():
                confirmation_form.save()
                return HttpResponseRedirect(
                    redirect_to=reverse("admission:acceptance:confirmation_done")
                )
            else:
                context = {
                    "confirmation_form": confirmation_form,
                    "contact_email": settings.LMS_CURATOR_EMAIL
                }
                return self.render_to_response(context)


class ConfirmationOfAcceptanceForStudiesDoneView(TemplateView):
    template_name = "lms/admission/confirmation_of_acceptance_done.html"

    def get_context_data(self, **kwargs):
        context = {
            "contact_email": settings.LMS_CURATOR_EMAIL
        }
        return context
