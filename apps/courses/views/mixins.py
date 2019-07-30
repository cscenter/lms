import logging

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from courses.models import Course

logger = logging.getLogger(__name__)


class CourseURLParamsMixin:
    """
    Makes sure `request.city_code` set by `core.middleware.CurrentCityMiddleware`
    is fulfilled from the request url query params.
    Provides a basic queryset for the course.
    """
    def setup(self, request, *args, **kwargs):
        if not kwargs['city_aware']:
            logger.warning("For this view `request.city_code` should be "
                           "populated from the GET-parameters")
            return HttpResponseBadRequest()
        super().setup(request, *args, **kwargs)
        self.course: Course = get_object_or_404(self.get_course_queryset())

    def get_course_queryset(self):
        """
        Returns queryset for the course based on request URL query params

        Note that `request.city_code` have to be set with `city_code` value
        captured from the URL.
        """
        return (Course.objects
                .in_city(self.request.city_code)
                .filter(semester__type=self.kwargs['semester_type'],
                        semester__year=self.kwargs['semester_year'],
                        meta_course__slug=self.kwargs['course_slug']))
