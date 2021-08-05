import uuid
from collections import Counter
from datetime import timedelta
from typing import Any, Dict, Optional, cast
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
from django.db.models import Avg, Case, Count, Prefetch, Q, Value, When
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.http.response import Http404, HttpResponse, HttpResponseForbidden
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import reverse as django_reverse
from django.utils import formats, timezone
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.generic.base import RedirectView, TemplateResponseMixin
from django.views.generic.edit import BaseCreateView, ModelFormMixin
from django.views.generic.list import BaseListView

from admission.filters import (
    ApplicantFilter, InterviewInvitationFilter, InterviewsCuratorFilter,
    InterviewsFilter, InterviewStreamFilter, RequiredSectionInterviewStreamFilter,
    ResultsFilter
)
from admission.forms import (
    ApplicantFinalStatusForm, ApplicantForm, ApplicantReadOnlyForm,
    ConfirmationAuthorizationForm, ConfirmationForm, InterviewAssignmentsForm,
    InterviewCommentForm, InterviewForm, InterviewFromStreamForm,
    InterviewStreamInvitationForm
)
from admission.models import (
    Acceptance, Applicant, Campaign, Comment, Contest, Interview, InterviewAssignment,
    InterviewInvitation, InterviewSlot, InterviewStream
)
from admission.services import (
    AccountData, ContestResultsImportState, EmailQueueService, StudentProfileData,
    UsernameError, create_invitation, create_student, create_student_from_applicant,
    get_acceptance_ready_to_confirm, get_applicants_for_invitation,
    get_latest_contest_results_task, get_meeting_time, get_ongoing_interview_streams,
    get_streams
)
from core.db.fields import ScoreField
from core.http import AuthenticatedHttpRequest, HttpRequest
from core.models import Branch
from core.timezone import get_now_utc, now_local
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.urls import reverse
from core.utils import bucketize, render_markdown
from tasks.models import Task
from users.api.serializers import PhotoSerializerField
from users.mixins import CuratorOnlyMixin
from users.models import User

from .constants import (
    SESSION_CONFIRMATION_CODE_KEY, ApplicantStatuses, ContestTypes,
    InterviewInvitationStatuses, InterviewSections
)
from .selectors import get_interview_invitation, get_occupied_slot
from .tasks import import_campaign_contest_results


def get_applicant_context(request, applicant_id) -> Dict[str, Any]:
    branches = Branch.objects.for_site(site_id=settings.SITE_ID)
    qs = (Applicant.objects
          .select_related("exam", "campaign__branch__site",
                          "online_test", "university")
          .filter(campaign__branch__in=branches,
                  pk=applicant_id))
    applicant = get_object_or_404(qs)
    online_test = applicant.get_testing_record()
    exam = applicant.get_exam_record()
    # Fetch contest records
    contest_pks = []
    if online_test and online_test.yandex_contest_id:
        contest_pks.append(online_test.yandex_contest_id)
    if exam and exam.yandex_contest_id:
        contest_pks.append(exam.yandex_contest_id)
    contests = {}
    if contest_pks:
        filters = [
            Q(contest_id__in=contest_pks),
            Q(campaign_id=applicant.campaign_id)
        ]
        queryset = Contest.objects.filter(*filters)
        contests = bucketize(queryset, key=lambda o: o.type)
    context = {
        "applicant": applicant,
        "applicant_form": ApplicantReadOnlyForm(request=request,
                                                instance=applicant),
        "campaign": applicant.campaign,
        "contests": contests,
        "ContestTypes": ContestTypes,
        "exam": exam,
        "online_test": online_test,
        "similar_applicants": applicant.get_similar(),
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
    return [{'name': InterviewSections.values[s], 'occupied': s == occupied} for s in sections]


class InterviewerSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='user_detail')
    full_name = serializers.CharField(source='get_full_name')
    photo = PhotoSerializerField(User.ThumbnailSize.INTERVIEW_LIST,
                                 thumbnail_options={"use_stab": False})

    class Meta:
        model = User
        fields = ("url", "full_name", "photo")


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
    filters = {'campaign': input_serializer.validated_data['campaign']}
    if input_serializer.validated_data['section']:
        filters['section'] = input_serializer.validated_data['section']
    interview_stream_filterset = InterviewStreamFilter(
        data=input_serializer.validated_data,
        queryset=(InterviewStream.objects
                  .filter(**filters)
                  .order_by('-date', '-start_at', 'pk')))
    return interview_stream_filterset


