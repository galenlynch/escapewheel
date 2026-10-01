"""Every exception this package raises on purpose; each derives from :class:`PacketError`.

- :class:`EscapewheelError` -- the base the validator's and the writer's errors share.
- :class:`ManifestError`, :class:`SourcesError` -- the manifest, or a source resolution document,
  is absent, unparsable, or of the wrong shape.
- :class:`RegistryUnavailable` -- a bound registry cannot be acquired or fails its digest.
- :class:`ResourceError` -- one resource cannot be read, and the rest of the packet can:
  :class:`ResourceNotFoundError`, :class:`ResourceUnreadableError`,
  :class:`UnsupportedCodecError`, :class:`UnresolvedSource`.
- :class:`Refused` -- the data is readable and the operation asked of it has no one right answer:
  :class:`NoTimeOrigin`, :class:`AmbiguousRun`, :class:`UnresolvableChannelIndex`,
  :class:`UnresolvableAxis`, :class:`MultiSessionUnresolved`, :class:`NotAligned`,
  :class:`Unanchored`, :class:`ClockMismatch`, :class:`StaleSupport`.
- :class:`PhysicalProfileError` -- the bundled profile descriptor is malformed or inconsistent.
"""

from __future__ import annotations


class EscapewheelError(Exception):
    """Base class for every error an Escapewheel package raises on purpose."""


class PacketError(EscapewheelError):
    """Base class for every error raised by this package."""


class ManifestError(PacketError):
    """The packet manifest is absent, unparsable, or does not conform to its schema."""


class SourcesError(ManifestError):
    """A source resolution document is unparsable, of an unknown version, or fails its schema."""


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


class ResourceError(PacketError):
    """One resource cannot be read, which leaves every other resource of the packet readable.

    Attributes
    ----------
    resource_id : str or None
        The resource, or None where the error was raised below the point that knows it.
    source : str or None
        The named source the resource's location is relative to, where it has one.
    """

    def __init__(self, message: str, *, resource_id: str | None = None, source: str | None = None) -> None:
        super().__init__(message)
        self.resource_id = resource_id
        self.source = source


class ResourceNotFoundError(ResourceError):
    """A resource was requested that the manifest does not declare."""


class ResourceUnreadableError(ResourceError):
    """A declared resource does not resolve to a readable file."""


class UnsupportedCodecError(ResourceError):
    """The reader cannot decode a codec one resource uses (Part 03 §6.4).

    Raised when the resource's values are asked for, never when the packet opens, so only that
    resource fails.

    Attributes
    ----------
    outside_floor : bool or None
        Whether the resource lies outside its interface's reader floor. False means this
        installation lacks a feature every conforming reader supports, so the installation is
        what to repair; True means the packet chose a feature beyond the portability guarantee.
        None where the metadata is reachable only through Zarr, which just failed to read it.
    """

    def __init__(self, resource_id: str, message: str, *, outside_floor: bool | None) -> None:
        super().__init__(f"{resource_id}: {message}", resource_id=resource_id)
        self.outside_floor = outside_floor


class UnresolvedSource(ResourceError):
    """An external resource names a source no available resolution document locates (Part 04 §5.5).

    A fact rather than a defect: which mirrors a reader can reach is a property of the reader,
    so the packet is not invalid. It is raised when the bytes are actually asked for, and the
    resource is otherwise readable metadata.
    """


class Refused(PacketError):
    """The data is readable, and the operation asked of it has no one right answer.

    Each subclass names a case where every fallback is plausible and wrong, so the reader raises
    in place of choosing one.
    """


class NoTimeOrigin(Refused):
    """The packet declares no `t_zero_tick`, so seconds are not defined (Part 01 §2.2).

    Tick zero, the session's wall-clock start and the first datum are all available and all
    wrong. A consumer that picks one silently produces numbers that cannot be compared with
    another consumer's, so this is raised instead.
    """


class AmbiguousRun(Refused):
    """Several runs produced the same thing and the packet does not say which to read.

    Part 01 §2.6. Reading them all concatenated is the failure this prevents: two sortings of one
    probe are two complete sets of units, so every count taken over both is wrong and nothing
    about the result says so. Picking the newest, or the first, produces numbers that cannot be
    compared with another consumer's.
    """


class UnresolvableChannelIndex(Refused):
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


class UnresolvableAxis(Refused):
    """An array's declared coordinates or scaling do not determine one answer.

    Raised rather than falling back to positions, because every fallback is plausible: another
    array's labels, labels in storage order, or a padding position read as a row.
    """


class MultiSessionUnresolved(Refused):
    """A packet holds several sessions and a scoped table cannot say which row is whose.

    Part 05 §13.1 requires a discriminator on every session-scoped table a reader presents. Part
    02 §7.1 requires every such table to carry `session_id`, so a conforming packet cannot reach
    this; a packet that lacks the column can, and its rows cannot be attributed.
    """


class NotAligned(Refused, ValueError):
    """A clock the spikes are on has no anchors, so its ticks reach no reference."""


class Unanchored(Refused, ValueError):
    """A clock has too few anchors to define a mapping.

    Two anchors define a segment but no median interval worth trusting, so the bound would
    rest on a single observation.
    """


class ClockMismatch(Refused, ValueError):
    """The spikes and the events are counted on different clocks.

    A tick has no meaning beside a tick on another clock, so comparing them would return rows
    that look right and are not. An event stream on another clock has to be mapped first.
    """


class StaleSupport(Refused, ValueError):
    """A table carries a support that no longer describes it.

    Raised when the row count has changed since the support was attached -- a filter, a slice
    or a concatenation. The support itself is still true of the thing it was read for; it is
    the association with *these rows* that has broken, so re-read rather than adjust.
    """


class PhysicalProfileError(PacketError, ValueError):
    """The physical-profile descriptor is malformed or internally inconsistent."""
