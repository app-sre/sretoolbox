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

"""
Threading abstractions.
"""

import traceback
import functools
from multiprocessing.dummy import Pool as ThreadPool


def full_traceback(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            msg = "{}\n\nOriginal {}".format(e, traceback.format_exc())
            raise type(e)(msg)
    return wrapper


def catching_traceback(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return e
    return wrapper


def run(func, iterable, thread_pool_size, return_exceptions=False, **kwargs):
    """run executes a function for each item in the input iterable.
    execution will be multithreaded according to the input
    thread_pool_size.  kwargs are passed to the input function
    (optional). If return_exceptions is true, any exceptions that may
    have happened in each thread are returned in the return value,
    allowing the caller to get as much work done as possible.
    """

    if return_exceptions:
        tracer = catching_traceback
    else:
        tracer = full_traceback

    func_partial = functools.partial(tracer(func), **kwargs)

    pool = ThreadPool(thread_pool_size)
    try:
        return pool.map(func_partial, iterable)
    finally:
        pool.close()
        pool.join()


def estimate_available_thread_pool_size(thread_pool_size, targets_len):
    # if there are 20 threads and only 3 targets,
    # each thread can use ~20/3 threads internally.
    # if there are 20 threads and 100 targts,
    # each thread can use 1 thread internally.
    available_thread_pool_size = int(thread_pool_size / targets_len)
    return max(available_thread_pool_size, 1)
