from __future__ import absolute_import, unicode_literals

import bleach
import hoep as h

from django.conf import settings
from hashids import Hashids
hashids = Hashids(salt=settings.HASHIDS_SALT, min_length=8)

# Some details here https://github.com/Anomareh/Hoep
MARKDOWN_EXTENSIONS = h.EXT_FENCED_CODE | h.EXT_AUTOLINK | \
             h.EXT_STRIKETHROUGH | h.EXT_TABLES | h.EXT_QUOTE | \
             h.EXT_NO_INTRA_EMPHASIS | h.EXT_SPACE_HEADERS | \
             h.EXT_MATH | h.EXT_MATH_EXPLICIT
MARKDOWN_RENDER_FLAGS = 0
markdown = h.Hoep(MARKDOWN_EXTENSIONS, MARKDOWN_RENDER_FLAGS)

MARKDOWN_ALLOWED_TAGS = [
    'p', 'ul', 'ol', 'li', 'em', 'strong', 'strike', 'pre', 'br', 'hr',
    'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a',
    'h1', 'h2', 'h3', 'h4', 'h5', 'blockquote', 'q', 'img',
    'iframe', 'b', 'i', 'div']
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

def get_club_domain(code = None):
    protocol = "http://"
    prefix = "kzn." if code == "RU KZN" else ""
    return (protocol + prefix + settings.CLUB_DOMAIN)

