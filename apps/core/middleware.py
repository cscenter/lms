import logging

from django.conf import settings
from django.http.response import HttpResponseRedirect, \
    HttpResponseNotFound

from core.exceptions import Redirect
from core.models import Branch

logger = logging.getLogger(__name__)


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
            # FIXME: handle case with wrong HTTP_HOST header. Now it raises 500 `Branch not found`
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


class HardCodedLocaleMiddleware:
    """
    i18n is enabled on compsciclub.ru (language is determined by prefix,
    prefix is not used for the default language)
    LMS actually has no EN translations so we could disable i18n on it
    or hard-code it by using `i18n_patterns(..., prefix_default_language=False)`
    in the root URLCONF.
    Since we share some functionality between LMS and compsciclub.ru the
    first option is not valid. The second one looks like a workaround, we
    abusing locale middleware logic to set request.LANGUAGE_CODE to the
    settings.LANGUAGE_CODE value. So let's explicitly set language code
    for the request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        return self.get_response(request)
