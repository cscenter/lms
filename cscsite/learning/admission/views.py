# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import json
import re
import uuid
from collections import Counter

from django.apps import apps
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.http.response import HttpResponseForbidden, HttpResponseBadRequest
from django.urls import reverse
from django.db.models import Q, Avg, When, Value, Case, IntegerField, Prefetch, Count
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.generic.base import TemplateResponseMixin, ContextMixin, \
    RedirectView
from django.views.generic.edit import BaseUpdateView, BaseCreateView, \
    ModelFormMixin
from django_filters.views import BaseFilterView
from extra_views import ModelFormSetView
from formtools.wizard.views import NamedUrlSessionWizardView
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import CuratorAccessPermission
from core.settings.base import DEFAULT_CITY_CODE, LANGUAGE_CODE, TIME_ZONES
from core.utils import render_markdown
from learning.admission.filters import ApplicantFilter, InterviewsFilter, \
    InterviewsCuratorFilter, InterviewStatusFilter
from learning.admission.forms import InterviewCommentForm, \
    ApplicantReadOnlyForm, \
    InterviewForm, ApplicantStatusForm, \
    InterviewResultsModelForm, ApplicationFormStep1, ApplicationInSpbForm, \
    ApplicationInNskForm, InterviewAssignmentsForm, InterviewFromStreamForm
from learning.admission.models import Interview, Comment, Contest, Test, Exam, \
    Applicant, Campaign, InterviewAssignment, InterviewSlot, InterviewStream, \
    InterviewInvitation
from learning.admission.serializers import InterviewSlotSerializer
from learning.admission.services import create_invitation
from learning.admission.utils import generate_interview_reminder, \
    calculate_time
from learning.viewmixins import InterviewerOnlyMixin, CuratorOnlyMixin

from users.models import CSCUser
from .tasks import application_form_send_email


ADMISSION_SETTINGS = apps.get_app_config("admission")


date_re = re.compile(
    r'(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{4})$'
)


# Note: Not useful without Yandex.Contest REST API support :<
# FIXME: Don't allow to save duplicates.
# TODO: I'm now sure we need server side wizard.
# TODO: The same we can achieve with Redux + some js.
class ApplicantRequestWizardView(NamedUrlSessionWizardView):
    template_name = "learning/admission/application_form.html"
    form_list = [
        ('welcome', ApplicationFormStep1),
        ('spb', ApplicationInSpbForm),
        ('nsk', ApplicationInNskForm),
    ]
    initial_dict = {
        'spb': {'has_job': 'Нет'},
        'nsk': {'has_job': 'Нет'},
    }

    def done(self, form_list, **kwargs):
        cleaned_data = {}
        for form in form_list:
            cleaned_data.update(form.cleaned_data)
        cleaned_data['where_did_you_learn'] = ",".join(
            cleaned_data['where_did_you_learn'])
        cleaned_data['preferred_study_programs'] = ",".join(
            cleaned_data['preferred_study_programs'])
        if cleaned_data['has_job'] == 'no':
            del cleaned_data['workplace']
            del cleaned_data['position']
        city_code = cleaned_data['city']
        today = timezone.now()
        campaign = (Campaign.objects
                    .filter(year=today.year, city__code=city_code)
                    .first())
        if not campaign:
            messages.error(self.request,
                           "Нет активной кампании для выбранного города!")
            return HttpResponseRedirect(reverse("admission_application"))
        cleaned_data['campaign'] = campaign
        del cleaned_data['city']
        applicant = Applicant(**cleaned_data)
        applicant.clean()
        applicant.save()
        if applicant.pk:
            application_form_send_email.delay(applicant.pk, LANGUAGE_CODE)
        else:
            print("SOMETHING WRONG?")
        return HttpResponseRedirect(reverse("admission_application_complete"))

    @staticmethod
    def show_spb_form(wizard):
        cleaned_data = wizard.get_cleaned_data_for_step('welcome')
        return cleaned_data and cleaned_data['city'] == 'spb'

    @staticmethod
    def show_nsk_form(wizard):
        cleaned_data = wizard.get_cleaned_data_for_step('welcome')
        return cleaned_data and cleaned_data['city'] == 'nsk'

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context['step1_data'] = self.storage.get_step_data('welcome')
        return context


