import itertools
import pytest
from sretoolbox.utils import cache

class ExampleCacheConsumer:
    """
    this is a test class
    """

    @cache.static("collection")
    def static(self):
        """
        cache based on collection name
        this returns a new map on every call - so that we can check for reference equality
        """
        return {}

    @cache.remove("collection")
    def remove(self):
        """
        mutate something in collection - needing a cache flush afterwards
        """
        return

    @cache.replace("collection")
    def replace(self):
        """
        store result without an initial cache lookup
        this returns a new map on every call - so that we can check for reference equality
        """
        return {}

    @cache.computed(
        lambda collection_id, item_id: (collection_id, item_id)
    )
    def computed(self, collection_id, item_id):
        """
        store/lookup with computed cache key
        this returns a new map on every call - so that we can check for reference equality
        """
        return {
            "collection_id": collection_id,
            "item_id": item_id
        }

class TestCache:
    def test_lazy_init(self):
        """
        Test lazy cache initialization by calling all cache functions
        in all possible orders and verifying that nothing explodes
        """
        def static(instance):
            instance.static()
        def replace(instance):
            instance.replace()
        def remove(instance):
            instance.remove()
        def computed(instance):
            instance.computed("foo", "bar")

        matrix = itertools.permutations([
            static,
            replace,
            remove,
            computed
        ])

        for test in matrix:
            ecc = ExampleCacheConsumer()
            for func in test:
                func(ecc)

    def test_cached_get(self):
        ecc = ExampleCacheConsumer()
        first_result = ecc.static()
        second_result = ecc.static()
        assert first_result is second_result

    def test_autoremove(self):
        ecc = ExampleCacheConsumer()
        first_result = ecc.static()
        # trigger autoremove
        ecc.remove()
        second_result = ecc.static()
        assert first_result is not second_result

    def test_replace(self):
        ecc = ExampleCacheConsumer()
        first_result = ecc.static()
        second_result = ecc.replace()
        assert first_result is not second_result
        third_result = ecc.static()
        assert second_result is third_result

    def test_dynamic_get(self):
        ecc = ExampleCacheConsumer()
        first_result = ecc.computed(1, 2)
        second_result = ecc.computed(1, 2)
        assert first_result is second_result
        third_result = ecc.computed(2, 3)
        assert second_result is not third_result
