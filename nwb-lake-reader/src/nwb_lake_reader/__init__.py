"""Read NWB-Lake packets.

A packet is a dataset bundle under a declared physical profile: Parquet tables, Zarr
arrays, and a JSON manifest binding them. This package opens one and provides tabular
access; it does not write packets and does not validate their contents beyond the
manifest's own shape.
"""

from __future__ import annotations

from importlib.metadata import version

from .errors import (
    ManifestError,
    PacketError,
    ResourceNotFoundError,
    ResourceUnreadableError,
    UnsupportedCodecError,
)
from .manifest import Manifest, Resource
from .packet import BASELINE_CODECS, Packet, Predicate, open_packet
from .resources import TableResource

__version__ = version("nwb-lake-reader")

__all__ = [
    "BASELINE_CODECS",
    "Manifest",
    "ManifestError",
    "Packet",
    "PacketError",
    "Predicate",
    "Resource",
    "ResourceNotFoundError",
    "ResourceUnreadableError",
    "TableResource",
    "UnsupportedCodecError",
    "__version__",
    "open_packet",
]
