import datetime
import logging

import bleach
import hoep as h

from django.conf import settings
from django.urls import reverse
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
    md_rendered = markdown.render(text)
    return bleach.clean(md_rendered, tags=MARKDOWN_ALLOWED_TAGS,
                        attributes=MARKDOWN_ALLOWED_ATTRS)


def is_club_site():
    return settings.SITE_ID == settings.CLUB_SITE_ID


def get_club_domain(code=None):
    protocol = "http://"
    prefix = "kzn." if code == "kzn" else ""
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


def city_aware_reverse(viewname, urlconf=None, args=None, kwargs=None,
                       current_app=None):
    assert "city_code" in kwargs
    kwargs["city_delimiter"] = ""
    if kwargs["city_code"] == settings.DEFAULT_CITY_CODE or is_club_site():
        kwargs["city_code"] = ""
    if kwargs["city_code"]:
        kwargs["city_delimiter"] = "/"
    return reverse(viewname, urlconf, args, kwargs, current_app)


def admin_datetime(dt: datetime.datetime) -> str:
    return formats.date_format(dt, 'j E Y г. G:i e')
