"""Source adapters.

An adapter reads one source and returns records. It never writes: the packet is assembled by
:class:`~nwb_lake_writer.writer.PacketWriter`, which validates before it commits. That split
exists because no single source carries a whole session -- see
`inventory/nwb-zarr-776259-2025-04-09.md` §6.
"""

import warnings
from importlib.metadata import entry_points
from typing import Any

from .aind import AcquisitionStream, SessionSource
from .lfp import LFPSource
from .nwb import NWBSource, SourceDefect
from .sorter import SortedStream, SorterSource
from .sync import SyncSource, SyncStream
from .tables import TablesSource
from .waveforms import WaveformSource

#: Entry-point group a distribution registers a source adapter under. `07` names one CLI and the
#: three packages share it through `nwb_lake.commands`; a source is the same problem one layer
#: down -- an extension's table needs an adapter that knows a raw format this package never will.
#:
#: Registering one is what keeps declaring an extension from being harder than adding a column to
#: core, which is the gradient that leaves NWB's own multiple-TimeIntervals mechanism unused.
SOURCE_GROUP = "nwb_lake.sources"

#: The built-in kinds a recipe may name, by the name it names them. `session.build` maps a kind to
#: a constructed adapter; this maps it to the class, which is what R63 §2.1's `PRODUCES` hangs on
#: and what a recipe check reads with nothing open.
ADAPTERS: dict[str, Any] = {
    "session": SessionSource,
    "sorter": SorterSource,
    "sync": SyncSource,
    "nwb": NWBSource,
    "waveforms": WaveformSource,
    "lfp": LFPSource,
    "tables": TablesSource,
}


def discovered() -> dict[str, Any]:
    """Source kinds registered by installed distributions, by the name they claim.

    Each entry point loads to a callable taking `(root, **options)` and returning an adapter --
    the same shape the built-in kinds have, because a registered source is not a lesser one.

    A kind whose entry point fails to import is skipped with its reason, not raised: one broken
    third-party package must not make every other source unavailable.
    """
    found: dict[str, Any] = {}
    for entry in entry_points(group=SOURCE_GROUP):
        try:
            found[entry.name] = entry.load()
        except Exception as exc:  # noqa: BLE001 - a broken plugin is one kind, not the whole build
            warnings.warn(f"source kind {entry.name!r} could not be loaded: {exc}", stacklevel=2)
    return found


__all__ = [
    "ADAPTERS",
    "SOURCE_GROUP",
    "AcquisitionStream",
    "LFPSource",
    "NWBSource",
    "SessionSource",
    "SortedStream",
    "SorterSource",
    "SourceDefect",
    "SyncSource",
    "SyncStream",
    "TablesSource",
    "WaveformSource",
    "discovered",
]
