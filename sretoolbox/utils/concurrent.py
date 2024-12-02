# ruff: noqa:A005
# Copyright 2021 Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Concurrent abstractions."""

from collections.abc import Iterable
from concurrent.futures import Executor
from functools import partial
from typing import Any, Callable

from sretoolbox.utils.exception import SystemExitWrapperError


def pmap(
    func: Callable[..., Any],
    iterable: Iterable[Any],
    executor: type[Executor],
    pool_size: int,
    return_exceptions: bool = False,  # noqa: FBT001
    **kwargs: Any,
) -> list[Any]:
    """Like map but with a pool of workers.

    Applies the provided function `func` to each element in the given
    `iterable` using a pool with a maximum of `pool_size`.

    Args:
        func (callable): A function to be applied to the elements of the
            iterable. This function should take one positional argument and
            return a result.
        iterable (iterable): An iterable object containing the input elements
            to be processed by the `func` function.
        executor (Executor): An object representing an executor to be used for
            running the mapping operation. This should be a class that
            implements the `__enter__` and `__exit__` methods, such as
            `concurrent.futures.ThreadPoolExecutor` or
            `concurrent.futures.ProcessPoolExecutor`.
        pool_size (int): An integer that specifies the maximum number of
            workers to be used for processing the iterable.
        return_exceptions (bool, optional): A boolean value indicating whether
            exceptions raised by the `func` function should be returned in the
            result list or not. Default is `False`.
        **kwargs: Optional keyword arguments that will be passed to the `func`
            function along with the input elements.

    Returns:
        list: A list of results after applying the `func` function to each
        element of the iterable.

    Raises:
        The function raises any exceptions raised by the `func` function, with
        full traceback information, if `return_exceptions` is `False`.

    Notes:
        - If `return_exceptions` is `True`, any exceptions raised by the `func`
          function are returned in the result list.
        - Otherwise this function catches `SystemExit` exceptions and
          propagates a `SystemExitWrapper` exception.

    Example:
        >>> def square(x):
        ...     return x ** 2
        >>> iterable = [1, 2, 3, 4, 5]
        >>> pool_size = 2
        >>> executor = concurrent.futures.ThreadPoolExecutor
        >>> pmap(square, iterable, executor, pool_size)
        [1, 4, 9, 16, 25]
    """
    tracer = _catching_traceback if return_exceptions else _full_traceback
    func_partial = partial(tracer, func, **kwargs)

    with executor(pool_size) as pool:
        try:
            return list(pool.map(func_partial, iterable))
        except SystemExitWrapperError as details:
            # a SystemExitWrapper is just a wrapper around a SystemExit
            # so we can catch it here reliably and propagate the actual
            # SystemExit as is
            raise details.original_sys_exit_exception from None


def _catching_traceback(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    try:
        return func(*args, **kwargs)
    except BaseException as details:  # noqa: BLE001
        return details


def _full_traceback(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    try:
        return func(*args, **kwargs)
    except SystemExit as details:
        # a SystemExit will not propagate up to the user of the Pool
        # hence it would wait forever for the child worker to finish
        # therefore we need to catch it here, wrap it in a regular
        # exception and unpack it again once the pool has finished
        # all tasks
        raise SystemExitWrapperError(details) from None
