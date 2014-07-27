# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
import mimetypes
import os.path
import posixpath
import re
import urllib2
from cStringIO import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_bytes

import yandexwebdav
from slideshare import SlideshareAPI, SlideShareServiceError

logger = logging.getLogger(__name__)


REQUIRED_SETTINGS = [
    "SLIDESHARE_API_KEY",
    "SLIDESHARE_SECRET",
    "SLIDESHARE_USERNAME",
    "SLIDESHARE_PASSWORD",
    "YANDEX_DISK_USERNAME",
    "YANDEX_DISK_PASSWORD",
    "YANDEX_DISK_SLIDES_ROOT"
]

for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            "Please add {0!r} to your settings module".format(attr))


def upload_to_slideshare(handle, title, description, tags):
    api = SlideshareAPI(settings.SLIDESHARE_API_KEY,
                        settings.SLIDESHARE_SECRET)

    # Note(lebedev): unfortunately 'slideshare' has no idea about
    # unicode strings, so we have to force everything to be bytes.
    mimetype, _ = mimetypes.guess_type(handle.name)
    srcfile = {
        "filename": force_bytes(os.path.basename(handle.name)),
        "mimetype": mimetype,
        "filehandle": handle
    }

    try:
        sls = api.upload_slideshow(
            settings.SLIDESHARE_USERNAME, settings.SLIDESHARE_PASSWORD,
            slideshow_title=force_bytes(title),
            slideshow_srcfile=srcfile,
            slideshow_description=force_bytes(description),
            slideshow_tags=[force_bytes(tag) for tag in tags])
        sl_id = sls["SlideShowUploaded"]["SlideShowID"]
        sl_meta = api.get_slideshow(sl_id)
        html = sl_meta["Slideshow"]["Embed"]

        # SlideShare adds an extra link to the embed HTML, we don't
        # need it.
        return re.sub(r"<div[^>]+>.+$", "", html)
    except (SlideShareServiceError, urllib2.URLError) as e:
        logger.error(e)
        return ""


def upload_to_yandex(handle):
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

    config = yandexwebdav.Config({
        "user": settings.YANDEX_DISK_USERNAME,
        "password": settings.YANDEX_DISK_PASSWORD
    })

    # FIXME(lebedev): this won't work with custom storage.
    # We expect handle path to be of form '.../<course>/<slides.pdf>'.
    course_uri = os.path.basename(os.path.dirname(handle.name))
    file_name = os.path.basename(handle.name)
    path = posixpath.join(settings.YANDEX_DISK_SLIDES_ROOT,
                          course_uri, file_name)

    try:
        mkdirs(config, path)

        # FIXME(lebedev): check if file exists.
        config.upload(handle.name, path)
    except yandexwebdav.ConnectionException as e:
        logger.error(e)
