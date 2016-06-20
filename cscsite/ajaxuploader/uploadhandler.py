# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import magic
from django.core.files.uploadhandler import MemoryFileUploadHandler, \
    StopUpload, TemporaryFileUploadHandler


class ImageUploadHandlerMixin(object):
    """Stop upload if mime type not allowed."""
    ALLOWED_MIME_TYPES = [
        'image/jpeg',
        'image/png'
    ]

    def receive_data_chunk(self, raw_data, start):
        # On first chunk data try to detect mime type and validate it.
        is_first_chunk = (start == 0)
        if is_first_chunk and not self.is_valid_mime_type(raw_data):
            raise StopUpload
        return super(ImageUploadHandlerMixin, self).receive_data_chunk(raw_data,
                                                                       start)

    def is_valid_mime_type(self, chunk):
        try:
            mime = magic.from_buffer(chunk, mime=True)
            # FIXME: Replace with simple .startswith('image/')?
            if mime in self.ALLOWED_MIME_TYPES:
                return True
        except magic.MagicException:
            # TODO: add logger
            pass
        return False


class MemoryImageUploadHandler(ImageUploadHandlerMixin,
                               MemoryFileUploadHandler):
    pass


class TemporaryImageUploadHandler(ImageUploadHandlerMixin,
                                  TemporaryFileUploadHandler):
    pass
