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
Multiprocessing abstractions.
"""

from multiprocessing import Pool

from sretoolbox.utils.exception import SystemExitWrapper


def run(func, iterable, process_pool_size,
        return_exceptions=False, **kwargs):
    """
    run_processes executes a function for each item in the input iterable.
    execution will be done in a processpool according to the input
    process_pool_size.  kwargs are passed to the input function
    (optional). If return_exceptions is true, any exceptions that may
    have happened in each thread are returned in the return value,
    allowing the caller to get as much work done as possible.

    SystemExit exceptions are treated the same way as regular exceptions.
    """
    if return_exceptions:
        tracer = _catching_traceback
    else:
        tracer = _full_traceback

    task_list = [(func, [i], kwargs) for i in iterable]
    with Pool(process_pool_size) as pool:
        try:
            return pool.map(tracer, task_list)
        except SystemExitWrapper as details:
            # a SystemExitWrapper is just a wrapper around a SystemExit
            # so we can catch it here reliably and propagate the actual
            # SystemExit as is
            raise details.origional_sys_exit_exception


def _catching_traceback(spec):
    try:
        func, args, kwargs = spec
        return func(*args, **kwargs)
    # pylint: disable=broad-except
    except BaseException as details:
        return details


def _full_traceback(spec):
    try:
        func, args, kwargs = spec
        return func(*args, **kwargs)
    except SystemExit as details:
        # a SystemExit will not propagate up to the user of the Pool
        # hence it would wait forever for the child process to finish
        # therefore we need to catch it here, wrap it in a regular
        # exception and unpack it again once the pool has finished
        # all tasks
        raise SystemExitWrapper(  # pylint: disable=raise-missing-from
            details
        )
