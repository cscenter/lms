from __future__ import unicode_literals

import logging

from django.http import Http404
from django.views.generic import DetailView

from textpages.models import Textpage

from braces.views import GroupRequiredMixin

from learning.models import Course

logger = logging.getLogger(__name__)


class TextpageOpenView(DetailView):
    model = Textpage

    template_name = "textpage.html"

    def get_object(self):
        requested_url_name = self.request.resolver_match.url_name
        try:
            return self.model.objects.get(url_name=requested_url_name)
        except self.model.DoesNotExist:
            logger.warning(
                "can't find {0} as a textpage".format(requested_url_name))
            raise Http404


class TextpageSyllabusView(TextpageOpenView):
    template_name = "syllabus_textpage.html"

    def get_context_data(self, *args, **kwargs):
        context = (super(TextpageSyllabusView, self)
                   .get_context_data(*args, **kwargs))
        context['courses'] = Course.objects.all()
        return context


class TextpageStudentView(GroupRequiredMixin, TextpageOpenView):
    group_required = 'Student'
