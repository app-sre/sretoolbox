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


def identity(x):
    return x


def raiser(*args, **kwargs):
    raise Exception("Oh noes!")


class TestWrappers(unittest.TestCase):

    def test_full_traceback_no_error(self):
        f = threaded._full_traceback(identity)

        self.assertEqual(f(42), 42)

    def tet_full_traceback_exception(self):
        f = threaded._full_traceback(raiser)

        with self.assertRaises(Exception):
            f(42)

    def test_catching_traceback_no_error(self):
        f = threaded._catching_traceback(identity)

        self.assertEqual(f(42), 42)

    def test_catching_traceback_exception(self):
        f = threaded._catching_traceback(raiser)

        rs = f(42)
        self.assertEqual(rs.args, ("Oh noes!", ))


class TestRunStuff(unittest.TestCase):
    def test_run_normal(self):
        rs = threaded.run(identity, [42, 43, 44], 1)
        self.assertEqual(rs, [42, 43, 44])

    def test_run_normal_with_exceptions(self):
        with self.assertRaises(Exception):
            threaded.run(raiser, [42], 1)

    def test_run_catching(self):
        rs = threaded.run(identity, [42, 43, 44], 1, return_exceptions=True)
        self.assertEqual(rs, [42, 43, 44])

    def test_run_return_exceptions(self):
        rs = threaded.run(raiser, [42], 1, return_exceptions=True)
        self.assertEqual(rs[0].args, ("Oh noes!", ))
        self.assertEqual(len(rs), 1)