ApplicantRequestWizardView.condition_dict = {
    'spb': ApplicantRequestWizardView.show_spb_form,
    'nsk': ApplicantRequestWizardView.show_nsk_form,
}


class ApplicationCompleteView(generic.TemplateView):
    template_name = "learning/admission/application_done.html"


class ApplicantContextMixin(object):
    @staticmethod
    def get_applicant_context(applicant_id):
        context = {}
        applicant = get_object_or_404(
            Applicant.objects
                     .select_related("exam", "campaign", "campaign__city",
                                     "online_test", "university")
                     .filter(pk=applicant_id))
        context["applicant"] = applicant
        context["applicant_form"] = ApplicantReadOnlyForm(instance=applicant)
        context["campaign"] = applicant.campaign
        contest_ids = []
        try:
            context["online_test"] = applicant.online_test
            contest_ids.append(context["online_test"].yandex_contest_id)
        except Test.DoesNotExist:
            pass
        try:
            context["exam"] = applicant.exam
            contest_ids.append(context["exam"].yandex_contest_id)
        except Exam.DoesNotExist:
            pass
        # get contests description
        contests = {}
        contest_ids = [c for c in contest_ids if c]
        if contest_ids:
            contests_query = Contest.objects.filter(contest_id__in=contest_ids)
            for c in contests_query:
                if c.contest_id == context["online_test"].yandex_contest_id:
                    contests["test"] = c
                elif c.contest_id == context["exam"].yandex_contest_id:
                    contests["exam"] = c
        context["contests"] = contests
        # Similar applicants
        conditions = [
            Q(email=applicant.email),
            (
                Q(first_name__iexact=applicant.first_name) &
                Q(surname__iexact=applicant.surname) &
                Q(patronymic__iexact=applicant.patronymic)
            ),
        ]
        if applicant.phone:
            conditions.append(Q(phone=applicant.phone))
        if applicant.stepic_id:
            conditions.append(Q(stepic_id=applicant.stepic_id))
        if applicant.yandex_id_normalize:
            conditions.append(Q(yandex_id_normalize=applicant.yandex_id_normalize))
        query = conditions.pop()
        for c in conditions:
            query |= c

        similar_applicants = Applicant.objects.filter(query)
        similar_applicants = filter(lambda a: a != applicant,
                                    similar_applicants)
        context["similar_applicants"] = similar_applicants
        return context


class ApplicantListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
    context_object_name = 'applicants'
    model = Applicant
    template_name = "learning/admission/applicant_list.html"
    filterset_class = ApplicantFilter
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset
        return context

    def get_queryset(self):
        return (Applicant.objects
                .select_related("exam", "online_test", "campaign", "university",
                                "campaign__city")
                .prefetch_related("interview")
                .annotate(exam__score_coalesce=Coalesce('exam__score',
                                                        Value(-1)))
                .order_by("-exam__score_coalesce", "-online_test__score", "pk"))

    def get(self, request, *args, **kwargs):
        """Set filter defaults and redirect"""
        user = self.request.user
        if user.is_curator and "campaign" not in self.request.GET:
            # Try to find user preferred current campaign id
            current = list(Campaign.objects.filter(current=True)
                           .only("pk", "city_id"))
            try:
                c = next(c.pk for c in current if c.city_id == user.city_id)
            except StopIteration:
                # We didn't find active campaign for user city. Try to get
                # any current campaign or show all if no active at all.
                c = next((c.pk for c in current), "")
            url = "{}?campaign={}&status=".format(
                reverse("admission_applicants"),
                c)
            return HttpResponseRedirect(redirect_to=url)
        return super().get(request, *args, **kwargs)


