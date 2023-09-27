"""This module contains definitions related to architecture types."""

from enum import Enum


class ArchType(Enum):
    """
    Enumeration of architecture types.

    This class represents different architecture types like x86_64 and ARM64.
    """

    X86_64 = 'x86_64'
    ARM64 = 'aarch64'
