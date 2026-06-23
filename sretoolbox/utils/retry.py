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

"""Functions to add resilience to function calls."""

from __future__ import annotations

import inspect
import itertools
import random
import time
from functools import wraps
from typing import TYPE_CHECKING, Literal, ParamSpec, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

# Type variables for proper decorator typing
P = ParamSpec("P")
T = TypeVar("T")

BackoffStrategy = Literal["linear", "exponential"]


def _validate_retry_params(
    max_attempts: int,
    backoff: BackoffStrategy,
    backoff_base: float,
    backoff_max: float | None,
) -> None:
    if max_attempts < 1:
        msg = "max_attempts must be >= 1"
        raise ValueError(msg)
    if backoff == "exponential":
        if backoff_base <= 0:
            msg = "backoff_base must be > 0 when backoff='exponential'"
            raise ValueError(msg)
        if backoff_max is not None and backoff_max <= 0:
            msg = "backoff_max must be > 0 when set"
            raise ValueError(msg)


def _compute_delay(
    attempt: int,
    *,
    backoff: BackoffStrategy,
    backoff_base: float,
    backoff_max: float | None,
    jitter: bool,
) -> float:
    if backoff == "linear":
        delay = float(attempt)
    else:
        delay = backoff_base ** (attempt - 1)
        if backoff_max is not None:
            delay = min(delay, backoff_max)
    if jitter:
        return random.uniform(0, delay)  # noqa: S311
    return delay


def _positional_param_count(signature: inspect.Signature) -> int:
    return sum(
        1
        for param in signature.parameters.values()
        if param.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }
    )


def _invoke_hook(
    hook: Callable[..., None] | None,
    exception: Exception,
    attempt: int,
    max_attempts: int,
) -> None:
    if not callable(hook):
        return
    try:
        param_count = _positional_param_count(inspect.signature(hook))
    except (TypeError, ValueError):
        hook(exception)
        return
    if param_count >= 3:
        hook(exception, attempt, max_attempts)
    elif param_count >= 2:
        hook(exception, attempt)
    else:
        hook(exception)


# Original Code:
# https://github.com/saltycrane/retry-decorator/blob/a26fe27/retry_decorator.py
def retry(
    exceptions: type[Exception] | tuple[type[Exception], ...] = Exception,
    max_attempts: int = 3,
    no_retry_exceptions: tuple[type[Exception], ...] = (),
    hook: Callable[..., None] | None = None,
    *,
    backoff: BackoffStrategy = "linear",
    backoff_base: float = 2.0,
    backoff_max: float | None = None,
    jitter: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
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
    :param hook: function called before each retry sleep. Accepts ``(exception)``,
        ``(exception, attempt)``, or ``(exception, attempt, max_attempts)`` depending
        on the hook signature.
    :type hook: Callable, optional
    :param backoff: delay strategy between retries. ``linear`` sleeps for ``attempt``
        seconds (default, unchanged legacy behavior). ``exponential`` sleeps for
        ``backoff_base ** (attempt - 1)`` seconds, optionally capped by ``backoff_max``.
    :type backoff: str, optional
    :param backoff_base: base for exponential backoff, defaults to 2.0
    :type backoff_base: float, optional
    :param backoff_max: maximum delay in seconds for exponential backoff
    :type backoff_max: float | None, optional
    :param jitter: when True, apply full jitter by sleeping for a random duration
        in ``[0, delay]`` instead of the full computed delay
    :type jitter: bool, optional
    :return: decorated function
    :rtype: function
    """
    _validate_retry_params(max_attempts, backoff, backoff_base, backoff_max)

    def deco_retry(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def f_retry(*args: P.args, **kwargs: P.kwargs) -> T:
            for attempt in itertools.count(1):
                try:
                    return function(*args, **kwargs)
                except no_retry_exceptions:
                    raise
                except exceptions as exception:
                    if attempt > max_attempts - 1:
                        raise
                    _invoke_hook(hook, exception, attempt, max_attempts)
                    delay = _compute_delay(
                        attempt,
                        backoff=backoff,
                        backoff_base=backoff_base,
                        backoff_max=backoff_max,
                        jitter=jitter,
                    )
                    time.sleep(delay)
            # make mypy happy
            raise RuntimeError("Unreachable code in retry decorator")

        return f_retry

    return deco_retry