class ApplicantDetailView(InterviewerOnlyMixin, ApplicantContextMixin,
                          TemplateResponseMixin, BaseCreateView):

    form_class = InterviewForm
    template_name = "learning/admission/applicant_detail.html"

    def get_queryset(self):
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        return (Applicant.objects
                .select_related("exam", "online_test", "campaign",
                                "campaign__city")
                .get(pk=applicant_id))

    def get_context_data(self, **kwargs):
        applicant_id = self.kwargs[self.pk_url_kwarg]
        context = kwargs
        context.update(self.get_applicant_context(applicant_id))
        applicant = context["applicant"]
        context["status_form"] = ApplicantStatusForm(instance=applicant)
        if 'form' not in kwargs:
            invitation = InterviewInvitation.objects.for_applicant(applicant)
            if not invitation:
                city_code = applicant.campaign.city_id
                context["form"] = InterviewFromStreamForm(city_code=city_code)
            else:
                context["invitation"] = invitation
        return context

    def get(self, request, *args, **kwargs):
        applicant_id = self.kwargs[self.pk_url_kwarg]
        try:
            interview = Interview.objects.get(applicant_id=applicant_id)
            return HttpResponseRedirect(reverse("admission_interview_detail",
                                                args=[interview.pk]))
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
            city_code=applicant.campaign.city_id,
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
        return reverse("admission_interview_detail", args=[self.object.pk])

    def create_interview_from_slot(self, applicant, stream_form, slot):
        data = InterviewForm.build_data(applicant, slot)
        form = InterviewForm(data=data)
        if form.is_valid():
            with transaction.atomic():
                sid = transaction.savepoint()
                interview = self.object = form.save()
                slot_has_taken = InterviewSlot.objects.take(slot, interview)
                generate_interview_reminder(interview, slot)
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
        stream = stream_form.cleaned_data['stream']
        try:
            create_invitation(stream, applicant,
                              uri_builder=self.request.build_absolute_uri)
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
        return reverse("admission_applicant_detail", args=[self.object.pk])


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


class InterviewListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
    context_object_name = 'interviews'
    model = Interview
    paginate_by = 50
    template_name = "learning/admission/interviews.html"

    def get(self, request, *args, **kwargs):
        """
        Redirects curator to appropriate campaign if no any provided.
        """
        user = self.request.user
        if user.is_curator and "campaign" not in self.request.GET:
            # Try to find user preferred current campaign id
            current = list(Campaign.objects.filter(current=True)
                           .only("pk", "city_id"))
            try:
                c = next(c.pk for c in current if c.city_id == user.city_id)
            except StopIteration:
                # We didn't find active campaign for user city. Try to get
                # any current campaign or show all if no active at all.
                c = next((c.pk for c in current), "")
            if not c:
                messages.error(self.request, "Нет активных кампаний по набору.")
            # Duplicate initial values from filterset
            status = InterviewStatusFilter.AGREED
            date = timezone.now().strftime("%d.%m.%Y")
            url = "{}?campaign={}&status={}&date={}".format(
                reverse("admission_interviews"),
                c, status, date)
            return HttpResponseRedirect(redirect_to=url)
        return super().get(request, *args, **kwargs)

    def get_filterset_class(self):
        if self.request.user.is_curator:
            return InterviewsCuratorFilter
        return InterviewsFilter

    def get_filterset_kwargs(self, filterset_class):
        # Note: With django-filter 1.0.4 the best way to define initial value
        # for form without magic is to put it in the view.
        kwargs = super().get_filterset_kwargs(filterset_class)
        if not kwargs["data"]:
            kwargs["data"] = {
                "status": InterviewStatusFilter.AGREED,
                "date": timezone.now().date()
            }
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO: collect stats for curators here?
        context["today"] = self.object_list.filter(
            date__date=timezone.now(),
            status=Interview.APPROVED).count()
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
             .select_related("applicant", "applicant__campaign")
             .prefetch_related("interviewers")
             .annotate(average=Coalesce(Avg('comments__score'), Value(0)))
             .order_by("date", "pk"))
        if not self.request.user.is_curator:
            # Show interviewers only interviews from current campaigns where
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
    template_name = "learning/admission/interview.html"

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
        context = self.get_applicant_context(interview.applicant_id)
        # Activate timezone for the whole detail view
        timezone.activate(context['applicant'].get_city_timezone())
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

    def get(self, request, *args, **kwargs):
        # Quick fix, return empty json on GET
        if not self.request.is_ajax():
            return JsonResponse({})
        return super(InterviewCommentView, self).get(request, *args, **kwargs)

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

    def get_success_url(self):
        messages.success(self.request, "Комментарий успешно сохранён",
                         extra_tags='timeout')
        return reverse("admission_interview_detail",
                       args=[self.object.interview_id])

    @transaction.atomic
    def form_valid(self, form):
        if self.request.is_ajax():
            _ = form.save()
            return JsonResponse({"success": "true"})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            return JsonResponse({"success": "false",
                                 "errors": form.errors.as_json()})
        return super().form_invalid(form)

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

    def get_form_kwargs(self):
        interview_id = self.kwargs["pk"]
        kwargs = super().get_form_kwargs()
        kwargs.update({
            "interviewer": self._get_interviewer(),
            "interview_id": interview_id
        })
        if self.request.is_ajax():
            try:
                json_data = json.loads(self.request.body.decode("utf-8"))
                kwargs.update({
                    'data': json_data,
                })
            except ValueError:
                pass
        return kwargs


