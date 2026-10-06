"""A dense array's own metadata, and its shape against the tables that describe it.

- :func:`check_packet_owned_arrays` -- every packet-owned array against the Zarr metadata in its
  store.
- :func:`declared_axes` -- each array's axes, labels and channels as the packet's tables assert
  them, as an :class:`ArrayAxes`.
- :func:`compare_shape` -- an external array's stored shape against its :class:`ArrayAxes`.

The same comparison of shape with label and channel rows serves a packet-owned and an external
array, reported under each one's own check IDs.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import pyarrow as pa
from escapewheel_reader import Packet, PacketError, ResourceUnreadableError
from escapewheel_reader.resource_ids import (
    CORE_ARRAY_CHANNELS,
)

from .. import check_table, stores
from ..check_table import CheckEntry
from ..errors import ResourceMissing, StoreUnreachable
from ..report import ROW_CAP, Report
from .floors import check_zarr_floor
from .owned import owned_uri


def _codec_names(pipeline: Iterable[Any]) -> set[str]:
    """Every codec a v3 pipeline names, inside a shard too, where Part 03 §6.2 bans `transpose` as well."""
    names = set()
    for codec in pipeline:
        if isinstance(codec, str):
            names.add(codec)
            continue
        names.add(str(codec.get("name", "")))
        configuration = codec.get("configuration") or {}
        for member in ("codecs", "index_codecs"):
            names |= _codec_names(configuration.get(member) or ())
    return names


def _check_one_array(resource: Any, handle: Any, declared: Mapping[str, ArrayAxes], report: Report) -> None:
    """Check one packet-owned array against the metadata document in its own store."""
    try:
        metadata = handle.metadata()
        actual = _codec_names(metadata.get("codecs") or handle.codecs)
        rank = len(handle.shape)
    except (ResourceUnreadableError, OSError, ValueError, KeyError) as exc:
        report.add_about(
            resource.resource_id,
            check_table.ARRAY_UNREADABLE,
            f"{resource.resource_id}: {exc}",
        )
        return

    if handle.zarr_format != 3:
        report.add_about(
            resource.resource_id,
            check_table.ARRAY_NOT_ZARR_V3,
            f"{resource.resource_id} is packet-owned but stored as Zarr v{handle.zarr_format}; "
            "Part 03 §6.1 allows v2 only for an array the packet references",
        )

    if "transpose" in actual:
        report.add_about(
            resource.resource_id,
            check_table.ARRAY_TRANSPOSE_CODEC,
            f"{resource.resource_id} uses the transpose codec, which Part 03 §6.2 forbids: axes are stored in the "
            "order the packet declares them",
        )

    check_zarr_floor(resource, metadata, report)

    if (grid := metadata.get("chunk_grid", {}).get("name")) != "regular":
        report.add_about(
            resource.resource_id,
            check_table.ARRAY_IRREGULAR_CHUNK_GRID,
            f"{resource.resource_id} declares a {grid!r} chunk grid; Part 03 §6.1 requires a regular one",
        )

    if "fill_value" not in metadata:
        report.add_about(
            resource.resource_id,
            check_table.ARRAY_NO_FILL_VALUE,
            f"{resource.resource_id} declares no fill_value, which Zarr v3 requires of array metadata; "
            "Part 03 §6.1 requires a packet-owned array to be Zarr v3",
        )

    if (axes := declared.get(resource.resource_id)) is None:
        return
    shape = [int(n) for n in handle.shape]
    if set(axes.names) != set(range(rank)):
        report.add_about(
            resource.resource_id,
            check_table.ARRAY_RANK_DISAGREES_WITH_DIMENSIONS,
            f"{resource.resource_id} has rank {rank} but its declaration-selected axes resource "
            f"gives axis_index {sorted(axes.names) or 'none'}; Part 02 §12.11 requires one row per stored axis",
        )
        return
    _report_axes(resource, shape, axes, _OWNED_AXIS_CHECKS, report)
    names = [axes.names[axis] for axis in range(rank)]
    if metadata.get("dimension_names") != names:
        report.add_about(
            resource.resource_id,
            check_table.ARRAY_DIMENSION_NAMES,
            f"{resource.resource_id} stores dimension_names {metadata.get('dimension_names')!r} where its axes "
            f"resource names {names!r}; Part 03 §6.4 requires a packet-owned array to carry them",
        )


def check_packet_owned_arrays(packet: Packet, report: Report) -> None:
    """Check every packet-owned array against its own Zarr metadata (Part 04 §5.3, level 2).

    Always runs, and needs no Zarr: a Zarr array's metadata is a JSON document in the store,
    which `ArrayResource` parses directly. The packet owns these bytes, so an array it
    describes wrongly is a defect in the packet rather than in the reader's situation. An
    external array is level 3 and stays with the requested mode, and `report_unassessed` reports it
    where that mode did not read it.

    Storage, not values, so the shim and not SQL (Part 05 §5.3): no query can see a chunk grid or a codec
    pipeline.
    """
    # A resource naming a source is not packet-owned whatever `external` says, and `check_sources`
    # has already reported the contradiction; resolving it here would raise instead of report.
    owned = [r for r in packet.resources(kind="dense_array") if not r.is_external and r.source is None]
    if not owned:
        return
    declared = declared_axes(packet)
    if not declared:
        report.add(
            check_table.ARRAY_NO_ARRAY_DIMENSIONS_TABLE,
            f"{len(owned)} packet-owned array(s) but no declaration-selected axes rows were resolved",
            counts={"arrays": len(owned)},
        )
    for resource in owned:
        try:
            stores.listing(owned_uri(packet, resource.entry))
        except ResourceMissing as exc:
            report.add_about(
                resource.resource_id,
                check_table.RESOURCE_MISSING,
                f"{resource.resource_id}: {exc}",
            )
            continue
        except StoreUnreachable:
            pass  # `_check_one_array` reports what it cannot read
        _check_one_array(resource, packet.array_resource(resource.resource_id), declared, report)


@dataclass
class ArrayAxes:
    """What a packet's tables assert about one dense array's axes (Part 02 §12.11).

    Keyed by stored `axis_index`. `labels` holds each labelled axis's rows as
    (`depends_on_position_index`, `position_index`), and `channels` holds `core.array_channels`
    rows as (`axis_index`, `channel_index`).
    """

    names: dict[int, Any] = field(default_factory=dict)
    depends: dict[int, int] = field(default_factory=dict)
    labelled: set[int] = field(default_factory=set)
    labels: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    channels: list[tuple[int, int]] = field(default_factory=list)


def _rows_by_array(
    packet: Packet, table_id: str, key: Sequence[str], columns: Sequence[str], cache: dict[Any, Any]
) -> dict[tuple[Any, ...], list[tuple[Any, ...]]]:
    """Read a table once and group the named columns by the array key, or return {} if unreadable."""
    if (table_id, tuple(key), tuple(columns)) in cache:
        return cache[table_id, tuple(key), tuple(columns)]
    grouped: dict[tuple[Any, ...], list[tuple[Any, ...]]] = {}
    try:
        present = set(packet.table_resource(table_id).schema().names)
        wanted = [*key, *(c for c in columns if c in present)]
        rows = packet.table(table_id, columns=list(dict.fromkeys(wanted)))
    except (PacketError, OSError, pa.ArrowException):
        cache[table_id, tuple(key), tuple(columns)] = grouped
        return grouped
    values = [rows.column(c).to_pylist() if c in rows.column_names else [None] * rows.num_rows for c in columns]
    for row in zip(*(rows.column(c).to_pylist() for c in key), *values, strict=True):
        grouped.setdefault(tuple(row[: len(key)]), []).append(tuple(row[len(key) :]))
    cache[table_id, tuple(key), tuple(columns)] = grouped
    return grouped


def declared_axes(packet: Packet) -> dict[str, ArrayAxes]:  # noqa: C901
    """Resolve each dense array's axes, labels and channels through its declaration and catalog row.

    The label rows are in the table the axes table's `coordinate_resource` names as its
    `discriminates_via`; they and `core.array_channels` reach the array through their
    reference to the axes table.
    """
    declarations: dict[str, Mapping[str, Any]] = {}
    for document in (packet.registry, *packet.extensions().values()):
        if isinstance(document, Mapping):
            declarations.update(document.get("resources", {}))

    cache: dict[Any, Any] = {}
    found: dict[str, ArrayAxes] = {}
    for resource in packet.resources(kind="dense_array"):
        declaration = declarations.get(resource.declaration_id)
        if declaration is None:
            continue
        instances = declaration["instances"]
        catalog_id = str(instances["catalog_resource"])
        resource_column = str(instances["resource_id_column"])
        axes_id = str(declaration["array"]["axes_resource"])
        catalog_declaration = declarations.get(catalog_id)
        axes_declaration = declarations.get(axes_id)
        if catalog_declaration is None or axes_declaration is None:
            continue
        catalog_key = list(catalog_declaration["table"]["primary_key"] or [])
        axes_table = axes_declaration["table"]
        binding = next(
            (
                reference
                for reference in axes_table["references"]
                if reference["resource"] == catalog_id and reference["resource_columns"] == catalog_key
            ),
            None,
        )
        if binding is None:
            continue
        catalog = _rows_by_array(packet, catalog_id, [resource_column], catalog_key, cache)
        if not (keys := catalog.get((resource.resource_id,))):
            continue
        wanted_key = keys[0]
        axes = ArrayAxes()
        extra = ["axis_index", "dimension_name", "coordinate_resource", "depends_on_axis_index"]
        for axis, name, coordinate, depends in _rows_by_array(packet, axes_id, binding["columns"], extra, cache).get(
            wanted_key, []
        ):
            if axis is None:
                continue
            axes.names[int(axis)] = name
            if coordinate is not None:
                axes.labelled.add(int(axis))
            if depends is not None:
                axes.depends[int(axis)] = int(depends)
        if not axes.names:
            continue
        found[resource.resource_id] = axes

        labels_id = next(
            (
                str(c["discriminates_via"]).rsplit(".", 1)[0]
                for c in axes_table["columns"]
                if c["name"] == "coordinate_resource" and c.get("discriminates_via")
            ),
            None,
        )
        for table_id, columns in (
            (labels_id, ["depends_on_position_index", "position_index"]),
            (CORE_ARRAY_CHANNELS, ["channel_index"]),
        ):
            table = (declarations.get(table_id or "") or {}).get("table")
            reference = next(
                (r for r in (table or {}).get("references", []) if r["resource"] == axes_id),
                None,
            )
            if reference is None:
                continue
            mapped = dict(zip(reference["resource_columns"], reference["columns"], strict=True))
            if "axis_index" not in mapped or not set(binding["columns"]) <= set(mapped):
                continue
            key = [mapped[c] for c in binding["columns"]]
            rows = _rows_by_array(packet, str(table_id), key, [mapped["axis_index"], *columns], cache)
            for row in rows.get(wanted_key, []):
                if any(value is None for value in row):
                    continue
                if table_id == labels_id:
                    axes.labels.setdefault(int(row[0]), []).append((int(row[1]), int(row[2])))
                else:
                    axes.channels.append((int(row[0]), int(row[1])))
    return found


class _AxisFault(Enum):
    """One way an array's label and channel rows disagree with its shape (Part 02 §12.11)."""

    LABEL_POSITION = auto()
    DEPENDS_ON_POSITION = auto()
    LABEL_MISSING = auto()
    CHANNEL_INDEX = auto()


