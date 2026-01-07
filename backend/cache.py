import time
from threading import Lock

_cache = {}
_lock = Lock()


def set_cache(key: str, value, ttl: int = 300):
    expires = time.time() + ttl
    with _lock:
        _cache[key] = (expires, value)


def get_cache(key: str):
    with _lock:
        item = _cache.get(key)
        if not item:
            return None
        expires, value = item
        if time.time() < expires:
            return value
        # expired
        del _cache[key]
        return None


def clear_cache():
    with _lock:
        _cache.clear()
