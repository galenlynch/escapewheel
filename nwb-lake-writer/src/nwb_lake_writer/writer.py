"""Stage, validate, and commit a packet.

`05`'s core principle is that **validation is importation**: copying or converting bytes is
only staging, and a resource is not imported until it has passed the checks for its schema.
This module is the writer and committer halves of that pipeline. It knows nothing about NWB,
SpikeInterface, or any other source -- adapters hand it records, and it turns them into a
packet or refuses to.

The commit sequence is `05` Stage 5's, and its ordering is the whole guarantee:

1. write staged resources under ``staging/``;
2. validate them there;
3. move them into their final paths;
4. rename the manifest to ``nwb.packet.json`` **last**.

Until step 4 the packet root holds no manifest, so a reader finds nothing rather than
finding a partial import that claims to be valid.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from nwb_lake_reader import open_packet
from nwb_lake_validator import Report, validate

from .arrow import build


def _version() -> str:
    """Read this package's version without importing it at module scope."""
    from . import __version__

    return __version__


#: Where a manifest lives once committed (`04`).
MANIFEST = "nwb.packet.json"

#: Where a packet embeds the registry it was written against (R2 §8).
REGISTRY_PATH = "schemas/logical_schemas.json"

#: `03`'s portable profile.
PROFILE = "nwb-lake-portable-v0.1"


class CommitRefused(Exception):
    """Validation found errors, so nothing was committed.

    Attributes
    ----------
    report : Report
        The findings. The staging directory is left in place for inspection.
    """

    def __init__(self, report: Report, staging: Path) -> None:
        errors = report.errors
        super().__init__(f"{errors} error(s); staged resources left at {staging}")
        self.report = report
        self.staging = staging


class PacketWriter:
    """Collect records and commit them as a validated packet.

    Parameters
    ----------
    registry : Mapping
        The registry to write against. It is embedded in the packet (R2 §8), so the packet
        stays readable when the reference registry moves on.
    packet_id : str
        The packet's identifier.
    description : str, optional
        Human-readable description for the manifest.

    Examples
    --------
    >>> writer = PacketWriter(registry, packet_id="s001")  # doctest: +SKIP
    >>> writer.add("core.sessions", [{"session_id": "s001", ...}])  # doctest: +SKIP
    >>> report = writer.commit(Path("s001"))  # doctest: +SKIP
    """

    def __init__(self, registry: Mapping[str, Any], *, packet_id: str, description: str | None = None) -> None:
        self._registry = registry
        self._packet_id = packet_id
        self._description = description
        self._tables: dict[str, list[Mapping[str, Any]]] = {}

    def add(self, resource_id: str, records: Sequence[Mapping[str, Any]]) -> None:
        """Add records for one table.

        Called more than once for the same resource, records accumulate; ordering is applied
        at commit, so an adapter may emit in whatever order is natural for its source.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID, e.g. ``core.trials``.
        records : sequence of Mapping
            Rows. Keys absent from the registry's column list are ignored.

        Raises
        ------
        KeyError
            If the registry does not define this resource.
        """
        if resource_id not in self._registry["tables"]:
            raise KeyError(f"the registry defines no table {resource_id}")
        self._tables.setdefault(resource_id, []).extend(records)

    @property
    def resources(self) -> list[str]:
        """Resource IDs with at least one record, in insertion order."""
        return list(self._tables)

    def _stage(self, staging: Path) -> list[dict[str, Any]]:
        """Write every table under `staging` and return its manifest entries."""
        entries = []
        for resource_id, records in self._tables.items():
            spec = self._registry["tables"][resource_id]
            namespace, name = resource_id.split(".", 1)
            relative = f"tables/{namespace}/{name}.parquet"
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(build(spec, records), path, compression="zstd")
            entries.append(
                {
                    "resource_id": resource_id,
                    "layer": namespace,
                    "kind": "table",
                    "schema_id": f"{resource_id}.v{self._registry['registry_version'].rsplit('.', 1)[0]}",
                    "physical_profile": "parquet",
                    "uri": relative,
                    "canonical": True,
                    "validation_state": "not_run",
                }
            )
        return entries

    def _manifest(self, entries: Sequence[Mapping[str, Any]], report: Report | None) -> dict[str, Any]:
        """Build the manifest for these resources."""
        sessions = sorted({r["session_id"] for r in self._tables.get("core.sessions", []) if "session_id" in r})
        now = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
        validation = {
            "status": "not_run" if report is None else ("passed" if report.passed else "failed"),
            "validated_at": now,
            "validator_name": "nwb_lake_validator",
            "validator_version": _version(),
        }
        manifest: dict[str, Any] = {
            "packet_id": self._packet_id,
            "packet_version": "0.1.0",
            "profile_id": PROFILE,
            "semantic_standard_version": self._registry["semantic_standard_version"],
            "logical_standard_version": self._registry["logical_standard_version"],
            "registry_version": self._registry["registry_version"],
            "created_at": now,
            "sessions": sessions,
            "required_codecs": [],
            "resources": [dict(e) for e in entries],
            "validation": validation,
        }
        if self._description is not None:
            manifest["description"] = self._description
        return manifest

    def commit(self, root: str | Path) -> Report:
        """Stage, validate, and commit.

        Parameters
        ----------
        root : str or Path
            The packet root. Created if absent; an existing packet is refused rather than
            overwritten, because immutability covers packet-owned bytes (R14 §2.3).

        Returns
        -------
        Report
            The validation report. Warnings do not prevent a commit; errors do.

        Raises
        ------
        FileExistsError
            If `root` already holds a committed manifest.
        ValueError
            If no `core.sessions` records were added.
        CommitRefused
            If validation found errors. Nothing is committed and staging is left in place.
        """
        root = Path(root)
        if (root / MANIFEST).exists():
            raise FileExistsError(f"{root} already holds a committed {MANIFEST}")
        # R1 §6 makes the session inventory part of the manifest and the schema requires it
        # non-empty. Refusing here beats letting the staged manifest fail its own schema,
        # which surfaces as an unhelpful error from a directory the caller never named.
        if not self._tables.get("core.sessions"):
            raise ValueError("a packet declares at least one session; core.sessions is empty (R1 §6)")

        staging = root / "staging"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)

        # 1. staged resources, plus the registry they were written against
        entries = self._stage(staging)
        (staging / "schemas").mkdir(parents=True, exist_ok=True)
        (staging / REGISTRY_PATH).write_text(json.dumps(self._registry, indent=2) + "\n")

        # 2. validate them where they stand -- a staged packet needs a manifest to be opened,
        #    so the candidate is written into staging rather than at the root, where its
        #    presence would announce a packet that is not yet committed.
        (staging / MANIFEST).write_text(json.dumps(self._manifest(entries, None), indent=2) + "\n")
        report = validate(open_packet(staging))
        if not report.passed:
            raise CommitRefused(report, staging)

        # 3. move into final paths
        for entry in entries:
            entry["validation_state"] = "passed"
        for name in ("tables", "schemas"):
            source = staging / name
            if source.exists():
                shutil.move(str(source), str(root / name))

        # 4. rename the manifest last: until this line the root holds no manifest at all,
        #    so a reader finds nothing rather than a partial import claiming to be valid.
        candidate = root / f"{MANIFEST}.candidate"
        candidate.write_text(json.dumps(self._manifest(entries, report), indent=2) + "\n")
        os.replace(candidate, root / MANIFEST)
        shutil.rmtree(staging)
        return report


__all__ = ["MANIFEST", "PROFILE", "REGISTRY_PATH", "CommitRefused", "PacketWriter"]
