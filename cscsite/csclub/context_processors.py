from __future__ import absolute_import, unicode_literals

from core.models import City

CITIES_LIST = []

def cities(request):
    if not CITIES_LIST:
        cities = City.objects.all()
        protocol = request.scheme + '://'
        for city in cities:
            city.url = request.get_host()
            subdomain = city.code.split(' ')[-1].lower() + '.'
            if city.code == 'RU SPB':
                subdomain = ''
            city.url = protocol + subdomain + request.site.domain + '/'
        CITIES_LIST[:] = cities
    else:
        cities = CITIES_LIST
    return {'CITIES_LIST': cities}

from .signals import *
