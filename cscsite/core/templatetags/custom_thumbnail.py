from django import template
from django.contrib.staticfiles.storage import staticfiles_storage
from django.template import Library
from django.template import TemplateSyntaxError
from django.utils.encoding import smart_str
from django.utils.six import text_type
from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.images import DummyImageFile, BaseImageFile
from sorl.thumbnail.templatetags.thumbnail import ThumbnailNode, kw_pat, \
    ThumbnailNodeBase

register = Library()


class StubImage(BaseImageFile):
    url = staticfiles_storage.url("img/center/profile_no_photo.png")

    def __init__(self):
        self.size = 175, 238

    def exists(self):
        return True


class BoyStubImage(StubImage):
    url = staticfiles_storage.url("img/csc_boy.svg")


class GirlStubImage(StubImage):
    url = staticfiles_storage.url("img/csc_girl.svg")


class UserThumbnailNode(ThumbnailNodeBase):
    """
    If picture not found, show empty stub picture based on user groups.
    May hit db to get user groups in that case.
    """
    child_nodelists = ('nodelist_file',)
    error_msg = ('Syntax error. Expected: ``userpreview user_obj '
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
            self.nodelist_file = parser.parse(('enduserpreview',))
            parser.delete_first_token()

    def _render(self, context):
        """Replace DummyImage with csc girl/boy"""
        user = self.user.resolve(context)
        file_ = getattr(user, "photo", None)
        geometry = self.geometry.resolve(context)
        options = {}
        for key, expr in self.options:
            noresolve = {'True': True, 'False': False, 'None': None}
            value = noresolve.get(text_type(expr), expr.resolve(context))
            if key == 'options':
                options.update(value)
            else:
                options[key] = value

        # Default crop settings
        if "crop" not in options:
            options["crop"] = "center top"
        if "cropbox" not in options:
            options["cropbox"] = user.photo_thumbnail_cropbox()

        thumbnail = get_thumbnail(file_, geometry, **options)

        if not thumbnail or isinstance(thumbnail, DummyImageFile):
            cls = user.__class__
            if not user.is_teacher and user.gender == cls.GENDER_MALE:
                thumbnail = BoyStubImage()
            elif not user.is_teacher and user.gender == cls.GENDER_FEMALE:
                thumbnail = GirlStubImage()
            else:
                thumbnail = StubImage()

        if self.as_var:
            context.push()
            context[self.as_var] = thumbnail
            output = self.nodelist_file.render(context)
            context.pop()
        else:
            output = thumbnail.url

        return output

    def __repr__(self):
        return "<ThumbnailNode>"

    def __iter__(self):
        for node in self.nodelist_file:
            yield node


@register.tag
def userpreview(parser, token):
    return UserThumbnailNode(parser, token)
