from django import template
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.shortcuts import get_current_site
from django.template import TemplateSyntaxError

from core import FLATPAGE_URL_CACHE

register = template.Library()


@register.simple_tag(takes_context=True)
def flatpage_url(context, url_name, **kwargs):
    """Chaching flatpage urls. Check url exist in DB"""
    global FLATPAGE_URL_CACHE
    if not FLATPAGE_URL_CACHE:
        if 'request' in context:
            site_pk = get_current_site(context['request']).pk
        else:
            site_pk = settings.SITE_ID
        qs = FlatPage.objects.filter(sites__id=site_pk).values('url')
        FLATPAGE_URL_CACHE = [p['url'] for p in qs]
    if url_name not in FLATPAGE_URL_CACHE:
        raise TemplateSyntaxError('"flatpage_url" tag got an unknown variable: %r' % url_name)
    return url_name
