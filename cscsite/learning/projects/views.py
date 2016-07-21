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
    PROJECT_ENROLLED = "enrolled"
    PROJECT_ALL = "all"  # FIXME: by fact - shows only active from current term
    PROJECT_ARCHIVE = "archive"
    FILTER_VALUES = [PROJECT_ENROLLED, PROJECT_ALL, PROJECT_ARCHIVE]

    def get_template_names(self):
        project_type = self.request.GET[self.FILTER_NAME]
        if project_type == self.PROJECT_ALL:
            return ["learning/projects/all.html"]
        elif project_type == self.PROJECT_ARCHIVE:
            return ["learning/projects/archive.html"]
        else:
            return ["learning/projects/enrolled.html"]

    def get(self, request, *args, **kwargs):
        # Set default filter if not provided
        if (self.FILTER_NAME not in request.GET or
                request.GET[self.FILTER_NAME] not in self.FILTER_VALUES):
            path = request.path
            params = request.GET.copy()
            params[self.FILTER_NAME] = self.PROJECT_ENROLLED
            return HttpResponsePermanentRedirect("{}?{}".format(
                path, params.urlencode()))

        response = super(ReviewerProjectsView, self).get(request, *args,
                                                         **kwargs)
        # FIXME: Remove implicit redirect
        # If enrolled list empty - show all projects
        # if not response.context_data["paginator"].count:
        #     return HttpResponseRedirect("{}?{}={}".format(
        #         reverse("projects:reviewer_projects"),
        #         self.FILTER_NAME,
        #         self.PROJECT_ALL))
        return response

    def get_queryset(self):
        queryset = (Project.objects
                    .select_related("semester")
                    .prefetch_related("students"))
        current_year, term_type = get_current_semester_pair()
        term_index = get_term_index(current_year, term_type)
        project_type = self.request.GET[self.FILTER_NAME]
        if project_type == self.PROJECT_ENROLLED:
            queryset = queryset.filter(reviewers=self.request.user,
                                       semester__index=term_index)
        return queryset.order_by("name", "pk")


class ReviewerAvailableProjectsView(ProjectReviewerOnlyMixin, generic.ListView):
    model = Project


class ProjectDetailView(ProjectReviewerOnlyMixin, generic.DetailView):
    model = Project
