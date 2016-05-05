# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime

from braces.views._access import AccessMixin

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views import generic
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.edit import BaseUpdateView, BaseCreateView
from django_filters.views import BaseFilterView

from learning.admission.filters import ApplicantFilter
from learning.admission.forms import InterviewCommentForm, ApplicantForm, \
    InterviewForm, ApplicantStatusForm
from learning.admission.models import Interview, Comment, Contest, Test, Exam, \
    Applicant
from learning.viewmixins import InterviewerOnlyMixin, CuratorOnlyMixin


class InterviewerAccessMixin(AccessMixin):
    def __init__(self):
        self.interview = None
        super(InterviewerAccessMixin, self).__init__()

    def dispatch(self, request, *args, **kwargs):
        interview_id = self.kwargs.get("pk", None)
        if not interview_id:
            raise Http404
        self.interview = get_object_or_404(
            Interview.objects
                .filter(pk=interview_id)
                .prefetch_related("interviewers", "assignments"))
        interviewers = [u.pk for u in self.interview.interviewers.all()]
        if not request.user.is_curator and request.user.pk not in interviewers:
            return self.handle_no_permission(request)

        return super(InterviewerAccessMixin, self).dispatch(
            request, *args, **kwargs)


class ApplicantContextMixin(object):
    @staticmethod
    def get_applicant_context(applicant_id):
        context = {}
        applicant = get_object_or_404(Applicant.objects
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
        return context


class ApplicantResultsListView(CuratorOnlyMixin, BaseFilterView,
                               generic.ListView):
    context_object_name = 'applicants'
    model = Applicant
    template_name = "learning/admission/applicant_list.html"
    filterset_class = ApplicantFilter
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super(ApplicantResultsListView, self).get_context_data(
            **kwargs)
        context["filter"] = self.filterset
        return context

    def get_queryset(self):
        return (Applicant.objects
                .select_related("exam", "online_test", "campaign")
                .prefetch_related("interviews")
                .annotate(exam_result_null=Coalesce('exam__score', Value(-1)))
                .order_by("-exam_result_null", "-exam__score",
                          "-online_test__score"))


class ApplicantResultsDetailView(CuratorOnlyMixin, ApplicantContextMixin,
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
        context = super(ApplicantResultsDetailView, self).get_context_data(
            **kwargs)
        context.update(self.get_applicant_context(applicant_id))
        context["status_form"] = ApplicantStatusForm(instance=context["applicant"])
        return context

    def get(self, request, *args, **kwargs):
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        try:
            interview = Interview.objects.get(applicant_id=applicant_id)
            return HttpResponseRedirect(reverse("admission_interview_detail",
                                                args=[interview.pk]))
        except Interview.DoesNotExist:
            return super(ApplicantResultsDetailView, self).get(request, *args,
                                                               **kwargs)

    def get_form_kwargs(self):
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        kwargs = super(ApplicantResultsDetailView, self).get_form_kwargs()
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

class InterviewListView(InterviewerOnlyMixin, generic.ListView):
    context_object_name = 'interviews'
    model = Interview
    template_name = "learning/admission/dashboard.html"

    def get_context_data(self, **kwargs):
        # TODO: In Django 1.9 implemented __date lookup field. Replace after migration
        today_min = datetime.datetime.combine(now(), datetime.time.min)
        today_max = datetime.datetime.combine(now(), datetime.time.max)
        context = super(InterviewListView, self).get_context_data(**kwargs)
        context["total"] = self.get_queryset().count()
        context["today"] = self.get_queryset().filter(date__range=(today_min, today_max)).count()
        return context

    def get_queryset(self):
        today = now() - datetime.timedelta(hours=2)
        q = (Interview.objects
                         .filter(decision=Interview.WAITING)
                         .select_related("applicant")
                         .prefetch_related("interviewers")
                         .order_by("date"))
        if not self.request.user.is_curator:
            q = q.filter(date__gte=today,
                         interviewers=self.request.user)
        return q


class InterviewDetailView(InterviewerAccessMixin, ApplicantContextMixin,
                          TemplateResponseMixin, BaseUpdateView):
    form_class = InterviewCommentForm
    template_name = "learning/admission/interview.html"

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
        for i in self.interview.interviewers.all():
            if i.pk == self.request.user.pk:
                return i
        return False

    def get_form_kwargs(self):
        interview_id = self.kwargs.get("pk", None)
        interviewer = self._get_interviewer()
        kwargs = super(InterviewDetailView, self).get_form_kwargs()
        kwargs['initial']['interview'] = interview_id
        if hasattr(interviewer, 'pk'):
            kwargs['initial']['interviewer'] = interviewer.pk
        else:
            kwargs['initial']['interviewer'] = self.request.user.pk
        # Store values to validate submitted interviewer/interview on form level
        kwargs.update({"interviewer": interviewer})
        kwargs.update({"interview_id": interview_id})
        return kwargs

    def get_success_url(self):
        messages.success(self.request, "Комментарий успешно сохранён",
                         extra_tags='timeout')
        return reverse("admission_interview_detail",
                       args=[self.object.interview.pk])
