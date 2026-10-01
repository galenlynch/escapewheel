"""Exceptions raised when reading a packet; each derives from :class:`PacketError`.

- :class:`ManifestError` -- the manifest is absent, unparsable, or of the wrong shape.
- :class:`RegistryUnavailable` -- a bound registry cannot be acquired or fails its digest.
- :class:`ResourceNotFoundError`, :class:`ResourceUnreadableError` -- a resource is undeclared,
  or does not resolve to readable bytes.
- :class:`UnsupportedCodecError` -- an array uses a codec the installed Zarr cannot decode.
- :class:`NoTimeOrigin` -- seconds were asked for and the packet declares no origin.
- :class:`AmbiguousRun` -- several runs produced the same thing and none is preferred.
- :class:`UnresolvableChannelIndex` -- a channel index names no electrode of its run.
- :class:`UnresolvedSource` -- no resolution document locates a named source.
"""

from __future__ import annotations


class PacketError(Exception):
    """Base class for every error raised by this package."""


class ManifestError(PacketError):
    """The packet manifest is absent, unparsable, or does not conform to its schema."""


class RegistryUnavailable(PacketError):
    """A bound registry cannot be used to resolve a declaration (Part 04 §10).

    Raised by the operation that needed the registry, never when the packet opens, so reading a
    resource no unavailable registry declares still works.

    Attributes
    ----------
    registry_id : str
        The descriptor's name in the manifest's `registries` map.
    reason : str
        ``missing``, ``unreadable``, or ``digest``, as Part 04 §10 names them, or ``invalid``
        where the verified bytes are not a JSON object.
    """

    def __init__(self, registry_id: str, reason: str, message: str) -> None:
        super().__init__(f"registry {registry_id!r}: {message}")
        self.registry_id = registry_id
        self.reason = reason


class ResourceNotFoundError(PacketError):
    """A resource was requested that the manifest does not declare."""


class ResourceUnreadableError(PacketError):
    """A declared resource does not resolve to a readable file."""


class UnsupportedCodecError(PacketError):
    """The reader cannot decode a codec one resource uses (Part 03 §6.1).

    Raised when the resource's values are asked for, never when the packet opens, so only that
    resource fails.

    Attributes
    ----------
    resource_id : str
        The resource that cannot be read.
    outside_floor : bool or None
        Whether the resource lies outside its interface's reader floor (Part 03 §6.4). False means
        this installation lacks a feature every conforming reader supports, so the installation is
        what to repair; True means the packet chose a feature beyond the portability guarantee.
        None where the metadata is reachable only through Zarr, which just failed to read it.
    """

    def __init__(self, resource_id: str, message: str, *, outside_floor: bool | None) -> None:
        super().__init__(f"{resource_id}: {message}")
        self.resource_id = resource_id
        self.outside_floor = outside_floor


class NoTimeOrigin(PacketError):
    """The packet declares no `t_zero_tick`, so seconds are not defined (Part 01 §2.2).

    Tick zero, the session's wall-clock start and the first datum are all available and all
    wrong. A consumer that picks one silently produces numbers that cannot be compared with
    another consumer's, so this is raised instead.
    """


class AmbiguousRun(PacketError):
    """Several runs produced the same thing and the packet does not say which to read.

    Part 01 §2.6. Reading them all concatenated is the failure this prevents: two sortings of one
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