class InterviewInvitationCreateView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "lms/admission/send_interview_invitations.html"

    # page number validation is not included
    class FilterSerializer(serializers.Serializer):
        campaign = serializers.PrimaryKeyRelatedField(
            required=True,
            queryset=(Campaign.objects
                      .filter(branch__site_id=settings.SITE_ID)
                      .select_related('branch')))
        section = serializers.ChoiceField(choices=InterviewSections.choices,
                                          required=True)

    class InputSerializer(serializers.Serializer):
        streams = serializers.ListField(
            child=serializers.IntegerField(min_value=1),
            min_length=1,
            allow_empty=False)
        ids = serializers.ListField(
            label="List of participant identifiers",
            child=serializers.IntegerField(min_value=1),
            min_length=1,
            allow_empty=False)

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
            context = self.get_context_data(filter_serializer=filter_serializer, **kwargs)
            return self.render_to_response(context)

        input_serializer = self.InputSerializer(data=request.POST)
        if not input_serializer.is_valid(raise_exception=False):
            messages.error(self.request, "Выберите поступающих перед отправкой формы.")
            context = self.get_context_data(filter_serializer=filter_serializer, **kwargs)
            return self.render_to_response(context)

        interview_stream_filterset = self.get_interview_stream_filterset(filter_serializer)
        streams = list(interview_stream_filterset.qs
                       .filter(pk__in=input_serializer.validated_data['streams'])
                       # location data used in email context)
                       .select_related('venue__city'))

        # Create interview invitations
        campaign = filter_serializer.validated_data['campaign']
        section = filter_serializer.validated_data['section']
        applicants = get_applicants_for_invitation(campaign=campaign, section=section)
        applicants = applicants.filter(pk__in=input_serializer.validated_data['ids'])
        with transaction.atomic():
            for applicant in applicants:
                applicant.campaign = campaign
                invitation = create_invitation(streams, applicant)
                EmailQueueService.generate_interview_invitation(invitation, streams,
                                                                url_builder=request.build_absolute_uri)
        messages.success(request, "Приглашения успешно созданы",
                         extra_tags='timeout')
        url = reverse("admission:interviews:invitations:send")
        redirect_to = f"{url}?campaign={campaign.id}&section={section}"
        return HttpResponseRedirect(redirect_to)

    @staticmethod
    def get_interview_stream_filterset(serializer: serializers.Serializer):
        return RequiredSectionInterviewStreamFilter(
            data=serializer.validated_data,
            queryset=(get_ongoing_interview_streams()
                      .order_by('-date', '-start_at', 'pk')))

    def get_context_data(self, **kwargs):
        filter_serializer = kwargs['filter_serializer']
        campaign = filter_serializer.validated_data['campaign']
        section = filter_serializer.validated_data['section']
        interview_stream_filterset = self.get_interview_stream_filterset(filter_serializer)

        applicants = (get_applicants_for_invitation(campaign=campaign,
                                                    section=section)
                      .select_related("exam", "online_test", "campaign", "university",
                                      "campaign__branch")
                      .annotate(exam__score_coalesce=Coalesce('exam__score', Value(-1, output_field=ScoreField())),
                                test__score_coalesce=Coalesce('online_test__score', Value(-1)))
                      .order_by("-exam__score_coalesce", "-test__score_coalesce", "-pk"))

        paginator = Paginator(applicants, 50)
        page_number = self.request.GET.get('page')
        page = paginator.get_page(page_number)
        paginator_url = reverse("admission:interviews:invitations:send")
        paginator_url = f"{paginator_url}?campaign={campaign.id}&section={section}"

        context = {
            'stream_filter_form': interview_stream_filterset.form,
            'stream_form': InterviewStreamInvitationForm(streams=interview_stream_filterset.qs),
            'applicants': page.object_list,
            'paginator_url': paginator_url,
            'paginator': paginator,
            'page': page,
        }
        return context


