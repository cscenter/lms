# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging

from io import BytesIO
from PIL import Image

from django.core.files.uploadhandler import MemoryFileUploadHandler, \
    StopUpload, TemporaryFileUploadHandler

logger = logging.getLogger(__name__)


class ImageUploadHandlerMixin(object):
    """Stop upload if mime type not allowed."""
    FILE_UPLOAD_MAX_SIZE = 5242880  # 5 Mb

    ALLOWED_MIME_TYPES = [
        'image/jpeg',
        'image/png'
    ]

    def handle_raw_input(self, input_data, META, content_length, boundary,
                         encoding=None):
        # Check the content-length header to see if we should
        if content_length > self.FILE_UPLOAD_MAX_SIZE:
            self.stop_upload = True
        else:
            self.stop_upload = False
        super(ImageUploadHandlerMixin, self).handle_raw_input(input_data,
                                                              META,
                                                              content_length,
                                                              boundary,
                                                              encoding)

    def new_file(self, *args, **kwargs):
        # TODO: Maybe should raise custom exception
        if self.stop_upload:
            raise StopUpload
        super(ImageUploadHandlerMixin, self).new_file(*args, **kwargs)

    def receive_data_chunk(self, raw_data, start):
        # On first chunk data try to detect mime type and validate it.
        is_first_chunk = (start == 0)
        if is_first_chunk and not self.is_valid_mime_type(raw_data):
            raise StopUpload
        return super(ImageUploadHandlerMixin, self).receive_data_chunk(raw_data,
                                                                       start)

    def is_valid_mime_type(self, chunk):
        try:
            # Lazy open image and read headers
            im = Image.open(BytesIO(chunk))
            im.close()
            return True
        except IOError:
            logger.debug("PIL can't open file and read image headers")
        return False


class MemoryImageUploadHandler(ImageUploadHandlerMixin,
                               MemoryFileUploadHandler):
    pass


class TemporaryImageUploadHandler(ImageUploadHandlerMixin,
                                  TemporaryFileUploadHandler):
    pass
