"""What a source adapter in another distribution imports from the writer.

The contract a build holds an adapter to (Part 05 §3.4):

- :class:`SourceAdapter` -- what every adapter has.
- :class:`Streams`, :class:`StagesArrays`, :class:`ReferencesArrays`, :class:`ReferencesMedia`,
  :class:`StagesPayloads`, :class:`DeclaresCompensations`, :class:`WithholdsAnchors`,
  :class:`Located` -- one capability each, which a build tests for.

What an adapter returns and raises:

- :class:`StagedArray`, :class:`ExternalArray`, :class:`ExternalMedia`, :class:`Payload` -- an
  array the packet will own, an array or media it references, and an opaque payload.
- :class:`SourceDefect`, :class:`SourceFault`, :class:`UnsupportedEncoding` -- a source the
  adapter cannot read, its code, and a source stored in an encoding the adapter does not read.
- :class:`Note`, :class:`NoteCode`, :func:`coded`, :func:`codes` -- what an adapter worked around.
- :class:`Compensation`, :class:`Compensates`, :data:`COMPENSATION_GROUP` -- a registered
  workaround for a source defect, the mixin that records each one applied, and the entry-point
  group a distribution registers its own under.

What an adapter reads with:

- :class:`Clock`, :func:`epoch_from`, :func:`zone_of`, :data:`HARP_TICK_RATE_HZ`,
  :data:`TICK_MIN`, :data:`TICK_MAX` -- a declared clock and the ticks it converts to.
- :class:`SourceStore`, :func:`source_root` -- a source tree, local or remote, read once.
- :func:`sex`, :func:`utc_offset`, :func:`clean`, :data:`ABSENT` -- source spellings as the values
  a core column takes.
- :class:`SortedStream`, :data:`STREAM_FOLDER`, :data:`ANALYZERS` -- one stream folder of a
  SpikeInterface tree, the pattern its name follows, and the folder holding the analyzers.

How an adapter is found and run:

- :data:`SOURCE_GROUP`, :func:`discovered`, :data:`ADAPTERS` -- the entry-point group a
  distribution registers an adapter under, the adapters registered, and the built-in ones.
- :data:`STREAM`, :data:`FILES`, :data:`FLIGHT`, :data:`PROTOCOLS` -- the delivery protocols an
  adapter may declare (Part 12 §3), and all of them.
- :func:`document_of`, :func:`shape_problems`, :data:`TERMS` -- the declaration document a
  class generates, where one fails the published schema, and the terms a build supplies
  (Part 12 §4, §7).
- :func:`serve` -- deliver an opened adapter's rows by one protocol.
- :func:`build_table`, :func:`write_zarr` -- what a build makes of delivered rows and of a staged
  array, for an adapter that checks its output or writes its own delivery.

:class:`NWBSource` is the one adapter meant for subclassing, by a dialect of NWB. A dialect
extends the class tables `FRAME_AXES`, `FRAME_BASIS`, `UNIT_AXES`, `UNIT_FRAME`, `TRIAL_EVENTS`,
`TRIAL_MAPPED` and `CARRIED_ELECTRODE`, and overrides `device_identity`,
`local_electrode_label`, `signal_device_id`, `annotation` and `unit_identity`, each of which
reads the file through `attrs` and `table`.
"""

from .arrays import write_zarr
from .arrow import build_table
from .bindings import ExternalArray, ExternalMedia, StagedArray
from .clock import HARP_TICK_RATE_HZ, TICK_MAX, TICK_MIN, Clock, epoch_from, zone_of
from .declaration import FILES, FLIGHT, PROTOCOLS, STREAM, document_of, shape_problems
from .errors import SourceDefect, SourceFault, UnsupportedEncoding
from .notes import Note, NoteCode, coded, codes
from .opaque import Payload
from .protocols import (
    DeclaresCompensations,
    Located,
    ReferencesArrays,
    ReferencesMedia,
    SourceAdapter,
    StagesArrays,
    StagesPayloads,
    Streams,
    WithholdsAnchors,
)
from .recipe import TERMS
from .serving import serve
from .sources import ADAPTERS, SOURCE_GROUP, discovered
from .sources.compensations import COMPENSATION_GROUP, Compensates, Compensation
from .sources.nwb.names import ABSENT, clean
from .sources.nwb.source import NWBSource
from .sources.sorter import STREAM_FOLDER, SortedStream
from .sources.store import SourceStore, source_root
from .sources.values import sex, utc_offset
from .sources.waveforms import ANALYZERS

__all__ = [
    "ABSENT",
    "ADAPTERS",
    "ANALYZERS",
    "COMPENSATION_GROUP",
    "FILES",
    "FLIGHT",
    "HARP_TICK_RATE_HZ",
    "PROTOCOLS",
    "SOURCE_GROUP",
    "STREAM",
    "STREAM_FOLDER",
    "TERMS",
    "TICK_MAX",
    "TICK_MIN",
    "Clock",
    "Compensates",
    "Compensation",
    "DeclaresCompensations",
    "ExternalArray",
    "ExternalMedia",
    "Located",
    "NWBSource",
    "Note",
    "NoteCode",
    "Payload",
    "ReferencesArrays",
    "ReferencesMedia",
    "SortedStream",
    "SourceAdapter",
    "SourceDefect",
    "SourceFault",
    "SourceStore",
    "StagedArray",
    "StagesArrays",
    "StagesPayloads",
    "Streams",
    "UnsupportedEncoding",
    "WithholdsAnchors",
    "build_table",
    "clean",
    "coded",
    "codes",
    "discovered",
    "document_of",
    "epoch_from",
    "serve",
    "sex",
    "shape_problems",
    "source_root",
    "utc_offset",
    "write_zarr",
    "zone_of",
]
