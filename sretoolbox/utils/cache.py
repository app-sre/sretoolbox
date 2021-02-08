"""
Caching helper decorator
"""

import functools

_CACHE = dict()


def cache(func):
    """
    Decorates a function to look up and cache the execution result.

    Cache access is scoped by a tuple built from:
    - the wrapped function object
    - *args
    - tuple from **kwargs

    This has some pitfalls: the way arguments are passed to the called function matters!

    All build different cache keys:
    foo(a, b, c)      # (foo, (a, b, c), ())
    foo(a, b, c=c)    # (foo, (a, b), (c))
    foo(a, b=b, c=c)  # (foo, (a), )
    foo(a, c=c, b=b)  # (foo, (a), (c, b))
    """
    @functools.wraps(func)
    def with_cache(*args, **kwargs):
        value = None
        key = (func, args, tuple(kwargs))
        print("key:", key)
        try:
            value = _CACHE[key]
        except KeyError:
            value = func(*args, **kwargs)
            _CACHE[key] = value
        return value
    return with_cache


def flush_all():
    """
    Removes all keys from the global cache object.
    """
    _CACHE.clear()


def flush_for(func):
    """
    Removes all keys associated with `func` from the global cache object.
    Iterates through all cache keys to do so.
    """

    func_ref = func.__wrapped__ if "__wrapped__" in func.__dict__ else func
    keys_to_be_flushed = []
    for key_tuple in _CACHE:
        print("key_tuple", key_tuple)
        print("key_tuple[0]", key_tuple[0])
        if key_tuple[0] is func:
            keys_to_be_flushed.append(key_tuple)
    print("keys_to_be_flushed", keys_to_be_flushed)
    for key in keys_to_be_flushed:
        del _CACHE[key]
