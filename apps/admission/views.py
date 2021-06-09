import uuid
from collections import Counter
from datetime import timedelta
from typing import Optional
from urllib import parse

import pytz
from braces.views import UserPassesTestMixin
from django_filters.views import BaseFilterView, FilterMixin
from extra_views.formsets import BaseModelFormSetView
from rest_framework import serializers
from vanilla import TemplateView

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.db.models import Avg, Case, Count, Prefetch, Sum, Value, When
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
    InterviewsFilter, InterviewStreamFilter, ResultsFilter
)
from admission.forms import (
    ApplicantReadOnlyForm, ApplicantStatusForm, InterviewAssignmentsForm,
    InterviewCommentForm, InterviewForm, InterviewFromStreamForm, ResultsModelForm
)
from admission.models import (
    Applicant, Campaign, Comment, Contest, Exam, Interview, InterviewAssignment,
    InterviewInvitation, InterviewSlot, InterviewStream, Test
)
from admission.services import (
    EmailQueueService, UsernameError, create_invitation, create_student_from_applicant,
    get_meeting_time, get_streams
)
from core.models import Branch
from core.timezone import get_now_utc, now_local
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.urls import reverse
from core.utils import render_markdown
from tasks.models import Task
from users.api.serializers import PhotoSerializerField
from users.mixins import CuratorOnlyMixin
from users.models import User

from .constants import InterviewInvitationStatuses, InterviewSections
from .selectors import get_interview_invitation, get_occupied_slot
from .tasks import import_testing_results


class ApplicantContextMixin:
    @staticmethod
    def get_applicant_context(request, applicant_id):
        qs = (Applicant.objects
              .select_related("exam", "campaign__branch",
                              "online_test", "university")
              .filter(pk=applicant_id))
        applicant = get_object_or_404(qs)
        contest_ids = []
        try:
            online_test = applicant.online_test
            contest_ids.append(online_test.yandex_contest_id)
        except Test.DoesNotExist:
            online_test = None
        try:
            exam = applicant.exam
            contest_ids.append(applicant.exam.yandex_contest_id)
        except Exam.DoesNotExist:
            exam = None
        contest_ids = [c for c in contest_ids if c]
        # get contests description
        contests = {}
        if contest_ids:
            contests_qs = Contest.objects.filter(contest_id__in=contest_ids)
            for c in contests_qs:
                if c.type == Contest.TYPE_TEST:
                    contests["test"] = c
                elif c.type == Contest.TYPE_EXAM:
                    contests["exam"] = c
        context = {
            "applicant": applicant,
            "applicant_form": ApplicantReadOnlyForm(request=request,
                                                    instance=applicant),
            "campaign": applicant.campaign,
            "contests": contests,
            "exam": exam,
            "online_test": online_test,
            "similar_applicants": applicant.get_similar(),
        }
        return context


class InterviewerOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_interviewer or user.is_curator


def import_campaign_testing_results(request, campaign_id: int):
    """
    Creates new task for importing testing results from yandex contests.
    Make sure `current` campaigns are already exist in DB before add new task.
    """
    if request.method == "POST" and request.user.is_curator:
        task = Task.build(
            task_name="admission.tasks.import_testing_results",
            kwargs={"campaign_id": campaign_id},
            creator=request.user)
        same_task_in_queue = (Task.objects
                              # Add new task even if the same task is locked
                              # and in progress since it could fail in the process
                              .filter(locked_by__isnull=True,
                                      processed_at__isnull=True,
                                      task_name=task.task_name,
                                      task_params=task.task_params,
                                      task_hash=task.task_hash))
        if not same_task_in_queue.exists():
            task.save()
            # FIXME: potential deadlock if using task id instead of (task_name, task_params)
            import_testing_results.delay(task_id=task.pk)
        return HttpResponse(status=201)
    return HttpResponseForbidden()


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
    date = serializers.DateTimeField(source='date_local', format=DATE_FORMAT_RU)
    time = serializers.DateTimeField(source='date_local', format=TIME_FORMAT_RU)
    interviewers = InterviewerSerializer(many=True)

    class Meta:
        model = Interview
        fields = ("date", "time", "interviewers")


def get_interview_stream_filterset(input_serializer: serializers.Serializer):
    filters = {'campaign': input_serializer.validated_data['campaign']}
    if input_serializer.validated_data['section']:
        filters['section'] = input_serializer.validated_data['section']
    interview_stream_filterset = InterviewStreamFilter(
        data=input_serializer.validated_data,
        queryset=(InterviewStream.objects
                  .filter(**filters)
                  .order_by('-date', '-start_at', 'pk')))
    # Set action attribute on filterset form
    url = reverse("admission:interviews:invitations:list")
    form_action = f"{url}?campaign={input_serializer.data['campaign']}&section={input_serializer.data['section']}"
    interview_stream_filterset.form.helper.form_action = form_action
    return interview_stream_filterset


