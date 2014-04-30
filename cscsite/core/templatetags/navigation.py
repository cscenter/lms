# Taken from blog.scur.pl/2012/09/highlighting-current-active-page-django/
# It's a shame this didn't make it to a library yet.

import logging
from django import template
from django.conf import settings

register = template.Library()
logger = logging.getLogger(__name__)


@register.simple_tag(takes_context=True)
def current(context, tag_url_name, return_value='current', **kwargs):
    def current_recursive(current_url_name):
        matched_simple = tag_url_name == current_url_name
        if not current_url_name in settings.MENU_URL_NAMES:
            logger.warning("can't find url {0} in MENU_URL_NAMES"
                           .format(current_url_name))
            return return_value if matched_simple else ''
        if matched_simple:
            return return_value
        url_info = settings.MENU_URL_NAMES[current_url_name]
        if 'alias' in url_info:
            return current_recursive(url_info['alias'])
        if 'parent' in url_info:
            return current_recursive(url_info['parent'])
        return ''

    return current_recursive(context['request'].resolver_match.url_name)
