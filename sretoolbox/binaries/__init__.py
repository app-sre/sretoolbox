"""
Exposes the binary libs for easy access.
"""

from sretoolbox.binaries.opm import Opm
from sretoolbox.binaries.operator_sdk import OperatorSDK


__all__ = [
    'Opm',
    'OperatorSDK',
]