def _axis_findings(shape: Sequence[int], axes: ArrayAxes) -> dict[_AxisFault, list[tuple[Any, ...]]]:
    """Compare one array's shape with its label and channel rows, by fault."""
    length = dict(enumerate(shape))
    found: dict[_AxisFault, list[tuple[Any, ...]]] = {fault: [] for fault in _AxisFault}
    for axis in sorted(axes.labelled | set(axes.labels)):
        if axis not in length:
            continue
        outer = axes.depends.get(axis)
        outer_length = length.get(outer, 0) if outer is not None else None
        seen: set[tuple[int, int]] = set()
        for depends_on, position in axes.labels.get(axis, []):
            if not 0 <= position < length[axis]:
                found[_AxisFault.LABEL_POSITION].append(
                    (f"axis_index {axis}", f"position_index {position}", f"length {length[axis]}")
                )
            elif outer_length is not None and not 0 <= depends_on < outer_length:
                found[_AxisFault.DEPENDS_ON_POSITION].append(
                    (f"axis_index {axis}", f"depends_on_position_index {depends_on}", f"length {outer_length}")
                )
            else:
                seen.add((depends_on if outer_length is not None else 0, position))
        if axis not in axes.labelled:
            continue
        outer_positions = outer_length if outer_length is not None else 1
        # `seen` holds only in-range pairs, and the key makes each unique, so the count is exact.
        if not (missing := outer_positions * length[axis] - len(seen)):
            continue
        pairs = itertools.product(range(outer_positions), range(length[axis]))
        # Capped per axis, so a wholly unlabelled axis does not list every position.
        for depends_on, position in itertools.islice((p for p in pairs if p not in seen), ROW_CAP):
            where = f"position_index {position}"
            if outer_length is not None:
                where = f"depends_on_position_index {depends_on}, {where}"
            found[_AxisFault.LABEL_MISSING].append((f"axis_index {axis}", where, f"{missing} missing"))
    for axis, channel in axes.channels:
        if axis in length and not 0 <= channel < length[axis]:
            found[_AxisFault.CHANNEL_INDEX].append(
                (f"axis_index {axis}", f"channel_index {channel}", f"length {length[axis]}")
            )
    return found


