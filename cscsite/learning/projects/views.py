# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging

from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Prefetch
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponsePermanentRedirect
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views import generic
from django.views.generic.edit import FormMixin
from django.utils.translation import ugettext_lazy as _

from core import comment_persistence
from core.utils import hashids
from core.views import LoginRequiredMixin
from learning.projects.forms import ReportCommentForm, ReportReviewForm, \
    ReportStatusForm, ReportSummarizeForm
from learning.projects.models import Project, ProjectStudent, Report, \
    ReportComment, Review
from learning.utils import get_current_semester_pair, get_term_index
from learning.viewmixins import ProjectReviewerGroupOnlyMixin, CuratorOnlyMixin
from notifications.signals import notify

logger = logging.getLogger(__name__)


class ReviewerProjectsView(ProjectReviewerGroupOnlyMixin, generic.ListView):
    """By default, show projects on which reviewer has enrolled."""
    paginate_by = 50
    context_object_name = "projects"
    FILTER_NAME = "show"
    PROJECT_REPORTS = "reports"  # show enrollments for current term
    PROJECT_AVAILABLE = "available"  # show all projects for current term
    PROJECT_ALL = "all"  # all projects
    FILTER_VALUES = [PROJECT_REPORTS, PROJECT_AVAILABLE, PROJECT_ALL]

    def get_template_names(self):
        assert self.FILTER_NAME in self.request.GET
        template_name = self.request.GET[self.FILTER_NAME]
        return ["learning/projects/{}.html".format(template_name)]

    def get(self, request, *args, **kwargs):
        # Dispatch, by default show enrollments from current term
        is_valid_filter = (self.FILTER_NAME in request.GET and
                           request.GET[self.FILTER_NAME] in self.FILTER_VALUES)
        if not is_valid_filter:
            path = request.path
            params = request.GET.copy()
            params[self.FILTER_NAME] = self.PROJECT_REPORTS
            return HttpResponsePermanentRedirect(
                "{}?{}".format(path, params.urlencode())
            )

        return super(ReviewerProjectsView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        current_year, term_type = get_current_semester_pair()
        current_term_index = get_term_index(current_year, term_type)
        project_type = self.request.GET[self.FILTER_NAME]
        queryset = (Project.objects
                    .select_related("semester")
                    .prefetch_related("students", "reviewers",
                                      "projectstudent_set__report",
                                      "projectstudent_set__student"))

        if project_type in [self.PROJECT_REPORTS, self.PROJECT_AVAILABLE]:
            queryset = queryset.filter(semester__index=current_term_index)
        if project_type == self.PROJECT_REPORTS:
            queryset = queryset.filter(reviewers=self.request.user)
        return queryset.order_by("-semester__index", "name", "pk")

    def get_context_data(self, **kwargs):
        context = super(ReviewerProjectsView, self).get_context_data(**kwargs)
        context["filter_active"] = self.request.GET[self.FILTER_NAME]
        current_year, term_type = get_current_semester_pair()
        context["current_term"] = "{} {}".format(_(term_type), current_year)
        return context


class ProjectDetailView(ProjectReviewerGroupOnlyMixin, generic.DetailView):
    model = Project
    context_object_name = "project"
    template_name = "learning/projects/project_detail.html"

    def get_queryset(self):
        qs = super(ProjectDetailView, self).get_queryset()
        return (qs.select_related("semester").prefetch_related(
            Prefetch("projectstudent_set",
                     queryset=(ProjectStudent
                               .objects
                               .select_related("report", "student"))),
            "reviewers")
        )

    def get_context_data(self, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        context["you_enrolled"] = (self.request.user in
                                      context["project"].reviewers.all())
        return context


class ProjectEnrollView(ProjectReviewerGroupOnlyMixin, generic.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        project_pk = kwargs.get("pk")
        project = get_object_or_404(
            Project.objects
                   .select_related("semester")
                   .filter(pk=project_pk)
        )
        if not project.is_active():
            return HttpResponseForbidden()

        project.reviewers.add(request.user.pk)
        project.save()
        # TODO: add notification when user unsubscribed
        notify.send(
            request.user,  # actor
            verb='enrolled on',
            action_object=project,
            recipient="")
        url = reverse("projects:reviewer_project_detail", args=[project.pk])
        return HttpResponseRedirect(url)


class ReviewerReportView(ProjectReviewerGroupOnlyMixin, FormMixin,
                         generic.DetailView):
    model = Report
    context_object_name = "report"
    template_name = "learning/projects/report_reviewer.html"

    def get_object(self, queryset=None):
        # TODO: check permissions here. Убедиться, что текущий объект связан с этим юзером хоть как-то
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        # TODO: show for students, hide for reviewers if status == SENT
        report = get_object_or_404(
            Report.objects.filter(
                project_student__student=student_pk,
                project_student__project=project_pk,
            ).select_related("project_student")
        )
        return report

    def form_valid(self, form):
        form.save()
        return super(ReviewerReportView, self).form_valid(form)

    def form_invalid(self, **kwargs):
        messages.error(self.request, _("Data not saved. Check errors."))
        return self.render_to_response(self.get_context_data(**kwargs))

    def get_context_data(self, **kwargs):
        # skip FormMixin.get_context_data() here
        context = super(FormMixin, self).get_context_data(**kwargs)
        report = context[self.context_object_name]
        form_kwargs = self.get_form_kwargs()
        if ReportStatusForm.prefix not in context:
            context[ReportStatusForm.prefix] = ReportStatusForm(
                instance=self.object,
                project_pk=self.object.project_student.project_id,
                student_pk=self.object.project_student.student_id)
        if ReportCommentForm.prefix not in context:
            context[ReportCommentForm.prefix] = ReportCommentForm(**form_kwargs)
        if ReportReviewForm.prefix not in context:
            form_kwargs["instance"] = self.get_review_object()
            context[ReportReviewForm.prefix] = ReportReviewForm(**form_kwargs)
        comments = (ReportComment.objects
                    .filter(report=report)
                    .order_by('created')
                    .select_related('author'))
        context["comments"] = comments
        context['clean_comments_json'] = comment_persistence.get_hashes_json()
        context["is_reviewer"] = self.request.user in report.project_student.project.reviewers.all()
        context["is_author"] = self.request.user == report.project_student.student
        return context

    def get_review_object(self):
        try:
            review = Review.objects.get(
                report=self.object, reviewer=self.request.user)
        except Review.DoesNotExist:
            review = None
        return review

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form_kwargs = self.get_form_kwargs()
        if ReportCommentForm.prefix in request.POST:
            success_msg = _("Comment successfully added.")
            form_class = ReportCommentForm
            form_name = ReportCommentForm.prefix
        elif ReportReviewForm.prefix in request.POST:
            # TODO: check permissions?
            success_msg = _("The data successfully saved.")
            form_class = ReportReviewForm
            form_name = ReportReviewForm.prefix
            form_kwargs["instance"] = self.get_review_object()
        else:
            return HttpResponseBadRequest()
        form = form_class(**form_kwargs)
        if form.is_valid():
            response = self.form_valid(form)
            messages.success(self.request, success_msg, extra_tags='timeout')
            return response
        else:
            return self.form_invalid(**{form_name: form})

    def get_form_kwargs(self):
        form_kwargs = super(ReviewerReportView, self).get_form_kwargs()
        # Required fields for both models, not represented in form
        form_kwargs["report"] = self.object
        form_kwargs["author"] = self.request.user
        return form_kwargs

    def get_success_url(self):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        return reverse_lazy(
            "projects:reviewer_project_report",
            kwargs={
                "project_pk": project_pk,
                "student_pk": student_pk
            }
        )


class ReportUpdateStatusView(CuratorOnlyMixin,
                             generic.UpdateView):
    http_method_names = ["post"]
    model = Report
    form_class = ReportStatusForm

    def get_object(self, queryset=None):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        report = get_object_or_404(
            Report.objects.filter(
                project_student__student=student_pk,
                project_student__project=project_pk,
            )
        )
        return report

    def get_success_url(self):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        success_msg = _("Status was successfully updated.")
        messages.success(self.request, success_msg, extra_tags='timeout')
        return reverse_lazy(
            "projects:reviewer_project_report",
            kwargs={
                "project_pk": project_pk,
                "student_pk": student_pk
            }
        )

    def get_form_kwargs(self):
        kwargs = super(ReportUpdateStatusView, self).get_form_kwargs()
        kwargs["project_pk"] = self.kwargs.get("project_pk")
        kwargs["student_pk"] = self.kwargs.get("student_pk")
        return kwargs


class ReportSummarizeView(CuratorOnlyMixin, generic.UpdateView):
    model = Report
    form_class = ReportSummarizeForm
    template_name = "learning/projects/report_summarize.html"

    # FIXME: replace with ReportObjectMixin? it's duplicated right now.
    def get_object(self, queryset=None):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        report = get_object_or_404(
            Report.objects.filter(
                project_student__student=student_pk,
                project_student__project=project_pk,
            )
        )
        return report

    def get_success_url(self):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        messages.success(self.request,
                         _("Report was successfully updated."),
                         extra_tags='timeout')
        return reverse_lazy(
            "projects:reviewer_project_report",
            kwargs={
                "project_pk": project_pk,
                "student_pk": student_pk
            }
        )


class ReportAttachmentDownloadView(LoginRequiredMixin, generic.View):

    def get(self, request, *args, **kwargs):
        try:
            attachment_type, pk = hashids.decode(kwargs['sid'])
        except IndexError:
            raise Http404

        qs = ReportComment.objects.filter(pk=pk)
        if not request.user.is_project_reviewer and not request.user.is_curator:
            qs = qs.filter(report__project_student__student=request.user)
        comment = get_object_or_404(qs)
        file_name = comment.attached_file_name
        file_url = comment.attached_file.url

        response = HttpResponse()
        del response['Content-Type']
        response['Content-Disposition'] = "attachment; filename={}".format(
            file_name)
        response['X-Accel-Redirect'] = file_url
        return response

