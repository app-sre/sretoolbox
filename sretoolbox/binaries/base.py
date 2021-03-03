"""
Abstractions around system binaries.
"""

import logging
import os

from abc import ABCMeta
from abc import abstractmethod
from collections import Counter
from pathlib import Path

import requests

from semver import VersionInfo

from sretoolbox.utils import run


LOG = logging.getLogger(__name__)


class CommandNotFoundError(Exception):
    """
    Used when a binary is not available in the system.
    """


class Binary(metaclass=ABCMeta):
    """
    Represents a binary in the system. Tries to find the system binary
    on the $PATH, in the specified version. When the binary is not
    available locally, tries to download it.

    :param version: the semantic version of the binary
    :param download_path: the path where to download the binary to,
                          in case we have to download it.

    :type version: str
    :type download_path: Path or str
    """
    binary_template = ''
    download_url_template = ''

    def __init__(self, version, download_path):
        # Making sure that the version contains
        # valid minor and patch elements
        counter = Counter(version)
        if counter['.'] == 0:
            version += '.0.0'
        elif counter['.'] == 1:
            version += '.0'

        self.expected_version = VersionInfo.parse(version=version)
        LOG.debug('Expected %s version: %s', self.binary,
                  self.expected_version)

        self.download_path = Path(download_path)

        downloaded = False
        # First try to get the path from the system
        self._command = self._get_command_path(self.binary)

        if self._command is None:
            # First try to download the binary
            downloaded_file = self._download()
            self._command = self.process_download(path=downloaded_file)
            downloaded = True

        # No luck. Binary is not on the system and it also can't
        # be downloaded.
        if self._command is None:
            raise CommandNotFoundError(f'Not able to find or download '
                                       f'{self.binary} version '
                                       f'{self.expected_version}')

        # Checking if we have the right version
        result = run(cmd=self.get_version_command())
        self._command_version = self.parse_version(version=result)
        if not self._compare(expected=self.expected_version,
                             actual=self._command_version):

            if downloaded:
                # If even after download, the version doesn't match,
                # we are done trying.
                raise CommandNotFoundError(f'Downloaded version of '
                                           f'{self.binary} did not match '
                                           f'the expected version '
                                           f'{self.expected_version}')

            # Version doesn't match and we didn't try to download
            # so far. Downloading.
            downloaded_file = self._download()
            self._command = self.process_download(path=downloaded_file)
            if self._command is None:
                raise CommandNotFoundError(f'Not able to download '
                                           f'{self.binary}')

            # Checking if we have the right version after download
            result = run(cmd=self.get_version_command())
            self._command_version = self.parse_version(version=result)
            if not self._compare(expected=self.expected_version,
                                 actual=self._command_version):
                raise CommandNotFoundError(f'Downloaded version of '
                                           f'{self.binary} did not match '
                                           f'the expected version '
                                           f'{self.expected_version}')

    @property
    def command(self):
        """
        The binary command full path.
        """
        return self._command

    @property
    def version(self):
        """
        The binary VersionInfo object instance.
        """
        return self._command_version

    @property
    def binary(self):
        """
        The binary name.
        """
        return self.binary_template.format(version=self.expected_version)

    @property
    def download_url(self):
        """
        The download URL.
        """
        return self.download_url_template.format(
            major=self.expected_version.major,
            minor=self.expected_version.minor,
            patch=self.expected_version.patch,
            prerelease=self.expected_version.prerelease,
            build=self.expected_version.build
        )

    def run(self, *args):
        """
        Runs binary with arbitrary options.
        """
        cmd = [self.command, *args]
        return run(cmd)

    @staticmethod
    def _compare(expected, actual):
        """
        Compares the not None fields from a VersionInfo object.

        :param expected: the expected version.
        :param actual: the actual version

        :type expected: VersionInfo
        :type actual: VersionInfo

        :return: True if the versions match.
        :rtype: bool
        """
        expected_version_dict = expected.to_dict()
        actual_version_dict = actual.to_dict()
        for item, value in expected_version_dict.items():
            if value is None:
                continue
            if actual_version_dict[item] != value:
                LOG.debug('Version mismatch: %s != %s', expected, actual)
                return False
        LOG.debug('Version match: %s == %s', expected, actual)
        return True

    def _get_command_path(self, cmd, check_exec=True):
        """
        Find a given command in the system.

        :param cmd: The command name.
        :param check_exec: Whether to check if the command is executable.

        :type cmd: str
        :type check_exec: bool

        :return: The command full path, when found.
        :rtype: string
        """
        bin_paths = [self.download_path]
        os_path = os.environ.get('PATH')
        if os_path is not None:
            bin_paths.extend([Path(item) for item in os_path.split(':')])

        for dir_path in bin_paths:
            cmd_path = dir_path / cmd
            if cmd_path.is_file():
                if check_exec:
                    if not os.access(cmd_path, os.R_OK | os.X_OK):
                        continue
                LOG.debug('Found %s', cmd_path)
                return str(cmd_path.resolve())

        return None

    @abstractmethod
    def get_version_command(self):
        """
        Gets the command and its option(s) to check the version.

        :return: version command
        :rtype: list
        """

    @abstractmethod
    def parse_version(self, version):
        """
        Parses version string as returned by the command execution
        to a VersionInfo instance.

        :param version: the return from the version command
        :type version: str

        :return: the parsed version as a VersionInfo object
        :rtype: VersionInfo
        """

    @abstractmethod
    def process_download(self, path):
        """
        Processes a downloaded file and returns the executable binary path.

        :param path: The downloaded file path
        :return: The executable binary path.
        """

    def _download(self):
        """
        Gets the binary from the internet in a specific version.

        :return: the command full path after downloaded
        :rtype: str or None
        """
        LOG.debug('Downloading %s', self.download_url)
        response = requests.get(self.download_url, allow_redirects=True)
        if response.status_code >= 300:
            LOG.debug('Error downloading %s: %s', self.download_url,
                      response.reason)
            return None

        bin_path = self.download_path / self.binary
        with open(bin_path, 'wb') as file_obj:
            file_obj.write(response.content)
        LOG.debug('Downloaded %s', bin_path)
        return str(bin_path)
