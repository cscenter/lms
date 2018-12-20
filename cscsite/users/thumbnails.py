from django.contrib.staticfiles.storage import staticfiles_storage
from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.images import BaseImageFile, DummyImageFile


class BaseStubImage(BaseImageFile):
    @property
    def url(self):
        return staticfiles_storage.url("v1/img/center/profile_no_photo.png")

    def __init__(self, **kwargs):
        geometry = kwargs.get("geometry", None)
        if geometry:
            self.size = geometry.split("x")
        else:
            self.size = 175, 238

    def exists(self):
        return True


class GirlStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url("v1/img/csc_girl.svg")


class BoyStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url("v1/img/csc_boy.svg")


def get_user_thumbnail(user, geometry, use_stub=True, **options):
    path_to_img = getattr(user, "photo", None)
    # Default crop settings
    if "crop" not in options:
        options["crop"] = "center top"
    if "cropbox" not in options:
        options["cropbox"] = user.photo_thumbnail_cropbox()
    thumbnail = get_thumbnail(path_to_img, geometry, **options)
    if not thumbnail or isinstance(thumbnail, DummyImageFile):
        if use_stub:
            if not user.is_teacher and user.gender == user.GENDER_MALE:
                factory = BoyStubImage
            elif not user.is_teacher and user.gender == user.GENDER_FEMALE:
                factory = GirlStubImage
            else:
                factory = BaseStubImage
            thumbnail = factory(geometry=geometry)
        else:
            thumbnail = None
    return thumbnail
