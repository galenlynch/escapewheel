"""Source adapters.

An adapter reads one source and returns records. It never writes: the packet is assembled by
:class:`~nwb_lake_writer.writer.PacketWriter`, which validates before it commits. That split
exists because no single source carries a whole session -- see
`inventory/nwb-zarr-776259-2025-04-09.md` §6.
"""

from .aind import AcquisitionStream, SessionSource
from .nwb import NWBSource, SourceDefect

__all__ = ["AcquisitionStream", "NWBSource", "SessionSource", "SourceDefect"]
