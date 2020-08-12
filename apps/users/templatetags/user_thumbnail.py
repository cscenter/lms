from django import template
from django.template import Library
from django.template import TemplateSyntaxError
from django.utils.encoding import smart_str
from sorl.thumbnail.images import DummyImageFile
from sorl.thumbnail.templatetags.thumbnail import kw_pat, ThumbnailNodeBase

register = Library()


class UserThumbnailNode(ThumbnailNodeBase):
    """
    Shows empty stub picture if picture not found.

    Note:
        May hit db to get authorized user groups to resolve what stub image
        to show, but csc-menu do it on each request.
    """
    child_nodelists = ('nodelist_file', 'nodelist_empty')
    error_msg = ('Syntax error. Expected: ``user_thumbnail user_obj '
                 '[key1=val1 key2=val2...] as var``')

    def __init__(self, parser, token):
        bits = token.split_contents()
        self.user = template.Variable(bits[1])
        self.geometry = parser.compile_filter(bits[2])
        self.options = []
        self.as_var = None
        self.nodelist_file = None

        if bits[-2] == 'as':
            options_bits = bits[3:-2]
        else:
            options_bits = bits[3:]

        for bit in options_bits:
            m = kw_pat.match(bit)
            if not m:
                raise TemplateSyntaxError(self.error_msg)
            key = smart_str(m.group('key'))
            expr = parser.compile_filter(m.group('value'))
            self.options.append((key, expr))

        if bits[-2] == 'as':
            self.as_var = bits[-1]
            self.nodelist_file = parser.parse(('empty', 'enduser_thumbnail',))
            if parser.next_token().contents == 'empty':
                self.nodelist_empty = parser.parse(('enduser_thumbnail',))
                parser.delete_first_token()

    def _render(self, context):
        user = self.user.resolve(context)
        geometry = self.geometry.resolve(context)
        options = {}
        for key, expr in self.options:
            noresolve = {'True': True, 'False': False, 'None': None}
            value = noresolve.get(str(expr), expr.resolve(context))
            if key == 'options':
                options.update(value)
            else:
                options[key] = value

        use_stub = bool(options.pop("use_stab", True))
        thumbnail = user.get_thumbnail(geometry, use_stub=use_stub, **options)

        render_empty = not thumbnail or isinstance(thumbnail, DummyImageFile)

        if self.as_var:
            context.push()
            context[self.as_var] = thumbnail
            if render_empty and self.nodelist_empty:
                output = self.nodelist_empty.render(context)
            else:
                output = self.nodelist_file.render(context)
            context.pop()
        else:
            # ?
            output = thumbnail.url

        return output

    def __repr__(self):
        return "<UserThumbnailNode>"

    def __iter__(self):
        for node in self.nodelist_file:
            yield node
        for node in self.nodelist_empty:
            yield node


@register.tag
def user_thumbnail(parser, token):
    return UserThumbnailNode(parser, token)
