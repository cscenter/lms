from django.contrib.staticfiles.storage import staticfiles_storage
from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.images import BaseImageFile, DummyImageFile

from users.constants import ThumbnailSizes


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
    # FIXME: create get_thumbnail with stub_factory keyword arg, rewrite this one
    path_to_img = getattr(user, "photo", None)
    # Default crop settings
    if "crop" not in options:
        options["crop"] = "center top"
    if "cropbox" not in options:
        options["cropbox"] = user.photo_thumbnail_cropbox()
    if path_to_img:
        thumbnail = get_thumbnail(path_to_img, geometry, **options)
    else:
        thumbnail = None
    # TODO: Override default DummyImageFile?
    if not thumbnail and use_stub:
        if user.gender == user.GENDER_MALE:
            factory = ManStubImage if stub_official else BoyStubImage
        elif user.gender == user.GENDER_FEMALE:
            factory = WomanStubImage if stub_official else GirlStubImage
        else:
            factory = BaseStubImage
        thumbnail = factory(geometry=geometry)
    return thumbnail
