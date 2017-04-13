from django.conf import settings
from django.shortcuts import redirect

from core.exceptions import Redirect
from .context_processors import cities


class CurrentCityMiddleware(object):
    """Set `city_code` based on sub domain for request object."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Presume we have only 1 lvl sub domains and cities from Russia"""
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if settings.SITE_ID == settings.CENTER_SITE_ID:
            # For center site always set spb
            request.city_code = settings.DEFAULT_CITY_CODE
        else:
            sub_domain = request.get_host().rsplit('.', 2)[:-2]
            if sub_domain:
                current = sub_domain[0].lower()
            else:
                current = None
            for city in cities(request)['CITY_LIST']:
                if city.code == current:
                    request.city_code = current
                    break
            if not hasattr(request, "city_code"):
                request.city_code = settings.DEFAULT_CITY_CODE

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response


class RedirectMiddleware(object):
    """
    You must add this middleware to MIDDLEWARE list,
    to make work Redirect exception. All arguments passed to
    Redirect will be passed to django built in redirect function.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, Redirect):
            return
        return redirect(*exception.args, **exception.kwargs)
