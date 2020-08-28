import logging

from django.conf import settings
from django.http import Http404

from core.exceptions import Redirect
from core.urls import branch_aware_reverse
from courses.models import Course

logger = logging.getLogger(__name__)


# TODO: share with compsciclub.ru?
class CoursePublicURLParamsMixin:
    """
    This mixin helps to retrieve course made by the current site (where
    main branch is related to the `request.site`).
    `settings.RE_COURSE_PUBLIC_URI` friendly URL prefix contains all the
    required parameters for this.
    Returns 404 in case course is not found, otherwise sets `course`
    attribute to the view instance.

    Natural key for a course is [meta_course, semester, branch].
    To retrieve unique course record without specifying PK's we need:
        * course slug (uniquely identifies course)
        * semester type + semester year (uniquely identifies semester)
        * branch code + site domain (uniquely identifies branch)

    Notes:
        * `settings.RE_COURSE_PUBLIC_URI` does not provide site domain
            information which we can get from the project settings or request
            object.
        * Main branch code is optional. Fallback to the default branch code
            if omitted

    """
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        main_branch_code = kwargs.get("main_branch_code", None)
        if hasattr(request, 'branch'):
            default_branch_code = request.branch.code
        else:
            default_branch_code = settings.DEFAULT_BRANCH_CODE
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
            main_branch_code = default_branch_code
        elif main_branch_code == default_branch_code:
            # Remove default branch code from the url
            url = branch_aware_reverse(request.resolver_match.view_name,
                                       subdomain=None,
                                       kwargs=kwargs)
            raise Redirect(to=url)

        courses = list(self.get_course_queryset()
                       .filter(main_branch__code=main_branch_code,
                               main_branch__site=request.site)
                       .order_by('pk'))
        if not courses:
            raise Http404

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
