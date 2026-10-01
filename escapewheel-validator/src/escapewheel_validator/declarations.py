"""The manifest's entries against the declarations they name, and the sources they name.

- :func:`check_resource_declarations` -- each entry against the declaration it names, and each
  declaration's requirements against the entries.
- :func:`check_sources` -- what a source declaration must be, and which named sources the
  resolution document beside the packet locates.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

import pyarrow as pa
from escapewheel_reader import Packet, PacketError
from escapewheel_reader.location import SOURCES_FILENAME

from . import check_table
from .registry_types import (
    visible_declarations,
)
from .report import Report


def check_resource_declarations(  # noqa: C901 - one ordered cross-artifact validation phase
    packet: Packet,
    core: Mapping[str, Any],
    extensions: Mapping[str, Mapping[str, Any]],
    withheld: Collection[str],
    report: Report,
) -> None:
    """Part 04 §10's `declaration` phase, from the bound registries that may direct checks.

    An entry in the namespace of an extension registry that failed binding or its registry result
    is withheld rather than reported undeclared: nothing about it can be decided (Part 05 §14.5).
    """
    visible = visible_declarations(core, list(extensions.values()))
    entries = [entry for entry in packet.resources() if entry.declaration_id.split(".", 1)[0] not in withheld]
    by_id = {entry.resource_id: entry for entry in packet.resources()}

    for entry in entries:
        declaration = visible.get(entry.declaration_id)
        if declaration is None:
            report.add(
                check_table.PACKET_RESOURCE_DECLARATION_UNKNOWN,
                f"{entry.resource_id}: declaration {entry.declaration_id!r} is not visible",
                resource=entry.resource_id,
            )
            continue
        instances = declaration["instances"]
        mode = instances["mode"]
        if mode == "singleton" and entry.resource_id != entry.declaration_id:
            report.add(
                check_table.PACKET_RESOURCE_SINGLETON_IDENTITY,
                f"{entry.resource_id}: singleton identity must equal {entry.declaration_id}",
                registry=report.owner(entry.declaration_id),
                resource=entry.resource_id,
            )
        if mode == "family" and entry.resource_id.split(".", 1)[0] != entry.declaration_id.split(".", 1)[0]:
            report.add(
                check_table.PACKET_RESOURCE_FAMILY_NAMESPACE,
                f"{entry.resource_id}: family identity is outside {entry.declaration_id}'s namespace",
                registry=report.owner(entry.declaration_id),
                resource=entry.resource_id,
            )
        for dependency in declaration["requires"]:
            if dependency not in by_id:
                report.add(
                    check_table.PACKET_RESOURCE_DEPENDENCY_MISSING,
                    f"{entry.resource_id}: required singleton {dependency} is absent",
                    registry=report.owner(entry.declaration_id),
                    resource=entry.resource_id,
                )
        if declaration["kind"] == "dense_array":
            axes = declaration["array"]["axes_resource"]
            if axes not in by_id:
                report.add(
                    check_table.PACKET_RESOURCE_ARRAY_AXES_MISSING,
                    f"{entry.resource_id}: declaration-selected axes resource {axes} is absent",
                    registry=report.owner(entry.declaration_id),
                    resource=entry.resource_id,
                )

        present = "derived_from" in entry.entry
        if declaration["lineage"] == "required" and not present:
            report.add(
                check_table.PACKET_RESOURCE_DERIVED_FROM_REQUIRED,
                f"{entry.resource_id}: derived_from is required by {entry.declaration_id}",
                registry=report.owner(entry.declaration_id),
                resource=entry.resource_id,
            )
        elif declaration["lineage"] == "forbidden" and present:
            report.add(
                check_table.PACKET_RESOURCE_DERIVED_FROM_FORBIDDEN,
                f"{entry.resource_id}: derived_from is forbidden by {entry.declaration_id}",
                registry=report.owner(entry.declaration_id),
                resource=entry.resource_id,
            )

    active_extension_ids = set(extensions)
    for declaration_id, declaration in visible.items():
        instances = declaration["instances"]
        active = declaration_id.split(".", 1)[0] in {"core", "analysis"} | active_extension_ids
        if (
            active
            and instances["mode"] == "singleton"
            and instances["presence"] == "required"
            and declaration_id not in by_id
        ):
            report.add(
                check_table.PACKET_RESOURCE_REQUIRED_MISSING,
                f"required singleton {declaration_id} is absent",
                registry=report.owner(declaration_id),
                resource=declaration_id,
            )

    for declaration_id, declaration in visible.items():
        if declaration["kind"] != "table" or declaration_id not in by_id:
            continue
        for reference in declaration["table"]["references"]:
            target = str(reference["resource"])
            if target in by_id:
                continue
            columns = list(reference["columns"])
            try:
                table = packet.table(declaration_id, columns=columns)
            except (PacketError, OSError, pa.ArrowException):
                continue
            values = zip(
                *(table.column(column).to_pylist() for column in columns),
                strict=True,
            )
            if any(all(value is not None for value in row) for row in values):
                report.add(
                    check_table.PACKET_RESOURCE_REFERENCE_TARGET_MISSING,
                    f"{declaration_id}: populated foreign key {columns} requires {target}",
                    registry=report.owner(declaration_id),
                    resource=declaration_id,
                    column=columns[0] if len(columns) == 1 else None,
                )

    catalog_families = {
        (declaration["instances"]["catalog_resource"], declaration["instances"]["resource_id_column"]): (
            declaration_id,
            declaration,
        )
        for declaration_id, declaration in visible.items()
        if declaration["instances"]["mode"] == "catalog"
    }
    for (catalog_id, column), (declaration_id, _) in catalog_families.items():
        if catalog_id not in by_id:
            continue
        try:
            values = packet.table(catalog_id, columns=[column]).column(column).to_pylist()
        except (PacketError, OSError, pa.ArrowException) as exc:
            report.add(
                check_table.PACKET_RESOURCE_CATALOG_TABLE_UNREADABLE,
                f"{catalog_id}.{column}: {exc}",
                registry=report.owner(catalog_id),
                resource=catalog_id,
                column=column,
            )
            continue
        normalized = [str(value) for value in values if value is not None]
        counts = Counter(normalized)
        for value, count in counts.items():
            matches = [
                entry for entry in entries if entry.resource_id == value and entry.declaration_id == declaration_id
            ]
            if count != 1 or len(matches) != 1:
                report.add(
                    check_table.PACKET_RESOURCE_CATALOG_ROW_BINDING,
                    f"{catalog_id}.{column}={value!r} does not bind one {declaration_id} resource",
                    registry=report.owner(declaration_id),
                    resource=catalog_id,
                    column=column,
                )
        catalog_values = set(normalized)
        for entry in entries:
            if entry.declaration_id == declaration_id and entry.resource_id not in catalog_values:
                report.add(
                    check_table.PACKET_RESOURCE_CATALOG_ROW_BINDING,
                    f"{entry.resource_id}: no row in {catalog_id}.{column}",
                    registry=report.owner(declaration_id),
                    resource=entry.resource_id,
                )

    permitted = {
        "core": {"core"},
        "extension": {"core", "extension"},
        "analysis": {"core", "extension", "analysis"},
        "compatibility_projection": {"core", "extension", "analysis"},
        "documentation": set(),
    }
    graph: dict[str, set[str]] = {}
    for entry in entries:
        declaration = visible.get(entry.declaration_id)
        sources = entry.entry.get("derived_from", [])
        if declaration is None or not isinstance(sources, list):
            continue
        graph[entry.resource_id] = set(map(str, sources))
        for source in sources:
            source_entry = by_id.get(str(source))
            source_declaration = None if source_entry is None else visible.get(source_entry.declaration_id)
            if source_declaration is None:
                report.add(
                    check_table.PACKET_RESOURCE_LINEAGE_UNRESOLVED,
                    f"{entry.resource_id}: lineage source {source!r} is absent or undeclared",
                    registry=report.owner(entry.declaration_id),
                    resource=entry.resource_id,
                )
            elif source_declaration["content_class"] not in permitted[declaration["content_class"]]:
                report.add(
                    check_table.PACKET_RESOURCE_LINEAGE_CLASS,
                    f"{entry.resource_id}: {declaration['content_class']} may not derive from "
                    f"{source_declaration['content_class']}",
                    registry=report.owner(entry.declaration_id),
                    resource=entry.resource_id,
                )

    def cyclic(node: str, path: frozenset[str]) -> bool:
        return node in path or any(cyclic(child, path | {node}) for child in graph.get(node, ()) if child in graph)

    for node in graph:
        if cyclic(node, frozenset()):
            report.add(check_table.PACKET_RESOURCE_LINEAGE_CYCLE, f"lineage cycle reaches {node}")
            break


def check_sources(packet: Packet, report: Report) -> None:
    """Check what a source declaration must be, without reaching the network (Part 04 §5.5).

    Two things are structural and one is not; the manifest schema already requires `external` beside
    a `source`. A `source` names a body of data rather than a location, so the entry's `uri` MUST be
    relative to it. `sources.json` MUST NOT be a declared resource: being outside the manifest is
    what keeps Part 03 §8.1's immutability off it, and a packet that declared it would freeze the
    one file that has to stay editable.

    Whether a source **resolves** is not structural and is reported rather than failed. An
    unresolved source is a fact about the reader's situation -- which mirrors it can reach -- and
    Part 04 §5.3 keeps structural validation off the network, so this reports what the packet names
    and leaves reachability to the mode that asks for it.
    """
    named: dict[str, list[str]] = {}
    for resource in packet.resources():
        source = resource.source
        if source is None:
            if Path(str(resource.entry.get("uri", ""))).name == SOURCES_FILENAME:
                report.add_about(
                    resource.resource_id,
                    check_table.SOURCES_DECLARED,
                    f"{resource.resource_id} declares {SOURCES_FILENAME} as a resource; Part 04 §5.5 keeps it "
                    "outside the manifest so Part 03 §8.1's immutability does not reach it",
                )
            continue
        named.setdefault(source, []).append(resource.resource_id)
        if "://" in resource.uri:
            report.add_about(
                resource.resource_id,
                check_table.SOURCES_ABSOLUTE_URI,
                f"{resource.resource_id} names source {source!r} and an absolute uri {resource.uri!r}; "
                "where a source is named the uri is a path under it (Part 04 §5.5)",
            )
    if not named:
        return
    located = dict(packet.location.sources)
    unresolved = sorted(name for name in named if name not in located)
    report.add(
        check_table.SOURCES_DECLARED_COUNT,
        f"{len(named)} source(s) named by {sum(len(v) for v in named.values())} resource(s); "
        f"{len(named) - len(unresolved)} located by a resolution document",
        counts={
            "sources": len(named),
            "resources": sum(len(v) for v in named.values()),
            "located": len(named) - len(unresolved),
        },
    )
    if unresolved:
        # A fact, not a defect: the packet is conforming and this reader cannot reach
        # those bytes. Reported so a report says which, rather than leaving it to a later failure.
        report.add(
            check_table.SOURCES_UNRESOLVED,
            f"{len(unresolved)} source(s) no available resolution document locates (Part 04 §5.5)",
            ((name, ", ".join(named[name][:3])) for name in unresolved),
            counts={"unresolved": len(unresolved)},
        )


__all__: list[str] = []
