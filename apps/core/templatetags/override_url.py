from django.template import Library

from core.urls import reverse

register = Library()

UNSET = object()


@register.simple_tag(takes_context=True)
def url(context, view, subdomain=UNSET, *args, **kwargs):
    """
    Resolves a URL in a template, using subdomain-based URL resolution.

    If no subdomain is provided and a ``request`` is in the template context
    when rendering, the URL will be resolved relative to the current request's
    subdomain. If no ``request`` is provided, the URL will be resolved relative
    to current domain with the ``settings.ROOT_URLCONF``.

    Usage::

        {% load override_url %}
        {% url 'view-name' subdomain='subdomain' %}
    """
    if subdomain is UNSET:
        request = context.get('request')
        if request is not None:
            subdomain = getattr(request, 'subdomain', None)
        else:
            subdomain = None
    elif subdomain == '':
        subdomain = None

    return reverse(view, subdomain=subdomain, args=args, kwargs=kwargs)
