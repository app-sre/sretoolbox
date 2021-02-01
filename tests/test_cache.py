import itertools
import pytest
from sretoolbox.utils import cache

class ExampleCacheConsumer:
    """
    this is a test class
    """

    @cache.static("my-fancy-key")
    def static(self):
        """
        cache based on static key name
        this returns a new map on every call - so that we can check for reference equality
        """
        return {}

    @cache.remove_static("my-fancy-key")
    def remove(self):
        """
        mutate something - needing a cache flush afterwards
        """
        return

    @cache.replace_static("my-fancy-key")
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

    @cache.replace_computed(
        lambda collection_id, item_id: (collection_id, item_id)
    )
    def replace_computed(self, collection_id, item_id):
        """
        update with computed cache key
        this returns a new map on every call - so that we can check for reference equality
        """
        return {
            "collection_id": collection_id,
            "item_id": item_id
        }

    @cache.remove_computed(
        lambda collection_id, item_id: (collection_id, item_id)
    )
    def remove_computed(self, collection_id, item_id):
        """
        mutate something - needing a computed cache invalidation afterwards
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
        def replace_computed(instance):
            instance.replace_computed("foo", "bar")
        def remove_computed(instance):
            instance.remove_computed("foo", "bar")

        matrix = itertools.permutations([
            static,
            replace,
            remove,
            computed,
            replace_computed,
            remove_computed
        ])

        for test in matrix:
            ecc = ExampleCacheConsumer()
            for func in test:
                func(ecc)

    def test_static_get(self):
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

    def test_copmuted_get(self):
        ecc = ExampleCacheConsumer()
        first_result = ecc.computed(1, 2)
        second_result = ecc.computed(1, 2)
        assert first_result is second_result
        third_result = ecc.computed(2, 3)
        assert second_result is not third_result

    def test_copmuted_autoremove(self):
        ecc = ExampleCacheConsumer()
        first_result = ecc.computed(1, 2)
        # trigger autoremove
        ecc.remove_computed(1, 2)
        second_result = ecc.computed(1, 2)
        assert first_result is not second_result

    def test_copmuted_replace(self):
        ecc = ExampleCacheConsumer()
        first_result = ecc.computed(1, 2)
        second_result = ecc.replace_computed(1, 2)
        assert first_result is not second_result
        third_result = ecc.computed(1, 2)
        assert second_result is third_result

    def test_raw_functions(self):
        ecc = ExampleCacheConsumer()
        cache.raw_set(ecc, "key", "value")
        value = cache.raw_get(ecc, "key")
        assert value is "value"
        cache.raw_remove(ecc, "key")
        with pytest.raises(KeyError):
            value = cache.raw_get(ecc, "key")
