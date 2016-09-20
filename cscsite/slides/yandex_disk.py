# -*- coding: utf-8 -*-

import logging
import posixpath
import webdav.client as wc

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

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
        try:
            client.list(path)
        except wc.RemoteParentNotFound:
            client.mkdir(path)


def upload_slides(handle, path, retries=3):
    options = {
        'webdav_hostname': "https://webdav.yandex.ru",
        'webdav_login': settings.YANDEX_DISK_USERNAME,
        'webdav_password': settings.YANDEX_DISK_PASSWORD
    }
    client = wc.Client(options)

    path = posixpath.join(settings.YANDEX_DISK_SLIDES_ROOT, path)

    exc = None
    for i in range(retries):
        try:
            mkdirs(client, path)

            client.upload_sync(remote_path=path, local_path=handle.name)
        except wc.WebDavException as webdav_exc:
            exc = webdav_exc
        else:
            return
    logger.error(exc)
