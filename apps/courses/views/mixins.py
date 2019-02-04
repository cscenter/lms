import logging

from django.http import HttpResponseBadRequest

from courses.models import Course
from courses.utils import semester_slug_re


logger = logging.getLogger(__name__)


class CourseURLParamsMixin:
    """
    Validates URL params from the `courses.urls.RE_COURSE_URI`.
    Provides a basic queryset for the course.
    """
    def dispatch(self, request, *args, **kwargs):
        if not kwargs['city_aware']:
            logger.warning("For this view `request.city_code` should be "
                           "populated from the GET-parameters")
            return HttpResponseBadRequest()
        try:
            if not semester_slug_re.search(kwargs['semester_slug']):
                raise ValueError("Semester slug is not valid")
            year, semester_type = kwargs['semester_slug'].split("-", 1)
            year = int(year)
        except ValueError:
            return HttpResponseBadRequest()
        # FIXME: separate `semester_slug` on route url lvl?
        #  But first needs to add this mixin to all views
        kwargs.update({
            "semester_type": semester_type,
            "semester_year": year
        })
        self.kwargs = kwargs
        return super().dispatch(request, *args, **kwargs)

    def get_course_queryset(self):
        """Returns queryset for the course based on view kwargs"""
        return (Course.objects
                .filter(semester__type=self.kwargs['semester_type'],
                        semester__year=self.kwargs['semester_year'],
                        meta_course__slug=self.kwargs['course_slug'])
                .in_city(self.request.city_code))
