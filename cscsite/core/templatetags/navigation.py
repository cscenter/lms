# Taken from blog.scur.pl/2012/09/highlighting-current-active-page-django/
# It's a shame this didn't make it to a library yet.

import logging
from django import template
from django.conf import settings

register = template.Library()
logger = logging.getLogger(__name__)


# pylint: disable=unused-argument
@register.simple_tag(takes_context=True)
def current(context, url_name, return_value='current', **kwargs):
    current_url_name = context['request'].resolver_match.url_name
    matched_simple = url_name == current_url_name
    if not current_url_name in settings.MENU_URL_NAMES:
        logger.warning("can't find url {0} in MENU_URL_NAMES".format(url_name))
        return return_value if matched_simple else ''
    else:
        url_info = settings.MENU_URL_NAMES[current_url_name]
        matched_alias = ('alias' in url_info and
                         url_info['alias'] == url_name)
        matched_parent = ('parent' in url_info and
                          url_info['parent'] == url_name)
        matched = matched_simple or matched_alias or matched_parent
        return return_value if matched else ''
