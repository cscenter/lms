# -*- coding: utf-8 -*-

import logging
import posixpath

import yandexwebdav
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

REQUIRED_SETTINGS = [
    "YANDEX_DISK_USERNAME",
    "YANDEX_DISK_PASSWORD",
    "YANDEX_DISK_SLIDES_ROOT"
]

for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            "Please add {0!r} to your settings module".format(attr))


logger = logging.getLogger(__name__)


def mkdirs(config, path):
    if path == posixpath.sep:
        return

    mkdirs(config, posixpath.dirname(path))
    _, ext = posixpath.splitext(path)
    if not ext:
        try:
            config.list(path)
        except yandexwebdav.ConnectionException:
            config.mkdir(path)


def upload_slides(handle, path, retries=5):
    config = yandexwebdav.Config({
        "user": settings.YANDEX_DISK_USERNAME,
        "password": settings.YANDEX_DISK_PASSWORD
    })

    path = posixpath.join(settings.YANDEX_DISK_SLIDES_ROOT, path)

    exc = None
    for i in range(retries):
        try:
            mkdirs(config, path)

            # FIXME(lebedev): check if file exists.
            config.upload(handle.name, path)
        except yandexwebdav.ConnectionException as connection_exc:
            exc = connection_exc
        else:
            return

    logger.error(exc)
