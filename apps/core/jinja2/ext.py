import logging

from django.conf import settings
from django.urls import NoReverseMatch
from jinja2.ext import Extension

from core.urls import reverse


logger = logging.getLogger(__name__)

MUTE_URLRESOLVE_EXCEPTIONS = getattr(settings, "JINJA2_MUTE_URLRESOLVE_EXCEPTIONS", False)


class UrlExtension(Extension):
    def __init__(self, environment):
        super().__init__(environment)
        environment.globals["url"] = self._url_reverse
        environment.globals["LMS_SUBDOMAIN"] = settings.LMS_SUBDOMAIN

    def _url_reverse(self, name, subdomain=None, scheme=None, **kwargs):
        try:
            return reverse(name, subdomain=subdomain, scheme=scheme,
                           args=None, kwargs=kwargs)
        except NoReverseMatch as exc:
            logger.error('Error: %s', exc)
            if not MUTE_URLRESOLVE_EXCEPTIONS:
                raise
            return ''
