import logging

from django import template
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.template import TemplateSyntaxError

from core import FLATPAGE_URL_CACHE
from htmlpages.models import HtmlPage

logger = logging.getLogger('root')
register = template.Library()


@register.simple_tag(takes_context=True)
def htmlpage_url(context, url_name, **kwargs):
    """Caching flatpage urls. Check url exist in DB"""
    if not FLATPAGE_URL_CACHE:
        if 'request' in context:
            site_pk = get_current_site(context['request']).pk
        else:
            site_pk = settings.SITE_ID
        qs = HtmlPage.objects.filter(sites__id=site_pk).values('url')
        FLATPAGE_URL_CACHE[:] = [p['url'] for p in qs]
    if url_name not in FLATPAGE_URL_CACHE:
        msg = '"htmlpage_url" tag got an unknown variable: %r' % url_name
        if settings.DEBUG:
            raise TemplateSyntaxError(msg)
        else:
            logger.warning(msg)
    return url_name
