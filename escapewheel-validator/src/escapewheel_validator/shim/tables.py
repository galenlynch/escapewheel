"""A table's physical schema, and the values a registry constrains without a rule.

- :func:`check_schemas` -- column presence and physical type, and each table's encodings against
  the reader floor.
- :func:`check_duplication` -- pairs of columns holding equal values in every row.
- :func:`check_unfilled_metadata` -- a declared `metadata` column no row fills.
- :func:`check_reserved_values` -- a value outside a column's reserved set.
- :func:`check_unit_codes` -- a unit column's values as UCUM codes.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from escapewheel_reader import Packet, PacketError

from .. import check_table
from ..registry_document import (
    UCUM_URI,
    ucum_error,
)
from ..registry_types import ARROW_TYPES
from ..report import ROW_CAP, Report
from ..vocabulary import EvaluationStatus
from .floors import check_parquet_floor


def check_schemas(packet: Packet, tables: Mapping[str, Any], report: Report) -> dict[str, Any]:
    """Check column presence and physical type, which SQL cannot see (Part 05 §5.3)."""
    declared = {r.resource_id for r in packet.resources()}
    present: dict[str, Any] = {}
    for resource_id, spec in tables.items():
        if resource_id not in declared:
            continue  # a packet need not carry every table
        handle = packet.table_resource(resource_id)
        try:
            schema = handle.schema()
        except PacketError as exc:
            report.add_about(resource_id, check_table.RESOURCE_MISSING, str(exc))
            continue
        present[resource_id] = handle
        for column in spec["columns"]:
            _check_column(resource_id, column, schema, report)
        path, filesystem = (handle.path, None) if handle.is_local else handle.location.store()
        try:
            footer = pq.read_metadata(path, filesystem=filesystem)
        except (OSError, pa.ArrowException) as exc:
            # An unreadable footer leaves the floor unassessed, which is incomplete rather than failed (Part 05 §9.4).
            report.record_evaluation(
                report.resource_owner(resource_id) or "core",
                EvaluationStatus.INCOMPLETE,
                rule=check_table.PHYSICAL_OUTSIDE_READER_FLOOR.id,
                detail=str(exc).splitlines()[0][:160],
            )
            continue
        check_parquet_floor(handle.resource, footer, report)
    return present


def _check_column(resource_id: str, column: Mapping[str, Any], schema: Any, report: Report) -> None:
    """Check one column's presence and type against the registry."""
    if column["name"] not in schema.names:
        if column["presence"] != "optional":
            report.add_about(
                resource_id,
                check_table.SCHEMA_COLUMN_ABSENT,
                f"{resource_id}.{column['name']} absent (presence={column['presence']})",
                column=column["name"],
            )
        return
    actual = schema.field(column["name"]).type
    # A dictionary is an encoding, not a type. Parquet has no dictionary type at all: the column
    # is BYTE_ARRAY/String either way, and only the Arrow schema pyarrow stores as metadata
    # distinguishes them. Comparing the wrapper would reject a conforming file over how its
    # writer chose to hold the column.
    if pa.types.is_dictionary(actual):
        actual = actual.value_type
    if str(actual) != ARROW_TYPES[column["type"]]:
        report.add_about(
            resource_id,
            check_table.SCHEMA_COLUMN_TYPE,
            f"{resource_id}.{column['name']} is {actual}, registry declares {column['type']}",
            column=column["name"],
        )


