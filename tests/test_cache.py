import itertools
import pytest
from sretoolbox.utils.cache import cache, flush_all, flush_for

class ExampleCacheConsumer:
    """
    this is a test class
    """

    @cache
    def do_something_expensive_without_args(self):
        """
        cache based on function name
        this returns a new map on every call - so that we can check for reference equality
        """
        return {}

    @cache
    def do_something_expensive_with_args(self, foo, bar):
        """
        cache based on function name
        this returns a new map on every call - so that we can check for reference equality
        """
            "foo": foo,
            "bar": bar
        }

    def flush_all(self):
        """
        mutate something - needing a cache flush afterwards
        """
        flush_all()
        return

    def flush_for_without_args(self):
        """
        mutate something - needing a cache flush for all cache keys of
        `self.do_something_expensive_without_args` afterwards
        """
        flush_for(self.do_something_expensive_without_args)
        return

    def flush_for_with_args(self):
        """
        mutate something - needing a cache flush for all cache keys of
        `self.do_something_expensive_with_args` afterwards
        """
        flush_for(self.do_something_expensive_with_args)
        return


class TestCache:
    def test_cache_without_args(self):
        ecc = ExampleCacheConsumer()
        a = ecc.do_something_expensive_without_args()
        b = ecc.do_something_expensive_without_args()
        assert a is b

    def test_cache_with_args(self):
        ecc = ExampleCacheConsumer()
        a = ecc.do_something_expensive_with_args("foo", "bar")
        b = ecc.do_something_expensive_with_args("foo", "bar")
        assert a is b
        third_result = ecc.do_something_expensive_with_args("foo2", "bar2")
        assert b is not third_result

    def test_flush_all(self):
        ecc = ExampleCacheConsumer()
        a_without_args = ecc.do_something_expensive_without_args()
        a_with_args = ecc.do_something_expensive_with_args("foo", "bar")

        ecc.flush_all()

        b_without_args = ecc.do_something_expensive_without_args()
        assert a_without_args is not b_without_args
        b_with_args = ecc.do_something_expensive_with_args("foo", "bar")
        assert a_with_args is not b_with_args

    def test_flush_for(self):
        ecc = ExampleCacheConsumer()
        a_without_args = ecc.do_something_expensive_without_args()
        a_with_args = ecc.do_something_expensive_with_args("foo", "bar")

        ecc.flush_for_without_args()

        b_with_args = ecc.do_something_expensive_with_args("foo", "bar")
        assert a_with_args is b_with_args
        b_without_args = ecc.do_something_expensive_without_args()
        assert a_without_args is not b_without_args

        ecc.flush_for_with_args()

        third_result_with_args = ecc.do_something_expensive_with_args("foo", "bar")
        assert b_with_args is not third_result_with_args
        third_result_without_args = ecc.do_something_expensive_without_args()
        assert b_without_args is third_result_without_args

    def test_cache_with_args_ordering(self):
        @cache
        def with_args(a, b, c):
            return {
                "a": a,
                "b": b,
                "c": c
            }

        first = with_args("a", "b", "c")
        second = with_args("a", b="b", c="c")
        third = with_args("a", c="b", b="c")

        assert first is not second
        assert second is not third
