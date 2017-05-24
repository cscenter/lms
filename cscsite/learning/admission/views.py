# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import json
import uuid
from collections import Counter
from random import choice
from string import ascii_lowercase
from string import digits

from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Avg, When, Value, Case, IntegerField, Prefetch, Count
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.generic.base import TemplateResponseMixin, ContextMixin, \
    RedirectView
from django.views.generic.edit import BaseUpdateView, BaseCreateView
from django_filters.views import BaseFilterView
from extra_views import ModelFormSetView
from formtools.wizard.views import NamedUrlCookieWizardView, \
    NamedUrlSessionWizardView

from core.settings.base import DEFAULT_CITY_CODE, LANGUAGE_CODE
from learning.admission.filters import ApplicantFilter, InterviewsFilter, \
    InterviewsCuratorFilter
from learning.admission.forms import InterviewCommentForm, ApplicantReadOnlyForm, \
    InterviewForm, ApplicantStatusForm,  \
    InterviewResultsModelForm, ApplicationFormStep1, ApplicationInSpbForm, \
    ApplicationInNskForm
from learning.admission.models import Interview, Comment, Contest, Test, Exam, \
    Applicant, Campaign
from learning.viewmixins import InterviewerOnlyMixin, CuratorOnlyMixin
from users.models import CSCUser
from .tasks import application_form_send_email


