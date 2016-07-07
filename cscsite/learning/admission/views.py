# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import json

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Q, Avg, When, Value, Case, IntegerField, Prefetch, Count
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views import generic
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from django.views.generic.edit import BaseUpdateView, BaseCreateView
from django_filters.views import BaseFilterView
from extra_views import ModelFormSetView

from learning.admission.filters import ApplicantFilter, InterviewsFilter
from learning.admission.forms import InterviewCommentForm, ApplicantForm, \
    InterviewForm, ApplicantStatusForm,  \
    InterviewResultsModelForm
from learning.admission.models import Interview, Comment, Contest, Test, Exam, \
    Applicant, Campaign
from learning.viewmixins import InterviewerOnlyMixin, CuratorOnlyMixin


class ApplicantContextMixin(object):
    @staticmethod
    def get_applicant_context(applicant_id):
        context = {}
        applicant = get_object_or_404(
            Applicant.objects
                     .select_related("exam", "campaign", "online_test")
                     .filter(pk=applicant_id))
        context["applicant"] = applicant
        context["applicant_form"] = ApplicantForm(instance=applicant)
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
        contest_ids = filter(None, contest_ids)
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
                Q(second_name__iexact=applicant.second_name) &
                Q(last_name__iexact=applicant.last_name)
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
        context = super(ApplicantListView, self).get_context_data(
            **kwargs)
        context["filter"] = self.filterset
        return context

    def get_queryset(self):
        return (Applicant.objects
                .select_related("exam", "online_test", "campaign")
                .prefetch_related("interviews")
                .annotate(exam_result_null=Coalesce('exam__score', Value(-1)))
                .order_by("-exam_result_null", "-exam__score",
                          "-online_test__score", "pk"))


class ApplicantDetailView(InterviewerOnlyMixin, ApplicantContextMixin,
                          TemplateResponseMixin, BaseCreateView):

    form_class = InterviewForm
    template_name = "learning/admission/applicant_detail.html"

    def get_queryset(self):
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        return (Applicant.objects
                .select_related("exam", "online_test", "campaign")
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
    filterset_class = InterviewsFilter
    paginate_by = 50
    template_name = "learning/admission/interviews.html"

    def get_context_data(self, **kwargs):
        # TODO: In Django 1.9 implemented __date lookup field. Replace after migration
        today_min = datetime.datetime.combine(now(), datetime.time.min)
        today_max = datetime.datetime.combine(now(), datetime.time.max)
        context = super(InterviewListView, self).get_context_data(**kwargs)
        # TODO: collect stats for curators here?
        context["today"] = self.get_queryset().filter(
            date__range=(today_min, today_max), status=Interview.WAITING).count()
        context["filter"] = self.filterset
        return context

    def get_queryset(self):
        q = (Interview.objects
             .filter(applicant__campaign__current=True)
             .select_related("applicant")
             .prefetch_related("interviewers")
             .annotate(average=Avg('comments__score'))
             .order_by("date", "pk"))
        if not self.request.user.is_curator:
            q = q.filter(interviewers=self.request.user)
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
                json_data = json.loads(self.request.body)
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


class InterviewResultsView(CuratorOnlyMixin, ModelFormSetView):
    """
    We can have multiple interviews for applicant
    """
    # TODO: add tests!
    context_object_name = 'interviews'
    template_name = "learning/admission/interview_results.html"
    campaign = None
    model = Applicant
    form_class = InterviewResultsModelForm
    UNREACHABLE_COMMENT_SCORE = Comment.MIN_SCORE - 1

    def get_context_data(self, **kwargs):
        # XXX: To avoid double query to DB, skip ModelFormSetView action
        context = ContextMixin.get_context_data(self, **kwargs)

        def cmp_interview_average(interview):
            if interview.average is not None:
                return interview.average
            else:
                return self.UNREACHABLE_COMMENT_SCORE

        for form in context["formset"].forms:
            # Select the highest interview score to sort by
            applicant = form.instance
            best_interview = max(applicant.interviews.all(),
                                 key=cmp_interview_average)
            if best_interview.average is not None:
                applicant.best_interview_score = best_interview.average
            else:
                applicant.best_interview_score = None
        context["formset"].forms.sort(
            key=lambda f: f.instance.best_interview_score,
            reverse=True)
        context["campaign"] = self.campaign
        return context

    def get_factory_kwargs(self):
        kwargs = super(InterviewResultsView, self).get_factory_kwargs()
        kwargs["extra"] = 0
        kwargs["can_order"] = False
        kwargs["can_delete"] = False
        return kwargs

    def get_queryset(self):
        """Sort data by average interview score"""
        if self.campaign is None:
            self.campaign = Campaign.objects.get(current=True)
        return (Applicant.objects
            # TODO: Carefully restrict by status also to optimize query
            .filter(campaign=self.campaign)
            .select_related("exam", "online_test")
            .annotate(has_interviews=Count("interviews__pk"))
            .filter(has_interviews__gt=0)
            .prefetch_related(
                Prefetch(
                    'interviews',
                    queryset=(Interview.objects
                              .annotate(average=Avg('comments__score'))),
                ),
            )
        )