class InterviewResultsDispatchView(CuratorOnlyMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        """Based on user settings, get preferred page address and redirect"""
        cs = (Campaign.objects
              .filter(current=True)
              .values_list("city_id", flat=True))
        preferred_city = self.request.user.city_id
        if preferred_city in cs:
            city_redirect_to = preferred_city
        else:
            city_redirect_to = next(cs.iterator(), DEFAULT_CITY_CODE)
        return reverse("admission_interview_results_by_city", kwargs={
            "city_slug": city_redirect_to
        })


class InterviewResultsView(CuratorOnlyMixin, ModelFormSetView):
    """
    We can have multiple interviews for applicant
    """
    # TODO: Think about pagination for model formsets in the future.
    context_object_name = 'interviews'
    template_name = "learning/admission/interview_results.html"
    model = Applicant
    form_class = InterviewResultsModelForm

    def get_context_data(self, **kwargs):
        # XXX: To avoid double query to DB, skip ModelFormSetView action
        context = ContextMixin.get_context_data(self, **kwargs)
        stats = Counter()
        for form in context["formset"].forms:
            # Select the highest interview score to sort by
            applicant = form.instance
            interview = applicant.interview
            stats.update((applicant.status,))

        def cpm_interview_best_score(form):
            # XXX: `average` score calculated with queryset
            if form.instance.interview.average is None:
                return Comment.UNREACHABLE_COMMENT_SCORE
            else:
                return form.instance.interview.average

        context["formset"].forms.sort(key=cpm_interview_best_score,
                                      reverse=True)
        context["stats"] = [(Applicant.get_name_by_status_code(s), cnt) for
                            s, cnt in stats.items()]
        context["active_campaigns"] = self.active_campaigns
        context["selected_campaign"] = self.selected_campaign
        return context

    def get_factory_kwargs(self):
        kwargs = super(InterviewResultsView, self).get_factory_kwargs()
        kwargs["extra"] = 0
        kwargs["can_order"] = False
        kwargs["can_delete"] = False
        return kwargs

    def get_queryset(self):
        """Sort data by average interview score"""
        return (Applicant.objects
            # TODO: Carefully restrict by status to optimize query
            .filter(campaign=self.selected_campaign)
            .select_related("exam", "online_test", "university")
            .exclude(interview__isnull=True)
            .prefetch_related(
                Prefetch(
                    'interview',
                    queryset=(Interview.objects
                              .annotate(average=Avg('comments__score'))),
                ),
            )
        )

    def dispatch(self, request, *args, **kwargs):
        # It's (mb?) irrelevant to POST action, but not a big deal
        self.active_campaigns = (Campaign.objects
                                 .filter(current=True)
                                 .select_related("city"))
        try:
            city_code = self.kwargs["city_slug"]
            self.selected_campaign = next(c for c in self.active_campaigns
                                          if c.city.code == city_code)
        except StopIteration:
            messages.error(self.request,
                           "Активная кампания по набору не найдена")
            return HttpResponseRedirect(reverse("admission_applicants"))
        return super().dispatch(request, *args, **kwargs)


class ApplicantCreateUserView(CuratorOnlyMixin, generic.View):
    http_method_names = ['post']

    @atomic
    def post(self, request, *args, **kwargs):
        # TODO: add tests
        applicant_pk = kwargs.get("pk")
        back_url = reverse("admission_applicants")
        try:
            applicant = Applicant.objects.get(pk=applicant_pk)
        except Applicant.DoesNotExist:
            messages.error(self.request, "Анкета не найдена",
                           extra_tags='timeout')
            return HttpResponseRedirect(reverse("admission_applicants"))
        try:
            user = CSCUser.create_student_from_applicant(applicant)
        except CSCUser.MultipleObjectsReturned:
            messages.error(
                self.request,
                "Всё плохо. Найдено несколько пользователей "
                "с email {}".format(applicant.email))
            return HttpResponseRedirect(back_url)
        except RuntimeError as e:
            # username already taken, failed to create the new unique one
            messages.error(self.request, e.args[0])
            return HttpResponseRedirect(back_url)
        # Link applicant and user
        applicant.user = user
        applicant.save()
        url = reverse("admin:users_cscuser_change", args=[user.pk])
        return HttpResponseRedirect(url)


class InterviewAppointmentView(generic.TemplateView):
    template_name = "learning/admission/interview_appointment.html"

    def dispatch(self, request, *args, **kwargs):
        """Validate GET-parameters"""
        try:
            date = datetime.datetime.strptime(self.kwargs['date'], '%d.%m.%Y')
            secret = uuid.UUID(self.kwargs['secret_code'], version=4)
        except ValueError:
            return HttpResponseBadRequest()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        invitation = self.get_invitation()
        timezone.activate(invitation.get_city_timezone())
        context = {
            "invitation": invitation,
            "interview": None
        }
        time_diff = datetime.timedelta(minutes=30)
        if hasattr(invitation.applicant, "interview"):
            interview = invitation.applicant.interview
            if invitation.stream.with_assignments:
                interview.date -= time_diff
            context["interview"] = interview
        elif not invitation.is_expired:
            slots = invitation.stream.slots.all()
            if invitation.stream.with_assignments:
                for slot in slots:
                    slot.start_at = calculate_time(slot.start_at, time_diff)
            context["slots"] = slots
        # FIXME: What if slots are all busy? Is it possible?
        return context

    def get_invitation(self):
        date = datetime.datetime.strptime(self.kwargs['date'], '%d.%m.%Y')
        return get_object_or_404(
            InterviewInvitation.objects
                .select_related("stream", "stream__venue", "applicant")
                .filter(date=date,
                        secret_code=self.kwargs['secret_code']))

    def post(self, request, *args, **kwargs):
        invitation = self.get_invitation()
        if "time" not in request.POST:
            messages.error(self.request, "Вы забыли указать время",
                           extra_tags="timeout")
            return HttpResponseRedirect(invitation.get_absolute_url())
        # Can't edit through admin interface
        # TODO: Do I really need to store date in invitation model?
        assert invitation.date == invitation.stream.date
        slot_id = int(request.POST['time'])
        slot = get_object_or_404(
            InterviewSlot.objects
                .filter(pk=slot_id,
                        # Additional check that slot consistent
                        # with invitation stream
                        stream_id=invitation.stream_id))
        data = InterviewForm.build_data(invitation.applicant, slot)
        form = InterviewForm(data=data)
        if form.is_valid():
            with transaction.atomic():
                sid = transaction.savepoint()
                interview = form.save()
                slot_has_taken = InterviewSlot.objects.take(slot, interview)
                generate_interview_reminder(interview, slot)
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


class InterviewSlots(APIView):
    """
    Returns interview slots for requested venue and date.
    """
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, format=None):
        slots = []
        if "stream" in request.GET:
            try:
                stream = int(self.request.GET["stream"])
            except ValueError:
                raise ParseError()
            slots = InterviewSlot.objects.filter(stream_id=stream)
        serializer = InterviewSlotSerializer(slots, many=True)
        return Response(serializer.data)
