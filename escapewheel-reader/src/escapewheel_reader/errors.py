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
    """The packet declares no `t_zero_tick`, so seconds are not defined (Part 01 §2.1).

    Tick zero, the session's wall-clock start and the first datum are all available and all
    wrong. A consumer that picks one silently produces numbers that cannot be compared with
    another consumer's, so this is raised instead.
    """


class AmbiguousRun(PacketError):
    """Several runs produced the same thing and the packet does not say which to read.

    Part 01 §2.4. Reading them all concatenated is the failure this prevents: two sortings of one
    probe are two complete sets of units, so every count taken over both is wrong and nothing
    about the result says so. Picking the newest, or the first, produces numbers that cannot be
    compared with another consumer's.
    """


class UnresolvableChannelIndex(PacketError):
    """A channel index names no electrode of its sorting run (Part 02 §12.2).

    `channels_declared` tells the two cases apart, because they call for different repairs.
    `None` means the run records no channel list, which a conforming packet may do: the gap is a
    fact about what the packet carries, so a consumer reports it and neither fails the packet nor
    falls back to `core.electrodes`, where the index names a plausible wrong contact. An integer
    means the run kept that many channels and the index falls outside them, so the index and the
    packet disagree about one run.
    """

    def __init__(self, message: str, *, channels_declared: int | None = None) -> None:
        super().__init__(message)
        self.channels_declared = channels_declared


class UnresolvedSource(PacketError):
    """An external resource names a source no available resolution document locates (Part 04 §5.5).

    A fact rather than a defect: which mirrors a reader can reach is a property of the reader,
    so the packet is not invalid. It is raised when the bytes are actually asked for, and the
    resource is otherwise readable metadata.
    """
