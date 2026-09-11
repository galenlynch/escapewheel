"""Read Escapewheel packets.

A packet is a dataset bundle under a declared physical profile: Parquet tables, Zarr
arrays, and a JSON manifest binding them. This package opens one and provides tabular
access; it does not write packets and does not validate their contents beyond the
manifest's own shape.
"""

from __future__ import annotations

from importlib.metadata import version

from .alignment import ClockMismatch, aligned_spikes, assigned_spikes, windows_disjoint
from .clocks import BOUND, NotAligned, Unanchored, align, on_clock, origin, seconds
from .dataset import (
    PROJECTED,
    Dataset,
    MultiSessionUnresolved,
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
    ManifestError,
    NoTimeOrigin,
    PacketError,
    ResourceNotFoundError,
    ResourceUnreadableError,
    UnresolvedSource,
    UnsupportedCodecError,
)
from .location import Location, read_sources
from .manifest import Manifest, Resource, sources_schema
from .observation import (
    StaleSupport,
    clock_windows,
    observed_seconds,
    observed_ticks,
    rate,
    rate_of,
    stream_windows,
    support_of,
    unit_windows,
)
from .packet import BASELINE_CODECS, DECODABLE, STORED, Packet, Predicate, open_packet, resolve_sources
from .resources import ArrayResource, TableResource
from .runs import Ambiguity, ambiguities, preferred_run
from .sql import quote, sql_name

__version__ = version("escapewheel-reader")

__all__ = [
    "BASELINE_CODECS",
    "BOUND",
    "DECODABLE",
    "PROJECTED",
    "STORED",
    "Ambiguity",
    "AmbiguousRun",
    "ArrayResource",
    "ClockMismatch",
    "Dataset",
    "Discriminator",
    "Location",
    "Manifest",
    "ManifestError",
    "MultiSessionUnresolved",
    "NoTimeOrigin",
    "NotAligned",
    "Packet",
    "PacketError",
    "Predicate",
    "Resource",
    "ResourceNotFoundError",
    "ResourceUnreadableError",
    "Session",
    "StaleSupport",
    "TableResource",
    "Unanchored",
    "Unresolved",
    "UnresolvedSource",
    "UnsupportedCodecError",
    "__version__",
    "align",
    "aligned_spikes",
    "ambiguities",
    "assigned_spikes",
    "clock_windows",
    "declared",
    "kinds",
    "observed_seconds",
    "observed_ticks",
    "on_clock",
    "open_dataset",
    "open_packet",
    "origin",
    "preferred_run",
    "quote",
    "rate",
    "rate_of",
    "read_sources",
    "resolve_sources",
    "resolved",
    "seconds",
    "session_scoped",
    "sources_schema",
    "specialised",
    "sql_name",
    "stream_windows",
    "support_of",
    "unit_windows",
    "unresolved",
    "windows_disjoint",
]
