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

"""Common Exceptions"""


class SystemExitWrapperError(Exception):
    """Acts as a wrapper to a SystemExit exception.

    SystemExit exceptions are special in a way that they do not inherit from
    but rather BaseException. As such, they are handled differently in the
    threading and multiprocessing Pools. Raising a SystemExit an exception
    (via sys.exit()) has negative consequences about the Pools liveness.
    So wrapping it in a new Exception to pass it along and unwrap it
    afterwards is a reliable way keep the SystemExit exception alive
    without having negative impact.
    """

    def __init__(self, original_sys_exit_exception):
        super().__init__(original_sys_exit_exception)
        self.original_sys_exit_exception = original_sys_exit_exception
