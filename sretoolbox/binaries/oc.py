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
Abstractions around the OC binary.
"""

import os
import platform

import tarfile

from semver import VersionInfo

from sretoolbox.binaries.base import Binary


class Oc(Binary):
    """
    Defines the properties of OC.
    """
    binary_template = 'oc-{version}'
    system = 'mac' if platform.system().lower() == 'darwin' else 'linux'
    download_url_template = ('https://mirror.openshift.com/pub/'
                             'openshift-v{major}/'
                             'clients/ocp/'
                             '{major}.{minor}.{patch}/'
                             f'openshift-client-{system}-'
                             '{major}.{minor}.{patch}.tar.gz')

    def get_version_command(self):
        """
        Gets the command and its option(s) to check the version.

        :return: version command
        :rtype: list
        """
        return [self.command, 'version', '--client']

    def parse_version(self, version):
        """
        Parses version string as returned by the command execution
        to a VersionInfo instance.

        :param version: the return from the version command
        :type version: str

        :return: the parsed version as a VersionInfo object
        :rtype: VersionInfo
        """
        # Example:
        # Client Version: 4.6.1
        oc_version = version.split(':')[1].strip()
        return VersionInfo.parse(version=oc_version)

    def process_download(self, path):
        """
        Processes a downloaded file and returns the executable binary path.

        :param path: The downloaded file path
        :return: The executable binary path.
        """
        # The downloaded file is actually a
        # tgz. Renaming first.
        tgz = f'{path}.tgz'
        os.rename(path, tgz)

        # Now we have to extract OC from the tgz to
        # the download_path
        with tarfile.open(tgz) as file_obj:
            file_obj.extract('oc', path=self.download_path)
        bin_path = f'{self.download_path}/oc'
        oc_path = f'{self.download_path}/{self.binary}'
        os.rename(bin_path, oc_path)

        # Making it executable
        os.chmod(oc_path, 0o777)

        return oc_path
