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
