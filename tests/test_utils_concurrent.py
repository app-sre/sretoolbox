import unittest
from concurrent.futures import ThreadPoolExecutor

from tests import fixture_function

from sretoolbox.utils import concurrent


class TestRunProcessStuff(unittest.TestCase):
    def test_run_no_errors(self):
        rs = concurrent.pmap(
            fixture_function.identity, [42, 43, 44], ThreadPoolExecutor, 3
        )
        self.assertEqual(rs, [42, 43, 44])

    def test_run_with_exceptions(self):
        with self.assertRaises(Exception):
            concurrent.pmap(
                fixture_function.raiser, [42, 43, 44], ThreadPoolExecutor, 3
            )

    def test_run_return_exceptions_no_errors(self):
        rs = concurrent.pmap(
            fixture_function.identity,
            [42, 43, 44],
            ThreadPoolExecutor,
            3,
            return_exceptions=True,
        )
        self.assertEqual(rs, [42, 43, 44])

    def test_run_return_exceptions_with_exceptions(self):
        rs = concurrent.pmap(
            fixture_function.raiser,
            [42, 43, 44],
            ThreadPoolExecutor,
            3,
            return_exceptions=True,
        )
        self.assertEqual(len(rs), 3)
        for r in rs:
            self.assertEqual(r.args, ("Oh noes!",))

    def test_run_return_exceptions_mixed_results(self):
        rs = concurrent.pmap(
            fixture_function.return_int_raise_value_error_otherwise,
            [42, 43, "Oh noes!"],
            ThreadPoolExecutor,
            3,
            return_exceptions=True,
        )
        self.assertEqual(len(rs), 3)
        self.assertEqual(rs[0], 42)
        self.assertEqual(rs[1], 43)
        self.assertTrue(isinstance(rs[2], ValueError))
        self.assertEqual(rs[2].args, ("Oh noes!",))

    def test_run_mixed_results(self):
        with self.assertRaises(Exception):
            concurrent.pmap(
                fixture_function.return_int_raise_value_error_otherwise,
                [42, "Oh noes!"],
                ThreadPoolExecutor,
                1,
            )

    def test_run_return_exceptions_sys_exit(self):
        rs = concurrent.pmap(
            fixture_function.sys_exit_func,
            [0, 1],
            ThreadPoolExecutor,
            2,
            return_exceptions=True,
        )
        self.assertIsInstance(rs[0], SystemExit)
        self.assertEqual(rs[0].args, (0,))

        self.assertIsInstance(rs[1], SystemExit)
        self.assertEqual(rs[1].args, (1,))

    def test_sys_exit(self):
        with self.assertRaises(SystemExit):
            concurrent.pmap(
                fixture_function.sys_exit_func, [0, 1], ThreadPoolExecutor, 2
            )
