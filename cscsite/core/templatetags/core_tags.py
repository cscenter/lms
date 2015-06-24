import hashlib
import re

from django import template
from django.utils.timezone import now

from core.admin import get_admin_url

register = template.Library()


@register.simple_tag
def admin_url(instance_or_qs):
    """
    A tag for reversing admin site URLs from templates.
    """
    return get_admin_url(instance_or_qs)


@register.filter
def to_css(s):
    return s.replace("_", "-")


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
def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    elif hasattr(value, 'has_key') and value.has_key(arg):
        return value[arg]
    elif numeric_test.match(str(arg)) and len(value) > int(arg):
        return value[int(arg)]
    else:
        return None