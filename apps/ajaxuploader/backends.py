import os

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.timezone import now
from sorl.thumbnail import delete


# FIXME: Do we really need this?
class AbstractUploadBackend:
    BUFFER_SIZE = 10485760  # 10MB

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def setup(self, filename, *args, **kwargs):
        """
        Responsible for doing any pre-processing needed before the upload
        starts.
        """

    def update_filename(self, request, filename, *args, **kwargs):
        """
        Returns a new name for the file being uploaded.
        """

    def upload_chunk(self, chunk, *args, **kwargs):
        """
        Called when a string was read from the client, responsible for
        writing that string to the destination file.
        """
        raise NotImplementedError

    def upload_complete(self, request, filename, *args, **kwargs):
        """
        Override to performs any actions needed post-upload, and returns
        a dict to be added to the render / json context
        """

    def upload(self, uploaded, filename, raw_data, *args, **kwargs):
        try:
            if raw_data:
                # File was uploaded via ajax, and is streaming in.
                chunk = uploaded.read(self.BUFFER_SIZE)
                while len(chunk) > 0:
                    self.upload_chunk(chunk, *args, **kwargs)
                    chunk = uploaded.read(self.BUFFER_SIZE)
            else:
                # File was uploaded via a POST, and is here.
                for chunk in uploaded.chunks():
                    self.upload_chunk(chunk, *args, **kwargs)
            return True
        except (IOError, OSError):
            # things went badly.
            return False


class DefaultStorageUploadBackend(AbstractUploadBackend):
    """
    Uses Django's default storage backend to store the uploaded files
    see https://docs.djangoproject.com/en/dev/topics/files/#file-storage
    https://docs.djangoproject.com/en/dev/howto/custom-file-storage/
    """

    UPLOAD_DIR = getattr(settings, "UPLOAD_DIR", "upload")

    def _get_upload_dir(self):
        if callable(self.UPLOAD_DIR):
            return self.UPLOAD_DIR()
        return now().strftime(self.UPLOAD_DIR)

    def setup(self, filename, *args, **kwargs):
        # join UPLOAD_DIR with filename.
        new_path = os.path.join(self._get_upload_dir(), filename)

        # save empty file in default storage with path = new_path
        self.path = default_storage.save(new_path, ContentFile(''))

        # create BufferedWriter for new file
        self._dest = default_storage.open(self.path, mode='wb')

    def upload(self, uploaded, filename, raw_data, *args, **kwargs):
        try:
            for chunk in uploaded.chunks():
                self.upload_chunk(chunk, *args, **kwargs)
            return True
        except (IOError, OSError):
            return False

    def upload_chunk(self, chunk, *args, **kwargs):
        self._dest.write(chunk)

    def upload_complete(self, request, filename, *args, **kwargs):
        """Returns file path relative to MEDIA_ROOT"""
        self._dest.close()
        return {"path": self.path}


class ProfileImageUploadBackend(DefaultStorageUploadBackend):
    UPLOAD_DIR = getattr(settings, "UPLOAD_DIR", "profile")

    def update_filename(self, request, filename, *args, **kwargs):
        # join UPLOAD_DIR with filename.
        return os.path.join(self._get_upload_dir(), filename)

    def setup(self, filename, *args, **kwargs):
        # save empty file in default storage with path = new_path
        if default_storage.exists(filename):
            # Clear sorl-thumbnail cache and delete file
            delete(filename, delete_file=True)
        self.path = default_storage.save(filename, ContentFile(''))

        # create BufferedWriter for new file
        self._dest = default_storage.open(self.path, mode='wb')

    def upload_complete(self, request, filename, *args, **kwargs):
        """Returns image url"""
        self._dest.close()
        path_to_img = os.path.join(settings.MEDIA_URL, self.path)
        return {"url": path_to_img}
