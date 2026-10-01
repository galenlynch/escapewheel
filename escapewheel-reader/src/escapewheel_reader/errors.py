"""Every exception this package raises on purpose; each derives from :class:`PacketError`.

- :class:`EscapewheelError` -- the base the validator's and the writer's errors share.
- :class:`ManifestError`, :class:`SourcesError` -- the manifest, or a source resolution document,
  is absent, unparsable, or of the wrong shape.
- :class:`RegistryUnavailable` -- a bound registry cannot be acquired or fails its digest, for
  one :class:`RegistryFault`.
- :class:`ResourceError` -- one resource cannot be read, and the rest of the packet can:
  :class:`ResourceNotFoundError`, :class:`ResourceUnreadableError`,
  :class:`UnsupportedCodecError`, :class:`UnresolvedSource`.
- :class:`Refused` -- the data is readable and the operation asked of it has no one right answer:
  :class:`NoTimeOrigin`, :class:`AmbiguousRun`, :class:`UnresolvableChannelIndex`,
  :class:`UnresolvableAxis`, :class:`MultiSessionUnresolved`, :class:`NotAligned`,
  :class:`Unanchored`, :class:`ClockMismatch`, :class:`StaleSupport`.
- :class:`NotDeclared` -- what was asked for is declared by neither the packet nor its registry.
- :class:`PhysicalProfileError` -- the bundled profile descriptor is malformed or inconsistent.
"""

from __future__ import annotations

from enum import StrEnum


class EscapewheelError(Exception):
    """Base class for every error an Escapewheel package raises on purpose."""


class PacketError(EscapewheelError):
    """Base class for every error raised by this package."""


class ManifestError(PacketError):
    """The packet manifest is absent, unparsable, or does not conform to its schema."""


class SourcesError(ManifestError):
    """A source resolution document is unparsable, of an unknown version, or fails its schema."""


class RegistryFault(StrEnum):
    """Why a bound registry cannot be used.

    Acquiring a registry fails as `MISSING`, `UNREADABLE` or `DIGEST`, the three outcomes
    Part 04 §10 names; parsing the acquired bytes fails as `INVALID`.
    """

    #: Nothing is stored at the descriptor's path, or the manifest binds no such registry.
    MISSING = "missing"
    #: The stored copy cannot be read or does not decode as the physical profile requires.
    UNREADABLE = "unreadable"
    #: The decoded bytes do not match the descriptor's `sha256`.
    DIGEST = "digest"
    #: The verified bytes are not a JSON object.
    INVALID = "invalid"


class RegistryUnavailable(PacketError):
    """A bound registry cannot be used to resolve a declaration (Part 04 §10).

    Raised by the operation that needed the registry, never when the packet opens, so reading a
    resource no unavailable registry declares still works.

    Attributes
    ----------
    registry_id : str
        The descriptor's name in the manifest's `registries` map.
    reason : RegistryFault
        Which of the closed set of causes applies.
    """

    def __init__(self, registry_id: str, reason: RegistryFault, message: str) -> None:
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


class AxisFault(StrEnum):
    """Why an array's declarations do not determine its axes or its scaling."""

    #: The resource is not declared as a dense array.
    NOT_AN_ARRAY = "not_an_array"
    #: The declaration has no catalog, or other than one catalog row names the array.
    UNCATALOGUED = "uncatalogued"
    #: The axes table does not declare each of the array's axes once.
    AXES_UNDECLARED = "axes_undeclared"
    #: An axis declares other than one coordinate form.
    FORM_COUNT = "form_count"
    #: An axis declares an origin without the step, clock or unit that completes it.
    FORM_INCOMPLETE = "form_incomplete"
    #: An axis depends on an axis that itself depends on another.
    DEPENDENCY_CHAIN = "dependency_chain"
    #: An axis depends on another and has no labels to vary with it.
    DEPENDENCY_UNLABELLED = "dependency_unlabelled"
    #: The packet holds no label table, or not the table an axis's labels name rows of.
    LABELS_ABSENT = "labels_absent"
    #: An axis has other than one label row at each position.
    LABEL_COUNT = "label_count"
    #: A label names no row of the table it stands for.
    LABEL_UNMATCHED = "label_unmatched"
    #: An axis's coordinate array is uncatalogued or of the wrong shape.
    COORDINATE_ARRAY = "coordinate_array"
    #: Scaling is declared on the array and per channel.
    SCALING_LEVELS = "scaling_levels"
    #: Channels are scaled on other than one axis.
    SCALING_AXIS = "scaling_axis"
    #: Some channels of the scaled axis have no scaling row.
    SCALING_COVERAGE = "scaling_coverage"
    #: A channel is converted into no unit.
    SCALING_UNIT_ABSENT = "scaling_unit_absent"
    #: The array's declared unit and its channels' units differ.
    SCALING_UNIT_DISAGREES = "scaling_unit_disagrees"


class UnresolvableAxis(Refused):
    """An array's declared coordinates or scaling do not determine one answer.

    Raised rather than falling back to positions, because every fallback is plausible: another
    array's labels, labels in storage order, or a padding position read as a row.

    Attributes
    ----------
    reason : AxisFault
        Which declaration is at fault.
    """

    def __init__(self, reason: AxisFault, message: str) -> None:
        super().__init__(message)
        self.reason = reason


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


class NotDeclared(PacketError, LookupError):
    """What was asked for is declared by neither the packet nor its registry.

    A stream of an event type, a run for a scope, a discriminator on a table, a reference between
    two tables, a clock's tick rate, or a table's support. The packet is readable; the thing named
    is not in it.
    """


class PhysicalProfileError(PacketError, ValueError):
    """The physical-profile descriptor is malformed or internally inconsistent."""
