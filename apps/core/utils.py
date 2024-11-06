import datetime
import enum
import logging
from functools import partial
from itertools import zip_longest
from typing import Any, Dict, Iterable, Iterator, List, Optional
from urllib.parse import parse_qs, urlparse

import bleach
import hoep as h
from django_jinja.builtins.extensions import make_template_fragment_key
from hashids import Hashids

from django.conf import settings
from django.core.cache import InvalidCacheBackendError, caches
from django.db.models import Max, Min
from django.utils import formats

import functools
try:
    from urlparse import urlunparse
except ImportError:
    from urllib.parse import urlunparse

from django.conf import settings
try:
    from django.urls import reverse as simple_reverse
except ImportError:  # Django<2.0
    from django.core.urlresolvers  import reverse as simple_reverse


def current_site_domain():
    from django.contrib.sites.models import Site
    domain = Site.objects.get_current().domain

    prefix = 'www.'
    if getattr(settings, 'REMOVE_WWW_FROM_DOMAIN', False) \
            and domain.startswith(prefix):
        domain = domain.replace(prefix, '', 1)

    return domain

get_domain = current_site_domain


def urljoin(domain, path=None, scheme=None):
    """
    Joins a domain, path and scheme part together, returning a full URL.

    :param domain: the domain, e.g. ``example.com``
    :param path: the path part of the URL, e.g. ``/example/``
    :param scheme: the scheme part of the URL, e.g. ``http``, defaulting to the
        value of ``settings.DEFAULT_URL_SCHEME``
    :returns: a full URL
    """
    if scheme is None:
        scheme = getattr(settings, 'DEFAULT_URL_SCHEME', 'http')

    return urlunparse((scheme, domain, path or '', None, None, None))


def reverse(viewname, subdomain=None, scheme=None, args=None, kwargs=None,
        current_app=None):
    """
    Reverses a URL from the given parameters, in a similar fashion to
    :meth:`django.urls.reverse`.

    :param viewname: the name of URL
    :param subdomain: the subdomain to use for URL reversing
    :param scheme: the scheme to use when generating the full URL
    :param args: positional arguments used for URL reversing
    :param kwargs: named arguments used for URL reversing
    :param current_app: hint for the currently executing application
    """
    urlconf = settings.SUBDOMAIN_URLCONFS.get(subdomain, settings.ROOT_URLCONF)

    domain = get_domain()
    if subdomain is not None:
        domain = '%s.%s' % (subdomain, domain)

    path = simple_reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs,
        current_app=current_app)
    return urljoin(domain, path, scheme=scheme)


#: :func:`reverse` bound to insecure (non-HTTPS) URLs scheme
insecure_reverse = functools.partial(reverse, scheme='http')

#: :func:`reverse` bound to secure (HTTPS) URLs scheme
secure_reverse = functools.partial(reverse, scheme='https')

#: :func:`reverse` bound to be relative to the current scheme
relative_reverse = functools.partial(reverse, scheme='')


logger = logging.getLogger(__name__)

hashids = Hashids(salt=settings.HASHIDS_SALT, min_length=8)

class Empty(enum.Enum):
    token = 0


_empty = Empty.token

# Some details here https://github.com/Anomareh/Hoep
MARKDOWN_EXTENSIONS = (h.EXT_FENCED_CODE |
                       h.EXT_AUTOLINK |
                       h.EXT_STRIKETHROUGH |
                       h.EXT_TABLES |
                       h.EXT_QUOTE |
                       h.EXT_NO_INTRA_EMPHASIS |
                       h.EXT_SPACE_HEADERS)
MARKDOWN_RENDER_FLAGS = 0
markdown = h.Hoep(MARKDOWN_EXTENSIONS, MARKDOWN_RENDER_FLAGS)

