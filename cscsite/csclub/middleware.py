from django.conf import settings

from core.models import City
from .context_processors import cities


class CurrentCityMiddleware(object):
    """
    Middleware that sets `city` attribute to request object. 
    Include after session middleware. Order to define current city:
    * subdomain (not supported)
    * user settings (not supported)
    * session
    * cookie
    * settings.DEFAULT_CITY_CODE (should be "RU SPB")
    """

    def process_request(self, request):
        CITIES_LIST = cities(request)['CITIES_LIST']

        subdomain = request.get_host().rsplit('.', 2)[:-2]
        if subdomain:
            current_city_code = 'RU ' + subdomain[0].upper()
        elif request.session.get(settings.CITY_SESSION_KEY):
            current_city_code = request.session.get(settings.CITY_COOKIE_NAME)
        elif settings.CITY_COOKIE_NAME in request.COOKIES:
            current_city_code = request.COOKIES[settings.CITY_COOKIE_NAME]
        else:
            current_city_code = settings.DEFAULT_CITY_CODE

        try:
            request.city = [x for x in CITIES_LIST if x.code == current_city_code][0]
        except Exception:
            request.city = [x for x in CITIES_LIST if x.code == settings.DEFAULT_CITY_CODE][0]
