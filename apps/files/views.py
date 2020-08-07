import os

from django.conf import settings
from django.http import HttpResponseNotFound, HttpResponseBadRequest, \
    HttpResponseRedirect
from django.views import generic
from nbformat.validator import NotebookValidationError

from auth.mixins import PermissionRequiredMixin
from files.response import ProtectedLocalFileResponse
from learning.utils import convert_ipynb_to_html


class ProtectedFileDownloadView(PermissionRequiredMixin, generic.View):
    """
    This view checks permissions of the authenticated user before
    downloading the protected file.

    Supports S3 for the remotely stored files and file system storage for
    the locally stored. Local files are distributed by nginx `X-Accel-Redirect`
    feature.
    """
    FILE_FIELD_NAME = None  # of the protected object

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.protected_object = self.get_protected_object()

    def get_protected_object(self):
        """Protected object contains a file stored in a private storage"""
        raise NotImplementedError()

    def get_permission_object(self):
        return self.protected_object

    def get_file_field(self):
        return getattr(self.protected_object, self.FILE_FIELD_NAME, None)

    def get(self, request, *args, **kwargs):
        if self.protected_object is None:
            return HttpResponseNotFound()

        file_field = self.get_file_field()
        if file_field is None:
            return HttpResponseNotFound()

        # FIXME: preprocess ipynb files and save locally or in S3!
        if settings.USE_S3_FOR_UPLOAD:
            signed_url = file_field.url
            return HttpResponseRedirect(redirect_to=signed_url)
        else:
            return self.get_local_private_file(file_field)

    def get_local_private_file(self, file_field):
        media_file_uri = file_field.url
        content_disposition = 'attachment'
        # Convert *.ipynb to html
        if self.request.GET.get("html", False):
            _, ext = os.path.splitext(media_file_uri)
            if ext == ".ipynb":
                ipynb_src_path = file_field.path
                html_ext = ".html"
                html_dest_path = ipynb_src_path + html_ext
                try:
                    exported = convert_ipynb_to_html(ipynb_src_path,
                                                     html_dest_path)
                except NotebookValidationError as e:
                    return HttpResponseBadRequest(e.message)
                if exported:
                    media_file_uri = media_file_uri + html_ext
                    content_disposition = 'inline'
        return ProtectedLocalFileResponse(media_file_uri, content_disposition)