class InterviewInvitationListView(CuratorOnlyMixin, TemplateResponseMixin, BaseListView):
    model = InterviewStream
    template_name = "lms/admission/interview_invitation_list.html"
    paginate_by = 50

    class InputSerializer(serializers.Serializer):
        campaign = serializers.PrimaryKeyRelatedField(
            required=True,
            queryset=(Campaign.objects
                      .filter(branch__site_id=settings.SITE_ID)))
        section = serializers.ChoiceField(choices=InterviewSections.choices,
                                          required=True,
                                          allow_blank=True)

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
        input_serializer = kwargs['input_serializer']
        interview_stream_filterset = get_interview_stream_filterset(input_serializer)
        invitations_waiting_for_response = Count(Case(
            When(interview_invitations__expired_at__lte=get_now_utc(), then=Value(None)),
            When(interview_invitations__status=InterviewInvitationStatuses.NO_RESPONSE, then=Value(1)),
            default=Value(None)
        ))
        interview_streams = (interview_stream_filterset.qs
                             .select_related('venue')
                             .annotate(invitations_total=invitations_waiting_for_response)
                             .defer('venue__description', 'venue__directions')
                             .prefetch_related('interviewers'))
        # Fetch filtered invitations
        filters = {"applicant__campaign": input_serializer.validated_data['campaign']}
        if input_serializer.validated_data['section']:
            filters["streams__section"] = input_serializer.validated_data['section']
        invitation_queryset = (InterviewInvitation.objects
                               .select_related('interview__venue__city', 'applicant')
                               .filter(**filters)
                               .prefetch_related('streams', 'interview__interviewers')
                               .order_by('applicant__last_name',
                                         'applicant_id',
                                         'pk'))
        interview_filterset = InterviewInvitationFilter(interview_stream_filterset.qs,
                                                        data=self.request.POST or None,
                                                        prefix="interview-invitation",
                                                        queryset=invitation_queryset)

        paginator = Paginator(interview_filterset.qs.distinct(), 50)
        page_number = self.request.GET.get('page')
        page = paginator.get_page(page_number)
        campaign = input_serializer.validated_data['campaign']
        section = input_serializer.validated_data['section']
        paginator_url = reverse("admission:interviews:invitations:list")
        paginator_url = f"{paginator_url}?campaign={campaign.id}&section={section}"

        interview_invitations = []
        for invitation in page.object_list:
            applicant = invitation.applicant
            interview = invitation.interview
            # Avoid additional queries on fetching time zone
            if invitation.interview_id:
                interview.applicant = applicant
                interview.applicant.campaign = input_serializer.validated_data['campaign']
            # TODO: add serializer
            student_invitation = {
                'applicant': applicant,
                'sections': get_interview_invitation_sections(invitation),
                'interview': InterviewSerializer(interview, context={'request': self.request}).data,
                'status': {
                    'value': invitation.status,
                    'label': invitation.get_status_display(),
                    'code': InterviewInvitationStatuses.get_code(invitation.status),
                },
            }
            interview_invitations.append(student_invitation)

        context = {
            "interview_stream_filter_form": interview_stream_filterset.form,
            "interview_invitation_filter_form": interview_filterset.form,
            "interview_invitations": interview_invitations,
            'paginator_url': paginator_url,
            'paginator': paginator,
            'page': page,
            "interview_streams": interview_streams
        }
        return context


