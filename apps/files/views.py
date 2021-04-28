import os
from abc import ABC, abstractmethod

from nbformat.validator import NotebookValidationError

from django.conf import settings
from django.http import (
    HttpResponseBadRequest, HttpResponseNotFound, HttpResponseRedirect
)
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from files.response import XAccelRedirectFileResponse
from files.utils import convert_ipynb_to_html


class ProtectedFileDownloadView(ABC, PermissionRequiredMixin, generic.View):
    """
    This view checks permissions of the authenticated user before
    downloading the protected file.

    Supports S3 for the remotely stored files and file system storage for
    the locally stored. Local files are distributed by nginx `X-Accel-Redirect`
    feature.
    """
    @property
    @abstractmethod
    def file_field_name(self):
        """Returns a file field name of the protected object"""
        pass

    @abstractmethod
    def get_protected_object(self):
        """Protected object contains a file stored in a private storage"""
        raise NotImplementedError()

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.protected_object = self.get_protected_object()

    def get_permission_object(self):
        return self.protected_object

    def get_file_field(self):
        return getattr(self.protected_object, self.file_field_name, None)

    def get(self, request, *args, **kwargs):
        if self.protected_object is None:
            return HttpResponseNotFound()

        file_field = self.get_file_field()
        if file_field is None:
            return HttpResponseNotFound()

        # FIXME: preprocess ipynb files and save locally or in S3!
        if settings.USE_CLOUD_STORAGE:
            signed_url = file_field.url
            if getattr(settings, "PROXYING_REMOTE_FILES", False):
                from urllib.parse import urlparse
                protocol = urlparse(signed_url).scheme
                url = signed_url.replace(protocol + '://', '')
                remote_file_location = f'/remote-files/{protocol}/{url}'
                content_disposition = 'attachment'
                return XAccelRedirectFileResponse(remote_file_location,
                                                  content_disposition)
            else:
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
        return XAccelRedirectFileResponse(media_file_uri, content_disposition)