# This is not really about markdown, This is about html tags that will be
# saved after markdown rendering
MARKDOWN_ALLOWED_TAGS = [
    'a',
    'b',
    'blockquote',
    'br',
    'code',
    'del',
    'div',
    'dl',
    'dd',
    'dt',
    'em',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'hr',
    'i',
    'iframe',
    'img',
    'li',
    'ol',
    'p',
    'pre',
    'q',
    'strike',
    'strong',
    'table',
    'tbody',
    'td',
    'th',
    'thead',
    'tr',
    'ul',
]
MARKDOWN_ALLOWED_ATTRS = {
    '*': ['class'],
    'a': ['href', 'aria-expanded', 'role', 'data-toggle'],
    'img': ['src'],
    'iframe': ['src', 'height', 'width', 'allowfullscreen', 'frameborder'],
    'div': ['id', 'role', 'aria-labelledby', 'aria-expanded']
}


def render_markdown(text):
    """Renders markdown, then sanitizes html based on allowed tags"""
    md_rendered = markdown.render(text)
    return bleach.clean(md_rendered, tags=MARKDOWN_ALLOWED_TAGS,
                        attributes=MARKDOWN_ALLOWED_ATTRS)


def render_markdown_and_cache(value, fragment_name, expires_in=0, *vary_on):
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


def is_club_site():
    return settings.SITE_ID == settings.CLUB_SITE_ID


def get_club_domain(code=None):
    protocol = "http://"
    if code in ('kzn', 'nsk'):
        prefix = f"{code}."
    else:
        prefix = ""
    return protocol + prefix + 'compsciclub.ru'


def admin_datetime(dt: datetime.datetime) -> str:
    return formats.date_format(dt, 'j E Y г. G:i e')


"""
Transliteration for cyrillic alphabet. Used LC ICAO doc 9303 as a reference.
Soft sign is ignored by this recommendation, we intentionally ignore this 
symbol since it's not valid for CN values in LDAP accounts. Common Name used 
as a branch name in `gerrit` code review system.
"""
_ru_en_mapping = {
    'А': "A",
    'Б': "B",
    'В': "V",
    'Г': "G",
    'Д': "D",
    'Е': "E",
    'Ё': "E",
    'Ж': "ZH",
    'З': "Z",
    'И': "I",
    'Й': "I",
    'К': "K",
    'Л': "L",
    'М': "M",
    'Н': "N",
    'О': "O",
    'П': "P",
    'Р': "R",
    'С': "S",
    'Т': "T",
    'У': "U",
    'Ф': "F",
    'Х': "KH",
    'Ц': "TS",
    'Ч': "CH",
    'Ш': "SH",
    'Щ': "SHCH",
    'Ъ': "IE",
    'Ы': "Y",
    'Ь': None,
    'Э': "E",
    'Ю': "IU",
    'Я': "IA",
    'а': "a",
    'б': "b",
    'в': "v",
    'г': "g",
    'д': "d",
    'е': "e",
    'ё': "e",
    'ж': "zh",
    'з': "z",
    'и': "i",
    'й': "i",
    'к': "k",
    'л': "l",
    'м': "m",
    'н': "n",
    'о': "o",
    'п': "p",
    'р': "r",
    'с': "s",
    'т': "t",
    'у': "u",
    'ф': "f",
    'х': "kh",
    'ц': "ts",
    'ч': "ch",
    'ш': "sh",
    'щ': "shch",
    'ъ': "ie",
    'ы': "y",
    'ь': None,
    'э': "e",
    'ю': "iu",
    'я': "ia",
}
ru_en_mapping = {ord(k): v for k, v in _ru_en_mapping.items()}


