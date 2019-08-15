import datetime
from itertools import zip_longest
from urllib.parse import urlparse, parse_qs

import hoep as h
import logging

import bleach
from django.conf import settings
from django.db.models import Max, Min
from django.utils import formats
from hashids import Hashids

hashids = Hashids(salt=settings.HASHIDS_SALT, min_length=8)

# Some details here https://github.com/Anomareh/Hoep
MARKDOWN_EXTENSIONS = (h.EXT_FENCED_CODE |
                       h.EXT_AUTOLINK |
                       h.EXT_STRIKETHROUGH |
                       h.EXT_TABLES |
                       h.EXT_QUOTE |
                       h.EXT_NO_INTRA_EMPHASIS |
                       h.EXT_SPACE_HEADERS |
                       h.EXT_MATH |
                       h.EXT_MATH_EXPLICIT)
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
    'a': ['href'],
    'img': ['src'],
    'iframe': ['src', 'height', 'width', 'allowfullscreen', 'frameborder']
}


def render_markdown(text):
    """Renders markdown, then sanitizes html based on allowed tags"""
    md_rendered = markdown.render(text)
    return bleach.clean(md_rendered, tags=MARKDOWN_ALLOWED_TAGS,
                        attributes=MARKDOWN_ALLOWED_ATTRS)


def is_club_site():
    return settings.SITE_ID == settings.CLUB_SITE_ID


def get_club_domain(code=None):
    protocol = "http://"
    if code in ('kzn', 'nsk'):
        prefix = f"{code}."
    else:
        prefix = ""
    return protocol + prefix + settings.CLUB_DOMAIN


class SQLFormatter(logging.Formatter):
    """
    In case you’re working with a 256 color terminal, you should use
    the Terminal256Formatter instead of the TerminalTrueColorFormatter.
    """
    def format(self, record):
        # Check if Pygments is available for coloring
        try:
            import pygments
            from pygments.lexers import SqlLexer
            from pygments.formatters import TerminalTrueColorFormatter
        except ImportError:
            pygments = None

        # Check if sqlparse is available for indentation
        try:
            import sqlparse
        except ImportError:
            sqlparse = None

        # Remove leading and trailing whitespaces
        sql = record.sql.strip()

        if sqlparse:
            # Indent the SQL query
            sql = sqlparse.format(sql, reindent=True)

        if pygments:
            # Highlight the SQL query
            sql = pygments.highlight(
                sql,
                SqlLexer(),
                TerminalTrueColorFormatter(style='monokai')
            )

        # Set the record's statement to the formatted query
        record.statement = sql
        return super(SQLFormatter, self).format(record)


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


# FIXME: add tests!
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
    Note that `use_offset=True` preserve original queryset ordering, but
    limit/offset pagination could be slow.
    """
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
        if limits['min']:
            for pk in range(limits['min'], limits['max'] + 1, chunk_size):
                for row in queryset.filter(pk__gte=pk)[:chunk_size]:
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


def chunks(iterable, n, fillvalue=None):
    """
    Collect data into fixed-length chunks or blocks:
    Example:
        In: grouper('ABCDEFG', 3, 'x')
        Out: ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    return zip_longest(fillvalue=fillvalue, *args)


def bucketize(iterable, key=None, value_transform=None):
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
    buckets = {}
    for val in iterable:
        bucket_key = key(val)
        buckets.setdefault(bucket_key, []).append(value_transform(val))
    return buckets
