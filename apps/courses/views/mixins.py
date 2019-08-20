import logging

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from courses.models import Course

logger = logging.getLogger(__name__)


class CourseURLParamsMixin:
    """
    Provides a basic queryset for the course.
    """
    def setup(self, request, *args, **kwargs):
        # TODO: move to RequestBranchRequired mixin?
        if not hasattr(request, "branch"):
            logger.error(f"{self.__class__} needs `request.branch` value")
            # request.branch = None
        super().setup(request, *args, **kwargs)
        self.course: Course = get_object_or_404(self.get_course_queryset())

    def get_course_queryset(self):
        """
        Returns queryset for the course based on request URL query params

        Note that `request.city_code` have to be set with `city_code` value
        captured from the URL.
        """
        return (Course.objects
                .in_branches(self.request.branch.pk)
                .filter(semester__type=self.kwargs['semester_type'],
                        semester__year=self.kwargs['semester_year'],
                        meta_course__slug=self.kwargs['course_slug']))
