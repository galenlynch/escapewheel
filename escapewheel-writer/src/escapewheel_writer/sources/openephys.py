"""The acquisition chain Open Ephys records, and the versions each element reports.

`settings.xml` describes every probe as a chain: a PXI **basestation** in a slot, a **connect
board** on that basestation, a **headstage** on a port, and the probe itself. Three of those four
report their own firmware or hardware version, and the versions differ within one session -- so a
packet recording only the probe cannot say that two probes ran different acquisition hardware.

Part 01 §3.5 makes each element that reports its own versions a device in its own right. This adapter
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
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

from .store import source_root

#: The file Open Ephys writes beside a recording, one per record node.
SETTINGS = "settings.xml"

#: Each element of the chain: how its identity is formed, which attributes describe it, what it
#: hangs off (Part 01 §3.5), and which attribute names the coordinate it hangs off at (R85 §2.1). A
#: basestation is the root -- the PXI chassis it sits in is not described by this file, and
#: inventing a device for it would assert something unmeasured. A connect board has a parent and
#: no coordinate: `slot` identifies the basestation and the board alike, so the file states no
#: place on the one where the other sits, and R85 §2.1 wants that left null rather than invented.
CHAIN = (
    (
        "basestation",
        ("slot",),
        "bs_part_number",
        "bs_serial_number",
        "bs_firmware_version",
        "bs_hardware_version",
        None,
        None,
    ),
    (
        "connect_board",
        ("slot",),
        "bsc_part_number",
        "bsc_serial_number",
        "bsc_firmware_version",
        "bsc_hardware_version",
        ("basestation", ("slot",)),
        None,
    ),
    (
        "headstage",
        ("slot", "port"),
        "headstage_part_number",
        "headstage_serial_number",
        None,
        "flex_version",
        ("connect_board", ("slot",)),
        "port",
    ),
)

#: Which attribute names the dock a probe sat in. The probe's own device row comes from the NWB,
#: so its port is handed over by `attachments` rather than written here.
PROBE_PORT = "dock"

#: What a source writes where it has no value. Recorded as given rather than as null, because a
#: source that reported `UNKNOWN` said something a source that stayed silent did not (Part 01 §3.5).
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

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset({"core.devices"})

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    def __init__(self, root: str | Path, *, session_id: str) -> None:
        self.root = source_root(root)
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
        """`core.devices`, one row per distinct chain element (Part 01 §3.5)."""
        rows: dict[str, dict[str, Any]] = {}
        for probe in self._probes():
            for kind, key, part, serial, firmware, hardware, parent, port in CHAIN:
                if any(probe.get(k) is None for k in key):
                    continue
                identifier = _identity((kind, key), probe)
                if identifier in rows:
                    continue
                rows[identifier] = {
                    "device_id": identifier,
                    "session_id": self.session_id,
                    "device_name": identifier,
                    # Open Ephys reports the part, not who made it. IMEC makes the Neuropixels
                    # chain, but the file does not say so and this adapter does not add it.
                    "manufacturer": None,
                    "model": _stated(probe.get(part)),
                    "firmware_version": _stated(probe.get(firmware)) if firmware else None,
                    "hardware_version": _stated(probe.get(hardware)),
                    "serial_number": _stated(probe.get(serial)),
                    # Part 01 §3.5: each element names the one below it in the chain. A basestation
                    # is the root here, because nothing in this file describes the PXI chassis.
                    "parent_device_id": _identity(parent, probe) if parent else None,
                    # R85 §2.1: and where the file coordinates that link, which port of it.
                    "parent_port": probe.get(port) if port else None,
                    # Part 02 §8.6: what the key states and no column holds. `port` is excluded
                    # because `parent_port` above is the column that holds it.
                    "metadata": {k: probe[k] for k in key if k in probe and k != port} or None,
                }
        return [rows[name] for name in sorted(rows)]

    def attachments(self) -> dict[str, dict[str, str | None]]:
        """Which headstage each probe was in and on which dock, by the acquisition's name for it.

        `custom_probe_name` is what Open Ephys calls the probe and what the NWB names its
        Device, so the two join without going through a serial number -- which matters for a
        quad-base probe, where one serial covers four stream names (R67 §1.2). The dock is the
        probe's `parent_port` (R85 §2.1), and it does not distinguish those four: all four bases
        report one dock, which is why Part 01 §3.5 keeps a port out of identity.
        """
        return {
            name: {
                "parent_device_id": _identity(("headstage", ("slot", "port")), probe),
                "parent_port": probe.get(PROBE_PORT),
            }
            for probe in self._probes()
            if (name := probe.get("custom_probe_name")) and all(k in probe for k in ("slot", "port"))
        }

    def offers(self) -> dict[str, int]:
        """Part 05 Stage 1: how many rows of each resource this root holds."""
        return {"core.devices": len(self.devices())}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID."""
        built = {"core.devices": self.devices()}
        return {resource: rows for resource, rows in built.items() if rows}


def _identity(element: tuple[str, tuple[str, ...]], probe: Mapping[str, str]) -> str:
    """Name one chain element from its kind and the positions that identify it.

    Physical position, because the serial numbers do not supply identity: every `bs_`, `bsc_`
    and `headstage_serial_number` in the measured session is `0`.
    """
    kind, key = element
    return ".".join([kind, *(f"{k}{probe[k]}" for k in key)])


def _stated(value: str | None) -> str | None:
    """Return what the file said, or None where it said nothing.

    `UNKNOWN` is kept: a source reporting that it does not know is not the same as a source that
    was never asked, and Part 01 §3.5 records the value verbatim either way. A serial of `0` is
    dropped, because it is this file's way of leaving the field blank rather than a serial.
    """
    return None if value is None or value in UNSET else value


__all__ = ["CHAIN", "PROBE_PORT", "SETTINGS", "OpenEphysSource"]
