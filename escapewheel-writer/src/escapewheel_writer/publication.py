"""What publishing a new packet and publishing a new version of one do differently (Part 05 §6).

- :class:`NewPacket` -- a packet at a root holding none.
- :class:`Amendment` -- a new version of the packet a root holds (Part 05 §15).

`PacketWriter` runs one pipeline over either. Each says where a resource is written, which
deliveries are staged, where the registries are bound, what the staged packet is and how it is
validated, which paths promotion creates, and how what was staged reaches them. One instance serves
one publication, and its methods are called in that order.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from escapewheel_reader import Manifest, Packet, open_packet
from escapewheel_reader.location import SOURCES_FILENAME
from escapewheel_reader.manifest import MANIFEST_FILENAME, MANIFESTS_DIRNAME
from escapewheel_validator import Report, validate

from . import opaque
from .amending import Held
from .attachments import Attachments
from .documents import VALIDATION_PASSED, retain, store_registries, writer_version
from .layout import PROMOTED, STAGING, retained
from .promotion import created

#: The manifest's candidate, written beside the manifest it is renamed onto.
CANDIDATE = f"{MANIFEST_FILENAME}.candidate"


class NewPacket:
    """A packet published at a root holding none.

    Parameters
    ----------
    root : Path
        The packet root.
    manifest : callable
        Builds the manifest from the resource entries, the registry descriptors and the validation
        report, the report being None before validation.
    sources : callable
        Given the `source` of each resource entry, returns the resolution document locating them,
        or None where it would locate nothing.

    Attributes
    ----------
    held : None
        A new packet settles against no held version.
    version : str
        The packet version, known once the staged packet is described.
    """

    def __init__(
        self,
        root: Path,
        *,
        manifest: Callable[
            [Sequence[Mapping[str, Any]], Mapping[str, Mapping[str, str]], Report | None], dict[str, Any]
        ],
        sources: Callable[[Iterable[str | None]], dict[str, Any] | None],
    ) -> None:
        self.root = root
        self.held = None
        self.version = ""
        self._staging = root / STAGING
        self._manifest = manifest
        self._sources = sources
        self._entries: list[dict[str, Any]] = []
        self._registries: Mapping[str, Mapping[str, str]] = {}
        self._located: dict[str, Any] | None = None
        self._promoted: list[str] = []

    def place(self, folder: str, resource_id: str, suffix: str) -> str:
        """Return where a resource is written under the packet root."""
        return _placed(folder, resource_id, suffix)

    def delivered(self, attachments: Attachments) -> list[tuple[opaque.StagedPayload, str]]:
        """Bind every delivered payload and return each with its declaration."""
        return attachments.bind_payloads()

    def bind_registries(self, documents: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
        """Store every registry in the staged packet and return the descriptors."""
        registries, _ = store_registries(documents, self._staging)
        return registries

    def describe(self, entries: list[dict[str, Any]], registries: Mapping[str, Mapping[str, str]]) -> None:
        """Write the staged packet's manifest, which makes it openable before it is validated."""
        self._entries, self._registries = entries, registries
        document = self._manifest(entries, registries, None)
        self.version = str(document["packet_version"])
        (self._staging / MANIFEST_FILENAME).write_text(json.dumps(document, indent=2) + "\n")

    def staged(self) -> Packet:
        """Open the staged packet."""
        return open_packet(self._staging)

    def validate(self, *, limits: Mapping[str, Any] | None, scan: Collection[str]) -> Report:
        """Validate the staged packet, scanning the order of the resources in `scan`."""
        return validate(self.staged(), limits=limits, scan=scan)

    def creates(self) -> Collection[str]:
        """Return every path promotion creates under the root."""
        self._located = self._sources(e.get("source") for e in self._entries)
        self._promoted = [name for name in PROMOTED if (self._staging / name).exists()]
        return [*self._promoted, *([SOURCES_FILENAME] if self._located is not None else []), CANDIDATE]

    def promote(self, report: Report) -> None:
        """Move what was staged into its final paths and write the manifest's candidate.

        The resolution document goes first, since it alone can still fail. Until the candidate is
        renamed the root holds no manifest, so a reader finds nothing and not a partial import.
        """
        if self._located is not None:
            # At the root so a copy carries it, and outside the manifest so a moved mirror is fixed by
            # editing it in place (Part 04 §5.5).
            (self.root / SOURCES_FILENAME).write_text(json.dumps(self._located, indent=2) + "\n")
        for entry in self._entries:
            entry["validation_state"] = VALIDATION_PASSED
        for name in self._promoted:
            shutil.move(str(self._staging / name), str(self.root / name))
        document = self._manifest(self._entries, self._registries, report)
        (self.root / CANDIDATE).write_text(json.dumps(document, indent=2) + "\n")


