"""Write Escapewheel packets.

`05`: **validation is importation**. Copying bytes is staging; a resource is imported only
once it has passed its checks. `PacketWriter` stages, validates, and commits in that order,
renaming the manifest last so a reader never finds a partial import claiming to be valid.

This package knows nothing about NWB or any other source. Adapters hand it records.
"""

from importlib.metadata import PackageNotFoundError, version

from .clock import Clock, NonFinite, OffGrid
from .writer import CommitRefused, PacketWriter

try:
    __version__ = version("escapewheel-writer")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

from .verify import verify

__all__ = ["Clock", "CommitRefused", "NonFinite", "OffGrid", "PacketWriter", "__version__", "verify"]
