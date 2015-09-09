# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
import mimetypes
import os.path
import urllib2

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_bytes
from slideshare import SlideshareAPI, SlideShareServiceError


logger = logging.getLogger(__name__)


REQUIRED_SETTINGS = [
    "SLIDESHARE_API_KEY",
    "SLIDESHARE_SECRET",
    "SLIDESHARE_USERNAME",
    "SLIDESHARE_PASSWORD"
]

for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            "Please add {0!r} to your settings module".format(attr))


def get_api():
    return SlideshareAPI(settings.SLIDESHARE_API_KEY,
                         settings.SLIDESHARE_SECRET)


def upload_slides(handle, title, description, tags):
    api = get_api()

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
        return sl_meta["Slideshow"]["URL"]
    except (SlideShareServiceError, urllib2.URLError) as e:
        logger.error(e)
        return ""
