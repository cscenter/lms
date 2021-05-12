
from core.locks import acquire_cache_lock, cache_lock


def test_do_not_release_after_timeout():
    lock_name = 'test_lock_name'
    with cache_lock(lock_name, timeout=0):
        # We can immediately acquire a lock with the same name
        assert acquire_cache_lock(lock_name, 5)
    # Lock shouldn't be released on exit from the context manager above
    assert not acquire_cache_lock(lock_name, 5)
