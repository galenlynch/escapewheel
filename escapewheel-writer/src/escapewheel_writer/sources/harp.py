"""Harp devices, read from the schema each one writes beside its own data.

- :class:`HarpSource` -- `core.devices`, one row per Harp device found under a root.
- :data:`SCHEMA` -- the name of the schema file.
- :data:`FIELDS` -- the fields this adapter reads from a device schema.

Only `device.yml` is read: the register streams beside it are Harp's binary message format, which
a Harp library decodes and no table here needs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from escapewheel_reader.resource_ids import CORE_DEVICES

from ..notes import Note, NoteCode
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
    prefix : str, optional
        Prepended to every device ID and name.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    """

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset({CORE_DEVICES})

    #: Part 05 §3.4: what of `PRODUCES` this adapter supplies only part of, which a source entry
    #: without `owns` contributes rather than owns.
    CONTRIBUTES = frozenset({CORE_DEVICES})

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply, resolved against Part 12 §4's terms first and the
    #: recipe's options second. A name resolving to neither is refused before any source is opened.
    #:
    #: An option the adapter can run without is left out: a declared name a recipe does not set
    #: resolves to nothing, so declaring one makes it mandatory.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id")

    #: Part 05 §3.4: options this adapter reads and can run without (Part 12 §4).
    ACCEPTS: ClassVar[tuple[str, ...]] = ("prefix", "source_cache")

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ()

    def __init__(self, root: str | Path, *, session_id: str, prefix: str = "", source_cache: str | None = None) -> None:
        self.root = source_root(root, cache=source_cache)
        self.session_id = session_id
        self.prefix = prefix
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
                self.notes.append(Note(f"{path}: declares no device name; skipped", NoteCode.DEVICE_UNNAMED))
                continue
            if name in rows:
                continue
            rows[name] = {
                "device_id": self.prefix + str(name),
                "session_id": self.session_id,
                "device_name": self.prefix + str(name),
                # Harp is the bus, not the maker: a schema names neither a manufacturer nor a
                # serial, and inventing either would assert what nothing states.
                "manufacturer": None,
                "model": f"Harp {declared['whoAmI']}" if declared.get("whoAmI") is not None else None,
                # Part 01 §3.5: verbatim, unparsed. `hardwareTargets` is this schema's name for the
                # hardware the firmware targets, which is the revision the device reports.
                "firmware_version": _clean(declared.get("firmwareVersion")),
                "hardware_version": _clean(declared.get("hardwareTargets")),
                "serial_number": None,
                # whoAmI is on `model`; what remains is nothing, so the column stays empty rather
                # than restating what two typed columns carry.
                "metadata": None,
            }
        return [rows[name] for name in sorted(rows)]

    def offers(self) -> dict[str, int]:
        """Part 05 §4.1: how many rows of each resource this root holds."""
        return {resource: len(rows) for resource, rows in self.records().items()}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID."""
        built = {CORE_DEVICES: self.devices()}
        return {resource: rows for resource, rows in built.items() if rows}


__all__ = ["FIELDS", "SCHEMA", "HarpSource"]
