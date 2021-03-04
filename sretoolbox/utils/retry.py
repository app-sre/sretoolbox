"""
Functions to add resilience to function calls.
"""


import itertools
import time

from functools import wraps


# source: https://www.calazan.com/retry-decorator-for-python-3/
def retry(exceptions=Exception, max_attempts=3, no_retry_exceptions=(),
          hook=None):
    """Adds resilience to function calls.

    This decorator will retry a function for several attempts if it raises an
    expected exception. Additionally it supports running a hook each time there
    is a new attempt.

    :param exceptions: collections of exceptions that will trigger a retry,
        defaults to Exception
    :type exceptions: tuple(Exception, ...), optional
    :param max_attempts: number of max attemps before giving up and raising
        the exception, defaults to 3
    :type max_attempts: int, optional
    :param no_retry_exceptions: exceptions to be excluded from the retry,
        defaults to ()
    :type no_retry_exceptions: tuple, optional
    :param hook: function which will be triggered each time there is a retry
        attempt, defaults to None
    :type hook: function(Exception), optional
    :return: decorated function
    :rtype: function
    """
    def deco_retry(function):

        @wraps(function)
        def f_retry(*args, **kwargs):
            for attempt in itertools.count(1):
                try:
                    return function(*args, **kwargs)
                except no_retry_exceptions as exception:
                    raise exception
                except exceptions as exception:  # pylint: disable=broad-except
                    if attempt > max_attempts - 1:
                        raise exception
                    if callable(hook):
                        hook(exception)
                    time.sleep(attempt)
            return None
        return f_retry
    return deco_retry
