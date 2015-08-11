from urlparse import urlparse

from django.conf import settings

from core.models import City
from .context_processors import CITIES_LIST


class CurrentCityMiddleware(object):
    """
    Middleware that sets `city` attribute to request object. 
    Include after session middleware. Order to define current city:
    * subdomain (not supported)
    * user settings (not supported)
    * session
    * cookie
    * settings.CITY_CODE (should be "RU SPB")
    """

    def process_request(self, request):
        if not CITIES_LIST:
            CITIES_LIST[:] = City.objects.all()

        # subdomain = request.get_host().rsplit('.', 2)[:-2]
        # if subdomain:
        #     try:
        #         request.city = [x for x in CITIES_LIST if x.code == 'RU ' + subdomain[0].upper()][0]
        if request.session.get(settings.CITY_SESSION_KEY):
            current_city_code = request.session.get(settings.CITY_COOKIE_NAME)
        elif settings.CITY_COOKIE_NAME in request.COOKIES:
            current_city_code = request.COOKIES[settings.CITY_COOKIE_NAME]
        else:
            current_city_code = settings.CITY_CODE

        try:
            request.city = [x for x in CITIES_LIST if x.code == current_city_code][0]
        except Exception:
            request.city = [x for x in CITIES_LIST if x.code == settings.CITY_CODE][0]
