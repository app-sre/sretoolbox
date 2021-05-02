# Copyright (c) 2013, SaltyCrane
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the
#     distribution.
#
# * Neither the name of the SaltyCrane nor the names of its
# contributors may be used to endorse or promote products derived
# from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Functions to add resilience to function calls.
"""

import itertools
import time

from functools import wraps


# Original Code:
# https://github.com/saltycrane/retry-decorator/blob/a26fe27/retry_decorator.py
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
