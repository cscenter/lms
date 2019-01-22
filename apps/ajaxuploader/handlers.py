"""
FIXME: What the heck is going on here? Handlers are look totally broken.
"""

import logging

from io import BytesIO
from PIL import Image

from django.core.files.uploadhandler import MemoryFileUploadHandler, \
    StopUpload, TemporaryFileUploadHandler

logger = logging.getLogger(__name__)





class FileSizeUploadHandlerMixin:
    pass



class MimeTypeUploadHandlerMixin:
    """
    Read the file mime type from the file header before uploading
    the whole file. Stop uploading if mime type is not allowed.
    """
    FILE_UPLOAD_MAX_SIZE = 5242880  # 5 Mb

    ALLOWED_MIME_TYPES = [
        'image/jpeg',
        'image/png'
    ]

    # FIXME: это уже другой mixin, нужно разнести их
    def handle_raw_input(self, input_data, META, content_length, boundary,
                         encoding=None):
        # Check the content-length header to see if we should
        if content_length > self.FILE_UPLOAD_MAX_SIZE:
            self.stop_upload = True
        else:
            self.stop_upload = False
        super().handle_raw_input(input_data, META, content_length, boundary,
                                 encoding)

    def new_file(self, *args, **kwargs):
        if self.stop_upload:
            raise StopUpload
        super().new_file(*args, **kwargs)

    def receive_data_chunk(self, raw_data, start):
        # On first chunk data try to detect mime type and validate it.
        is_first_chunk = (start == 0)
        if is_first_chunk and not self.is_valid_mime_type(raw_data):
            raise StopUpload
        return super().receive_data_chunk(raw_data, start)

    # FIXME: and where do you read mime type? idiot
    def is_valid_mime_type(self, chunk):
        try:
            # Lazy open image and read headers
            im = Image.open(BytesIO(chunk))
            im.close()
            return True
        except IOError:
            logger.debug("PIL can't open file and read image headers")
        return False


class MemoryImageUploadHandler(MimeTypeUploadHandlerMixin,
                               MemoryFileUploadHandler):
    pass


class TemporaryImageUploadHandler(MimeTypeUploadHandlerMixin,
                                  TemporaryFileUploadHandler):
    pass