# Note: Not useful without Yandex.Contest REST API support :<
# FIXME: Don't allow to save duplicates.
# TODO: I'm now sure we need server side wizard.
# TODO: The same we can achieve with Redux + some js.
class ApplicantRequestWizardView(NamedUrlSessionWizardView):
    template_name = "learning/admission/application.html"
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
        today = now()
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
                     .select_related("exam", "campaign", "online_test",
                                     "university")
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
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        context = super(ApplicantDetailView, self).get_context_data(
            **kwargs)
        context.update(self.get_applicant_context(applicant_id))
        context["status_form"] = ApplicantStatusForm(
            instance=context["applicant"])
        return context

    def get(self, request, *args, **kwargs):
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        try:
            interview = Interview.objects.get(applicant_id=applicant_id)
            return HttpResponseRedirect(reverse("admission_interview_detail",
                                                args=[interview.pk]))
        except Interview.DoesNotExist:
            return super(ApplicantDetailView, self).get(request, *args,
                                                        **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.is_curator:
            return self.handle_no_permission(request)
        return super(ApplicantDetailView, self).post(request, *args, **kwargs)

    def get_form_kwargs(self):
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        kwargs = super(ApplicantDetailView, self).get_form_kwargs()
        kwargs['initial']['applicant'] = applicant_id
        return kwargs

    def get_success_url(self):
        messages.success(self.request, "Собеседование успешно добавлено",
                         extra_tags='timeout')
        return reverse("admission_interview_detail", args=[self.object.pk])


class ApplicantStatusUpdateView(CuratorOnlyMixin, generic.UpdateView):
    form_class = ApplicantStatusForm
    model = Applicant

    def get_success_url(self):
        messages.success(self.request, "Статус успешно обновлён",
                         extra_tags='timeout')
        return reverse("admission_applicant_detail", args=[self.object.pk])


class InterviewListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
    context_object_name = 'interviews'
    model = Interview
    paginate_by = 50
    template_name = "learning/admission/interviews.html"

    def get_filterset_class(self):
        if self.request.user.is_curator:
            return InterviewsCuratorFilter
        return InterviewsFilter

    def get_context_data(self, **kwargs):
        context = super(InterviewListView, self).get_context_data(**kwargs)
        # TODO: collect stats for curators here?
        context["today"] = self.object_list.filter(
            date__date=now(),
            status=Interview.APPROVED).count()
        context["filter"] = self.filterset
        # Get name for selected campaign
        context["selected_campaign"] = _("Current campaign")
        if "campaign" in self.filterset.form.declared_fields:
            campaign_field = self.filterset.form.fields["campaign"]
            try:
                default_city = self.request.user.city_id
                c = (Campaign.objects
                     .only('pk')
                     .get(current=True,
                          city_id=default_city))
                campaign_field.initial = c.pk
            except Campaign.DoesNotExist:
                pass
            context["selected_campaign"] = _("All campaigns")
            campaign_value = self.filterset.data.get("campaign",
                                                     campaign_field.initial)
            for campaign_id, name in self.filterset.form.declared_fields["campaign"].choices:
                try:
                    if campaign_id == int(campaign_value):
                        context["selected_campaign"] = name
                except (ValueError, TypeError):
                    pass
        return context

    def get_queryset(self):
        q = (Interview.objects
             .select_related("applicant")
             .prefetch_related("interviewers")
             .annotate(average=Coalesce(Avg('comments__score'), Value(0)))
             .order_by("date", "pk"))
        # Show current campaigns only by default
        if not self.request.user.is_curator:
            try:
                current_campaigns = list(Campaign.objects
                                         .filter(current=True)
                                         .values_list("pk", flat=True))
            except Campaign.DoesNotExist:
                messages.error(self.request, "Нет активных кампаний по набору.")
                return Interview.objects.none()
            q = (q.filter(applicant__campaign_id__in=current_campaigns)
                  .filter(interviewers=self.request.user))
        elif not self.request.GET.get("campaign", False):
            # TODO: Determine default campaign and redirect
            pass
        return q


class InterviewDetailView(InterviewerOnlyMixin, ApplicantContextMixin,
                          TemplateResponseMixin, BaseUpdateView):
    form_class = InterviewCommentForm
    template_name = "learning/admission/interview.html"

    def dispatch(self, request, *args, **kwargs):
        interview_id = self.kwargs.get("pk", None)
        if not interview_id:
            raise Http404
        self.interview = get_object_or_404(Interview.objects
                                           .filter(pk=interview_id)
                                           .prefetch_related("interviewers",
                                                             "assignments"))
        return super(InterviewDetailView, self).dispatch(request, *args,
                                                         **kwargs)

    def get_object(self, queryset=None):
        """Try to fetch comment by interview id and interviewer id"""
        if queryset is None:
            queryset = self.get_queryset()
        try:
            obj = queryset.get()
            return obj
        except (AttributeError, queryset.model.DoesNotExist):
            return None

    def get_queryset(self):
        interview_id = self.kwargs.get("pk", None)
        return Comment.objects.filter(interview=interview_id,
                                      interviewer=self.request.user)

    def get_context_data(self, **kwargs):
        context = super(InterviewDetailView, self).get_context_data(**kwargs)
        context["interview"] = self.interview
        context.update(self.get_applicant_context(self.interview.applicant_id))
        if hasattr(self, "object"):
            comment = self.object
        else:
            comment = self.get_object()
        if comment or self.request.user.is_curator:
            context["comments"] = Comment.objects.filter(
                interview=self.interview.pk).select_related("interviewer")
        else:
            context["comments"] = False
        return context

    def _get_interviewer(self):
        if self.request.user.is_curator:
            return self.request.user
        for i in self.interview.interviewers.all():
            if i.pk == self.request.user.pk:
                return i
        return False

    def get_form_kwargs(self):
        interview_id = self.kwargs.get("pk", None)
        interviewer = self._get_interviewer()
        kwargs = super(InterviewDetailView, self).get_form_kwargs()
        kwargs['initial']['interview'] = interview_id
        kwargs['initial']['interviewer'] = self.request.user.pk
        # Store values to validate submitted interviewer/interview on form level
        kwargs.update({"interviewer": interviewer})
        kwargs.update({"interview_id": interview_id})
        if self.request.is_ajax():
            try:
                json_data = json.loads(self.request.body.decode("utf-8"))
                kwargs.update({
                    'data': json_data,
                })
            except ValueError:
                pass
        return kwargs

    def get_success_url(self):
        messages.success(self.request, "Комментарий успешно сохранён",
                         extra_tags='timeout')
        return reverse("admission_interview_detail",
                       args=[self.object.interview.pk])

    def form_valid(self, form):
        if self.request.is_ajax():
            _ = form.save()
            return JsonResponse({"success": "true"})
        return super(InterviewDetailView, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            return JsonResponse({"success": "false",
                                 "errors": form.errors.as_json()})
        return super(InterviewDetailView, self).form_invalid(form)


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
        applicant_pk = kwargs.get("pk")
        back_url = reverse("admission_applicants")
        try:
            applicant = Applicant.objects.get(pk=applicant_pk)
        except Applicant.DoesNotExist:
            messages.error(self.request, "Анкета не найдена",
                           extra_tags='timeout')
            return HttpResponseRedirect(reverse("admission_applicants"))

        try:
            user = CSCUser.objects.get(email=applicant.email)
        except CSCUser.MultipleObjectsReturned:
            messages.error(
                self.request,
                "Всё плохо. Найдено несколько пользователей "
                "с email {}".format(applicant.email))
            return HttpResponseRedirect(back_url)
        except CSCUser.DoesNotExist:
            username = applicant.email.split("@", maxsplit=1)[0]
            if CSCUser.objects.filter(username=username).exists():
                username = self.generate_random_username(attempts=5)
            if not username:
                messages.error(
                    self.request,
                    "Всё плохо. Имя {} уже занято. Cлучайное имя сгенерировать "
                    "не удалось".format(username))
                return HttpResponseRedirect(back_url)
            random_password = CSCUser.objects.make_random_password()
            user = CSCUser.objects.create_user(username=username,
                                               email=applicant.email,
                                               password=random_password)

        user.groups.add(CSCUser.group.STUDENT_CENTER)
        # Migrate data from application form to user profile
        same_attrs = [
            "first_name",
            "patronymic",
            "stepic_id",
            "phone"
        ]
        for attr_name in same_attrs:
            setattr(user, attr_name, getattr(applicant, attr_name))
        user.last_name = applicant.surname
        user.enrollment_year = user.curriculum_year = now().year
        # Looks like the same fields below
        user.yandex_id = applicant.yandex_id if applicant.yandex_id else ""
        # For github left part after github.com/ only
        if applicant.github_id:
            user.github_id = applicant.github_id.split("github.com/",
                                                       maxsplit=1)[-1]
        user.workplace = applicant.workplace if applicant.workplace else ""
        user.uni_year_at_enrollment = applicant.course
        user.city_id = applicant.campaign.city_id
        user.university = applicant.university.name
        user.save()
        # Link applicant and user
        applicant.user = user
        applicant.save()

        return HttpResponseRedirect(reverse("admin:users_cscuser_change",
                                            args=[user.pk]))

    @staticmethod
    def generate_random_username(length=30,
                                 chars=ascii_lowercase + digits,
                                 split=4,
                                 delimiter='-',
                                 attempts=10):
        if not attempts:
            return None

        username = ''.join([choice(chars) for _ in range(length)])

        if split:
            username = delimiter.join(
                [username[start:start + split] for start in
                 range(0, len(username), split)])

        try:
            CSCUser.objects.get(username=username)
            attempts -= 1
            return ApplicantCreateUserView.generate_random_username(
                length=length, chars=chars, split=split, delimiter=delimiter,
                attempts=attempts)
        except CSCUser.DoesNotExist:
            return username
