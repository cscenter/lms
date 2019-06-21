from django.contrib.staticfiles.storage import staticfiles_storage
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.images import BaseImageFile, DummyImageFile

from users.constants import ThumbnailSizes, GenderTypes


def photo_thumbnail_cropbox(data):
    try:
        return ",".join(map(str, (
            data["x"],
            data["y"],
            data["x"] + data["width"],
            data["y"] + data["height"],
        )))
    except (KeyError, TypeError):
        return ""


# FIXME: add django checks for mandatory fields for this mixin: photo, gender
# FIXME: Make gender optional
class UserThumbnailMixin:
    """
    This Django's model mixin helps to generate thumbnail for photo image field.

    In case of no photo provided generates stub thumbnail which depends
    on user gender.
    """
    ThumbnailSize = ThumbnailSizes

    def get_thumbnail(self, geometry=ThumbnailSizes.BASE, **options):
        return get_user_thumbnail(self, geometry, **options)

    def photo_thumbnail_cropbox(self):
        """Used by `thumbnail` template tag. Format: x1,y1,x2,y2"""
        if hasattr(self, "cropbox_data"):
            return photo_thumbnail_cropbox(self.cropbox_data)
        return ""

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_photo_field())
        return errors

    @classmethod
    def _check_photo_field(cls):
        errors = []
        try:
            photo = cls._meta.get_field("photo")
            # TODO: check field type
        except FieldDoesNotExist:
            errors.append(
                checks.Error(
                    f'`{cls.__name__}` must define `photo` image field',
                    hint='define photo = models.ImageField(...)',
                    obj=cls,
                    id='users.thumbnails.E001',
                ))
        return errors


class BaseStubImage(BaseImageFile):
    @property
    def url(self):
        return staticfiles_storage.url("v1/img/center/profile_no_photo.png")

    def __init__(self, **kwargs):
        geometry = kwargs.get("geometry", ThumbnailSizes.BASE)
        self.size = geometry.split("x")

    @property
    def _suffix(self):
        if self.size[0] == self.size[1]:
            return f"_{ThumbnailSizes.SQUARE}"
        return ""

    def exists(self):
        return True


class BoyStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/boy{self._suffix}.png")


class GirlStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/girl{self._suffix}.png")


class ManStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/man{self._suffix}.png")


class WomanStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/woman{self._suffix}.png")


def get_user_thumbnail(user, geometry, use_stub=True,
                       stub_official=True, **options):
    path_to_img = getattr(user, "photo", None)
    # Default crop settings
    if "crop" not in options:
        options["crop"] = "center top"
    if "cropbox" not in options:
        options["cropbox"] = user.photo_thumbnail_cropbox()
    # FIXME: Instead of factory we could pass in path to stub image, but to do with cropbox in that case?
    if use_stub:
        if user.gender == GenderTypes.MALE:
            factory = ManStubImage if stub_official else BoyStubImage
        elif user.gender == GenderTypes.FEMALE:
            factory = WomanStubImage if stub_official else GirlStubImage
        else:
            factory = BaseStubImage
    else:
        factory = None
    return get_thumbnail_or_stub(path_to_img, geometry, stub_factory=factory,
                                 **options)


def get_thumbnail_or_stub(path_to_img, geometry, stub_factory=None, **options):
    if path_to_img:
        # Could return DummyImageFile instance
        thumbnail = get_thumbnail(path_to_img, geometry, **options)
    else:
        thumbnail = None
    # TODO: Override default DummyImageFile
    if not thumbnail and stub_factory:
        thumbnail = stub_factory(geometry=geometry)
    return thumbnail
