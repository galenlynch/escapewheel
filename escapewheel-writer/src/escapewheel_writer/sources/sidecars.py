"""Sidecars a recipe lists, each a file or directory the packet owns or a resource it references.

- :class:`SidecarSource` -- `core.sidecars` and `core.sidecar_scopes` rows for each sidecar listed,
  with the payload or reference that each row binds (Part 02 §12.10).
- :data:`FIELDS` -- the keys a listed sidecar may carry.

Nothing here reads a sidecar's contents: a row states what the recipe says of the sidecar, and the
payload is handed over byte for byte.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

from escapewheel_reader.resource_ids import CORE_SIDECAR_INSTANCES, CORE_SIDECAR_SCOPES, CORE_SIDECARS

from ..bindings import ExternalResource
from ..errors import SourceDefect, SourceFault
from ..opaque import Payload

#: What a listed sidecar may carry. `resource_id` and one of `path` and `uri` are required;
#: `source` names a body of data a relative `uri` resolves against (Part 04 §5.5).
FIELDS = frozenset({"resource_id", "path", "uri", "source", "sidecar_type", "media_type", "description", "scopes"})


class SidecarSource:
    """`core.sidecars` and `core.sidecar_scopes`, one row per sidecar a recipe lists and per scope.

    Parameters
    ----------
    root : str or Path
        The directory a sidecar's `path` is relative to.
    sidecars : sequence of mapping
        Each sidecar: its `resource_id`, which the recipe author chooses (Part 02 §12.10); a `path`
        under `root` to a file or directory the packet will own, or a `uri` the packet references;
        and optionally `source`, `sidecar_type`, `media_type`, `description`, and `scopes`, each
        scope a mapping of `scope_kind` and `scope`.
    """

    PRODUCES = frozenset({CORE_SIDECARS, CORE_SIDECAR_SCOPES})

    #: Empty: an entry without `owns` owns both tables, and a recipe whose other source also lists
    #: sidecars names both under each entry's `contributes` (Part 05 §3.4).
    CONTRIBUTES: frozenset[str] = frozenset()

    STATES: ClassVar[dict[str, str]] = {}

    #: `opaque_location` because a listed `path` is a payload the packet owns (Part 12 §5).
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "sidecars", "opaque_location")

    ACCEPTS: ClassVar[tuple[str, ...]] = ()

    CONSUMES: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self, root: str | Path, *, sidecars: Sequence[Mapping[str, Any]], opaque_location: str | None = None
    ) -> None:
        # A payload is handed over as bytes and the build writes it into `opaque_location`.
        del opaque_location
        self.root = Path(root)
        self.notes: list[str] = []
        self.sidecars = [self._checked(sidecar) for sidecar in sidecars]

    def _checked(self, sidecar: Mapping[str, Any]) -> Mapping[str, Any]:
        """Refuse a listed sidecar no row and binding can be made from, naming what it lacks."""
        resource_id = sidecar.get("resource_id")
        where = str(resource_id) if resource_id else None
        if not resource_id:
            raise SourceDefect(
                f"a listed sidecar states no resource_id: {dict(sidecar)}", code=SourceFault.SIDECAR_UNSTATED
            )
        if unknown := sorted(set(sidecar) - FIELDS):
            raise SourceDefect(
                f"{resource_id}: a listed sidecar carries {', '.join(unknown)}, which is none of {sorted(FIELDS)}",
                code=SourceFault.SIDECAR_UNSTATED,
                where=where,
            )
        if ("path" in sidecar) == ("uri" in sidecar):
            raise SourceDefect(
                f"{resource_id}: a listed sidecar states exactly one of a path the packet owns and a uri it references",
                code=SourceFault.SIDECAR_UNSTATED,
                where=where,
            )
        if "path" in sidecar and not (self.root / sidecar["path"]).exists():
            raise SourceDefect(
                f"{resource_id}: {self.root / sidecar['path']} holds no file or directory",
                code=SourceFault.SIDECAR_ABSENT,
                where=where,
            )
        for scope in sidecar.get("scopes", ()):
            if set(scope) != {"scope_kind", "scope"}:
                raise SourceDefect(
                    f"{resource_id}: a scope states exactly scope_kind and scope, not {sorted(scope)}",
                    code=SourceFault.SIDECAR_UNSTATED,
                    where=where,
                )
        return sidecar

    def offers(self) -> dict[str, int]:
        """Part 05 §4.1: how many rows of each resource the recipe lists."""
        return {resource: len(rows) for resource, rows in self.records().items()}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID."""
        listed = [
            {
                "resource_id": str(s["resource_id"]),
                "sidecar_type": s.get("sidecar_type"),
                "media_type": s.get("media_type"),
                "description": s.get("description"),
                "metadata": None,
            }
            for s in self.sidecars
        ]
        scopes = [
            {"resource_id": str(s["resource_id"]), "scope_kind": str(scope["scope_kind"]), "scope": str(scope["scope"])}
            for s in self.sidecars
            for scope in s.get("scopes", ())
        ]
        built = {CORE_SIDECARS: listed, CORE_SIDECAR_SCOPES: scopes}
        return {resource: rows for resource, rows in built.items() if rows}

    def staged_payloads(self) -> list[Payload]:
        """Each listed `path`, as the file or directory the packet will own under its resource ID."""
        handed = []
        for sidecar in self.sidecars:
            if "path" not in sidecar:
                continue
            path = self.root / sidecar["path"]
            resource_id = str(sidecar["resource_id"])
            if path.is_file():
                handed.append(Payload(resource_id, path.name, data=path.read_bytes()))
            else:
                files = {f.relative_to(path).as_posix(): f.read_bytes() for f in sorted(path.rglob("*")) if f.is_file()}
                handed.append(Payload(resource_id, path.name, files=files))
        return handed

    def external_resources(self) -> dict[str, ExternalResource]:
        """Each listed `uri`, as a resource the packet references and no byte of which it reads."""
        return {
            str(s["resource_id"]): ExternalResource(CORE_SIDECAR_INSTANCES, str(s["uri"]), source=s.get("source"))
            for s in self.sidecars
            if "uri" in s
        }


__all__ = ["FIELDS", "SidecarSource"]
