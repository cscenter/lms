import logging
import posixpath

import webdav3.client as wc
from webdav3.exceptions import WebDavException

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class UploadSlidesError(Exception):
    pass


REQUIRED_SETTINGS = [
    "YANDEX_DISK_USERNAME",
    "YANDEX_DISK_PASSWORD",
    "YANDEX_DISK_SLIDES_ROOT"
]
for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            "Please add {0!r} to your settings module".format(attr))


def mkdirs(client, path):
    """Makes all intermediate-level directories before save file"""
    if path == posixpath.sep:
        return

    mkdirs(client, posixpath.dirname(path))
    _, ext = posixpath.splitext(path)
    if not ext:
        if not client.check(path):
            client.mkdir(path)


def upload_file(webdav_client, local_path, remote_path, retries=3):
    try:
        if webdav_client.check(remote_path):
            logger.debug("Resource {} already exists".format(remote_path))
            return
    except wc.MethodNotSupported:
        # Webdav client can raise `MethodNotSupported` exception here
        # even on 404 HTTP status. To avoid this we should recursively check
        # existence of each directory in the path or just ignore
        # this type of error due to yandex webdav api supports PROPFIND
        pass
    except WebDavException as e:
        logger.error(e)
        return

    exc = None
    for i in range(retries):
        try:
            mkdirs(webdav_client, remote_path)
            webdav_client.upload_sync(remote_path=remote_path, local_path=local_path)
        except WebDavException as webdav_exc:
            exc = webdav_exc
        else:
            logger.debug("Slides successfully uploaded on Yandex.Disk "
                         "to {}".format(remote_path))
            return
    msg = f"Failed to upload slides {local_path} on Yandex.Disk {remote_path}"
    raise UploadSlidesError(msg) from exc
    # logger.error(exc)