class ApplicantListView(CuratorOnlyMixin, FilterMixin, generic.ListView):
    request: AuthenticatedHttpRequest
    context_object_name = 'applicants'
    model = Applicant
    template_name = "admission/applicant_list.html"
    filterset_class = ApplicantFilter
    paginate_by = 50

    def get_queryset(self):
        branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        return (
            Applicant.objects
            .filter(campaign__branch__in=branches)
            .select_related("exam", "online_test", "campaign", "university",
                            "campaign__branch")
            .prefetch_related("interviews")
            .annotate(exam__score_coalesce=Coalesce('exam__score', Value(-1, output_field=ScoreField())),
                      test__score_coalesce=Coalesce('online_test__score',
                                                    Value(-1)))
            .order_by("-exam__score_coalesce", "-test__score_coalesce", "-pk"))

    def get(self, request: AuthenticatedHttpRequest, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)

        if not self.filterset.is_valid():
            campaign = get_default_campaign_for_user(request.user)
            if not campaign:
                messages.info(request, "No active campaigns")
                return HttpResponseRedirect(redirect_to='/')
            url = reverse("admission:applicants:list")
            url = f"{url}?campaign={campaign.pk}&status="
            return HttpResponseRedirect(redirect_to=url)

        self.object_list = self.filterset.qs
        context = self.get_context_data(filter=self.filterset,
                                        object_list=self.object_list)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = context['filter'].form.cleaned_data.get('campaign')
        if campaign and campaign.current and self.request.user.is_curator:
            contest = dict()
            contest['testing_results'] = {"campaign": campaign, "contest_type": ContestTypes.TEST}
            contest['exam_results'] = {"campaign": campaign, "contest_type": ContestTypes.EXAM}
            contest['task_testing'] = get_latest_contest_results_task(campaign, ContestTypes.TEST)
            contest['task_exam'] = get_latest_contest_results_task(campaign, ContestTypes.EXAM)
            contest['task_types'] = [['task_testing', 'testing_results'], ['task_exam', 'exam_results']]

            for task in contest['task_types']:
                if contest[task[0]]:
                    tz = self.request.user.time_zone
                    contest[task[1]]['latest_task'] = ContestResultsImportState(
                        date=contest[task[0]].created_at_local(tz),
                        status=contest[task[0]].status)

            context["import_exam_results"] = contest['exam_results']
            context["import_testing_results"] = contest['testing_results']
        return context


class ApplicantDetailView(InterviewerOnlyMixin, TemplateResponseMixin,
                          BaseCreateView):

    form_class = InterviewForm
    template_name = "admission/applicant_detail.html"

    def get_context_data(self, **kwargs):
        applicant_id = self.kwargs[self.pk_url_kwarg]
        context = kwargs
        context.update(get_applicant_context(self.request, applicant_id))
        applicant = context["applicant"]
        context["status_form"] = ApplicantForm(instance=applicant)
        if 'form' not in kwargs:
            invitation = InterviewInvitation.objects.for_applicant(applicant)
            if not invitation or invitation.status == InterviewInvitationStatuses.DECLINED:
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
            Applicant.objects
            .filter(pk=applicant_id)
            .select_related("campaign"))
        self.object = None
        stream_form = InterviewFromStreamForm(
            branch=applicant.campaign.branch,
            data=self.request.POST)
        if not stream_form.is_valid():
            msg = "Действие было отменено"
            messages.error(self.request, msg, extra_tags='timeout')
            return self.form_invalid(stream_form)
        slot = stream_form.cleaned_data.get('slot')
        if slot:
            response = self.create_interview_from_slot(applicant, stream_form,
                                                       slot)
        else:
            response = self.create_invitation(applicant, stream_form)
        return response

    def get_success_url(self):
        messages.success(self.request, "Собеседование успешно добавлено",
                         extra_tags='timeout')
        return reverse("admission:interviews:detail", args=[self.object.pk])

    def create_interview_from_slot(self, applicant, stream_form, slot):
        data = InterviewForm.build_data(applicant, slot)
        form = InterviewForm(data=data)
        if form.is_valid():
            with transaction.atomic():
                sid = transaction.savepoint()
                interview = self.object = form.save()
                slot_has_taken = InterviewSlot.objects.lock(slot, interview)
                EmailQueueService.generate_interview_reminder(interview,
                                                              slot.stream)
                if not slot_has_taken:
                    transaction.savepoint_rollback(sid)
                    messages.error(
                        self.request,
                        "Cлот уже был занят другим участником! Нужно вручную "
                        "разобраться в ситуации.<br><a target='_blank' "
                        "href='{}'>Перейти в админ-панель</a>".format(
                            reverse("admin:admission_interviewstream_change",
                                    args=[slot.stream.pk])))
                    return self.form_invalid(stream_form)
                else:
                    transaction.savepoint_commit(sid)
            return super(ModelFormMixin, self).form_valid(form)
        else:
            # It never happens until user trying to change data by hand.
            messages.error(self.request, "Unknown error. Repeat your "
                                         "request or tell everyone about "
                                         "this disaster.")
            return self.form_invalid(stream_form)

    def create_invitation(self, applicant, stream_form):
        streams = stream_form.cleaned_data['streams']
        try:
            with transaction.atomic():
                invitation = create_invitation(list(streams), applicant)
                EmailQueueService.generate_interview_invitation(invitation, streams,
                                                                url_builder=self.request.build_absolute_uri)
            messages.success(
                self.request,
                "Приглашение успешно создано и должно быть отправлено в "
                "течение 5 минут.",
                extra_tags='timeout')
        except IntegrityError:
            messages.error(self.request, "Приглашение не было создано.")
        url = applicant.get_absolute_url()
        return HttpResponseRedirect("{}#create".format(url))


