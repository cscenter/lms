import logging

from django.conf import settings
from django.urls import NoReverseMatch
from django.utils.html import strip_spaces_between_tags
from jinja2 import nodes
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


class SpacelessExtension(Extension):
    """
    Removes whitespace between HTML tags, including tab and
    newline characters. Works exactly like Django's own tag.

    Adopted from: https://github.com/openstack/deb-python-coffin/blob/master/coffin/common.py
    """

    tags = {'spaceless'}

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(['name:endspaceless'], drop_needle=True)
        return nodes.CallBlock(
            self.call_method('_strip_spaces', [], [], None, None),
            [], [], body,
        ).set_lineno(lineno)

    def _strip_spaces(self, caller=None):
        return strip_spaces_between_tags(caller().strip())
