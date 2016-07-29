# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging

from django.core.urlresolvers import reverse
from django.db.models import Prefetch
from django.http import HttpResponseForbidden
from django.http import HttpResponsePermanentRedirect
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import generic

from learning.projects.models import Project, ProjectStudent, Report
from learning.utils import get_current_semester_pair, get_term_index
from learning.viewmixins import ProjectReviewerGroupOnlyMixin


logger = logging.getLogger(__name__)


class ReviewerProjectsView(ProjectReviewerGroupOnlyMixin, generic.ListView):
    """By default, show projects on which reviewer has enrolled."""
    paginate_by = 50
    context_object_name = "projects"
    FILTER_NAME = "show"
    PROJECT_ACTIVE = "active"  # show enrollments for current term
    PROJECT_AVAILABLE = "available"  # show all projects for current term
    PROJECT_ARCHIVE = "archive"  # past enrollments
    PROJECT_ALL = "all"  # all projects
    FILTER_VALUES = [PROJECT_ACTIVE, PROJECT_AVAILABLE, PROJECT_ARCHIVE,
                     PROJECT_ALL]

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
            params[self.FILTER_NAME] = self.PROJECT_ACTIVE
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
                    .prefetch_related("students"))

        if project_type in [self.PROJECT_ACTIVE, self.PROJECT_AVAILABLE]:
            queryset = queryset.filter(semester__index=current_term_index)
        if project_type in [self.PROJECT_ACTIVE, self.PROJECT_ARCHIVE]:
            queryset = queryset.filter(reviewers=self.request.user)
        return queryset.order_by("-semester__index", "name", "pk")

    def get_context_data(self, **kwargs):
        context = super(ReviewerProjectsView, self).get_context_data(**kwargs)
        context["filter_active"] = self.request.GET[self.FILTER_NAME]
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


# TODO: Add log? Then implement in course enrollment action?
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
        url = reverse("projects:reviewer_project_detail", args=[project.pk])
        return HttpResponseRedirect(url)


class ReviewerReportView(generic.DetailView):
    model = Report
    context_object_name = "report"
    template_name = "learning/projects/report_reviewer.html"

    def get_object(self, queryset=None):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        report = get_object_or_404(
            Report.objects.filter(
                project_student__student=student_pk,
                project_student__project=project_pk,
            )
        )
        # TODO: Check if user is not curator and status =Report.SENT
        return report

