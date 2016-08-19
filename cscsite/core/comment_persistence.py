# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import json
import hashlib
import re

from django.core.cache import cache


HASH_LEN = 16 + 1
HASH_N = 100
HASH_MAX_TTL = 60 * 10
CACHE_KEY = 'comment_persistence'


def report_saved(comment_text):
    nowhite_text = re.sub('\s+', '', comment_text)
    comment_md5 = hashlib.md5(nowhite_text.encode('utf-8')).hexdigest()
    # NOTE(Dmitry): there is a race here, but it shouldn't matter
    old_md5s = cache.get(CACHE_KEY, "")
    new_md5s = "{}|{}".format(comment_md5, old_md5s[:(HASH_LEN * HASH_N)])
    cache.set(CACHE_KEY, new_md5s, HASH_MAX_TTL)


def get_hashes_json():
    hashes = cache.get(CACHE_KEY, "").split("|")
    return json.dumps({h: 0 for h in cache.get(CACHE_KEY, "").split("|") if h})
