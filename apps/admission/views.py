# -*- coding: utf-8 -*-

import uuid
from collections import Counter
from datetime import timedelta
from typing import Optional
from urllib import parse

from braces.views import UserPassesTestMixin
from django.conf import settings
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.db.models import Avg, Value, Prefetch
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.http import HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponseForbidden, HttpResponseBadRequest, \
    Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone, formats
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.generic.base import TemplateResponseMixin, RedirectView
from django.views.generic.edit import BaseCreateView, \
    ModelFormMixin
from django_filters.views import BaseFilterView, FilterMixin
from extra_views.formsets import BaseModelFormSetView

from admission.filters import ApplicantFilter, InterviewsFilter, \
    InterviewsCuratorFilter, ResultsFilter
from admission.forms import InterviewCommentForm, \
    ApplicantReadOnlyForm, InterviewForm, ApplicantStatusForm, \
    ResultsModelForm, InterviewAssignmentsForm, InterviewFromStreamForm
from admission.models import Interview, Comment, Contest, Applicant, Campaign, \
    InterviewAssignment, InterviewSlot, \
    InterviewInvitation, Test, Exam
from admission.services import create_invitation, create_student_from_applicant, \
    EmailQueueService, UsernameError, get_meeting_time
from core.timezone import now_local
from core.urls import reverse
from core.utils import render_markdown, bucketize
from core.views import RequestBranchMixin
from tasks.models import Task
from users.mixins import CuratorOnlyMixin
from users.models import User
from .tasks import import_testing_results


class ApplicantContextMixin:
    @staticmethod
    def get_applicant_context(request, applicant_id):
        applicant = get_object_or_404(
            Applicant.objects
                     .select_related("exam", "campaign", "campaign__branch",
                                     "online_test", "university")
                     .filter(pk=applicant_id))
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


def applicant_testing_new_task(request):
    """
    Creates new task for importing testing results from yandex contests.
    Make sure `current` campaigns are already exist in DB before add new task.
    """
    if request.method == "POST" and request.user.is_curator:
        task = Task.build(
            task_name="admission.tasks.import_testing_results",
            creator=request.user)
        # Not really atomic, just trying to avoid useless rows in DB
        try:
            # FIXME: Deal with deadlocks (locked tasks which were started
            # processing by rqworker but did fail during the processing)
            # Without it this try-block looks useless
            Task.objects.get(locked_by__isnull=True,
                             processed_at__isnull=True,
                             task_name=task.task_name,
                             task_hash=task.task_hash)
            # TODO: update `.created`?
        except Task.MultipleObjectsReturned:
            # Even more than 1 job in Task.MAX_RUN_TIME seconds
            pass
        except Task.DoesNotExist:
            task.save()
            import_testing_results.delay(task_id=task.pk)
        return HttpResponse(status=201)
    return HttpResponseForbidden()


class ApplicantListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
    context_object_name = 'applicants'
    model = Applicant
    template_name = "admission/applicant_list.html"
    filterset_class = ApplicantFilter
    paginate_by = 50

    def get_queryset(self):
        return (
            Applicant.objects
            .select_related("exam", "online_test", "campaign", "university",
                            "campaign__branch")
            .prefetch_related("interview")
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
            url = reverse("admission:applicants")
            url = f"{url}?campaign={campaign_id}&status="
            return HttpResponseRedirect(redirect_to=url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = context['filter'].form.cleaned_data.get('campaign')
        import_testing_results_btn_state = None
        if campaign and campaign.current and self.request.user.is_curator:
            task_name = "admission.tasks.import_testing_results"
            latest_task = (Task.objects
                           .get_task(task_name)
                           .order_by("-id")
                           .first())
            if latest_task:
                tz = self.request.user.get_timezone()
                import_testing_results_btn_state = {
                    # TODO: humanize
                    "date": latest_task.created_at_local(tz),
                    "status": latest_task.status
                }
            else:
                import_testing_results_btn_state = {}
        context["import_testing_results"] = import_testing_results_btn_state
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
            if not invitation:
                branch = applicant.campaign.branch
                context["form"] = InterviewFromStreamForm(branch=branch)
            else:
                context["invitation"] = invitation
        return context

    def get(self, request, *args, **kwargs):
        applicant_id = self.kwargs[self.pk_url_kwarg]
        try:
            interview = Interview.objects.get(applicant_id=applicant_id)
            return HttpResponseRedirect(interview.get_absolute_url())
        except Interview.DoesNotExist:
            return super().get(request, *args, **kwargs)

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
        return reverse("admission:interview_detail", args=[self.object.pk])

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
        return reverse("admission:applicant_detail", args=[self.object.pk])


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
    active_campaigns = list(Campaign.objects.filter(current=True)
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
            url = "{}?{}".format(reverse("admission:interviews"), params)
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
        q = (Interview.objects
             .select_related("applicant", "applicant__campaign",
                             "applicant__campaign__branch")
             .prefetch_related("interviewers")
             .annotate(average=Coalesce(Avg('comments__score'), Value(0)))
             .order_by("date", "pk"))
        if not self.request.user.is_curator:
            # To interviewers show interviews from current campaigns where
            # they participate.
            try:
                current_campaigns = list(Campaign.objects.filter(current=True)
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
        interview = get_object_or_404(
            Interview.objects
                .filter(pk=interview_id)
                .prefetch_related(
                    "interviewers",
                    "assignments",
                    Prefetch("comments",
                             queryset=(Comment.objects
                                       .select_related("interviewer")))))
        context = self.get_applicant_context(self.request, interview.applicant_id)
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
        if self.request.is_ajax():
            _ = form.save()
            return JsonResponse({"success": "true"})
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Комментарий успешно сохранён",
                         extra_tags='timeout')
        return reverse("admission:interview_detail",
                       args=[self.object.interview_id])

    def form_invalid(self, form):
        if self.request.is_ajax():
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
        branches = (Campaign.objects.filter(current=True)
                    .values_list("branch__code", flat=True))
        branch_code = self.request.user.branch.code
        if branch_code not in branches:
            branch_code = next(branches.iterator(), settings.DEFAULT_BRANCH_CODE)
        return reverse("admission:branch_interview_results", kwargs={
            "branch_code": branch_code,
        })


class InterviewResultsView(CuratorOnlyMixin, FilterMixin,
                           RequestBranchMixin, TemplateResponseMixin,
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
        self.active_campaigns = Campaign.objects.filter(current=True)
        try:
            self.selected_campaign = next(c for c in self.active_campaigns
                                          if c.branch_id == request.branch.pk)
        except StopIteration:
            messages.error(self.request,
                           "Активная кампания по набору не найдена")
            return HttpResponseRedirect(reverse("admission:applicants"))
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
            .exclude(interview__isnull=True)
            .select_related("exam", "online_test", "university")
            .prefetch_related(
                Prefetch(
                    'interview',
                    queryset=(Interview.objects
                              .annotate(_average_score=Avg('comments__score'))),
                ),
            ))

    def get_context_data(self, filter, formset, **kwargs):

        def cpm_interview_best_score(form):
            a = form.instance
            exam_score = a.exam.score if hasattr(a, "exam") else -1
            if a.interview.average_score is None:
                return Comment.UNREACHABLE_COMMENT_SCORE, exam_score
            else:
                return a.interview.average_score, exam_score

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


class ApplicantCreateUserView(CuratorOnlyMixin, generic.View):
    http_method_names = ['post']

    @atomic
    def post(self, request, *args, **kwargs):
        applicant_pk = kwargs.get("pk")
        back_url = reverse("admission:applicants")
        try:
            applicant = Applicant.objects.get(pk=applicant_pk)
        except Applicant.DoesNotExist:
            messages.error(self.request, "Анкета не найдена",
                           extra_tags='timeout')
            return HttpResponseRedirect(reverse("admission:applicants"))
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


class InterviewAppointmentView(generic.TemplateView):
    template_name = "admission/interview_appointment.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            secret_code = uuid.UUID(self.kwargs['secret_code'], version=4)
        except ValueError:
            raise Http404
        campaign_year = self.kwargs['year']
        # FIXME: если кампания закончилась? тупо 404 или показывать страницу об окончании?
        self.invitation = get_object_or_404(
            InterviewInvitation.objects
                .select_related("applicant")
                .prefetch_related("streams")
                .filter(secret_code=secret_code,
                        applicant__campaign__year=campaign_year))

    def get_context_data(self, **kwargs):
        invitation = self.invitation
        context = {
            "invitation": invitation,
            "interview": None,
            "slots": None
        }
        if invitation.is_accepted:
            # No any locked slot if applicant interview was created manually
            slot = (InterviewSlot.objects
                    .filter(interview_id=invitation.interview_id,
                            interview__applicant_id=invitation.applicant_id)
                    .select_related("interview",
                                    "stream",
                                    "stream__interview_format",
                                    "interview__applicant__campaign"))
            slot = get_object_or_404(slot)
            if slot.interview.applicant_id != invitation.applicant_id:
                # Interview accepted by invitation could be reassigned
                # to another applicant
                # TODO: 404 or show relevant error?
                raise Http404
            interview = slot.interview
            interview.date = get_meeting_time(interview.date, slot.stream)
            context["interview"] = interview
        elif not invitation.is_expired:
            streams = [s.id for s in invitation.streams.all()]
            slots = (InterviewSlot.objects
                     .filter(stream_id__in=streams)
                     .select_related("stream", "stream__interview_format",
                                     "stream__venue", "stream__venue__city")
                     .order_by("stream__date", "start_at"))
            any_slot_is_empty = False
            for slot in slots:
                if slot.is_empty:
                    any_slot_is_empty = True
                meeting_at = get_meeting_time(slot.datetime_local, slot.stream)
                slot.start_at = meeting_at.time()
            context["grouped_slots"] = bucketize(slots, key=lambda s: s.stream)
            if not any_slot_is_empty:
                # TODO: Do something bad
                pass
        return context

    def post(self, request, *args, **kwargs):
        invitation = self.invitation
        if invitation.is_accepted:
            messages.error(self.request, "Приглашение уже принято",
                           extra_tags="timeout")
            return HttpResponseRedirect(invitation.get_absolute_url())
        try:
            slot_id = int(request.POST.get('time', ''))
        except ValueError:
            messages.error(self.request, "Вы забыли указать время",
                           extra_tags="timeout")
            return HttpResponseRedirect(invitation.get_absolute_url())
        slot = get_object_or_404(InterviewSlot.objects.filter(pk=slot_id))
        # Check that slot is consistent with one of invitation streams
        if slot.stream_id not in [s.id for s in invitation.streams.all()]:
            return HttpResponseBadRequest()
        interview_data = InterviewForm.build_data(invitation.applicant, slot)
        form = InterviewForm(data=interview_data)
        if form.is_valid():
            with transaction.atomic():
                sid = transaction.savepoint()
                interview = form.save()
                slot_has_taken = InterviewSlot.objects.lock(slot, interview)
                EmailQueueService.generate_interview_confirmation(interview,
                                                                  slot.stream)
                EmailQueueService.generate_interview_reminder(interview,
                                                              slot.stream)
                # Mark invitation as accepted
                (InterviewInvitation.objects
                 .filter(pk=invitation.pk)
                 .update(interview_id=interview.id,
                         modified=timezone.now()))
                if not slot_has_taken:
                    transaction.savepoint_rollback(sid)
                    messages.error(
                        self.request,
                        "Извините, но слот уже был занят другим участником. "
                        "Выберите другое время и повторите попытку.")
                else:
                    transaction.savepoint_commit(sid)
            return HttpResponseRedirect(invitation.get_absolute_url())
        return HttpResponseBadRequest()


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
