# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponsePermanentRedirect
from django.http import HttpResponseRedirect
from django.http.request import QueryDict
from django.views import generic

from learning.projects.models import Project
from learning.utils import get_current_semester_pair, get_term_index
from learning.viewmixins import ProjectReviewerOnlyMixin


logger = logging.getLogger(__name__)


class ReviewerProjectsView(ProjectReviewerOnlyMixin, generic.ListView):
    """
    By default, show projects on which reviewer has enrolled.

    Add GET-param ?show=all to show all available projects in current term.
    """
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
        project_type = self.request.GET[self.FILTER_NAME]
        if project_type == self.PROJECT_AVAILABLE:
            return ["learning/projects/all.html"]
        elif project_type == self.PROJECT_ARCHIVE:
            return ["learning/projects/archive.html"]
        else:
            return ["learning/projects/enrolled.html"]

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


class ReviewerAvailableProjectsView(ProjectReviewerOnlyMixin, generic.ListView):
    model = Project


class ProjectDetailView(ProjectReviewerOnlyMixin, generic.DetailView):
    model = Project
