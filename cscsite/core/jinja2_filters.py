from django.utils.safestring import mark_safe
from django_jinja.builtins.extensions import make_template_fragment_key
from django.core.cache import InvalidCacheBackendError, caches

from core.utils import render_markdown


def markdown(value, fragment_name, expires_in=0, *vary_on):
    try:
        fragment_cache = caches['markdown_fragments']
    except InvalidCacheBackendError:
        fragment_cache = caches['default']
    cache_key = make_template_fragment_key(fragment_name, vary_on)
    rendered = fragment_cache.get(cache_key)
    if rendered is None:
        rendered = render_markdown(value)
        fragment_cache.set(cache_key, rendered, expires_in)
    # TODO: think about escaping
    return rendered
