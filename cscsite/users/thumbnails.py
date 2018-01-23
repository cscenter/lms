from django.contrib.staticfiles.storage import staticfiles_storage
from sorl.thumbnail.images import BaseImageFile


class BaseStubImage(BaseImageFile):
    url = staticfiles_storage.url("img/center/profile_no_photo.png")

    def __init__(self, **kwargs):
        geometry = kwargs.get("geometry", None)
        if geometry:
            self.size = geometry.split("x")
        else:
            self.size = 175, 238

    def exists(self):
        return True


class GirlStubImage(BaseStubImage):
    url = staticfiles_storage.url("img/csc_girl.svg")


class BoyStubImage(BaseStubImage):
    url = staticfiles_storage.url("img/csc_boy.svg")