_AXIS_MESSAGES = {
    _AxisFault.LABEL_POSITION: "label row(s) name a position_index beyond the axis (Part 02 §12.11)",
    _AxisFault.DEPENDS_ON_POSITION: (
        "label row(s) name a depends_on_position_index beyond the axis depended on (Part 02 §12.11)"
    ),
    _AxisFault.LABEL_MISSING: "position(s) of a labelled axis have no label row (Part 02 §12.11)",
    _AxisFault.CHANNEL_INDEX: "core.array_channels row(s) name a channel_index beyond their axis (Part 05 §5.3)",
}


#: The check each fault of a packet-owned array is reported under.
_OWNED_AXIS_CHECKS = {
    _AxisFault.LABEL_POSITION: check_table.ARRAY_LABEL_POSITION_OUT_OF_RANGE,
    _AxisFault.DEPENDS_ON_POSITION: check_table.ARRAY_DEPENDS_ON_POSITION_OUT_OF_RANGE,
    _AxisFault.LABEL_MISSING: check_table.ARRAY_LABEL_MISSING,
    _AxisFault.CHANNEL_INDEX: check_table.ARRAY_CHANNEL_INDEX_OUT_OF_RANGE,
}


#: The check each fault of an external array is reported under.
_EXTERNAL_AXIS_CHECKS = {
    _AxisFault.LABEL_POSITION: check_table.EXTERNAL_ARRAY_LABEL_POSITION_OUT_OF_RANGE,
    _AxisFault.DEPENDS_ON_POSITION: check_table.EXTERNAL_ARRAY_DEPENDS_ON_POSITION_OUT_OF_RANGE,
    _AxisFault.LABEL_MISSING: check_table.EXTERNAL_ARRAY_LABEL_MISSING,
    _AxisFault.CHANNEL_INDEX: check_table.EXTERNAL_ARRAY_CHANNEL_INDEX_OUT_OF_RANGE,
}