def _duplicated_columns(handle: Any, spec: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Pairs of this table's columns holding equal values in every row.

    Bounded by the footer, not by a row sample. Two columns can hold equal values in every row
    only if their per-chunk minimum, maximum and null count agree, which Parquet already records,
    so statistics decide almost every pair and values are read for the few that survive.

    Constant columns are excluded rather than reported. A column holding one value equals every
    other column holding that value, which says nothing about either.
    """
    reader = pq.ParquetFile(handle.path)
    meta, names = reader.metadata, reader.schema_arrow.names
    ranges: dict[str, list[Any]] = {}
    for index, name in enumerate(names):
        chunks: list[tuple[Any, Any, int | None]] = []
        for group in range(meta.num_row_groups):
            stats = meta.row_group(group).column(index).statistics
            if stats is None or not stats.has_min_max:
                chunks = []
                break
            chunks.append((stats.min, stats.max, stats.null_count))
        ranges[name] = chunks
    candidates = [
        (a, b)
        for a, b in itertools.combinations(names, 2)
        if ranges[a] and ranges[a] == ranges[b] and any(c[0] != c[1] for c in ranges[a])
    ]
    if not candidates:
        return []
    wanted = sorted({n for pair in candidates for n in pair})
    table = reader.read(columns=wanted)
    return [(a, b) for a, b in candidates if table.column(a).equals(table.column(b))]


def check_duplication(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 05 §5.3. Reported at `info` and never as a failure.

    Independently numbered identifiers can coincide, which is a fact about a packet rather than a
    defect in it.
    """
    for resource_id, handle in present.items():
        try:
            pairs = _duplicated_columns(handle, tables[resource_id])
        except (OSError, pa.ArrowException):
            continue
        for a, b in pairs:
            report.add_about(
                resource_id,
                check_table.columns_duplicated(resource_id),
                f"{a} and {b} hold equal values in every row",
            )


def check_unfilled_metadata(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 05 §5.3. A declared `metadata` column a resource's file omits or leaves null, at `info`.

    Whether a table in Part 02 §8.6's middle band declares one is a judgement, and this is the
    evidence against which it is revisited. Never a failure — Part 02 §6 makes an optional
    column's absence conforming, and a source with nothing unmodelled to say is the ordinary case.

    Bounded by the footer. A null count per row group is what Parquet already records, so no
    value is read.
    """
    for resource_id, handle in present.items():
        if not any(c["name"] == "metadata" for c in tables[resource_id]["columns"]):
            continue
        try:
            meta = pq.ParquetFile(handle.path).metadata
            index = meta.schema.names.index("metadata") if "metadata" in meta.schema.names else None
        except (OSError, pa.ArrowException):
            continue
        if index is None:
            report.add_about(
                resource_id,
                check_table.metadata_unfilled(resource_id),
                "metadata is declared and the file omits it",
            )
            continue
        nulls = 0
        for group in range(meta.num_row_groups):
            stats = meta.row_group(group).column(index).statistics
            if stats is None or stats.null_count is None:
                break
            nulls += stats.null_count
        else:
            if meta.num_rows and nulls == meta.num_rows:
                report.add_about(
                    resource_id,
                    check_table.metadata_unfilled(resource_id),
                    "metadata is null in every row",
                )


def check_reserved_values(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Report a value outside a column's reserved set at `info` (Part 02 §9.3).

    Never a failure: an open vocabulary admits an unrecognised value. A synonym of a reserved value
    is prohibited and cannot be recognised from the packet, so that obligation binds the writer and
    no check here enforces it.
    """
    for resource_id, handle in present.items():
        for column in tables[resource_id]["columns"]:
            reserved = column.get("reserved_values")
            if not reserved:
                continue
            name = column["name"]
            try:
                table = pq.read_table(handle.path, columns=[name])
            except (OSError, pa.ArrowException, KeyError):
                continue
            outside = sorted({v for v in table.column(name).to_pylist() if v is not None and v not in set(reserved)})
            if outside:
                report.add_about(
                    resource_id,
                    check_table.outside_reserved_set(resource_id, name),
                    f"{len(outside)} value(s) outside the reserved set: "
                    f"{', '.join(repr(v) for v in outside[:ROW_CAP])}" + (" ..." if len(outside) > ROW_CAP else ""),
                    column=name,
                    counts={"values": len(outside)},
                )


def check_unit_codes(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 05 §5.3. Every non-null value of a unit column is a UCUM code (Part 02 §8.4).

    Covers every table a directing registry declares (Part 05 §5.4), and files each finding and each
    unreadable column under that registry. Distinct values are parsed once each.
    """
    for resource_id, handle in present.items():
        for column in tables[resource_id]["columns"]:
            if not any(entry.get("uri") == UCUM_URI for entry in column.get("authority", ())):
                continue
            name = column["name"]
            check = check_table.ucum_code(resource_id, name)
            registry = report.resource_owner(resource_id) or "core"
            try:
                values = pc.unique(pq.read_table(handle.path, columns=[name]).column(name)).to_pylist()
            except (OSError, pa.ArrowException, KeyError) as exc:
                report.record_evaluation(
                    registry, EvaluationStatus.INCOMPLETE, rule=check.id, detail=str(exc).splitlines()[0][:160]
                )
                continue
            invalid = sorted(value for value in values if value is not None and ucum_error(value) is not None)
            if invalid:
                report.add(
                    check,
                    f"{len(invalid)} value(s) are not UCUM codes: {', '.join(repr(v) for v in invalid[:ROW_CAP])}"
                    + (" ..." if len(invalid) > ROW_CAP else ""),
                    [(value,) for value in invalid],
                    registry=registry,
                    resource=resource_id,
                    column=name,
                    counts={"values": len(invalid)},
                )


__all__: list[str] = []
