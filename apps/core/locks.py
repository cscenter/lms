"""
Make sure default cache manager is treated as a single cache
"""

import contextlib
import logging
import time

from django.core.cache import caches
from django.core.cache.backends.locmem import LocMemCache

logger = logging.getLogger(__name__)


DEFAULT_CACHE_ALIAS = 'default'
LOCK_CACHE_KEY = 'core.locks.{}'


class LockError(Exception):
    pass


def acquire_lock(name: str, timeout: int, cache=None):
    """
    Acquire a lock and hold it for no more than the given `timeout`
    period, in seconds.

    Returns True if the lock was acquired, False otherwise.
    """
    if cache is None:
        cache = caches[DEFAULT_CACHE_ALIAS]
    return cache.add(LOCK_CACHE_KEY.format(name), 1, timeout)


def release_lock(name, cache=None):
    if cache is None:
        cache = caches[DEFAULT_CACHE_ALIAS]
    cache.delete(LOCK_CACHE_KEY.format(name))


@contextlib.contextmanager
def lock(name, timeout, exception=None, cache=None):
    """
    Cache based implementation of lock context manager.
    Acquire a lock on process/machine level by specifying different
    cache backend.
    """
    if cache is None:
        cache = caches[DEFAULT_CACHE_ALIAS]
    if isinstance(cache, LocMemCache):
        logger.warning("LocMemCache is per-process. Configure cache "
                       "backend for locking at per-machine level")
    if not acquire_lock(name, timeout, cache):
        logging.warning('Unable to acquire lock: %s', name)
        raise exception or LockError(name)
    time_acquired = time.time()
    try:
        yield
    finally:
        if time.time() <= time_acquired + timeout:
            release_lock(name, cache)
