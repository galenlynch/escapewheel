"""The conformance corpus's packets, each declared once as a record."""

from .amendments import AMENDMENT_PACKETS
from .axes import AXIS_PACKETS
from .devices import DEVICE_PACKETS
from .digests import DIGEST_PACKETS
from .floors import FLOOR_PACKETS
from .intervals import INTERVAL_PACKETS
from .opaque import OPAQUE_PACKETS
from .record import Packet
from .replacements import REPLACEMENT_PACKETS
from .rows import ROW_PACKETS
from .schema import SCHEMA_PACKETS
from .session import VALID
from .sidecars import SIDECAR_PACKETS
from .spikes import SPIKE_PACKETS
from .subsets import SUBSET_PACKETS
from .units import UNIT_PACKETS

#: Every packet of the corpus, in the order it is written.
PACKETS: tuple[Packet, ...] = (
    VALID,
    *ROW_PACKETS,
    *SCHEMA_PACKETS,
    *SUBSET_PACKETS,
    *DIGEST_PACKETS,
    *FLOOR_PACKETS,
    *AXIS_PACKETS,
    *INTERVAL_PACKETS,
    *DEVICE_PACKETS,
    *UNIT_PACKETS,
    *OPAQUE_PACKETS,
    *AMENDMENT_PACKETS,
    *REPLACEMENT_PACKETS,
    *SPIKE_PACKETS,
    *SIDECAR_PACKETS,
)
if len({packet.name for packet in PACKETS}) != len(PACKETS):
    raise SystemExit("two packets of the corpus share a name")
