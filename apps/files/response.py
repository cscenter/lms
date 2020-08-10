import os

from django.http import HttpResponse


class XAccelRedirectFileResponse(HttpResponse):
    """
    Files under `media/assignments/` location are protected by nginx `internal`
    directive and could be returned by providing `X-Accel-Redirect`
    response header.
    Without this header the client error 404 (Not Found) is returned.
    Note:
        FileSystemStorage is a default storage for the local media/ directory.
    """
    def __init__(self, file_uri, content_disposition='inline', **kwargs):
        """
        file_uri (X-Accel-Redirect header value) is a URL where the contents
        of the file can be accessed if `internal` directive wasn't set.
        In case of FileSystemStorage this URL starts with
        `settings.MEDIA_URL` value.
        """
        super().__init__(**kwargs)
        if content_disposition == 'attachment':
            # FIXME: Does it necessary to delete content type here?
            del self['Content-Type']
            file_name = os.path.basename(file_uri)
            # XXX: Content-Disposition doesn't have appropriate non-ascii
            # symbols support
            self['Content-Disposition'] = f"attachment; filename={file_name}"
        self['X-Accel-Redirect'] = file_uri
