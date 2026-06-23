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

"""Wrapper around the Skopeo utility."""

from __future__ import annotations

import logging
import shutil
import subprocess

_LOG = logging.getLogger(__name__)


class SkopeoCmdError(Exception):
    """Indicates that the skopeo command failed."""


class Skopeo:
    """Abstracts Skopeo and implements its features."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        skopeo_cmd = shutil.which("skopeo")
        if not skopeo_cmd:
            raise SkopeoCmdError("skopeo command not found in PATH")
        self.skopeo_cmd = skopeo_cmd

    def copy(
        self,
        src_image: str,
        dst_image: str,
        src_creds: str | None = None,
        dest_creds: str | None = None,
        copy_all: bool = False,
    ) -> None:
        """Runs the skopeo "copy" sub-command.

        The skopeo "copy" pulls the source image from the online repository
        and pushes it to the destination image online repository.

        :param src_image: The image to be pulled.
        :type src_image: str
        :param dst_image: The image to be pushed.
        :type dst_image: str
        :param src_creds: (optional) The source repository
                           credentials in the format
                           "username:password".
        :type src_creds: str
        :param dest_creds: (optional) The destination repository
                           credentials in the format
                           "username:password".
        :type dest_creds: str
        :param copy_all: (optional) Whether to copy all the architectures
                         from a given tag or only the architecture of the OS
                         Skopeo is running on.
        :type copy_all: bool
        """
        return self._run_skopeo(
            "copy",
            str(src_image),
            str(dst_image),
            src_creds=src_creds,
            dest_creds=dest_creds,
            all_=copy_all,
        )

    def inspect(self, image: str, creds: str | None = None) -> None:
        """Runs the skopeo "inspect" sub-command.

        The skopeo "inspect" returns low-level information about the image.
        This implementation only checks that the command was successful,
        meaning that the image exists.

        :param image: The image to be inspected.
        :type image: str
        :param creds: (optional) The source repository
                      credentials in the format
                      "username:password".
        :type creds: str
        """
        return self._run_skopeo("inspect", str(image), creds=creds)

    def _run_skopeo(
        self,
        subcomand: str,
        *args: str,
        src_creds: str | None = None,
        dest_creds: str | None = None,
        creds: str | None = None,
        all_: bool = False,
    ) -> str:
        """Helper to streamline the execution of skopeo commands

        :param subcomand: The skopeo subcommand to execute.
                          E.g. inspect, copy, ...
        :type subcomand: str
        :param *args: Additional positional arguments according
                      to the sub-command.
        :type *args: str
        :param src_creds: (optional) The source repository
                           credentials in the format
                           "username:password".
        :type src_creds: str
        :param dest_creds: (optional) The destination repository
                           credentials in the format
                           "username:password".
        :type dest_creds: str
        :param all_: (optional) Whether to add the --all option to the
                     command line.
        :type all_: bool
        """
        cmd: list[str] = [self.skopeo_cmd, subcomand]

        if src_creds is not None:
            cmd.append(f"--src-creds={src_creds}")
        if dest_creds is not None:
            cmd.append(f"--dest-creds={dest_creds}")
        if creds is not None:
            cmd.append(f"--creds={creds}")
        if all_:
            cmd.append("--all")
        cmd.extend(args)

        if subcomand == "copy":
            _LOG.info([subcomand, *args])
            if self.dry_run:
                return ""

        result = subprocess.run(cmd, check=False, capture_output=True)  # noqa: S603

        for line in result.stdout.decode().splitlines():
            _LOG.debug(" %s", line)

        if result.returncode:
            for line in result.stderr.decode().splitlines():
                _LOG.error(" %s", line)
            raise SkopeoCmdError(f"exit code: {result.returncode}")

        return result.stdout.decode("utf-8")
