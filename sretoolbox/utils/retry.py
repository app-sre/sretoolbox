"""
Functions to add resilience to function calls.
"""


import itertools
import time

from functools import wraps


# source: https://www.calazan.com/retry-decorator-for-python-3/
def retry(exceptions=Exception, max_attempts=3):
    """
    Adds resilience to function calls.
    """
    def deco_retry(function):

        @wraps(function)
        def f_retry(*args, **kwargs):
            for attempt in itertools.count(1):
                try:
                    return function(*args, **kwargs)
                except exceptions as exception:  # pylint: disable=broad-except
                    if attempt > max_attempts - 1:
                        raise exception
                    time.sleep(attempt)
        return f_retry
    return deco_retry
