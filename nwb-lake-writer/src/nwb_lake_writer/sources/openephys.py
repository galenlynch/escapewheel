"""The acquisition chain Open Ephys records, and the versions each element reports.

`settings.xml` describes every probe as a chain: a PXI **basestation** in a slot, a **connect
board** on that basestation, a **headstage** on a port, and the probe itself. Three of those four
report their own firmware or hardware version, and the versions differ within one session -- so a
packet recording only the probe cannot say that two probes ran different acquisition hardware.

R66 §2.3 makes each element that reports its own versions a device in its own right. This adapter
emits those three and **not the probe**, whose device row comes from the NWB: two sources writing
one row would collide on its key, and the NWB knows the probe's own part number and serial.

Identity comes from physical position, because the serial numbers do not supply it. Every
`bs_serial_number`, `bsc_serial_number` and `headstage_serial_number` in the measured session is
`0`. A slot identifies a basestation and its connect board; a slot and port identify a headstage,
which is what makes seven headstages out of ten probe streams: a quad-base probe presents four
streams from one part number, one serial, and one headstage.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

#: The file Open Ephys writes beside a recording, one per record node.
SETTINGS = "settings.xml"

#: Each element of the chain: how its identity is formed, and which attributes describe it.
#: `flex_version` is the headstage's hardware revision -- the flex is the part it names.
CHAIN = (
    ("basestation", ("slot",), "bs_part_number", "bs_serial_number", "bs_firmware_version", "bs_hardware_version"),
    (
        "connect_board",
        ("slot",),
        "bsc_part_number",
        "bsc_serial_number",
        "bsc_firmware_version",
        "bsc_hardware_version",
    ),
    ("headstage", ("slot", "port"), "headstage_part_number", "headstage_serial_number", None, "flex_version"),
)

#: What a source writes where it has no value. Recorded as given rather than as null, because a
#: source that reported `UNKNOWN` said something a source that stayed silent did not (R66 §2.1).
UNSET = {"", "0"}


class OpenEphysSource:
    """`core.devices`, one row per element of the acquisition chain that reports a version.

    Parameters
    ----------
    root : str or Path
        A directory holding record nodes, a record node itself, or a `settings.xml`.
    session_id : str
        The session this hardware was used in.
    """

    #: R63 §2.1: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset({"core.devices"})

    def __init__(self, root: str | Path, *, session_id: str) -> None:
        self.root = Path(root)
        self.session_id = session_id
        self.notes: list[str] = []

    def settings(self) -> list[Path]:
        """Every `settings.xml` under `root`, sorted so two runs read them in one order."""
        if self.root.is_file():
            return [self.root]
        if (self.root / SETTINGS).is_file():
            return [self.root / SETTINGS]
        return sorted(self.root.glob(f"*/{SETTINGS}"))

    def _probes(self) -> list[dict[str, str]]:
        """Every `NP_PROBE` element's attributes, across every record node."""
        found = []
        for path in self.settings():
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError as exc:
                self.notes.append(f"{path}: not parseable as XML ({exc}); skipped")
                continue
            found.extend(element.attrib for element in root.findall(".//NP_PROBE"))
        return found

    def devices(self) -> list[dict[str, Any]]:
        """`core.devices`, one row per distinct chain element (R66 §2.3)."""
        rows: dict[str, dict[str, Any]] = {}
        for probe in self._probes():
            for kind, key, part, serial, firmware, hardware in CHAIN:
                if any(probe.get(k) is None for k in key):
                    continue
                identifier = ".".join([kind, *(f"{k}{probe[k]}" for k in key)])
                if identifier in rows:
                    continue
                rows[identifier] = {
                    "device_id": identifier,
                    "session_id": self.session_id,
                    "name": identifier,
                    # Open Ephys reports the part, not who made it. IMEC makes the Neuropixels
                    # chain, but the file does not say so and this adapter does not add it.
                    "manufacturer": None,
                    "model": _stated(probe.get(part)),
                    "firmware_version": _stated(probe.get(firmware)) if firmware else None,
                    "hardware_version": _stated(probe.get(hardware)),
                    "serial_number": _stated(probe.get(serial)),
                    "metadata": {k: probe[k] for k in key if k in probe} or None,
                }
        return [rows[name] for name in sorted(rows)]

    def offers(self) -> dict[str, int]:
        """`05` Stage 1: how many rows of each resource this root holds."""
        return {"core.devices": len(self.devices())}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID."""
        built = {"core.devices": self.devices()}
        return {resource: rows for resource, rows in built.items() if rows}


def _stated(value: str | None) -> str | None:
    """Return what the file said, or None where it said nothing.

    `UNKNOWN` is kept: a source reporting that it does not know is not the same as a source that
    was never asked, and R66 §2.1 records the value verbatim either way. A serial of `0` is
    dropped, because it is this file's way of leaving the field blank rather than a serial.
    """
    return None if value is None or value in UNSET else value


__all__ = ["CHAIN", "SETTINGS", "OpenEphysSource"]
