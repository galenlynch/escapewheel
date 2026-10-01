"""`core.devices` and `core.probes` from an NWB file's Devices and ElectrodeGroups."""

from __future__ import annotations

from collections.abc import Mapping
from functools import cached_property
from os.path import commonprefix
from typing import Any

from ...notes import Note, NoteCode
from .file import NWBFile
from .names import clean


class Devices(NWBFile):
    """The instruments an NWB file names, and the probes that recorded."""

    def _attachment(self) -> dict[str, dict[str, str | None]]:
        """Which headstage each probe was in and on which dock, or nothing."""
        if self.attachments is None:
            return {}
        from ..openephys import OpenEphysSource

        return OpenEphysSource(self.attachments, session_id=self.session_id, prefix=self.prefix).attachments()

    @cached_property
    def _devices(self) -> list[dict[str, Any]]:
        """`core.devices`, one row per physical instrument (Part 01 §3.5).

        One row per *object*, not per NWB Device: a quad-base probe presents four Devices with
        one serial number, and recording four rows asserts four probes where the session had
        one. Identity is the serial the file states; the four remain four `core.probes` rows.
        The surviving row takes the common prefix of the names it covers where there is one --
        naming only, since the serial is what decided identity.
        """
        found: dict[str, dict[str, Any]] = {}
        attached = self._attachment()
        for name in self.store.members("general/devices"):
            described = self.attrs(f"general/devices/{name}")
            identity = self.device_identity(described)
            serial = identity["serial_number"]
            attachment = attached.get(name) or {}
            row = {
                "device_id": self.prefix + name,
                "session_id": self.session_id,
                "device_name": self.prefix + name,
                "manufacturer": clean(described.get("manufacturer")),
                "model": identity["model"],
                "serial_number": serial,
                "parent_device_id": attachment.get("parent_device_id"),
                # R85 §2.1: the dock of that headstage. Null where no attachment is stated, and
                # null is what a consumer must read as unrecorded rather than parse out of a name.
                "parent_port": attachment.get("parent_port"),
                "metadata": identity["metadata"],
            }
            # A device with no serial is its own object: nothing says two of them are one.
            key = serial or f"\0{name}"
            if (kept := found.get(key)) is None:
                found[key] = row | {"covers": [name]}
            else:
                kept["covers"].append(name)
        rows = []
        for row in found.values():
            covers = row.pop("covers")
            if len(covers) > 1:
                shared = commonprefix(covers).rstrip("-_ .") or covers[0]
                row |= {"device_id": self.prefix + shared, "device_name": self.prefix + shared}
                self.notes.append(
                    Note(
                        f"devices: {', '.join(covers)} share serial {row['serial_number']}; "
                        f"recorded as one device named {shared} (Part 01 §3.5)",
                        NoteCode.DEVICES_MERGED,
                    )
                )
            rows.append(row)
        return rows

    def devices(self) -> list[dict[str, Any]]:
        """`core.devices`, computed once: it reads the store and the attachment file."""
        return self._devices

    def device_identity(self, described: Mapping[str, Any]) -> dict[str, Any]:
        """Return what a `Device` states about the object it names: model, serial, and the rest.

        Core 2.9.0 declares all three as attributes, so that is where they are read. A producer
        that leaves them unset and packs the same facts into `description` needs a dialect.
        """
        description = clean(described.get("description"))
        return {
            "model": clean(described.get("model_number")) or clean(described.get("model_name")),
            "serial_number": clean(described.get("serial_number")),
            "metadata": {"description": description} if description else None,
        }

    def _device_of(self) -> dict[str, dict[str, Any]]:
        """Every NWB Device name mapped to the `core.devices` row that covers it."""
        by_name = {}
        for name in self.store.members("general/devices"):
            described = self.attrs(f"general/devices/{name}")
            by_name[name] = self.device_identity(described)["serial_number"]
        rows = {row["serial_number"]: row for row in self.devices() if row["serial_number"]}
        named = {row["device_name"]: row for row in self.devices()}
        return {name: rows.get(serial) or named.get(self.prefix + name) for name, serial in by_name.items()}

    def probes(self) -> list[dict[str, Any]]:
        """`core.probes`, one row per NWB ElectrodeGroup.

        An ElectrodeGroup is what actually recorded, which is why it -- and not the Device --
        is the probe: each shank of a quad-base probe gets a group of its own, and a Device may
        have recorded nothing.
        """
        devices = self._device_of()
        rows = []
        for name in self.store.members("general/extracellular_ephys"):
            if name == "electrodes":
                continue
            described = self.attrs(f"general/extracellular_ephys/{name}")
            linked = [
                link["path"].rsplit("/", 1)[-1]
                for link in described.get("zarr_link", [])
                if link.get("name") == "device"
            ]
            device = devices.get(linked[0]) if linked else devices.get(name)
            rows.append(
                {
                    "probe_id": self.prefix + name,
                    "session_id": self.session_id,
                    "device_id": device["device_id"] if device else None,
                    "probe_name": self.prefix + name,
                    "probe_type": device["model"] if device else None,
                    "manufacturer": device["manufacturer"] if device else None,
                    "serial_number": device["serial_number"] if device else None,
                    "target_region": clean(described.get("location")),
                    "metadata": {"description": described["description"]} if described.get("description") else None,
                }
            )
        return rows


__all__ = ["Devices"]
