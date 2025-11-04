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

import pytest

from sretoolbox.utils import replace_values
from sretoolbox.utils.datatransformation import deep_merge


class TestReplaceValues:
    def test_parser(self):
        obj = [
            True,
            False,
            None,
            {"foo": True, "bar": {"foobar": False, "barfoo": [True, False, None]}},
        ]

        replace_map = {True: "true", False: "false", None: ""}

        expected_result = [
            "true",
            "false",
            "",
            {
                "foo": "true",
                "bar": {"foobar": "false", "barfoo": ["true", "false", ""]},
            },
        ]

        result = replace_values(obj, replace_map)
        assert result == expected_result


class TestDeepMerge:
    @pytest.mark.parametrize(
        "dict1,dict2,expected",
        [
            # Empty dictionaries
            ({}, {}, {}),
            # Empty dict1
            ({}, {"a": 1}, {"a": 1}),
            # Empty dict2
            ({"a": 1}, {}, {"a": 1}),
            # Simple merge without overlap
            ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
            # Simple merge with overlap (dict2 wins)
            ({"a": 1}, {"a": 2}, {"a": 2}),
            # Nested dict merge
            (
                {"a": {"b": 1}},
                {"a": {"c": 2}},
                {"a": {"b": 1, "c": 2}},
            ),
            # Nested dict with overlap
            (
                {"a": {"b": 1, "c": 3}},
                {"a": {"b": 2}},
                {"a": {"b": 2, "c": 3}},
            ),
            # Deep nested merge
            (
                {"a": {"b": {"c": 1}}},
                {"a": {"b": {"d": 2}}},
                {"a": {"b": {"c": 1, "d": 2}}},
            ),
            # Mixed types (dict2 replaces dict1)
            ({"a": 1}, {"a": {"b": 2}}, {"a": {"b": 2}}),
            ({"a": {"b": 1}}, {"a": 2}, {"a": 2}),
            # Lists (dict2 replaces dict1, no merging)
            ({"a": [1, 2]}, {"a": [3, 4]}, {"a": [3, 4]}),
            # Multiple top-level keys
            (
                {"a": 1, "b": 2, "c": 3},
                {"b": 20, "d": 4},
                {"a": 1, "b": 20, "c": 3, "d": 4},
            ),
            # Complex nested structure
            (
                {"config": {"database": {"host": "localhost", "port": 5432}}},
                {"config": {"database": {"port": 3306}, "cache": {"enabled": True}}},
                {
                    "config": {
                        "database": {"host": "localhost", "port": 3306},
                        "cache": {"enabled": True},
                    }
                },
            ),
            # Different value types
            (
                {"a": "string", "b": 123, "c": True},
                {"a": "new", "d": None},
                {"a": "new", "b": 123, "c": True, "d": None},
            ),
        ],
    )
    def test_deep_merge_parametrized(
        self, dict1: dict, dict2: dict, expected: dict
    ) -> None:
        assert deep_merge(dict1, dict2) == expected

    def test_deep_merge_immutability(self) -> None:
        """Test that original dictionaries are not modified."""
        dict1 = {"a": {"b": 1}}
        dict2 = {"a": {"c": 2}}
        dict1_copy = {"a": {"b": 1}}
        dict2_copy = {"a": {"c": 2}}

        deep_merge(dict1, dict2)

        assert dict1 == dict1_copy
        assert dict2 == dict2_copy

    def test_deep_merge_three_levels_deep(self) -> None:
        """Test merging with three levels of nesting."""
        dict1 = {"level1": {"level2": {"level3": {"a": 1}}}}
        dict2 = {"level1": {"level2": {"level3": {"b": 2}}}}
        expected = {"level1": {"level2": {"level3": {"a": 1, "b": 2}}}}

        assert deep_merge(dict1, dict2) == expected

    def test_deep_merge_type_preservation(self) -> None:
        """Test that integer keys are preserved when merging."""
        dict1 = {1: "one", 2: "two"}
        dict2 = {2: "TWO", 3: "three"}
        expected = {1: "one", 2: "TWO", 3: "three"}

        assert deep_merge(dict1, dict2) == expected
