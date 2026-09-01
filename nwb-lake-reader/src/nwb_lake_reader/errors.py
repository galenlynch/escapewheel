"""Exceptions raised when reading a packet."""

from __future__ import annotations


class PacketError(Exception):
    """Base class for every error raised by this package."""


class ManifestError(PacketError):
    """The packet manifest is absent, unparsable, or does not conform to its schema."""


class ResourceNotFoundError(PacketError):
    """A resource was requested that the manifest does not declare."""


class ResourceUnreadableError(PacketError):
    """A declared resource does not resolve to a readable file."""


class UnsupportedCodecError(PacketError):
    """The packet requires a codec this reader does not support."""


class NoTimeOrigin(PacketError):
    """The packet declares no `t_zero_tick`, so seconds are not defined (R39 §2.3).

    Tick zero, the session's wall-clock start and the first datum are all available and all
    wrong. A consumer that picks one silently produces numbers that cannot be compared with
    another consumer's, so this is raised instead.
    """
