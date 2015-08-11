from __future__ import absolute_import, unicode_literals

from core.models import City

CITIES_LIST = []

def cities(request):
    if not CITIES_LIST:
        cities = City.objects.all()
        CITIES_LIST[:] = cities
    else:
        cities = CITIES_LIST
    return {'CITIES_LIST': cities}

from .signals import *