def _report_axes(
    resource: Any, shape: Sequence[int], axes: ArrayAxes, entries: Mapping[_AxisFault, CheckEntry], report: Report
) -> None:
    """Report each way an array's label and channel rows disagree with its shape, under its entry of `entries`."""
    for fault, rows in _axis_findings(shape, axes).items():
        if rows:
            report.add_about(
                resource.resource_id,
                entries[fault],
                f"{resource.resource_id}: {_AXIS_MESSAGES[fault]}",
                rows,
            )


def compare_shape(
    resource: Any, metadata: Mapping[str, Any], declared: Mapping[str, ArrayAxes], report: Report
) -> list[str]:
    """Check an external array's stored shape against what the packet's tables assert (Part 02 §12.11).

    This is the check that catches a change actually invalidating the packet. A re-generated
    array with a different channel count leaves its label rows naming positions that are not
    there, or positions with none; neither changes what the packet claims about the array's
    values, which is why this and not a content digest is what an external array needs verified.

    Cheap: one request for the metadata document the array's store already holds.
    """
    if (axes := declared.get(resource.resource_id)) is None or not axes.names:
        return []
    if not isinstance(shape := metadata.get("shape"), list):
        return []
    if set(axes.names) != set(range(len(shape))):
        report.add_about(
            resource.resource_id,
            check_table.EXTERNAL_ARRAY_RANK,
            f"{resource.resource_id} is stored with rank {len(shape)} but its declaration-selected "
            f"axes resource gives axis_index {sorted(axes.names)}; Part 02 §12.11 requires one row per stored axis",
        )
        return ["rank"]
    _report_axes(resource, [int(n) for n in shape], axes, _EXTERNAL_AXIS_CHECKS, report)
    return ["rank", *(["labels"] if axes.labelled else []), *(["channels"] if axes.channels else [])]


__all__: list[str] = []
