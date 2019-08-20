import logging

from django.conf import settings
from django.http.response import Http404, HttpResponseRedirect, \
    HttpResponseNotFound

from compsciclub_ru.context_processors import get_branches
from core.exceptions import Redirect
from core.models import Branch
from core.utils import is_club_site

logger = logging.getLogger(__name__)


class CurrentCityMiddleware:
    """
    Attach city code to request object:
        * On compsciclub.ru always resolve city from sub domain
        * If view contains `city_aware` keyword argument, get city code from
          URL parameters
        * If not, try to cast sub domain to city code.
        * Otherwise, fallback to `settings.DEFAULT_CITY_CODE`. It makes
          sense in case of `www` or empty sub domain.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        url_aware_of_the_city = bool(view_kwargs.get("city_aware", False))
        url_aware_of_the_branch = bool(view_kwargs.get("branch_aware", False))
        url_timezone_aware = url_aware_of_the_city or url_aware_of_the_branch
        if url_aware_of_the_city and not is_club_site():
            # No need in delimiter if we always explicitly set city code
            use_delimiter = view_kwargs.get("use_delimiter", True)
            delimiter = view_kwargs.get("city_delimiter", None)
            city_code = view_kwargs["city_code"]
            if not city_code:
                if use_delimiter and delimiter:
                    # For the default city delimiter must be empty
                    raise Http404
                city_code = settings.DEFAULT_CITY_CODE
            elif city_code not in settings.TIME_ZONES or (use_delimiter and
                                                          not delimiter):
                # None-empty delimiter if valid city code provided
                raise Http404
        elif url_aware_of_the_branch:
            # FIXME: pure hack for admission interview results
            city_code = view_kwargs["branch_code"]
        else:
            if url_aware_of_the_city:
                # FIXME: Подразумевается, что никогда не используем в url?
                if view_kwargs["city_code"] or view_kwargs["city_delimiter"]:
                    raise Http404
            # Assume we have only 1 lvl sub domains
            sub_domain = request.get_host().rsplit('.', 2)[:-2]
            if sub_domain:
                current = sub_domain[0].lower()
            else:
                current = None
            for city in get_branches(request)['BRANCH_LIST']:
                if city.code == current:
                    city_code = current
                    break
            else:
                city_code = settings.DEFAULT_CITY_CODE
        request.city_code = city_code
        return None


class RedirectMiddleware:
    """
    Add this middleware to `MIDDLEWARE` setting to enable processing
    Redirect exception on each request.

    All arguments passed to
    Redirect will be passed to django's' `redirect` shortcut.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, Redirect):
            return
        redirect_to = exception.to
        if isinstance(redirect_to, HttpResponseRedirect):
            return redirect_to
        return HttpResponseRedirect(redirect_to, **exception.kwargs)


class CurrentBranchMiddleware:
    """
    Middleware that sets `branch` attribute to request object based on
    subdomain and `request.site` values.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allows adding a missing branch through the admin interface
        if not request.path.startswith(settings.ADMIN_URL):
            request.branch = Branch.objects.get_current(request)
        return self.get_response(request)


class BranchViewMiddleware:
    """
    Middleware that sets `branch` attribute to request object based on
    `request.site` and `branch_code_request` view keyword argument.

    Will override `request.branch` value set by `CurrentBranchMiddleware`
    if both are included (view middleware is called later in
    the middleware chain)

    Two named view arguments are required for the middleware to set
    `branch` attribute to the request object:
        branch_code_request: str - should be empty for the default branch code
        branch_trailing_slash: str - "/" or empty in case of default branch code

    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        branch_code = view_kwargs.get("branch_code_request", None)
        if branch_code is not None:
            slash = view_kwargs.get("branch_trailing_slash", None)
            if slash is not None:
                # /aaa//bbb case
                if not branch_code and slash:
                    return HttpResponseNotFound()
                # /aa/xxxbb or /aa/xxxcbb cases, where `xxx` is a branch code
                # and `c` is invalid trailing slash value
                elif branch_code and (not slash or slash != "/"):
                    return HttpResponseNotFound()
                elif not branch_code:
                    branch_code = settings.DEFAULT_BRANCH_CODE
                try:
                    request.branch = Branch.objects.get_by_natural_key(
                        branch_code, request.site.id)
                except Branch.DoesNotExist:
                    return HttpResponseNotFound()
