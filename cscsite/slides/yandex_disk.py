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
        if not client.check(path):
            client.mkdir(path)


def upload_slides(local_file, path, academic_year, retries=3):
    options = {
        'webdav_hostname': "https://webdav.yandex.ru",
        'webdav_login': settings.YANDEX_DISK_USERNAME,
        'webdav_password': settings.YANDEX_DISK_PASSWORD
    }
    client = wc.Client(options)

    local_path = local_file.name
    academic_period = "{}-{}".format(academic_year, academic_year + 1)
    remote_path = posixpath.join(settings.YANDEX_DISK_SLIDES_ROOT,
                                 academic_period,
                                 path)
    try:
        if client.check(remote_path):
            logger.debug("Resource {} already exists".format(remote_path))
            return
    except wc.MethodNotSupported:
        # Webdav client can raise `MethodNotSupported` exception here
        # even on 404 HTTP status. To avoid this we should recursively check
        # existence of each directory in the path or just ignore
        # this type of error due to yandex webdav api supports PROPFIND
        pass
    except wc.WebDavException as e:
        logger.error(e)
        return

    exc = None
    for i in range(retries):
        try:
            mkdirs(client, remote_path)
            client.upload_sync(remote_path=remote_path, local_path=local_path)
        except wc.WebDavException as webdav_exc:
            exc = webdav_exc
        else:
            logger.debug("Slides successfully uploaded on Yandex.Disk "
                         "to {}".format(remote_path))
            return
    logger.error(exc)
