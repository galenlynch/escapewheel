"""Build Escapewheel packets from a recipe (Part 05 §2).

:func:`build` runs the sources a :class:`Recipe` names and returns a :class:`PacketWriter` holding
the staged packet, and :meth:`PacketWriter.commit` validates and publishes it. ``escapewheel
import`` runs the same two steps from the command line. :func:`verify` records what a published
packet's external resources hold, once they can be reached.

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

from .clock import Clock
from .errors import CommitRefused, NonFinite, OffGrid
from .recipe import Recipe
from .session import build
from .writer import PacketWriter

try:
    __version__ = version("escapewheel-writer")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

from .verify import verify

__all__ = [
    "Clock",
    "CommitRefused",
    "NonFinite",
    "OffGrid",
    "PacketWriter",
    "Recipe",
    "__version__",
    "build",
    "verify",
]
