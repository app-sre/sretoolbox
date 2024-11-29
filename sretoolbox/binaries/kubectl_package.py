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

"""Abstractions around the kubectl-package binary."""

import platform
import re

from semver import VersionInfo

from sretoolbox.binaries.base import Binary


class KubectlPackage(Binary):
    """Defines the properties of KubectlPackage."""

    system = platform.system().lower()
    machine = platform.machine()
    sanitized_machine = "amd64" if machine == "x86_64" else machine

    binary_template = f"kubectl-package_{system}_{sanitized_machine}"
    download_url_template = (
        "https://github.com/package-operator/"
        "package-operator/releases/download/"
        "v{major}.{minor}.{patch}/"
        f"kubectl-package_{system}_{sanitized_machine}"
    )

    def get_version_command(self):
        """
        Gets the command and its option(s) to check the version.

        :return: version command
        :rtype: list
        """
        return [self.command, "--version"]

    def parse_version(self, version):
        """Parses version string as returned by the command execution to a VersionInfo.

        :param version: the return from the version command
        :type version: str

        :return: the parsed version as a VersionInfo object
        :rtype: VersionInfo
        """
        match = re.search(r"\d+\.\d+\.\d+", version)
        return VersionInfo.parse(version=match.group(0) if match else "")

    def process_download(self, path):  # noqa: ARG002
        """Processes a downloaded file and returns the executable binary path.

        :param path: The downloaded file path
        :return: The executable binary path.
        """
        bin_path = self.download_path / self.binary
        bin_path.chmod(0o777)
        return bin_path
