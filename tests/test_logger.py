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
from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest

from sretoolbox.utils.logger import get_json_logger, get_text_logger

if TYPE_CHECKING:
    from collections.abc import Mapping


@pytest.mark.parametrize(
    "params",
    [
        {
            "name": "json1",
            "message": "message1",
            "extra": {"key1": "val1", "key2": "val2"},
        },
        {"name": "json2", "message": "message2", "extra": {}},
    ],
)
def test_json_logger(params: Mapping) -> None:
    log_capture_string = io.StringIO()
    logger = get_json_logger(name=params["name"], stream=log_capture_string)

    logger.info(params["message"], extra=params["extra"])

    # get dict from string
    log_contents = log_capture_string.getvalue()
    str_dict = log_contents[log_contents.find("{") :]
    d = eval(str_dict)  # noqa: S307

    assert d["message"] == params["message"]
    for k, v in params["extra"].items():
        assert d[k] == v


@pytest.mark.parametrize(
    "params",
    [
        {"name": "text1", "message": "message1"},
        {"name": "text2", "message": "message2"},
    ],
)
def test_json_logger_simple(params: Mapping) -> None:
    log_capture_string = io.StringIO()
    logger = get_text_logger(name=params["name"], stream=log_capture_string)
    logger.info(params["message"])
    log_contents = log_capture_string.getvalue()
    assert log_contents.find(params["message"]) > -1
