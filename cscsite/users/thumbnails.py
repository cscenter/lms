from django.contrib.staticfiles.storage import staticfiles_storage
from sorl.thumbnail.images import BaseImageFile


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
