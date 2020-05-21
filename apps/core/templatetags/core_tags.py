import os
import re

import itertools
from django.core.cache import InvalidCacheBackendError, caches
from django.core.cache.utils import make_template_fragment_key
from django.template import (
    Library, Node, TemplateSyntaxError, VariableDoesNotExist,
)
from django.template.base import TextNode
from django.utils.numberformat import format
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from multiselectfield.db.fields import MSFList

from ..admin import get_admin_url
from ..utils import render_markdown

numeric_test = re.compile(r"^\d+$")
register = Library()


@register.simple_tag
def admin_url(instance_or_qs):
    """
    A tag for reversing admin site URLs from templates.
    """
    return get_admin_url(instance_or_qs)


@register.filter
def to_css(s):
    return s.replace("_", "-")


# FIXME: DeprecationWarning: invalid escape sequence
TEX_SYMBOLS_TO_ESCAPE = {
    '#': r'\#',
    '$': r'\$',
    '%': r'\%',
    '_': r'\_',
    '&': r'\&',
    '{': r'\{',
    '}': r'\}',
}


@register.filter
def tex(s):
    for a, b in TEX_SYMBOLS_TO_ESCAPE.items():
        s = s.replace(a, b)
    # TODO: replace double quotes in a loop (presume we haven't nested quotes)
    return s.replace('"', '``', 1).replace('"', "''", 1)


@register.filter
def date_soon_css(d):
    days_diff = (d.date() - now().date()).days
    if days_diff < 0:
        return "past"
    elif days_diff == 0:
        return "today"
    elif days_diff == 1:
        return "tomorrow"
    elif days_diff == 2:
        return "day-after-tomorrow"
    else:
        return "in-future"

# http://stackoverflow.com/a/1112236/1341309


@register.filter
def lookup(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    elif arg in value:
        return value[arg]
    elif numeric_test.match(str(arg)) and len(value) > int(arg):
        return value[int(arg)]
    else:
        return None


@register.filter
def startswith(value, arg):
    """Usage, {% if value|startswith:"arg" %}"""
    return value.startswith(arg)


@register.filter
def endswith(value, arg):
    """Usage, {% if value|endswith:"arg" %}"""
    return value.endswith(arg)


@register.filter
def markdownify(text):
    return render_markdown(text)


class MarkdownNode(Node):
    def __init__(self, nodelist, expire_time_var, fragment_name, vary_on):
        self.nodelist = nodelist
        self.expire_time_var = expire_time_var
        self.fragment_name = fragment_name
        self.vary_on = vary_on

    def render(self, context):
        try:
            expire_time = self.expire_time_var.resolve(context)
        except VariableDoesNotExist:
            raise TemplateSyntaxError('"cache" tag got an unknown variable: %r' % self.expire_time_var.var)
        try:
            expire_time = int(expire_time)
        except (ValueError, TypeError):
            raise TemplateSyntaxError('"cache" tag got a non-integer timeout value: %r' % expire_time)
        try:
            fragment_cache = caches['markdown_fragments']
        except InvalidCacheBackendError:
            fragment_cache = caches['default']

        vary_on = [var.resolve(context) for var in self.vary_on]
        cache_key = make_template_fragment_key(self.fragment_name, vary_on)
        value = fragment_cache.get(cache_key)
        if value is None:
            context.autoescape = False
            # Remove unnecessary line breaks and whitespaces. Example:
            # {% markdown %}\n <- LB for readability in tpl{% endmarkdown %}
            if self.nodelist:
                if isinstance(self.nodelist[0], TextNode) and \
                   not self.nodelist[0].s.strip():
                    self.nodelist[0].s = ''
                if isinstance(self.nodelist[-1], TextNode) and \
                   not self.nodelist[-1].s.strip():
                    self.nodelist[-1].s = ''
            value = self.nodelist.render(context)
            value = render_markdown(value)
            fragment_cache.set(cache_key, value, expire_time)
        return mark_safe(value)


# Note: Inspired by django.templatetags.cache
@register.tag('markdown')
def do_markdown(parser, token):
    """
    This will markdownify the contents of a template fragment, sanitize and
    cache for a given amount of time.

    Usage::

        {% load markdown %}
        {% markdown [expire_time] [fragment_name] %}
            .. some expensive processing ..
        {% endmarkdown %}

    This tag also supports varying by a list of arguments::

        {% load markdown %}
        {% markdown [expire_time] [fragment_name] [var1] [var2] .. %}
            .. some expensive processing ..
        {% endmarkdown %}

    Each unique set of arguments will result in a unique cache entry.
    """
    nodelist = parser.parse(('endmarkdown',))
    parser.delete_first_token()
    tokens = token.split_contents()
    if len(tokens) < 3:
        raise TemplateSyntaxError("'%r' tag requires at least 2 arguments."
                                  % tokens[0])

    return MarkdownNode(
        nodelist,
        parser.compile_filter(tokens[1]),
        tokens[2],  # fragment_name
        [parser.compile_filter(t) for t in tokens[3:]],
    )


@register.filter
def floatdot(value, decimal_pos=2):
    """print formatted float with dot as separator"""
    return format(value, ".", decimal_pos)
floatdot.is_safe = True


@register.filter
def chunks(value, chunk_length):
    """
    Breaks a list up into a list of lists of size <chunk_length>
    """
    i = iter(value)
    while True:
        chunk = list(itertools.islice(i, int(chunk_length)))
        if chunk:
            yield chunk
        else:
            break


@register.filter
def replace(value, args):
    """Args must be separated by space"""
    old, new = args.split(" ")
    if isinstance(value, MSFList):
        value = str(value)
    return value.replace(old, new)
# replace.is_safe = True


@register.simple_tag
def call_method(obj, method_name, *args, **kwargs):
    method = getattr(obj, method_name)
    return method(*args, **kwargs)


@register.simple_tag
def can_enroll_in_course(user, course, student_profile):
    from learning.permissions import EnrollInCourse, EnrollPermissionObject
    perm_obj = EnrollPermissionObject(course, student_profile)
    return user.has_perm(EnrollInCourse.name, perm_obj)


@register.simple_tag
def can_enroll_in_course_by_invitation(user, course_invitation, student_profile):
    from learning.permissions import EnrollInCourseByInvitation, \
        InvitationEnrollPermissionObject
    perm_obj = InvitationEnrollPermissionObject(course_invitation,
                                                student_profile)
    return user.has_perm(EnrollInCourseByInvitation.name, perm_obj)


@register.filter
def file_name(value):
    return os.path.basename(value.file.name)
