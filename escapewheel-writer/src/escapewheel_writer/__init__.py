"""Build Escapewheel packets from a recipe (Part 05 §2).

:func:`import_packet` builds the packet a :class:`Recipe` describes and commits it, as
``escapewheel import`` does from the command line. Its two steps are :func:`build`, which runs the
recipe's sources and returns a :class:`PacketWriter` holding the staged packet, and
:meth:`PacketWriter.commit`, which validates and publishes it and takes what
:func:`materializers` derives from a recipe; a caller holding no recipe passes
:func:`materialize_spike_events` itself. :func:`verify` records what a published packet's external
resources hold, once they can be reached, and :func:`prune` removes the files a packet no longer
needs.

A source adapter in another distribution imports from :mod:`escapewheel_writer.adapter`. Every
other module is the package's own.

Its modules:

recipe
    Parse and check a recipe before any source opens.
session
    Order a recipe's sources, run them, and keep what each one owns.
writer
    Stage records, validate the staged packet, and commit it.
sources
    One adapter per source format, each returning records.
keys, clock, arrow, encoding
    Assigned identifiers, ticks on a declared clock, Arrow tables in the registry's types, and
    column encodings.
arrays, opaque
    Packet-owned Zarr arrays and opaque payloads.
materialize
    The analysis tables derived from core.
amending, replacing, compare
    A recipe that amends a packet or replaces others.
declaration, delivery
    An adapter's declarations as a document, and the protocols that deliver its rows.
extensions, scaffold
    Finding an extension's registry document, and drafting one.
verify, prune
    Recording what external resources hold, and removing files a packet no longer needs.
errors
    Every exception the package raises on purpose.

Notes
-----
    What an adapter or a build worked around, each with a code.

A resource is imported only once it has passed validation (Part 05 §2), so a commit renames the
manifest into place last.
"""

from importlib.metadata import PackageNotFoundError, version

from .errors import (
    AmendmentFault,
    AmendmentRefused,
    CarriedNotAnInteger,
    Collided,
    CommitRefused,
    CompensationsInvalid,
    DeclarationUnreadable,
    DeliveryFailed,
    ExtensionNotFound,
    FixedOffsetZone,
    MaterializerNotFound,
    NaiveTimestamp,
    NonFinite,
    NotCommitted,
    NotesUnderStrict,
    OffGrid,
    OutOfRange,
    PacketOccupied,
    PayloadFault,
    PayloadProblem,
    PayloadRefused,
    PromotionRecordUnreadable,
    RecipeError,
    RecipeFault,
    RecipeUnreadable,
    RecipeUnsound,
    ReplacementRefused,
    SourceDefect,
    SourceFault,
    SourcesNotOrdered,
    TermUnfilled,
    TickOverflow,
    UndeclaredResource,
    UnknownCompensation,
    UnknownSourceKind,
    UnsupportedEncoding,
    UsageError,
    UsageFault,
    WriterError,
)
from .materialize import materialize_spike_events
from .notes import Note, NoteCode
from .prune import prune
from .recipe import Recipe
from .session import build, import_packet, materializers
from .writer import PacketWriter

try:
    __version__ = version("escapewheel-writer")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

from .verify import verify

__all__ = [
    "AmendmentFault",
    "AmendmentRefused",
    "CarriedNotAnInteger",
    "Collided",
    "CommitRefused",
    "CompensationsInvalid",
    "DeclarationUnreadable",
    "DeliveryFailed",
    "ExtensionNotFound",
    "FixedOffsetZone",
    "MaterializerNotFound",
    "NaiveTimestamp",
    "NonFinite",
    "NotCommitted",
    "Note",
    "NoteCode",
    "NotesUnderStrict",
    "OffGrid",
    "OutOfRange",
    "PacketOccupied",
    "PacketWriter",
    "PayloadFault",
    "PayloadProblem",
    "PayloadRefused",
    "PromotionRecordUnreadable",
    "Recipe",
    "RecipeError",
    "RecipeFault",
    "RecipeUnreadable",
    "RecipeUnsound",
    "ReplacementRefused",
    "SourceDefect",
    "SourceFault",
    "SourcesNotOrdered",
    "TermUnfilled",
    "TickOverflow",
    "UndeclaredResource",
    "UnknownCompensation",
    "UnknownSourceKind",
    "UnsupportedEncoding",
    "UsageError",
    "UsageFault",
    "WriterError",
    "__version__",
    "build",
    "import_packet",
    "materialize_spike_events",
    "materializers",
    "prune",
    "verify",
]