class InterviewInvitationListView(CuratorOnlyMixin, TemplateResponseMixin, BaseListView):
    model = InterviewStream
    template_name = "lms/admission/interview_invitation_list.html"
    paginate_by = 50

    class InputSerializer(serializers.Serializer):
        campaign = serializers.PrimaryKeyRelatedField(
            required=True,
            queryset=(Campaign.objects
                      .filter(branch__site_id=settings.SITE_ID)
                      .select_related("branch")
                      .order_by("-year", "branch__order").all()))
        section = serializers.ChoiceField(choices=InterviewSections.choices,
                                          required=True,
                                          allow_blank=True)

    def get(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.GET)
        if not serializer.is_valid(raise_exception=False):
            campaign = get_default_campaign_for_user(self.request.user)
            campaign_id = campaign.id if campaign else ""
            url = reverse("admission:interviews:invitations:list")
            url = f"{url}?campaign={campaign_id}&section="
            return HttpResponseRedirect(redirect_to=url)
        context = self.get_context_data(input_serializer=serializer, **kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        input_serializer = kwargs['input_serializer']
        interview_stream_filterset = get_interview_stream_filterset(input_serializer)
        invitations_waiting_for_response = Count(Case(
            When(interview_invitations__expired_at__lte=get_now_utc(), then=Value(None)),
            When(interview_invitations__status=InterviewInvitationStatuses.CREATED, then=Value(1)),
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
                               .select_related('interview', 'applicant')
                               .filter(**filters)
                               .prefetch_related('streams', 'interview__interviewers')
                               .order_by('applicant__last_name',
                                         'applicant_id',
                                         'pk'))
        interview_filterset = InterviewInvitationFilter(interview_stream_filterset.qs,
                                                        data=self.request.POST or None,
                                                        prefix="interview-invitation",
                                                        queryset=invitation_queryset)

        interview_invitations = []
        for invitation in interview_filterset.qs.distinct():
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
            "interview_streams": interview_streams
        }
        return context


class ApplicantListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
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
            .annotate(exam__score_coalesce=Coalesce('exam__score', Value(-1)),
                      test__score_coalesce=Coalesce('online_test__score',
                                                    Value(-1)))
            .order_by("-exam__score_coalesce", "-test__score_coalesce", "-pk"))

    def get(self, request, *args, **kwargs):
        """Sets filter defaults and redirects"""
        user = self.request.user
        if user.is_curator and "campaign" not in self.request.GET:
            campaign = get_default_campaign_for_user(user)
            campaign_id = campaign.id if campaign else ""
            url = reverse("admission:applicants:list")
            url = f"{url}?campaign={campaign_id}&status="
            return HttpResponseRedirect(redirect_to=url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = context['filter'].form.cleaned_data.get('campaign')
        testing_results = {"campaign": campaign}
        if campaign and campaign.current and self.request.user.is_curator:
            task_name = "admission.tasks.import_testing_results"
            latest_task = (Task.objects
                           .get_task(task_name, kwargs={"campaign_id": campaign.pk})
                           .order_by("-id")
                           .first())
            if latest_task:
                tz = self.request.user.time_zone
                testing_results["latest_task"] = {
                    # TODO: humanize
                    "date": latest_task.created_at_local(tz),
                    "status": latest_task.status
                }
        context["import_testing_results"] = testing_results
        return context


class ApplicantDetailView(InterviewerOnlyMixin, ApplicantContextMixin,
                          TemplateResponseMixin, BaseCreateView):

    form_class = InterviewForm
    template_name = "admission/applicant_detail.html"

    def get_queryset(self):
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        return (Applicant.objects
                .select_related("exam", "online_test", "campaign",
                                "campaign__branch")
                .get(pk=applicant_id))

    def get_context_data(self, **kwargs):
        applicant_id = self.kwargs[self.pk_url_kwarg]
        context = kwargs
        context.update(self.get_applicant_context(self.request, applicant_id))
        applicant = context["applicant"]
        context["status_form"] = ApplicantStatusForm(instance=applicant)
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
            create_invitation(streams, applicant)
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
    form_class = ApplicantStatusForm
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
             .select_related("applicant", "applicant__campaign",
                             "applicant__campaign__branch")
             .prefetch_related("interviewers")
             .annotate(average=Coalesce(Avg('comments__score'), Value(0)))
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


class InterviewDetailView(InterviewerOnlyMixin, ApplicantContextMixin,
                          generic.TemplateView):
    template_name = "admission/interview_detail.html"

    def get_context_data(self, **kwargs):
        interview_id = self.kwargs['pk']
        qs = (Interview.objects
              .filter(pk=interview_id)
              .prefetch_related("interviewers",
                                "assignments",
                                Prefetch("comments",
                                         queryset=(Comment.objects
                                                   .select_related("interviewer")))))
        interview = get_object_or_404(qs)
        context = self.get_applicant_context(self.request, interview.applicant_id)
        interview.applicant = context['applicant']
        context.update({
            "interview": interview,
            "assignments_form": InterviewAssignmentsForm(instance=interview),
        })
        show_all_comments = self.request.user.is_curator
        form_kwargs = {
            "interview_id": interview.pk,
            "interviewer": self.request.user.pk
        }
        for comment in interview.comments.all():
            if comment.interviewer == self.request.user:
                show_all_comments = True
                form_kwargs["instance"] = comment
        context["show_all_comments"] = show_all_comments
        context["comment_form"] = InterviewCommentForm(**form_kwargs)
        return context

    def post(self, request, *args, **kwargs):
        """Update list of assignments"""
        if not request.user.is_curator:
            return HttpResponseForbidden()
        interview = get_object_or_404(Interview.objects
                                      .filter(pk=self.kwargs["pk"]))
        form = InterviewAssignmentsForm(instance=interview,
                                        data=self.request.POST)
        if form.is_valid():
            form.save()
            messages.success(self.request, "Список заданий успешно обновлён",
                             extra_tags='timeout')
        url = "{}#assignments".format(interview.get_absolute_url())
        return HttpResponseRedirect(url)


class InterviewCommentView(InterviewerOnlyMixin, generic.UpdateView):
    """Update/Insert view for interview comment"""
    form_class = InterviewCommentForm
    http_method_names = ['post', 'put']

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        try:
            obj = queryset.get()
            return obj
        except (AttributeError, queryset.model.DoesNotExist):
            return None

    def get_queryset(self):
        return Comment.objects.filter(interview=self.kwargs["pk"],
                                      interviewer=self.request.user)

    @transaction.atomic
    def form_valid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            _ = form.save()
            return JsonResponse({"success": "true"})
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Комментарий успешно сохранён",
                         extra_tags='timeout')
        return reverse("admission:interviews:detail",
                       args=[self.object.interview_id])

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # TODO: return 400 status code?
            msg = "<br>".join(m for ms in form.errors.values() for m in ms)
            r = JsonResponse({"errors": msg})
            r.status_code = 400
            return r
        return super().form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            "interviewer": self._get_interviewer(),
            "interview_id": self.kwargs["pk"]
        })
        return kwargs

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
    """
    We can have multiple interviews for applicant
    """
    context_object_name = 'interviews'
    template_name = "admission/interview_results.html"
    model = Applicant
    form_class = ResultsModelForm
    filterset_class = ResultsFilter

    def dispatch(self, request, *args, **kwargs):
        self.active_campaigns = (Campaign.objects
                                 .filter(current=True, branch__site_id=settings.SITE_ID))
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
        """Sort data by average interview score"""
        return (
            Applicant.objects
            # TODO: Carefully restrict by status to optimize query
            .filter(campaign=self.selected_campaign)
            .annotate(interviews_count=Count("interviews"))
            .filter(interviews_count__gt=0)
            .select_related("exam", "online_test", "university")
            .prefetch_related(
                Prefetch(
                    'interviews',
                    queryset=(Interview.objects
                              .annotate(_average_score=Avg('comments__score'))),
                ),
            ))

    def get_context_data(self, filter, formset, **kwargs):

        def cpm_interview_best_score(form):
            a = form.instance
            exam_score = a.exam.score if hasattr(a, "exam") and a.exam.score else -1
            interviews_average_score_sum = 0
            for interview in a.interviews.all():
                if interview.average_score is not None:
                    interviews_average_score_sum += interview.average_score
            return interviews_average_score_sum, exam_score

        formset.forms.sort(key=cpm_interview_best_score, reverse=True)
        stats = Counter()
        received_statuses = {
            Applicant.ACCEPT,
            Applicant.ACCEPT_IF,
            Applicant.VOLUNTEER,
            Applicant.WAITING_FOR_PAYMENT,
            Applicant.ACCEPT_PAID,
        }
        received = 0
        for form in formset.forms:
            # Select the highest interview score to sort by
            applicant = form.instance
            stats.update((applicant.status,))
            if applicant.status in received_statuses:
                received += 1

        stats = [(Applicant.get_name_by_status_code(s), cnt) for
                 s, cnt in stats.items()]
        if received:
            stats.append(("Планируем принять всего", received))
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

        context = {
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
