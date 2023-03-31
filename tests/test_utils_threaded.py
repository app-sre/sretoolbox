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

import unittest

from sretoolbox.utils import threaded
from tests import fixture_function


class TestRunThreadStuff(unittest.TestCase):
    def test_run_normal(self):
        rs = threaded.run(fixture_function.identity, [42, 43, 44], 1)
        self.assertEqual(rs, [42, 43, 44])

    def test_run_normal_with_exceptions(self):
        with self.assertRaises(Exception):
            threaded.run(fixture_function.raiser, [42], 1)

    def test_run_catching(self):
        rs = threaded.run(fixture_function.identity, [42, 43, 44], 1, return_exceptions=True)
        self.assertEqual(rs, [42, 43, 44])

    def test_run_return_exceptions(self):
        rs = threaded.run(fixture_function.raiser, [42], 1, return_exceptions=True)
        self.assertEqual(rs[0].args, ("Oh noes!", ))
        self.assertEqual(len(rs), 1)

    def test_run_normal_sys_exit(self):
        with self.assertRaises(SystemExit):
            threaded.run(fixture_function.sys_exit_func, [0, 0], 2)
