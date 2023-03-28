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
from concurrent.futures import ProcessPoolExecutor

from sretoolbox.utils.concurrent import pmap


def run(func, iterable, process_pool_size,
        return_exceptions=False, **kwargs):
    """
    run executes a function for each item in the input iterable.
    execution will be done in a processpool according to the input
    process_pool_size.  kwargs are passed to the input function
    (optional). If return_exceptions is true, any exceptions that may
    have happened in each thread are returned in the return value,
    allowing the caller to get as much work done as possible.

    SystemExit exceptions are treated the same way as regular exceptions.
    """
    return pmap(func,
                iterable,
                ProcessPoolExecutor,
                process_pool_size,
                return_exceptions,
                **kwargs)
