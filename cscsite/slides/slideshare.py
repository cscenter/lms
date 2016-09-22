# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
import mimetypes
import os.path
try:
    # For Python 3.0 and later
    from urllib.error import URLError
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import URLError

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from slideshare.client import SlideShareAPI, SlideShareError


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
    return SlideShareAPI(api_key=settings.SLIDESHARE_API_KEY,
                         shared_secret=settings.SLIDESHARE_SECRET,
                         username=settings.SLIDESHARE_USERNAME,
                         password=settings.SLIDESHARE_PASSWORD)


def upload_slides(handle, title, description, tags):
    """Used in `maybe_upload_slides_slideshare` task"""
    api = get_api()
    path_to_file = handle.name
    try:
        sls = api.upload_slideshow(
            slideshow_title=title,
            slideshow_srcfile=path_to_file,
            slideshow_description=description,
            slideshow_tags=[tag for tag in tags])
        sl_id = sls["SlideShowUploaded"]["SlideShowID"]
        sl_meta = api.get_slideshow(sl_id)
        return sl_meta["Slideshow"]["URL"]
    except (SlideShareError, URLError) as e:
        logger.error(e)
        # Reraise to save exception in failed jobs queue also
        raise
