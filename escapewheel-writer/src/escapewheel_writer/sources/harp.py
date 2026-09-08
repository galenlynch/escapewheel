"""Harp devices, read from the schema each one writes beside its own data.

A Harp acquisition directory carries `device.yml`, the device schema the Harp protocol defines:
the device's name, its `whoAmI` type code, its firmware version, and the registers it emits.
That is a complete instrument declaration, and it sits in the data directory rather than in any
metadata document -- measured on `ecephys_786867`, no rig JSON, session JSON or processing JSON
mentions the sensor at all, while its own schema names it, versions it, and documents the
register whose value sets its sampling rate.

**Only `device.yml` is read here.** The register streams beside it are Harp's binary message
format, and decoding those is a job for a Harp library -- `contraqctor` and `harp-python` both
do it. Nothing in this packet needs them: the signal itself reaches us through the NWB, already
aligned, so what was missing was never the samples but the sentence saying what produced them.
Adding a dependency to read four YAML scalars would buy nothing and cost a dependency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from .store import source_root


def _clean(value: Any) -> str | None:
    """Return a schema value as the string a column takes, or None where the schema omitted it."""
    return None if value is None else str(value)


#: The schema file the Harp protocol puts beside a device's data.
SCHEMA = "device.yml"

#: What a device schema is asked for. `whoAmI` is the Harp device *type* -- 1401 is a sniff
#: detector, whatever this one is called -- so it belongs with the model rather than the serial.
FIELDS = ("device", "whoAmI", "firmwareVersion", "hardwareTargets")


class HarpSource:
    """`core.devices`, one row per Harp device found under `root`.

    Parameters
    ----------
    root : str or Path
        A directory holding Harp acquisition directories, or one such directory itself. Each is
        recognised by the `device.yml` inside it.
    session_id : str
        The session these devices were used in.
    """

    #: R63 §2.1: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset({"core.devices"})

    #: R87 §2.2: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    def __init__(self, root: str | Path, *, session_id: str) -> None:
        self.root = source_root(root)
        self.session_id = session_id
        self.notes: list[str] = []

    def schemas(self) -> list[Path]:
        """Every `device.yml` under `root`, sorted, deduplicated by the device it declares.

        A session restarted mid-recording writes one acquisition directory per run, each with an
        identical schema; the device is one device however many times it was started.
        """
        found = [self.root / SCHEMA] if (self.root / SCHEMA).is_file() else []
        found += sorted(p / SCHEMA for p in sorted(self.root.iterdir()) if (p / SCHEMA).is_file())
        return found

    def _read(self, path: Path) -> dict[str, Any]:
        """Parse one device schema, keeping only what a device row needs."""
        import yaml

        parsed = yaml.safe_load(path.read_text()) or {}
        return {field: parsed.get(field) for field in FIELDS}

    def devices(self) -> list[dict[str, Any]]:
        """`core.devices`, one row per distinct device declared under `root`."""
        rows: dict[str, dict[str, Any]] = {}
        for path in self.schemas():
            declared = self._read(path)
            name = declared.get("device")
            if not name:
                self.notes.append(f"{path}: declares no device name; skipped")
                continue
            if name in rows:
                continue
            rows[name] = {
                "device_id": str(name),
                "session_id": self.session_id,
                "device_name": str(name),
                # Harp is the bus, not the maker: a schema names neither a manufacturer nor a
                # serial, and inventing either would assert what nothing states.
                "manufacturer": None,
                "model": f"Harp {declared['whoAmI']}" if declared.get("whoAmI") is not None else None,
                # R66 §2.1: verbatim, unparsed. `hardwareTargets` is this schema's name for the
                # hardware the firmware targets, which is the revision the device reports.
                "firmware_version": _clean(declared.get("firmwareVersion")),
                "hardware_version": _clean(declared.get("hardwareTargets")),
                "serial_number": None,
                # whoAmI is on `model`; what remains is nothing, so the column stays empty rather
                # than restating what two typed columns now carry (R66 §1.2).
                "metadata": None,
            }
        return [rows[name] for name in sorted(rows)]

    def offers(self) -> dict[str, int]:
        """`05` Stage 1: how many rows of each resource this root holds."""
        return {"core.devices": len(self.devices())}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID."""
        built = {"core.devices": self.devices()}
        return {resource: rows for resource, rows in built.items() if rows}


__all__ = ["FIELDS", "SCHEMA", "HarpSource"]
