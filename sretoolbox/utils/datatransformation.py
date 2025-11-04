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

"""Utilities to transform data."""

from typing import Any, TypeVar


def replace_values(obj: Any, replace_map: dict[Any, Any]) -> Any:
    """Deep replace of object values according to provided map.

    :param obj: the object to have the values replaced
    :param replace_map: the map of values with their replacements
    :return: obj with replaced values
    """
    if isinstance(obj, list):
        for key, value in enumerate(obj):
            obj[key] = replace_values(value, replace_map)

    elif isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = replace_values(value, replace_map)

    elif obj in replace_map:
        return replace_map[obj]

    return obj


KeyType = TypeVar("KeyType")


def deep_merge(
    dict1: dict[KeyType, Any], dict2: dict[KeyType, Any]
) -> dict[KeyType, Any]:
    """Merge two dictionaries recursively"""
    return dict1 | {
        key: (
            deep_merge(dict1[key], value)
            if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict)
            else value
        )
        for key, value in dict2.items()
    }
