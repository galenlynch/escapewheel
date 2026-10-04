"""Read Escapewheel packets: Parquet tables, Zarr arrays, and the JSON manifest binding them.

Open a packet with :func:`open_packet`, or several as one relation with :func:`open_packets`, then
pass it to the functions below. An access function takes ``(packet, ...)`` and returns a
`pyarrow.Table`; a semantics function such as :func:`on_clock` takes ``(packet, table)`` and returns
a table, so the two compose. `Packet` has no method doing what one of them does. The
documentation's Design page explains why each function exists.

Two tiers of names are public. The user tier is this module's ``__all__``. The support tier is for
another Escapewheel package: each name a module's ``__all__`` holds and this module does not
export. Any other name is the reader's own.

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
discriminators
    The rows a discriminator's kind names.
observation
    When something was observing, and rates over that span.
packet
    Opening one packet and reading its resources.
packet_set
    Many packets as one relation.
predicates
    Row constraints as Arrow expressions, on stored values or on a clock.
gathering
    A table's rows gathered into one row per key.
runs
    Which of several coexisting sortings or curations to read.
manifest, resources, location
    What the manifest declares, handles that read it, and where its bytes are.
errors
    What reading raises.
sql
    A resource's name in SQL.
protocols, resource_ids, profile, ordering, registries, uri, scripts.cli
    The support tier's own modules: what a function asks of a packet, resource IDs, the physical
    profile, stored order, registry acquisition, URI forms, and the command line the other
    packages extend.
descriptor, dictionaries, duck
    The reader's own: the profile descriptor's checks, dictionary-encoded columns, and a packet's
    tables in DuckDB.
"""

from __future__ import annotations

from importlib.metadata import version as _version

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
from .clocks import BOUND, align, attach_clocks, on_clock, origin, reference_clock, seconds, seconds_expression
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
    AxisFault,
    ClockMismatch,
    EscapewheelError,
    ManifestError,
    MultiSessionUnresolved,
    NotAligned,
    NotDeclared,
    NoTimeOrigin,
    PacketError,
    PhysicalProfileError,
    Refused,
    RegistryFault,
    RegistryUnavailable,
    ResourceError,
    ResourceNotFoundError,
    ResourceUnreadableError,
    SourcesError,
    StaleSupport,
    Unanchored,
    Unordered,
    UnresolvableAxis,
    UnresolvableChannelIndex,
    UnresolvedSource,
    UnsupportedCodecError,
)
from .gathering import ragged
from .location import Location, check_sources, read_sources
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
from .packet import Packet, open_packet
from .packet_set import PacketSet, Session, open_packets
from .predicates import tick_bounds, tick_range, where
from .resources import ArrayResource, TableResource, read_pool
from .runs import Ambiguity, ambiguities, preferred_run
from .sql import quote, sql_name

__version__ = _version("escapewheel-reader")

__all__ = [
    "BOUND",
    "STORED",
    "Ambiguity",
    "AmbiguousRun",
    "ArrayDescription",
    "ArrayResource",
    "Axis",
    "AxisFault",
    "ChannelsUndeclared",
    "ClockMismatch",
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
    "NotDeclared",
    "NumericAxis",
    "Packet",
    "PacketError",
    "PacketSet",
    "PhysicalProfileError",
    "Refused",
    "RegistryBinding",
    "RegistryFault",
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
    "Unordered",
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
    "attach_clocks",
    "check_sources",
    "clock_windows",
    "declared",
    "describe",
    "distinct",
    "electrode_at",
    "events",
    "intervals",
    "kept_channels",
    "kinds",
    "observed_seconds",
    "observed_ticks",
    "on_clock",
    "open_packet",
    "open_packets",
    "origin",
    "preferred_run",
    "quote",
    "ragged",
    "rate",
    "rate_of",
    "read_pool",
    "read_sources",
    "reference_clock",
    "resolved",
    "runs_without_channels",
    "seconds",
    "seconds_expression",
    "specialised",
    "spike_times",
    "sql_name",
    "stream_windows",
    "support_of",
    "tick_bounds",
    "tick_range",
    "unit_windows",
    "units",
    "unresolved",
    "where",
    "windows_disjoint",
]
