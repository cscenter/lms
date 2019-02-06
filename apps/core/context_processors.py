from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from core.models import City

CITY_LIST = {"CACHE": []}


def cities(request):
    if not CITY_LIST["CACHE"]:
        protocol = request.scheme + '://'
        CITY_LIST["CACHE"] = City.objects.all()
        for city in CITY_LIST["CACHE"]:
            city.url = request.get_host()
            sub_domain = city.code + "." if city.code != 'spb' else ''
            city.url = "{}{}{}/".format(protocol, sub_domain,
                                        request.site.domain, '/')
    return dict(CITY_LIST=CITY_LIST["CACHE"])


def subdomain(request):
    return {"LMS_SUBDOMAIN": getattr(settings, "LMS_SUBDOMAIN", "")}


from core.signals import *
