"""
Make sure default cache manager is treated as a single cache
"""

import contextlib
import logging
import time
from copy import deepcopy
from functools import wraps

from django_rq.queues import get_connection, get_redis_connection
from redis.exceptions import LockError

from django.core.cache import caches
from django.core.cache.backends.locmem import LocMemCache

logger = logging.getLogger(__name__)


DEFAULT_CACHE_ALIAS = 'default'
LOCK_CACHE_KEY = 'core.locks.{}'


class CacheLockError(Exception):
    pass


def get_shared_connection():
    """
    This redis connection is shared among all projects
    """
    from django_rq.settings import QUEUES
    config = deepcopy(QUEUES['default'])
    config['DB'] = 0
    return get_redis_connection(config)


def distributed_lock(name, blocking_timeout=3, timeout=None,
                     get_client=None, **options):
    """
    Acquire a redis lock within **blocking_timeout** seconds before
    executing the decorated function and hold it for no more than the given
    **timeout** period, in seconds (default `None` means lock will be
    hold until release). Do nothing if lock is not acquired within the given time.

    By default it uses connection from the `default` redis task queue.
    """

    def distributed_lock_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            redis_client = get_client() if get_client else get_connection()
            try:
                with redis_client.lock(name,
                                       timeout=timeout,
                                       blocking_timeout=blocking_timeout,
                                       **options):
                    return func(*args, **kwargs)
            except LockError as e:
                logger.info(str(e))
        return wrapper
    return distributed_lock_decorator


def acquire_cache_lock(name: str, timeout: int, cache=None):
    """
    Acquire a lock and hold it for no more than the given `timeout`
    period, in seconds.

    Returns True if the lock was acquired, False otherwise.
    """
    if cache is None:
        cache = caches[DEFAULT_CACHE_ALIAS]
    return cache.add(LOCK_CACHE_KEY.format(name), 1, timeout)


def release_cache_lock(name, cache=None):
    if cache is None:
        cache = caches[DEFAULT_CACHE_ALIAS]
    cache.delete(LOCK_CACHE_KEY.format(name))


@contextlib.contextmanager
def cache_lock(name, timeout, exception=None, cache=None):
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
    if not acquire_cache_lock(name, timeout, cache):
        logging.warning('Unable to acquire lock: %s', name)
        raise exception or CacheLockError(name)
    time_acquired = time.time()
    try:
        yield
    finally:
        if time.time() <= time_acquired + timeout:
            release_cache_lock(name, cache)
