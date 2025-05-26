import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.contrib.sites.models import Site

from core.exceptions import Redirect
from core.urls import reverse
from courses.models import Course

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django.views import View
    CourseURLParamsMixinBase = View
else:
    CourseURLParamsMixinBase = object


class CourseURLParamsMixin(CourseURLParamsMixinBase):
    """
    This mixin helps to get course by url parameters and assigns it to the
    `course` attribute of the view instance.
    Returns 404 if course is not found or friendly part of the URL is not valid.

    Note:
        Previously friendly URL prefix was used to retrieve course record,
        now `settings.RE_COURSE_URI` contains course PK to avoid url collisions.
    """
    course: Course

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.course: Course = get_object_or_404(
            self.get_course_queryset()
                .filter(pk=kwargs['course_id'],
                        main_branch_id=kwargs['main_branch_id'],
                        meta_course__slug=kwargs['course_slug'],
                        semester__type=kwargs['semester_type'],
                        semester__year=kwargs['semester_year'])
                .available_on_site(Site.objects.get(pk=settings.SITE_ID))
                .order_by('pk')
        )

    def get_course_queryset(self):
        """Returns base queryset for the course"""
        return (Course.objects
                .select_related('meta_course', 'semester', 'main_branch'))


class CoursePublicURLParamsMixin(CourseURLParamsMixinBase):
    """
    This mixin helps to retrieve course made by the current site (where
    main branch is related to the `settings.SITE_ID`), `RE_COURSE_PUBLIC_URI`
    friendly URL prefix contains all the required parameters for this.
    Returns 404 in case course is not found, otherwise sets `course`
    attribute to the view instance.

    Natural key for a course is [meta_course, semester, branch].
    To retrieve unique course record without specifying PK's we need:
        * course slug (uniquely identifies course)
        * semester type + semester year (uniquely identifies semester)
        * branch code + site domain (uniquely identifies branch)

    Notes:
        * `RE_COURSE_PUBLIC_URI` does not provide site domain
            information which we can get from the project settings or request
            object.
        * Main branch code is optional. Fallback to the default branch code
            if omitted

    """
    course: Course

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
            kwargs['main_branch_code'] = ""
            kwargs['branch_trailing_slash'] = ""
            url = reverse(request.resolver_match.view_name,
                          subdomain=None,
                          kwargs=kwargs)
            raise Redirect(to=url)

        courses = list(self.get_course_queryset()
                       .filter(main_branch__code=main_branch_code,
                               main_branch__active=True,
                               main_branch__site=Site.objects.get(pk=settings.SITE_ID))
                       .order_by('pk'))
        if not courses:
            raise Http404

        self.course = courses[0]

    def get_course_queryset(self):
        """
        Returns queryset for the course based on request URL params
        """
        return (Course.objects
                .filter(meta_course__slug=self.kwargs['course_slug'],
                        semester__type=self.kwargs['semester_type'],
                        semester__year=self.kwargs['semester_year'])
                .select_related('meta_course', 'semester', 'main_branch'))