class ApplicantStatusUpdateView(CuratorOnlyMixin, generic.UpdateView):
    form_class = ApplicantForm
    model = Applicant

    def get_success_url(self):
        messages.success(self.request, "Статус успешно обновлён",
                         extra_tags='timeout')
        return reverse("admission:applicants:detail", args=[self.object.pk])


# FIXME: rewrite with rest framework
class InterviewAssignmentDetailView(CuratorOnlyMixin, generic.DetailView):
    def get(self, request, **kwargs):
        assignment_id = self.kwargs['pk']
        assignment = get_object_or_404(
            InterviewAssignment.objects.filter(pk=assignment_id))
        rendered_text = render_markdown(assignment.description)
        return JsonResponse({
            'id': assignment_id,
            'name': assignment.name,
            'description': rendered_text
        })


def get_default_campaign_for_user(user: User) -> Optional[Campaign]:
    active_campaigns = list(Campaign.objects
                            .filter(current=True, branch__site_id=settings.SITE_ID)
                            .only("pk", "branch_id")
                            .order_by('branch__order'))
    try:
        campaign = next(c for c in active_campaigns
                        if c.branch_id == user.branch_id)
    except StopIteration:
        # Get any campaign if no active campaign found for the user branch
        campaign = next((c for c in active_campaigns), None)
    return campaign


# FIXME: For interviewers filterset form use user timezone instead of UTC?
class InterviewListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
    """
    XXX: Filter by date uses UTC time zone
    """
    context_object_name = 'interviews'
    model = Interview
    paginate_by = 50
    template_name = "admission/interview_list.html"

    def get(self, request, *args, **kwargs):
        """
        Redirects curator to appropriate campaign if no any provided.
        """
        user = self.request.user
        if user.is_curator and "campaign" not in self.request.GET:
            # Try to find user preferred current campaign id
            campaign = get_default_campaign_for_user(user)
            if not campaign:
                messages.error(self.request, "Нет активных кампаний по набору.")
                today_local = timezone.now()  # stub
            else:
                today_local = now_local(campaign.branch.get_timezone())
            date = formats.date_format(today_local, "SHORT_DATE_FORMAT")
            params = parse.urlencode({
                'campaign': campaign.pk,
                'status': [Interview.COMPLETED, Interview.APPROVED],
                'date_from': date,
                'date_to': date
            }, doseq=True)
            url = "{}?{}".format(reverse("admission:interviews:list"), params)
            return HttpResponseRedirect(redirect_to=url)
        return super().get(request, *args, **kwargs)

    def get_filterset_class(self):
        if self.request.user.is_curator:
            return InterviewsCuratorFilter
        return InterviewsFilter

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        kwargs['request'] = self.request
        if not kwargs["data"]:
            today = formats.date_format(timezone.now(), "SHORT_DATE_FORMAT")
            kwargs["data"] = {
                "status": [Interview.COMPLETED, Interview.APPROVED],
                "date_from": today,
                "date_to": today
            }
        return kwargs

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
        q = (Interview.objects
             .filter(applicant__campaign__branch__in=branches)
             .select_related("applicant__campaign__branch",
                             "venue__city")
             .prefetch_related("interviewers")
             .annotate(average=Coalesce(Avg('comments__score'), Value(0.0)))
             .order_by("date", "pk"))
        if not self.request.user.is_curator:
            # To interviewers show interviews from current campaigns where
            # they participate.
            try:
                current_campaigns = list(Campaign.objects
                                         .filter(current=True,
                                                 branch__site_id=settings.SITE_ID)
                                         .values_list("pk", flat=True))
            except Campaign.DoesNotExist:
                messages.error(self.request, "Нет активных кампаний по набору.")
                return Interview.objects.none()
            q = q.filter(applicant__campaign_id__in=current_campaigns,
                         interviewers=self.request.user)
        return q


