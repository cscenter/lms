import logging

from django.conf import settings
from django.db.models import Q, Case, When, PositiveIntegerField
from django.http import Http404, HttpResponseNotFound
from django.shortcuts import get_object_or_404

from core.models import Branch
from courses.models import Course

logger = logging.getLogger(__name__)


# Don't bind a course lookup with `request.site` if set to False.
COURSE_FRIENDLY_URL_USE_SITE = getattr(settings, "COURSE_FRIENDLY_URL_USE_SITE", True)


class CourseURLParamsMixin:
    """
    This mixin helps to retrieve course record based on `settings.RE_COURSE_URI`
    friendly URL prefix. Returns 404 in case course is not found,
    otherwise sets `course` attribute to the view instance.

    Natural key for a course is [meta_course, semester, branch].
    To retrieve unique course record without specifying PK's we need:
        * course slug (uniquely identifies course)
        * semester type + semester year (uniquely identifies semester)
        * branch code + site domain (uniquely identifies branch)

    Notes:
        * `settings.RE_COURSE_URI` does not provide site domain information
        * Main branch code is optional. Fallback to the default
            branch if omitted
        * Multiple readings of the course in the semester on the same site
            is not supported

    """
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        main_branch_code = kwargs.get("main_branch_code", None)
        slash = kwargs.get("branch_trailing_slash", None)
        # /aaa//bbb double slash problem. Actually doesn't happen, turn nginx
        # directive `merge_slashes` on to enable this behaviour
        if not main_branch_code and slash:
            raise Http404
        # Case when branch trailing slash is omitted, e.g.
        # `.../algorithms-1/xxx2019-autumn/`, where `xxx` is a branch code
        elif main_branch_code and (not slash or slash != "/"):
            raise Http404
        elif not main_branch_code:
            main_branch_code = settings.DEFAULT_BRANCH_CODE

        # At this moment it's possible to narrow the search to the courses
        # with a target course slug in a target semester where main branch
        # has a target code.
        # From this selection we need to filter out all courses that are not
        # relevant to the current site (course is not shared on any branch
        # of the current site).
        courses = list(self.get_course_queryset()
                       .filter(main_branch__code=main_branch_code)
                       .available_on_site(request.site)
                       .order_by('pk'))
        if not courses:
            raise Http404

        # FIXME: log warning/error if we don't meet a limitation "1 reading of the course in a semester on site"?

        self.course: Course = courses[0]

    def get_course_queryset(self):
        """
        Returns queryset for the course based on request URL params
        """
        return (Course.objects
                .filter(meta_course__slug=self.kwargs['course_slug'],
                        semester__type=self.kwargs['semester_type'],
                        semester__year=self.kwargs['semester_year'])
                .select_related('meta_course', 'semester', 'main_branch'))
