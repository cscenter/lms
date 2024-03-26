from typing import Optional

from sorl.thumbnail import get_thumbnail as sorl_get_thumbnail
from sorl.thumbnail.images import BaseImageFile, DummyImageFile

from django import forms
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models import ImageField

from users.constants import GenderTypes, ThumbnailSizes


# TODO: add validation for unbound coords and width=img.width
class CropboxData(forms.Form):
    width = forms.FloatField(required=True)
    height = forms.FloatField(required=True)
    x = forms.FloatField(required=True)
    y = forms.FloatField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        try:
            for v in cleaned_data.values():
                rounded = int(v)
        except ValueError:
            raise ValidationError("Can't round value to int")

    def to_json(self):
        xs = {}
        for k, v in self.cleaned_data.items():
            xs[k] = int(v)
        return xs


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


class ThumbnailMixin:
    ThumbnailSize = ThumbnailSizes

    def get_thumbnail(self, geometry=ThumbnailSizes.BASE, **options):
        raise NotImplementedError

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_photo_field())
        return errors

    @classmethod
    def _check_photo_field(cls):
        errors = []
        try:
            img_field = cls._meta.get_field("photo")
            if not isinstance(img_field, ImageField):
                errors.append(
                    checks.Error(
                        f'Wrong type of the `{cls.__name__}.photo` field',
                        hint='photo field must be sublass of '
                             'models.ImageField(...)',
                        obj=cls,
                        id='users.thumbnails.E002',
                    ))
        except FieldDoesNotExist:
            errors.append(
                checks.Error(
                    f'`{cls.__name__}` must define `photo` image field',
                    hint='define photo = models.ImageField(...)',
                    obj=cls,
                    id='users.thumbnails.E001',
                ))
        return errors


class UserThumbnailMixin(ThumbnailMixin):
    """
    This Django's model mixin helps to generate thumbnail for photo image field.

    In case of no photo provided generates stub thumbnail which depends
    on user gender.
    """

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
        errors.extend(cls._check_required_fields())
        return errors

    @classmethod
    def _check_required_fields(cls):
        errors = []
        try:
            gender_field = cls._meta.get_field("gender")
        except FieldDoesNotExist:
            errors.append(
                checks.Error(
                    f'`{cls.__name__}` depends on `gender` choice field',
                    hint='define gender = models.CharField(...)',
                    obj=cls,
                    id='users.thumbnails.E002',
                ))
        return errors

class ApplicantThumbnailMixin(ThumbnailMixin):
    def get_thumbnail(self, geometry=ThumbnailSizes.BASE, **options):
        stub_factory = get_stub_factory(self.gender)
        kwargs = {
            "cropbox": None,
            "stub_factory": stub_factory,
            **options
        }
        return get_thumbnail(path_to_img=self.photo, geometry=geometry,
                             **kwargs)

class BaseStubImage(BaseImageFile):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/user{self._suffix}.png")

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


class BoyStubImageSVG(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/boy{self._suffix}.svg")


class GirlStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/girl{self._suffix}.png")


class GirlStubImageSVG(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/girl{self._suffix}.svg")


class ManStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/man{self._suffix}.png")


class WomanStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url(f"v2/img/placeholder/woman{self._suffix}.png")


def get_stub_factory(gender, official=True, svg=False):
    if gender == GenderTypes.MALE:
        if official:
            factory = ManStubImage
        else:
            factory = BoyStubImageSVG if svg else BoyStubImage
    elif gender == GenderTypes.FEMALE:
        if official:
            factory = WomanStubImage
        else:
            factory = GirlStubImageSVG if svg else GirlStubImage
    else:
        factory = BaseStubImage
    return factory


def get_user_thumbnail(user, geometry, use_stub=True,
                       stub_official=True, **options):
    path_to_img = getattr(user, "photo", None)
    if "cropbox" not in options:
        options["cropbox"] = user.photo_thumbnail_cropbox()
    if use_stub:
        factory = get_stub_factory(user.gender, official=stub_official)
    else:
        factory = None
    return get_thumbnail(path_to_img, geometry, stub_factory=factory, **options)


def get_thumbnail(path_to_img, geometry, stub_factory=None, **options) -> Optional[BaseImageFile]:
    """
    Returns an image thumbnail if path to the image is correct and the
    image exists along that path.
    Otherwise it returns None or the result of *stub_factory* if stub factory
    is specified.
    """
    if "crop" not in options:
        options["crop"] = "center top"
    if path_to_img:
        # Could return DummyImageFile instance
        thumbnail = sorl_get_thumbnail(path_to_img, geometry, **options)
    else:
        thumbnail = None
    thumbnail_is_missing = not thumbnail or isinstance(thumbnail, DummyImageFile)
    if thumbnail_is_missing:
        if stub_factory:
            thumbnail = stub_factory(geometry=geometry)
        else:
            thumbnail = None  # DummyImageFile -> None
    return thumbnail
