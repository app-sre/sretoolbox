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
Abstractions around the OperatorSDK binary.
"""

import os
import platform

from semver import VersionInfo

from sretoolbox.binaries.base import Binary


class OperatorSDK(Binary):
    """
    Defines the properties of OperatorSDK.
    """
    binary_template = 'operator-sdk-{version}'
    system = platform.system().lower()
    download_url_template = ('https://github.com/operator-framework/'
                             'operator-sdk/releases/download/'
                             'v{major}.{minor}.{patch}/'
                             f'operator-sdk_{system}_amd64')

    def get_version_command(self):
        """
        Gets the command and its option(s) to check the version.

        :return: version command
        :rtype: list
        """
        return [self.command, 'version']

    def parse_version(self, version):
        """
        Parses version string as returned by the command execution
        to a VersionInfo instance.

        :param version: the return from the version command
        :type version: str

        :return: the parsed version as a VersionInfo object
        :rtype: VersionInfo
        """
        opm_version = version.split('"')[1].split('v', 1)[1]
        return VersionInfo.parse(version=opm_version)

    def process_download(self, path):
        """
        Processes a downloaded file and returns the executable binary path.

        :param path: The downloaded file path
        :return: The executable binary path.
        """
        os.chmod(path, 0o777)
        return path
