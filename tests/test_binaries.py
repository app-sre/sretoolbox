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

from pathlib import Path

import pytest

from sretoolbox.binaries import KubectlPackage, Mtcli, Oc, OperatorSDK, Opm


@pytest.mark.parametrize(
    ("instance", "version"),
    [
        (Mtcli, "0.0.0"),
        (Mtcli, "0.10.0"),
        (Oc, "4.6.1"),
        (Opm, "1.15.1"),
        (OperatorSDK, "1.4.2"),
        (KubectlPackage, "1.4.0"),
    ],
)
def test_download_binaries(
    instance: KubectlPackage | Mtcli | Oc | OperatorSDK | Opm,
    version: str,
    tmp_path: Path,
):
    _ = instance(version=version, download_path=tmp_path)
