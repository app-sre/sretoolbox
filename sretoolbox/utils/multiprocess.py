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

"""Multiprocessing abstractions."""

from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable

from sretoolbox.utils.concurrent import pmap


def run(
    func: Callable[..., Any],
    iterable: Iterable[Any],
    process_pool_size: int,
    return_exceptions: bool = False,  # noqa: FBT001
    **kwargs: Any,
) -> list[Any]:
    """Applies the provided function `func` to each element in the given `iterable`.

    This function uses a process pool with a maximum of `process_pool_size`.

    Args:
        func (callable): A function to be applied to the elements of the
            iterable. This function should take one positional argument and
            return a result.
        iterable (iterable): An iterable object containing the input elements
            to be processed by the `func` function.
        process_pool_size (int): An integer that specifies the maximum number
            of workers to be used for processing the iterable.
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
        >>> run(square, iterable, pool_size)
        [1, 4, 9, 16, 25]
    """
    return pmap(
        func,
        iterable,
        ProcessPoolExecutor,
        process_pool_size,
        return_exceptions,
        **kwargs,
    )
