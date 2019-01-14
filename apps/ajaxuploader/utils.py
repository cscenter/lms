# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals


def photo_thumbnail_cropbox(data):
    try:
        return ",".join(map(str, (
            data["x"],
            data["y"],
            data["x"] + data["width"],
            data["y"] + data["height"],
        )))
    except KeyError:
        return ""
