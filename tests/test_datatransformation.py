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

from sretoolbox.utils import replace_values


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
