# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.images import DummyImageFile

from ajaxuploader.uploadhandler import MemoryImageUploadHandler, \
    TemporaryImageUploadHandler
from ajaxuploader.utils import photo_thumbnail_cropbox
from users.settings import PROFILE_THUMBNAIL_WIDTH, PROFILE_THUMBNAIL_HEIGHT
from users.models import User

try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django.http import HttpResponseBadRequest, JsonResponse


from ajaxuploader.backends import ProfileImageUploadBackend
from ajaxuploader.signals import file_uploaded


class AjaxProfileImageUploader(generic.base.View):
    http_method_names = ['post']

    def __init__(self, backend=None, **kwargs):
        super(AjaxProfileImageUploader, self).__init__(**kwargs)
        if backend is None:
            backend = ProfileImageUploadBackend
        self.get_backend = lambda: backend(**kwargs)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """
        Custom upload handlers which validates mime type on first chunk.
        Disable csrf verification to prevent read form data, then add handlers.
        """
        request.upload_handlers = [MemoryImageUploadHandler(request),
                                   TemporaryImageUploadHandler(request)]
        return self._dispatch(request, *args, **kwargs)

    @method_decorator(csrf_protect)
    def _dispatch(self, request, *args, **kwargs):
        return super(AjaxProfileImageUploader, self).dispatch(request, *args,
                                                              **kwargs)

    @staticmethod
    def _save_crop_data(request, user):
        attrs = ("width", "height", "x", "y")
        # TODO: add long story validation with unbound coords and width=img.width
        try:
            data = {attr: int(float(request.POST.get(attr))) for attr in
                      attrs}
        except (KeyError, ValueError):
            return False

        # Generate thumbnail
        photo_geometry = "{}x{}".format(PROFILE_THUMBNAIL_WIDTH,
                                        PROFILE_THUMBNAIL_HEIGHT)
        # FIXME: Check that img stil exist?
        thumbnail = get_thumbnail(user.photo.path, photo_geometry,
                                  crop='center',
                                  cropbox=photo_thumbnail_cropbox(data))
        if not thumbnail or isinstance(thumbnail, DummyImageFile):
            ret_json = {"success": False,
                        "reason": "Thumbnail generation error"}
        else:
            user.cropbox_data = data
            user.save()
            ret_json = {"success": True, "thumbnail": thumbnail.url}
        return ret_json

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated or "user_id" not in request.POST:
            return HttpResponseBadRequest("Bad user")

        try:
            user_id = request.POST["user_id"]
            if not request.user.is_curator:
                user_id = request.user.pk
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return HttpResponseBadRequest("Bad user")

        if "crop_data" in request.POST:
            ret_json = self._save_crop_data(request, user)
            return JsonResponse(ret_json)

        if len(request.FILES) > 1:
            return HttpResponseBadRequest("Multi upload not supported")

        if len(request.FILES) == 1:
            upload = list(request.FILES.values())[0]
        else:
            return HttpResponseBadRequest("Check file format and size")

        try:
            _filename = request.POST['_photo']
            _, file_extension = _filename.rsplit(".", 1)
            filename = "{}.{}".format(str(user_id), file_extension)
        except KeyError:
            return HttpResponseBadRequest("Photo not found")

        backend = self.get_backend()
        # custom filename handler
        filename = (backend.update_filename(request, filename, *args, **kwargs)
                    or filename)
        # save empty file
        backend.setup(filename, *args, **kwargs)
        is_raw = False
        success = backend.upload(upload, filename, is_raw, *args, **kwargs)

        if success:
            user.photo.name = filename
            user.cropbox_data = {}
            user.save()
            # send signals
            file_uploaded.send(sender=self.__class__, backend=backend,
                               request=request)

        # callback
        extra_context = backend.upload_complete(request, filename, *args,
                                                **kwargs)

        # TODO: generate default crop settings and return them
        ret_json = {'success': success, 'filename': filename}
        if extra_context is not None:
            ret_json.update(extra_context)

        return JsonResponse(ret_json)
