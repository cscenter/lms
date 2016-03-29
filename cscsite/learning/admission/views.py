# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.views import generic


class DashboardView(generic.TemplateView):
    template_name = "learning/admission/dashboard.html"