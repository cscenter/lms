# Taken from blog.scur.pl/2012/09/highlighting-current-active-page-django/
# It's a shame this didn't make it to a library yet.

import logging
from django import template
from django.conf import settings

register = template.Library()
logger = logging.getLogger(__name__)


@register.simple_tag(takes_context=True)
def current(context, tag_url_name, return_value='current', **kwargs):
    """
    In templates we use "current" tag to add css class to DIVs and LIs
    that are used in navigation (default class name is "current"). This
    tag is used with url name (as in urls.py) of the page on which it should
    return "return_value". There are three cases when "return_value" will
    be returned:

    1. When current URL name matches with provided URL;
    2. When current URL lists provided URL as a "parent" in
    settings.MENU_URL_NAMES;
    3. When current URL is an "alias" (as defined in settings.MENU_URL_NAMES)
    to an URL that follows one of this three criteria.

    Here is an example:

    ```
    [first_level_menu_item]
             ^
             | parent
             |                 alias
    [second_level_menu_item] <-------- [some_url]
    ```

    If the current URL is "some_url", "return_value" will be returned
    for {% current "some_url" %}, {% current "second_level_menu_item" %} and
    {% current "first_level_menu_item" %}.
    """
    def inner_recursive(current_url_name):
        matched_simple = tag_url_name == current_url_name
        if current_url_name not in settings.MENU_URL_NAMES:
            logger.warning("can't find url {0} in MENU_URL_NAMES"
                           .format(current_url_name),
                           extra={"request": context["request"]})
            return return_value if matched_simple else ''
        if matched_simple:
            return return_value
        url_info = settings.MENU_URL_NAMES[current_url_name]
        if 'alias' in url_info:
            return inner_recursive(url_info['alias'])
        if 'parent' in url_info:
            return inner_recursive(url_info['parent'])
        return ''

    if context['request'].resolver_match.url_name == 'html_pages':
        current_url_name = context['request'].resolver_match.kwargs['url']
        if not current_url_name.startswith('/'):
            current_url_name = '/' + current_url_name
    else:
        current_url_name = context['request'].resolver_match.url_name

    return inner_recursive(current_url_name)
