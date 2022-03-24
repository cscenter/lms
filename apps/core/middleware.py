import logging

from django.conf import settings
from django.http.response import (
    HttpResponse, HttpResponseRedirect, HttpResponseServerError
)

from core.exceptions import Redirect
from core.models import Branch

logger = logging.getLogger(__name__)


def show_debug_toolbar(request) -> bool:
    """Function to determine whether to show the toolbar on a given page"""
    return settings.DEBUG and (request.META.get("REMOTE_ADDR") in settings.INTERNAL_IPS or
                               request.user.is_superuser)


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


class SubdomainBranchMiddleware:
    """
    Middleware that sets `branch` attribute to the request object based on
    subdomain and `request.site` values.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allows adding a missing branch through the admin interface
        if not request.path.startswith(settings.ADMIN_URL):
            request.branch = Branch.objects.get_current(request)
        return self.get_response(request)


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


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET":
            if request.path == "/health-check/":
                return HttpResponse("OK")
            elif request.path == "/readiness/":
                return self.readiness(request)
        return self.get_response(request)

    @staticmethod
    def readiness(request):
        try:
            from django.db import connections
            for name in connections:
                cursor = connections[name].cursor()
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                if row is None:
                    return HttpResponseServerError("db: invalid response")
        except Exception as e:
            logger.exception(e)
            return HttpResponseServerError("db: cannot connect to database.")
        return HttpResponse("OK")