class Amendment:
    """A new version of the packet a root holds (Part 05 §15).

    Parameters
    ----------
    root : Path
        The packet root.
    held : Held
        The packet version amended.
    superseded : Mapping
        That version's manifest.
    version : str
        The new packet version.
    description : str, optional
        A description replacing the packet's.
    sources : callable
        As for :class:`NewPacket`.
    """

    def __init__(
        self,
        root: Path,
        held: Held,
        superseded: Mapping[str, Any],
        version: str,
        *,
        description: str | None,
        sources: Callable[[Iterable[str | None]], dict[str, Any] | None],
    ) -> None:
        self.root = root
        self.held = held
        self.version = version
        self._staging = root / STAGING
        self._superseded = superseded
        self._description = description
        self._entries: list[dict[str, Any]] = []
        self._registries: Mapping[str, Mapping[str, str]] = {}
        self._added: list[str] = []
        self._amended: dict[str, Any] = {}
        self._moved: list[str] = []
        self._sources = sources
        self._located: dict[str, Any] | None = None

    def place(self, folder: str, resource_id: str, suffix: str) -> str:
        """Return where a resource is written, apart from any file the packet holds (Part 03 §9)."""
        relative = _placed(folder, resource_id, suffix)
        if (self.root / relative).exists():
            relative = _placed(folder, resource_id, f"{self.version}.{suffix}")
        return relative

    def delivered(self, attachments: Attachments) -> list[tuple[opaque.StagedPayload, str]]:
        """Bind the delivered payloads and drop each instance the packet already names (Part 05 §4.3)."""
        payloads = [
            (payload, declaration)
            for payload, declaration in attachments.bind_payloads()
            if not self.held.holds(payload.resource_id, declaration)
        ]
        for instances in (attachments.staged, attachments.arrays, attachments.media):
            for resource_id in [r for r, i in instances.items() if self.held.holds(r, i.declaration_id)]:
                del instances[resource_id]
        return payloads

    def bind_registries(self, documents: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
        """Bind every registry and return the descriptors.

        Before validation, since the validator acquires each registry through the candidate's
        descriptor (Part 04 §10); one the packet does not yet store is bound under staging/.
        """
        registries, self._added = store_registries(documents, self.root, staging=self._staging)
        return registries

    def describe(self, entries: list[dict[str, Any]], registries: Mapping[str, Mapping[str, str]]) -> None:
        """Take what is staged; an amended manifest is built from it and written only at promotion."""
        self._entries, self._registries = entries, registries

    def _candidate(self) -> dict[str, Any]:
        """Return the amended manifest with every written resource still under staging/."""
        written = {e["resource_id"] for e in self._entries}
        amended = dict(self._superseded)
        amended["packet_version"] = self.version
        amended["registries"] = self._registries
        amended["resources"] = [
            *(e for e in self._superseded["resources"] if e["resource_id"] not in written),
            *(e if e.get("external") else dict(e, uri=f"{STAGING}/{e['uri']}") for e in self._entries),
        ]
        if self._description is not None:
            amended["description"] = self._description
        return amended

    def staged(self) -> Packet:
        """Open the amended packet, each written resource read from staging/."""
        return Packet(self.root, Manifest.from_dict(self._candidate()))

    def validate(self, *, limits: Mapping[str, Any] | None, scan: Collection[str]) -> Report:
        """Validate the whole amended packet, against the superseded version too (Part 05 §15.6)."""
        amended = self._candidate()
        amended["resources"] = self.held.without_stale(amended["resources"], self._entries)
        self._amended = amended
        return validate(
            Packet(self.root, Manifest.from_dict(amended)),
            limits=limits,
            scan=scan,
            recheck={e["resource_id"] for e in self._entries},
            superseded=self._superseded,
        )

    def creates(self) -> Collection[str]:
        """Return the outermost path promotion creates for each file it writes under the root."""
        self._moved = [e["uri"] for e in self._entries if not e.get("external")]
        copies = [
            f"{MANIFESTS_DIRNAME}/{retained(manifest)}"
            for manifest in (self._superseded, self._amended)
            if not (self.root / MANIFESTS_DIRNAME / retained(manifest)).exists()
        ]
        creates = {created(self.root, relative) for relative in (*self._moved, *self._added, *copies)}
        # Part 05 §6 refuses a promotion onto a path that exists, so a resolution document the root
        # already holds is left as it is.
        self._located = (
            None
            if (self.root / SOURCES_FILENAME).exists()
            else self._sources(e.get("source") for e in self._amended["resources"])
        )
        return creates | {CANDIDATE} | ({SOURCES_FILENAME} if self._located is not None else set())

    def promote(self, report: Report) -> None:
        """Move what was staged into its final paths, retain both manifests and write the candidate."""
        if self._located is not None:
            (self.root / SOURCES_FILENAME).write_text(json.dumps(self._located, indent=2) + "\n")
        for relative in (*self._moved, *self._added):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(self._staging / relative), str(destination))
        by_id = {e["resource_id"]: e for e in self._entries}
        amended = self._amended
        amended["resources"] = [
            dict(by_id[e["resource_id"]], validation_state=VALIDATION_PASSED) if e["resource_id"] in by_id else e
            for e in amended["resources"]
        ]
        amended["registries"] = {
            name: dict(bound, path=str(bound["path"]).removeprefix(f"{STAGING}/"))
            for name, bound in self._registries.items()
        }
        amended["validation"] = {
            "status": VALIDATION_PASSED,
            "validated_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "validator_name": "escapewheel_validator",
            "validator_version": writer_version(),
        }
        body = (json.dumps(amended, indent=2) + "\n").encode()
        retain(self.root, self._superseded, amended, body)
        (self.root / CANDIDATE).write_bytes(body)


def _placed(folder: str, resource_id: str, suffix: str) -> str:
    """Return `<folder>/<namespace>/<name>.<suffix>` for a resource ID."""
    namespace, name = resource_id.split(".", 1)
    return f"{folder}/{namespace}/{name}.{suffix}"


__all__ = ["CANDIDATE", "Amendment", "NewPacket"]
