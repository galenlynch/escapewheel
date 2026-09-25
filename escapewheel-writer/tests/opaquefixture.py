"""An adapter owning opaque resources, handing over as bytes whatever tree its root mirrors.

Its root holds one directory per resource ID, each holding the payload to deliver, so a test lays
out what a source has and the adapter delivers it by whichever route the recipe chose.
"""

from pathlib import Path
from typing import Any, ClassVar

from escapewheel_writer.opaque import Payload


class Clips:
    """Deliver every payload under its root, with a `core.media_assets` row for each `core.` one."""

    PROTOCOLS = ("files-v0.1", "stream-v0.1", "flight-v0.1")
    PRODUCES = frozenset({"core.media_assets"})
    CONTRIBUTES: frozenset[str] = frozenset()
    STATES: ClassVar[dict[str, str]] = {}
    NEEDS = ("root", "session_id", "opaque_location")
    ACCEPTS: tuple[str, ...] = ()
    CONSUMES: tuple[str, ...] = ()

    #: The keywords each construction was given, for a test asking what a build supplied.
    constructed: ClassVar[list[set[str]]] = []

    def __init__(self, root: Any, *, session_id: str, **supplied: Any) -> None:
        self.root, self.session_id = Path(root), session_id
        self.notes: list[str] = []
        Clips.constructed.append(set(supplied))

    def _resources(self) -> list[Path]:
        return sorted(path for path in self.root.iterdir() if path.is_dir())

    def records(self) -> dict[str, list[dict[str, Any]]]:
        rows = []
        for directory in self._resources():
            if directory.name.startswith("core."):
                asset = directory.name.split(".", 1)[1]
                rows.append(
                    {
                        "session_id": self.session_id,
                        "media_asset_id": asset,
                        "resource_id": directory.name,
                        "media_asset_name": asset,
                    }
                )
        return {"core.media_assets": rows}

    def staged_payloads(self) -> list[Payload]:
        handed = []
        for directory in self._resources():
            (payload,) = directory.iterdir()
            if payload.is_file():
                handed.append(Payload(directory.name, payload.name, data=payload.read_bytes()))
            else:
                files = {f.relative_to(payload).as_posix(): f.read_bytes() for f in payload.rglob("*") if f.is_file()}
                handed.append(Payload(directory.name, payload.name, files=files))
        return handed


class Reports(Clips):
    """The same, also producing an extension's opaque singleton."""

    PRODUCES = frozenset({"core.media_assets", "qc.report"})


class Plain(Clips):
    """An adapter owning nothing opaque, which declares no `opaque_location`."""

    NEEDS = ("root", "session_id")

    def staged_payloads(self) -> list[Payload]:
        return []


class Undeclared(Clips):
    """An adapter handing payloads over without declaring where they go."""

    NEEDS = ("root", "session_id")
