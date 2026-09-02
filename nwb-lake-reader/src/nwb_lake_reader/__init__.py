"""Read NWB-Lake packets.

A packet is a dataset bundle under a declared physical profile: Parquet tables, Zarr
arrays, and a JSON manifest binding them. This package opens one and provides tabular
access; it does not write packets and does not validate their contents beyond the
manifest's own shape.
"""

from __future__ import annotations

from importlib.metadata import version

from .alignment import ClockMismatch, aligned_spikes, assigned_spikes, windows_disjoint
from .clocks import BOUND, NotAligned, Unanchored, align
from .errors import (
    AmbiguousRun,
    ManifestError,
    NoTimeOrigin,
    PacketError,
    ResourceNotFoundError,
    ResourceUnreadableError,
    UnsupportedCodecError,
)
from .manifest import Manifest, Resource
from .packet import BASELINE_CODECS, STORED, Packet, Predicate, open_packet
from .resources import ArrayResource, TableResource
from .runs import Ambiguity, ambiguities, preferred_run
from .sql import quote, sql_name

__version__ = version("nwb-lake-reader")

__all__ = [
    "BASELINE_CODECS",
    "BOUND",
    "STORED",
    "Ambiguity",
    "AmbiguousRun",
    "ArrayResource",
    "ClockMismatch",
    "Manifest",
    "ManifestError",
    "NoTimeOrigin",
    "NotAligned",
    "Packet",
    "PacketError",
    "Predicate",
    "Resource",
    "ResourceNotFoundError",
    "ResourceUnreadableError",
    "TableResource",
    "Unanchored",
    "UnsupportedCodecError",
    "__version__",
    "align",
    "aligned_spikes",
    "ambiguities",
    "assigned_spikes",
    "open_packet",
    "preferred_run",
    "quote",
    "sql_name",
    "windows_disjoint",
]
