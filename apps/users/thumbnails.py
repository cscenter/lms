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


class BoyStubV2Image(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url("v2/img/placeholder/boy.png")


class GirlStubV2Image(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url("v2/img/placeholder/girl.png")


class ManStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url("v2/img/placeholder/man.png")


class WomanStubImage(BaseStubImage):
    @property
    def url(self):
        return staticfiles_storage.url("v2/img/placeholder/woman.png")


def get_user_thumbnail(user, geometry, use_stub=True, new_stub=False,
                       stub_official=True, **options):
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
    if not thumbnail and use_stub:
        if not new_stub:
            if not user.is_teacher and user.gender == user.GENDER_MALE:
                factory = BoyStubImage
            elif not user.is_teacher and user.gender == user.GENDER_FEMALE:
                factory = GirlStubImage
            else:
                factory = BaseStubImage
        else:
            if user.gender == user.GENDER_MALE:
                factory = ManStubImage if stub_official else BoyStubV2Image
            elif user.gender == user.GENDER_FEMALE:
                factory = WomanStubImage if stub_official else GirlStubV2Image
            else:
                factory = BaseStubImage
        thumbnail = factory(geometry=geometry)
    return thumbnail