def queryset_iterator(queryset, chunk_size=1000, use_offset=False):
    """
    Memory efficient iteration over a Django queryset with
    `prefetch_related` support.

    Django normally loads all objects into memory when iterating over a
    queryset, which could lead to excessive memory consumption. It's possible
    to avoid doing any caching at the QuerySet level by using `.iterator()`
    method but this causes `prefetch_related` to be ignored and N+1 problem
    as a result.

    Default implementation overrides ordering with primary key.
    Note that `use_offset=True` preserves original queryset ordering, but
    limit/offset pagination could be slow.
    """
    if chunk_size <= 0:
        return

    if use_offset:
        if not queryset.ordered:
            queryset = queryset.order_by('pk')
        total = queryset.count()
        for i in range(0, total, chunk_size):
            for row in queryset[i:i + chunk_size]:
                yield row
    else:
        queryset = queryset.order_by('pk')
        limits = queryset.aggregate(min=Min('pk'), max=Max('pk'))
        logger.info(f'Queryset iterator chunk size: {chunk_size}, offset: {use_offset}')
        if limits['min']:
            for pk in range(limits['min'], limits['max'] + 1, chunk_size):
                logger.info(f'Next range [{pk}, {pk + chunk_size})')
                for row in queryset.filter(pk__gte=pk, pk__lt=pk + chunk_size)[:chunk_size]:
                    yield row


def get_youtube_video_id(video_url):
    """
    Returns Youtube video id extracted from the given valid url.

    Supported formats:
        https://youtu.be/sxnSFdRECas
        https://www.youtube.com/watch?v=0lZJicHYJXM
        http://www.youtube.com/v/_lOT2p_FCvA?version=3&amp;hl=en_US
        https://www.youtube.com/embed/8SPq-9kS69M
        https://www.youtube-nocookie.com/embed/8SPq-9kS69M
        youtube.com/embed/8SPq-9kS69M
    """
    if video_url.startswith(('youtu', 'www')):
        video_url = 'https://' + video_url
    parsed = urlparse(video_url)
    video_id = None
    if 'youtube' in parsed.hostname:
        if parsed.path == '/watch':
            qs = parse_qs(parsed.query)
            video_id = qs['v'][0]
        elif parsed.path.startswith(('/embed/', '/v/')):
            video_id = parsed.path.split('/', maxsplit=2)[2]
    elif 'youtu.be' in parsed.hostname:
        video_id = parsed.path.split('/')[1]
    return video_id


def normalize_yandex_login(value: str) -> str:
    return value.lower().replace('-', '.')


def chunks(iterable: Iterable, n: int, fillvalue: Optional[Any] = None) -> Iterator[Any]:
    """
    Collect data into fixed-length chunks or blocks:
    Example:
        In: grouper('ABCDEFG', 3, 'x')
        Out: ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    return zip_longest(fillvalue=fillvalue, *args)


def bucketize(iterable, key=None, value_transform=None) -> Dict[Any, List[Any]]:
    """
    Collect data into buckets from the iterable grouping values by key.

    The *key* is a function computing a key value for each element.
    If not specified or is ``None``, *key* defaults to an identity function and
    returns the element unchanged.
    The *value_transform* is a function modifying a value before adding
    into bucket.
    """
    if key is None:
        key = lambda x: x
    if value_transform is None:
        value_transform = lambda x: x
    buckets: Dict[Any, List[Any]] = {}
    for val in iterable:
        bucket_key = key(val)
        buckets.setdefault(bucket_key, []).append(value_transform(val))
    return buckets


# noinspection PyPep8Naming
class instance_memoize:
    """
    Method decorator that helps caching the return value on the
    instance whose method was invoked. All arguments passed to a method
    decorated with `Memoize` must be hashable.

    If a memoized method is invoked directly on its class the result will not
    be cached. Instead the method will be invoked like a static method.

    Assumes that read and write operations are mutually exclusive per request.
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner=None):
        if instance is None:
            return self.func
        return partial(self, instance)

    def __call__(self, *args, **kwargs):
        obj = args[0]
        try:
            cache = obj._instance_memoize_cache
        except AttributeError:
            cache = obj._instance_memoize_cache = {}
        key = (self.func, args[1:], frozenset(kwargs.items()))
        if key not in cache:
            cache[key] = self.func(*args, **kwargs)
        return cache[key]

    @classmethod
    def delete_cache(cls, instance):
        cache_attr_name = "_instance_memoize_cache"
        if hasattr(instance, cache_attr_name):
            delattr(instance, cache_attr_name)
