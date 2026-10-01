"""The arrays, media and opaque payloads a packet owns or references (Part 04 §5, Part 12 §5).

- :class:`Attachments` -- what the sources delivered beside their rows, each bound to its catalog
  row, staged under the packet root and described by a manifest entry.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from escapewheel_reader.uri import encode

from . import opaque
from .bindings import ExternalArray, ExternalMedia, StagedArray, check_reference
from .documents import resource_entry
from .errors import PayloadFault, PayloadProblem, PayloadRefused, UsageError, UsageFault
from .registries import Declarations


class Attachments:
    """Every resource of a packet that is not a table, and the catalog row each binds.

    Parameters
    ----------
    declarations : Declarations
        The registries the packet is written against.
    rows : callable
        Returns the records added so far for one table. A catalog row is bound in place, so the
        records returned are the ones the packet will write.
    """

    def __init__(self, declarations: Declarations, rows: Callable[[str], Sequence[Mapping[str, Any]]]) -> None:
        self._declarations = declarations
        self._rows = rows
        #: Arrays the packet will own, by resource ID.
        self.staged: dict[str, StagedArray] = {}
        #: Arrays and media the packet references, by resource ID.
        self.arrays: dict[str, ExternalArray] = {}
        self.media: dict[str, ExternalMedia] = {}
        #: Packet-owned opaque resources as each source delivered them, bound at commit, once every
        #: source's catalog rows are in (Part 12 §5).
        self.payloads: list[opaque.StagedPayload] = []

    @property
    def referenced(self) -> tuple[ExternalArray | ExternalMedia, ...]:
        """Every referenced array, then every referenced media asset."""
        return (*self.arrays.values(), *self.media.values())

    def add_array(self, resource_id: str, array: StagedArray) -> None:
        """Take a dense array to write into the packet, bound to its catalog row."""
        if resource_id in self.staged:
            raise UsageError(
                f"{resource_id} already has an array staged", code=UsageFault.STAGED_TWICE, where=resource_id
            )
        if array.resource_id != resource_id:
            raise UsageError(
                f"{resource_id}: staged array declares resource_id {array.resource_id!r}",
                code=UsageFault.RESOURCE_ID_DIFFERS,
                where=resource_id,
            )
        if not array.declaration_id:
            array = self._delivered_binding(resource_id, array)
        declaration = self._declarations.family(array.declaration_id, resource_id, "dense_array")
        self._bind_catalog_row(declaration, resource_id, "array_asset_id", array.array_asset_id)
        self.staged[resource_id] = array

    def reference_array(self, resource_id: str, array: ExternalArray) -> None:
        """Take a dense array the packet references, bound to its catalog row."""
        if resource_id in self.staged or resource_id in self.arrays:
            raise UsageError(f"{resource_id} already has an array", code=UsageFault.STAGED_TWICE, where=resource_id)
        array = replace(array, uri=check_reference(resource_id, array.uri, array.source))
        declaration = self._declarations.family(array.declaration_id, resource_id, "dense_array")
        self._bind_catalog_row(declaration, resource_id, "array_asset_id", array.array_asset_id)
        self.arrays[resource_id] = array

    def reference_media(self, resource_id: str, media: ExternalMedia) -> None:
        """Take a media asset the packet references, bound to its catalog row."""
        if resource_id in self.media:
            raise UsageError(f"{resource_id} already has media", code=UsageFault.STAGED_TWICE, where=resource_id)
        media = replace(media, uri=check_reference(resource_id, media.uri, media.source))
        declaration = self._declarations.family(media.declaration_id, resource_id, "opaque")
        self._bind_catalog_row(declaration, resource_id, "media_asset_id", media.media_asset_id)
        self.media[resource_id] = media

    def add_payloads(
        self, source: str, location: str | Path, *, owned: Collection[str] | None = None
    ) -> list[opaque.StagedPayload]:
        """Take every payload one source placed in its `opaque_location`, to bind at commit."""
        found = opaque.read(source, location, owned)
        self.payloads.extend(found)
        return found

    def bind_payloads(self) -> list[tuple[opaque.StagedPayload, str]]:
        """Bind each payload by its resource directory's name, refusing before anything is validated.

        A name binds the catalog row of an opaque catalog family carrying it, or otherwise the opaque
        singleton declaration it names (Part 12 §5). Every opaque catalog row must be bound, and
        no resource ID twice, whether by two payloads or by a payload and a referenced resource.

        Returns
        -------
        list of tuple
            Each payload and the declaration ID it binds to.

        Raises
        ------
        PayloadRefused
            Naming each directory and resource ID that binds no resource, binds two, is bound twice,
            or is a singleton the recipe does not leave its source owning.
        """
        families, singletons = self._declarations.opaque()
        rows: dict[str, list[str]] = {}
        unbound: list[PayloadProblem] = []
        for declaration_id, (catalog, column) in sorted(families.items()):
            for row in self._rows(catalog):
                value = row.get(column)
                if value is None:
                    shown = {k: v for k, v in row.items() if k != "metadata"}
                    unbound.append(
                        PayloadProblem(
                            PayloadFault.ROW_UNNAMED,
                            f"a {catalog} row carries no {column}, so nothing binds it: {shown}",
                        )
                    )
                    continue
                rows.setdefault(str(value), []).append(declaration_id)
        referenced = {*self.media, *self.arrays}
        problems: list[PayloadProblem] = []
        bound: list[tuple[opaque.StagedPayload, str]] = []
        by_id: dict[str, list[opaque.StagedPayload]] = {}
        for payload in self.payloads:
            resource_id, where = payload.resource_id, opaque.shown(payload.path.parent)
            by_id.setdefault(resource_id, []).append(payload)
            matched, singleton = rows.get(resource_id, []), resource_id in singletons
            if matched and singleton:
                problems.append(
                    PayloadProblem(
                        PayloadFault.ROW_AND_SINGLETON,
                        f"{payload.source}: {where} names {resource_id}, which is both a catalog row's resource_id "
                        "and an opaque singleton declaration",
                    )
                )
            elif singleton:
                if payload.owned is not None and resource_id not in payload.owned:
                    problems.append(
                        PayloadProblem(
                            PayloadFault.SINGLETON_NOT_OWNED,
                            f"{payload.source}: delivers a payload for opaque singleton {resource_id}, which the "
                            f"recipe does not leave {payload.source} owning (Part 05 §3.4)",
                        )
                    )
                bound.append((payload, resource_id))
            elif len(matched) == 1:
                bound.append((payload, matched[0]))
            elif matched:
                problems.append(
                    PayloadProblem(
                        PayloadFault.SEVERAL_ROWS,
                        f"{payload.source}: {where} names {resource_id}, which {len(matched)} catalog rows carry",
                    )
                )
            else:
                problems.append(
                    PayloadProblem(
                        PayloadFault.BINDS_NOTHING,
                        f"{payload.source}: {where} names {resource_id}, which is the resource_id of no catalog row "
                        "of an opaque catalog family and the ID of no opaque singleton declaration",
                    )
                )
        for resource_id, payloads in sorted(by_id.items()):
            places = ", ".join(f"{p.source} at {opaque.shown(p.path.parent)}" for p in payloads)
            if len(payloads) > 1:
                problems.append(
                    PayloadProblem(
                        PayloadFault.DELIVERED_TWICE,
                        f"{resource_id} is delivered as a payload {len(payloads)} times: {places}",
                    )
                )
            if resource_id in referenced:
                problems.append(
                    PayloadProblem(
                        PayloadFault.DELIVERED_AND_REFERENCED,
                        f"{resource_id} is delivered both as a payload ({places}) and as a referenced resource",
                    )
                )
        delivered = set(by_id) | referenced
        unbound += [
            PayloadProblem(
                PayloadFault.ROW_UNBOUND,
                f"{families[declaration_id][0]} row with resource_id {resource_id} is bound by no payload or "
                "referenced resource",
            )
            for resource_id, declarations in sorted(rows.items())
            for declaration_id in declarations
            if resource_id not in delivered
        ]
        if refused := [*problems, *unbound]:
            raise PayloadRefused("; ".join(p.message for p in refused) + " (Part 12 §5)", problems=refused)
        return bound

    def stage_arrays(self, staging: Path, place: Callable[[str, str, str], str]) -> list[dict[str, Any]]:
        """Write every staged array under `staging` and return its manifest entries.

        `place` returns where a resource is written under the packet root, given its folder,
        its resource ID and its suffix.
        """
        if not self.staged:
            return []
        from .arrays import write_zarr

        entries = []
        for resource_id, spec in self.staged.items():
            declaration_id = spec.declaration_id
            relative = place("arrays", resource_id, "zarr")
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if spec.written is not None:
                # Delivered: the adapter wrote it, so staging moves it rather than writing it
                # again, and what the manifest says about it is read off the array (Part 12 §5).
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(spec.written), str(path))
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            else:
                if spec.dimension_names is None:
                    spec = replace(spec, dimension_names=self._dimension_names(spec))
                size = write_zarr(path, spec)
            uri = encode(relative.split("/"))
            entries.append(resource_entry(resource_id, declaration_id, uri, owned=path, size_bytes=size))
        return entries

    def stage_payloads(self, staging: Path, bound: Sequence[tuple[opaque.StagedPayload, str]]) -> list[dict[str, Any]]:
        """Move each bound payload's resource directory under `staging` and return its manifest entries.

        The directory holds its payload alone, so moving it whole publishes the payload under its own
        name in a directory holding nothing else (Part 03 §11), and promotion is then one rename.
        """
        entries = []
        for payload, declaration_id in bound:
            directory = staging / opaque.ROOT / payload.resource_id
            directory.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(payload.path.parent), str(directory))
            staged = directory / payload.path.name
            uri = encode((opaque.ROOT, payload.resource_id, payload.path.name))
            entries.append(
                resource_entry(payload.resource_id, declaration_id, uri, owned=staged, size_bytes=opaque.size(staged))
            )
        return entries

    def array_entries(self) -> list[dict[str, Any]]:
        """Return a manifest entry per referenced array. Copies nothing and reads nothing."""
        return [
            resource_entry(resource_id, array.declaration_id, array.uri, referenced=array)
            for resource_id, array in self.arrays.items()
        ]

    def media_entries(self) -> list[dict[str, Any]]:
        """Return a manifest entry per referenced media asset. Copies nothing and reads nothing."""
        return [
            resource_entry(resource_id, media.declaration_id, media.uri, referenced=media)
            for resource_id, media in self.media.items()
        ]

    def _bind_catalog_row(
        self,
        declaration: Mapping[str, Any],
        resource_id: str,
        source_column: str,
        source_value: str,
    ) -> None:
        """Put packet identity on the one catalog row delivered for a payload."""
        instances = declaration["instances"]
        catalog = str(instances["catalog_resource"])
        resource_column = str(instances["resource_id_column"])
        rows = self._rows(catalog)
        matching = [row for row in rows if str(row.get(source_column)) == source_value]
        if len(matching) != 1:
            raise UsageError(
                f"{resource_id}: {catalog}.{source_column}={source_value!r} resolves {len(matching)} catalog rows",
                code=UsageFault.CATALOG_ROW_UNBOUND,
                where=resource_id,
            )
        current = matching[0].get(resource_column)
        if current is not None and current != resource_id:
            raise UsageError(
                f"{catalog}.{resource_column} is {current!r}, not delivered resource {resource_id!r}",
                code=UsageFault.CATALOG_ROW_TAKEN,
                where=resource_id,
            )
        matching[0][resource_column] = resource_id

    def _delivered_binding(self, resource_id: str, array: StagedArray) -> StagedArray:
        """Bind an array delivered by name to the one catalog row carrying that name (Part 12 §5).

        A delivery names an array's directory by the row's `resource_id` and says nothing else, so
        the row is found among every dense-array catalog, and the array takes that catalog's
        declaration and the row's own identifier.
        """
        matching = []
        for declaration_id in [d for document in self._declarations.documents for d in document["resources"]]:
            declaration = self._declarations.declaration(declaration_id)
            if declaration is None or declaration["kind"] != "dense_array":
                continue
            instances = declaration["instances"]
            if instances["mode"] != "catalog":
                continue
            column = str(instances["resource_id_column"])
            matching += [
                (declaration_id, row)
                for row in self._rows(str(instances["catalog_resource"]))
                if row.get(column) == resource_id
            ]
        if len(matching) != 1:
            raise UsageError(
                f"{resource_id}: a delivered array binds {len(matching)} catalog rows, not one",
                code=UsageFault.CATALOG_ROW_UNBOUND,
                where=resource_id,
            )
        declaration_id, row = matching[0]
        return replace(array, declaration_id=declaration_id, array_asset_id=str(row["array_asset_id"]))

    def _dimension_names(self, spec: StagedArray) -> tuple[str, ...] | None:
        """Return a staged array's axis names from its axes records, or None where it has none."""
        declaration = self._declarations.declaration(spec.declaration_id) or {}
        axes = (declaration.get("array") or {}).get("axes_resource")
        rows = sorted(
            (r for r in self._rows(str(axes)) if str(r.get("array_asset_id")) == spec.array_asset_id),
            key=lambda r: int(r["axis_index"]),
        )
        return tuple(str(r["dimension_name"]) for r in rows) or None


__all__ = ["Attachments"]
