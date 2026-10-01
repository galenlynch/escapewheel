"""Read Escapewheel packets: Parquet tables, Zarr arrays, and the JSON manifest binding them.

Open a packet with :func:`open_packet`, or several as one relation with :func:`open_dataset`, then
pass it to the functions below. An access function takes ``(packet, ...)`` and returns a
`pyarrow.Table`; a semantics function such as :func:`on_clock` takes ``(packet, table)`` and returns
a table, so the two compose. The `Packet` methods of the same names are one-line delegates. The
documentation's Design page explains why each function exists.

Its modules:

access
    The commonest reads: :func:`intervals`, :func:`units`, :func:`events`, :func:`spike_times`.
alignment
    Spikes against events, per event or per spike.
axes
    What a dense array's positions and values mean.
channels
    The electrode a sorter's channel index names.
clocks
    Ticks onto one clock, and ticks to seconds.
dataset
    Many packets as one relation.
discriminators
    The rows a discriminator's kind names.
observation
    When something was observing, and rates over that span.
packet
    Opening one packet and reading its resources.
runs
    Which of several coexisting sortings or curations to read.
manifest, resources, location
    What the manifest declares, handles that read it, and where its bytes are.
errors
    What reading raises.
profile, descriptor, ordering, registries, dictionaries, sql, uri
    Shared with the writer and validator.
"""

from __future__ import annotations

from importlib.metadata import version

from .access import STORED, distinct, events, intervals, spike_times, units
from .alignment import aligned_spikes, assigned_spikes, windows_disjoint
from .axes import (
    ArrayDescription,
    Axis,
    IrregularAxis,
    LabelledAxis,
    NumericAxis,
    Scaling,
    TickAxis,
    describe,
)
from .channels import ChannelsUndeclared, electrode_at, kept_channels, runs_without_channels
from .clocks import BOUND, align, on_clock, origin, reference_clock, seconds
from .dataset import (
    PROJECTED,
    Dataset,
    Session,
    open_dataset,
    session_scoped,
)
from .discriminators import (
    Discriminator,
    Unresolved,
    declared,
    kinds,
    resolved,
    specialised,
    unresolved,
)
from .errors import (
    AmbiguousRun,
    ClockMismatch,
    EscapewheelError,
    ManifestError,
    MultiSessionUnresolved,
    NotAligned,
    NoTimeOrigin,
    PacketError,
    Refused,
    RegistryUnavailable,
    ResourceError,
    ResourceNotFoundError,
    ResourceUnreadableError,
    SourcesError,
    StaleSupport,
    Unanchored,
    UnresolvableAxis,
    UnresolvableChannelIndex,
    UnresolvedSource,
    UnsupportedCodecError,
)
from .location import Location, check_sources, read_sources, sources_schema
from .manifest import Manifest, RegistryBinding, Resource
from .observation import (
    clock_windows,
    observed_seconds,
    observed_ticks,
    rate,
    rate_of,
    stream_windows,
    support_of,
    unit_windows,
)
from .packet import Packet, Predicate, open_packet, resolve_sources
from .profile import interface_for, physical_profile
from .resources import ArrayResource, TableResource
from .runs import Ambiguity, ambiguities, preferred_run
from .sql import quote, sql_name

__version__ = version("escapewheel-reader")

__all__ = [
    "BOUND",
    "PROJECTED",
    "STORED",
    "Ambiguity",
    "AmbiguousRun",
    "ArrayDescription",
    "ArrayResource",
    "Axis",
    "ChannelsUndeclared",
    "ClockMismatch",
    "Dataset",
    "Discriminator",
    "EscapewheelError",
    "IrregularAxis",
    "LabelledAxis",
    "Location",
    "Manifest",
    "ManifestError",
    "MultiSessionUnresolved",
    "NoTimeOrigin",
    "NotAligned",
    "NumericAxis",
    "Packet",
    "PacketError",
    "Predicate",
    "Refused",
    "RegistryBinding",
    "RegistryUnavailable",
    "Resource",
    "ResourceError",
    "ResourceNotFoundError",
    "ResourceUnreadableError",
    "Scaling",
    "Session",
    "SourcesError",
    "StaleSupport",
    "TableResource",
    "TickAxis",
    "Unanchored",
    "UnresolvableAxis",
    "UnresolvableChannelIndex",
    "Unresolved",
    "UnresolvedSource",
    "UnsupportedCodecError",
    "__version__",
    "align",
    "aligned_spikes",
    "ambiguities",
    "assigned_spikes",
    "check_sources",
    "clock_windows",
    "declared",
    "describe",
    "distinct",
    "electrode_at",
    "events",
    "interface_for",
    "intervals",
    "kept_channels",
    "kinds",
    "observed_seconds",
    "observed_ticks",
    "on_clock",
    "open_dataset",
    "open_packet",
    "origin",
    "physical_profile",
    "preferred_run",
    "quote",
    "rate",
    "rate_of",
    "read_sources",
    "reference_clock",
    "resolve_sources",
    "resolved",
    "runs_without_channels",
    "seconds",
    "session_scoped",
    "sources_schema",
    "specialised",
    "spike_times",
    "sql_name",
    "stream_windows",
    "support_of",
    "unit_windows",
    "units",
    "unresolved",
    "windows_disjoint",
]
