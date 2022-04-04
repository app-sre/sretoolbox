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
Abstractions around the mtcli binary.
"""

import os
import platform
import re
import tarfile

from semver import VersionInfo

from sretoolbox.binaries.base import Binary


class Mtcli(Binary):
    """
    Defines the properties of mtcli.
    """

    binary_template = "mtcli-{version}"
    system = platform.system()
    machine = platform.machine()
    download_url_template = (
        "https://github.com/mt-sre/addon-metadata-operator/"
        "releases/download/v{major}.{minor}.{patch}/"
        "mtcli_{major}.{minor}.{patch}_"
        f"{system}_{machine}.tar.gz"
    )

    def get_version_command(self):
        """
        Gets the command and its option(s) to check the version.

        :return: version command
        :rtype: list
        """
        return [self.command, "version"]

    def parse_version(self, version):
        """
        Parses version string as returned by the command execution
        to a VersionInfo instance.

        :param version: the return from the version command
        :type version: str

        :return: the parsed version as a VersionInfo object
        :rtype: VersionInfo
        """
        match = re.search(r"\d+\.\d+\.\d+", version)
        return VersionInfo.parse(version=match.group(0) if match else "")

    def process_download(self, path):
        """
        Processes a downloaded file and returns the executable binary path.

        :param path: The downloaded file path
        :return: The executable binary path.
        """
        # The downloaded file is actually a
        # tgz. Renaming first.
        tgz = f"{path}.tgz"
        os.rename(path, tgz)

        # Now we have to extract mtcli from the tgz to
        # the download_path
        with tarfile.open(tgz) as file_obj:
            file_obj.extract("mtcli", path=self.download_path)
        bin_path = f"{self.download_path}/mtcli"
        mtcli_path = f"{self.download_path}/{self.binary}"
        os.rename(bin_path, mtcli_path)

        # Making it executable
        os.chmod(mtcli_path, 0o777)

        return mtcli_path
