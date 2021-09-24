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

"""
JSON and Text loggers abstractions.
"""

import logging
import sys
from enum import Enum

from pythonjsonlogger import jsonlogger


class LoggerType(Enum):
    """Enum for supported logger types."""

    TEXT = 1
    JSON = 2


def get_text_logger(name, stream=sys.stdout, level=logging.INFO):
    """
    Sets up or returns a singleton text logger.

    :param name: logger name
    :type name: str
    :param stream: stream where to log
    :type stream: io.TextIOWrapper
    :param level: log level
    :type level: int
    :return: text logger
    :rtype: logging.Logger
    """
    return LoggersSingleton(
        name=name, kind=LoggerType.TEXT, stream=stream, level=level
    )


def get_json_logger(name, stream=sys.stdout, level=logging.INFO):
    """
    Sets up or returns a singleton JSON logger.

    :param name: logger name
    :type name: str
    :param stream: stream where to log
    :type stream: io.TextIOWrapper
    :param level: log level
    :type level: int
    :return: text logger
    :rtype: logging.Logger
    """
    return LoggersSingleton(
        name=name, kind=LoggerType.JSON, stream=stream, level=level
    )


def _setup_text_logger(name, stream, level):
    """Setup a text logger."""
    res = logging.getLogger(name)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(fmt="%(message)s"))
    res.addHandler(handler)
    res.setLevel(level)
    return res


def _setup_json_logger(name, stream, level):
    """Setup a JSON logger."""
    res = logging.getLogger(name)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(jsonlogger.JsonFormatter())
    res.addHandler(handler)
    res.setLevel(level)
    return res


# pylint: disable=too-few-public-methods
class LoggersSingleton:
    """Singleton wrapper around loggers."""

    # Loggers are indexed first by kind, after by name
    _instances = {k: {} for k in LoggerType.__members__}

    def __new__(cls, kind, name, stream, level):
        if cls._instances.get(kind.name).get(name) is None:
            if kind == LoggerType.TEXT:
                cls._instances[kind.name][name] = _setup_text_logger(
                    name, stream, level
                )
            elif kind == LoggerType.JSON:
                cls._instances[kind.name][name] = _setup_json_logger(
                    name, stream, level
                )
        return cls._instances[kind.name][name]