class InterviewDetailView(InterviewerOnlyMixin, generic.TemplateView):
    template_name = "admission/interview_detail.html"

    def get_queryset(self):
        branches = Branch.objects.for_site(site_id=settings.SITE_ID)
        return (Interview.objects
                .filter(pk=self.kwargs['pk'],
                        applicant__campaign__branch__in=branches))

    def get_context_data(self, **kwargs):
        qs = (self.get_queryset()
              .prefetch_related("interviewers",
                                "assignments",
                                Prefetch("comments",
                                         queryset=(Comment.objects
                                                   .select_related("interviewer")))))
        interview = get_object_or_404(qs)
        context = get_applicant_context(self.request, interview.applicant_id)
        interview.applicant = context['applicant']
        show_all_comments = self.request.user.is_curator
        form_kwargs = {
            "interview": interview,
            "interviewer": self.request.user
        }
        for comment in interview.comments.all():
            if comment.interviewer == self.request.user:
                show_all_comments = True
                form_kwargs["instance"] = comment
        context.update({
            "interview": interview,
            "assignments_form": InterviewAssignmentsForm(instance=interview),
        })
        context["show_all_comments"] = show_all_comments
        context["comment_form"] = InterviewCommentForm(**form_kwargs)
        return context

    def post(self, request, *args, **kwargs):
        """Update list of assignments"""
        if not request.user.is_curator:
            return HttpResponseForbidden()
        interview = get_object_or_404(self.get_queryset())
        form = InterviewAssignmentsForm(instance=interview,
                                        data=self.request.POST)
        if form.is_valid():
            form.save()
            messages.success(self.request, "Список заданий успешно обновлён",
                             extra_tags='timeout')
        url = "{}#assignments".format(interview.get_absolute_url())
        return HttpResponseRedirect(url)


# FIXME: rewrite as API view
class InterviewCommentUpsertView(InterviewerOnlyMixin, GenericModelView):
    """Update/Insert view for interview comment"""
    http_method_names = ['post', 'put']

    def post(self, request, *args, **kwargs):
        qs = (Interview.objects
              .select_related('applicant__campaign__branch__site')
              .filter(pk=self.kwargs['pk']))
        interview = get_object_or_404(qs)
        comment = self.object = self.get_object()
        form = InterviewCommentForm(data=request.POST,
                                    instance=comment,
                                    interview=interview,
                                    interviewer=self._get_interviewer())
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_object(self, queryset=None):
        try:
            return (Comment.objects
                    .get(interview=self.kwargs["pk"],
                         interviewer=self.request.user))
        except Comment.DoesNotExist:
            return None

    @transaction.atomic
    def form_valid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            _ = form.save()
            return JsonResponse({"success": "true"})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            msg = "<br>".join(m for ms in form.errors.values() for m in ms)
            r = JsonResponse({"errors": msg})
            r.status_code = 400
            return r
        return super().form_invalid(form)

    def get_success_url(self):
        messages.success(self.request, "Комментарий успешно сохранён",
                         extra_tags='timeout')
        return reverse("admission:interviews:detail",
                       args=[self.object.interview_id])

    def _get_interviewer(self):
        interview_id = self.kwargs["pk"]
        interview = get_object_or_404(Interview.objects
                                      .filter(pk=interview_id)
                                      .prefetch_related("interviewers"))
        if self.request.user.is_curator:
            return self.request.user
        for i in interview.interviewers.all():
            if i.pk == self.request.user.pk:
                return i
        return None


