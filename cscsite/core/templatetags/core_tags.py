from django import template

from core.admin import get_admin_url

register = template.Library()

@register.simple_tag
def admin_url(instance_or_qs):
    """A tag for reversing admin site URLs from templates."""
    return get_admin_url(instance_or_qs)


