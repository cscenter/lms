# Taken from blog.scur.pl/2012/09/highlighting-current-active-page-django/
# It's a shame this didn't make it to a library yet.

import logging
from django import template
from django.core import urlresolvers

register = template.Library()
logger = logging.getLogger(__name__)

URL_NAMES = {
    'index': {},

    'syllabus': {'parent': 'about'},
    'orgs': {'parent': 'about'},
    'profs': {'parent': 'about'},
    'alumni': {'parent': 'about'},

    'news_list': {},
    'news_detail': {'alias': 'news_list'},

    'contacts': {}
}

@register.simple_tag(takes_context=True)
def current(context, url_name, return_value='current', **kwargs):
    current_url_name = context['request'].resolver_match.url_name
    matched_simple = url_name == current_url_name
    if not current_url_name in URL_NAMES:
        logger.warning("can't find url {0} in URL_NAMES".format(url_name))
        return return_value if matched_simple else ''
    else:
        url_info = URL_NAMES[current_url_name]
        matched_alias = ('alias' in url_info and
                         url_info['alias'] == url_name)
        matched_parent = ('parent' in url_info and
                          url_info['parent'] == url_name)
        matched = matched_simple or matched_alias or matched_parent
        return return_value if matched else ''
