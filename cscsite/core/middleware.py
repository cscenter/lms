from django.conf import settings

from .context_processors import cities


class CurrentCityMiddleware(object):
    """Set `city_code` based on sub domain for request object."""

    def process_request(self, request):
        """Presume we have only 1 lvl sub domains and cities from Russia"""
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
