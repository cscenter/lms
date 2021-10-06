import hashlib
import json
import re

from django.core.cache import cache

HASH_LEN = 16 + 1
HASH_N = 100
HASH_MAX_TTL = 600  # in seconds
CACHE_KEY = 'comment_persistence'


def add_to_gc(comment_text: str) -> None:
    """
    After comment was saved to the persistent data storage mark it as not
    'in-use' for the client garbage collector.
    """
    nowhite_text = re.sub(r"\s+", '', comment_text)
    comment_md5 = hashlib.md5(nowhite_text.encode('utf-8')).hexdigest()
    # NOTE(Dmitry): there is a race here, but it shouldn't matter
    old_md5s = cache.get(CACHE_KEY, "")
    new_md5s = "{}|{}".format(comment_md5, old_md5s[:(HASH_LEN * HASH_N)])
    cache.set(CACHE_KEY, new_md5s, HASH_MAX_TTL)


def get_garbage_collection() -> str:
    hashes = cache.get(CACHE_KEY, "").split("|")
    return json.dumps({h: 0 for h in hashes if h})