class InterviewResultsDispatchView(CuratorOnlyMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        """Based on user settings, get preferred page address and redirect"""
        branches = (Campaign.objects
                    .filter(current=True,
                            branch__site_id=settings.SITE_ID)
                    .values_list("branch__code", flat=True))
        if self.request.user.branch_id is not None:
            branch_code = self.request.user.branch.code
        else:
            branch_code = settings.DEFAULT_BRANCH_CODE
        if branch_code not in branches:
            branch_code = next(branches.iterator(), settings.DEFAULT_BRANCH_CODE)
        return reverse("admission:results:list", kwargs={
            "branch_code": branch_code,
        })


class BranchFromURLViewMixin:
    """
    This view mixin sets `branch` attribute to the request object based on
    `request.site` and non-empty `branch_code` url named argument
    """
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        branch_code = kwargs.get("branch_code", None)
        if not branch_code:
            raise ImproperlyConfigured(
                f"{self.__class__} is subclass of {self.__class__.__name__} but "
                f"`branch_code` view keyword argument is not specified or empty")
        request.branch = Branch.objects.get_by_natural_key(branch_code,
                                                           request.site.id)


class InterviewResultsView(CuratorOnlyMixin, FilterMixin,
                           BranchFromURLViewMixin, TemplateResponseMixin,
                           BaseModelFormSetView):
    context_object_name = 'interviews'
    template_name = "lms/admission/admission_results.html"
    model = Applicant
    form_class = ApplicantFinalStatusForm
    filterset_class = ResultsFilter

    def dispatch(self, request, *args, **kwargs):
        self.active_campaigns = (Campaign.objects
                                 .filter(current=True,
                                         branch__site_id=settings.SITE_ID)
                                 .select_related('branch'))
        try:
            self.selected_campaign = next(c for c in self.active_campaigns
                                          if c.branch_id == request.branch.pk)
        except StopIteration:
            messages.error(self.request,
                           "Активная кампания по набору не найдена")
            return HttpResponseRedirect(reverse("admission:applicants:list"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        formset = self.construct_formset()
        context = self.get_context_data(filter=self.filterset,
                                        formset=formset)
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
        kwargs['branch_code'] = self.kwargs["branch_code"]
        return kwargs

    def get_formset_kwargs(self):
        """Overrides queryset for instantiating the formset."""
        kwargs = super().get_formset_kwargs()
        kwargs['queryset'] = self.filterset.qs
        return kwargs

    def get_queryset(self):
        return (
            Applicant.objects
            .filter(campaign=self.selected_campaign,
                    status__in=ApplicantStatuses.RESULTS_STATUSES)
            .select_related("exam", "online_test", "university")
            .prefetch_related(
                Prefetch(
                    'interviews',
                    queryset=(Interview.objects
                              .select_related('venue__city')
                              .annotate(_average_score=Avg('comments__score'))),
                ),
            ))

    def get_context_data(self, filter, formset, **kwargs):
        stats = Counter()
        final_statuses = {
            Applicant.ACCEPT,
            Applicant.ACCEPT_IF,
            Applicant.VOLUNTEER,
            Applicant.WAITING_FOR_PAYMENT,
            Applicant.ACCEPT_PAID,
        }
        received = 0
        for form in formset.forms:
            applicant = form.instance
            stats.update((applicant.status,))
            if applicant.status in final_statuses:
                received += 1
        stats = [(Applicant.get_name_by_status_code(s), cnt) for
                 s, cnt in stats.items()]
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
            "selected_campaign": self.selected_campaign
        }
        return context


class ApplicantCreateStudentView(CuratorOnlyMixin, generic.View):
    http_method_names = ['post']

    @atomic
    def post(self, request, *args, **kwargs):
        applicant_pk = kwargs.get("pk")
        back_url = reverse("admission:applicants:list")
        try:
            applicant = Applicant.objects.get(pk=applicant_pk)
        except Applicant.DoesNotExist:
            messages.error(self.request, "Анкета не найдена",
                           extra_tags='timeout')
            return HttpResponseRedirect(reverse("admission:applicants:list"))
        try:
            user = create_student_from_applicant(applicant)
        except User.MultipleObjectsReturned:
            messages.error(
                self.request,
                f"Найдено несколько пользователей с email {applicant.email}")
            return HttpResponseRedirect(back_url)
        except UsernameError as e:
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
    url = django_reverse("appointment:api:interview_appointment_slots", kwargs={
        "year": invitation.applicant.campaign.year,
        "secret_code": invitation.secret_code.hex,
        "slot_id": 42})
    endpoint, _ = url.rsplit("42", 1)
    return endpoint + "{slotId}/"


class InterviewAppointmentView(TemplateView):
    template_name = "lms/admission/interview_appointment.html"

    class InputSerializer(serializers.Serializer):
        secret_code = serializers.UUIDField(format='hex_verbose')
        year = serializers.IntegerField()

    def get(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=kwargs)
        if not serializer.is_valid(raise_exception=False):
            return HttpResponseNotFound()

        invitation = get_interview_invitation(**serializer.validated_data)
        if not invitation or invitation.is_expired or invitation.is_declined:
            raise Http404

        tz_msk = pytz.timezone("Europe/Moscow")
        invitation_deadline = formats.date_format(invitation.expired_at.astimezone(tz_msk),
                                                  "j E H:i")
        decline_invitation_url = django_reverse("appointment:api:interview_appointment", kwargs={
            "year": invitation.applicant.campaign.year,
            "secret_code": invitation.secret_code.hex
        })

        context: Dict[str, Any] = {
            "invitation": invitation,
            "interview": None,
            "app_data": {
                "props": {
                    "invitationDeadline": invitation_deadline,
                    "endpointSlotOccupation": get_slot_occupation_url(invitation),
                    "endpointDeclineInvitation": decline_invitation_url,
                    "csrfToken": get_token(request)
                }
            }
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
                    "slots": [AppointmentSlotSerializer(instance=s).data for s in slots]
                }
                days.append(day)
            context["app_data"]["props"]["days"] = days
        return self.render_to_response(context)


class InterviewAppointmentAssignmentsView(generic.TemplateView):
    template_name = "admission/interview_appointment_assignments.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            secret_code = uuid.UUID(self.kwargs['secret_code'], version=4)
        except ValueError:
            raise Http404
        campaign_year = self.kwargs['year']
        interview = get_object_or_404(
            Interview.objects
                .filter(secret_code=secret_code,
                        applicant__campaign__year=campaign_year)
                .select_related("applicant")
                .prefetch_related('assignments'))
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
        campaign_year: int = kwargs['year']
        access_key: str = kwargs['access_key']
        try:
            branches = Branch.objects.for_site(site_id=settings.SITE_ID)
            acceptance = get_acceptance_ready_to_confirm(year=campaign_year,
                                                         access_key=access_key,
                                                         filters=[Q(applicant__campaign__branch__in=branches)])
        except ValidationError:
            raise Http404
        if not acceptance:
            raise Http404
        self.acceptance = acceptance

    def get(self, request: HttpRequest, *args, **kwargs):
        context: Dict[str, Any]
        confirmation_code = request.session.get(SESSION_CONFIRMATION_CODE_KEY)
        is_authorized = confirmation_code and self.acceptance.confirmation_code == confirmation_code
        if not is_authorized:
            authorization_form = ConfirmationAuthorizationForm(instance=self.acceptance)
            context = {"authorization_form": authorization_form}
        else:
            confirmation_form = ConfirmationForm(acceptance=self.acceptance)
            context = {"confirmation_form": confirmation_form}
        return self.render_to_response(context)

    def post(self, request: HttpRequest, *args, **kwargs):
        context: Dict[str, Any]
        confirmation_code = request.session.get(SESSION_CONFIRMATION_CODE_KEY)
        is_authorized = confirmation_code and self.acceptance.confirmation_code == confirmation_code
        if not is_authorized:
            # Check authorization form
            authorization_form = ConfirmationAuthorizationForm(instance=self.acceptance,
                                                               data=request.POST)
            if authorization_form.is_valid():
                # Save confirmation code in user session and redirect
                request.session[SESSION_CONFIRMATION_CODE_KEY] = authorization_form.cleaned_data['authorization_code']
                return HttpResponseRedirect(redirect_to=request.path_info)
            else:
                context = {"authorization_form": authorization_form}
                return self.render_to_response(context)
        else:
            confirmation_form = ConfirmationForm(acceptance=self.acceptance,
                                                 data=request.POST,
                                                 files=request.FILES)
            if confirmation_form.is_valid():
                confirmation_form.save()
                return HttpResponseRedirect(redirect_to=reverse("admission:acceptance:confirmation_done"))
            else:
                context = {"confirmation_form": confirmation_form}
                return self.render_to_response(context)


class ConfirmationOfAcceptanceForStudiesDoneView(TemplateView):
    template_name = "lms/admission/confirmation_of_acceptance_done.html"
