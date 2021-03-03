"""
Abstractions around subprocess
"""

import subprocess


def run(cmd):
    """
    Calls subprocess.run with select options.
    """
    return subprocess.run(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          check=True).stdout.decode()
