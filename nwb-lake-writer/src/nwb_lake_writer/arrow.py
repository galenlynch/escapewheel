"""Turn records into Arrow tables with exactly the schema the registry declares.

A writer does not invent a schema. Every column's type and presence comes from
``logical_schemas.json``, so a packet cannot disagree with the registry it embeds.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pyarrow as pa


class NaiveTimestamp(ValueError):
    """A wall-clock value carried no UTC offset.

    `03` requires wall-clock columns to be ``TIMESTAMP(MICROS, UTC)``, so a value without an
    offset is not merely inconvenient -- it is unlocatable, and assuming UTC would be a guess.
    Real source metadata gets this wrong: an aind-data-schema `session.json` in
    `inventory/nwb-zarr-776259-2025-04-09.md` §6.4 stamps `+00:00` on a Pacific wall clock, a
    seven-hour error. Refusing naive values does not catch a wrong offset, but it does stop a
    writer inventing one.
    """


def localize(value: datetime | str, zone: ZoneInfo) -> datetime:
    """Attach a declared IANA zone to a naive wall-clock value.

    An adapter that knows its source's zone may call this; the writer itself never guesses
    (see :class:`NaiveTimestamp`). The zone must be an IANA zone, **not** a fixed offset,
    because a fixed offset is wrong for half the year and the error is silent.

    The dataset in `inventory/nwb-zarr-776259-2025-04-09.md` shows why: its session is PDT
    (−07:00) and the HARP epoch its ticks count from is PST (−08:00), so a rig constant of
    −07:00 misplaces anything before the March transition by an hour.

    Parameters
    ----------
    value : datetime or str
        A naive wall-clock value. One that already carries an offset is returned unchanged.
    zone : zoneinfo.ZoneInfo
        The zone the value was recorded in, e.g. ``ZoneInfo("America/Los_Angeles")``.

    Returns
    -------
    datetime
        Offset-aware, with the zone's offset for that date.

    Raises
    ------
    TypeError
        If `zone` is a fixed offset rather than an IANA zone.
    """
    if not isinstance(zone, ZoneInfo):
        raise TypeError(f"{zone!r} is a fixed offset; pass an IANA zone so DST resolves per date")
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value if value.tzinfo is not None else value.replace(tzinfo=zone)


def _timestamp(value: Any, column: str) -> Any:
    """Coerce a wall-clock value, refusing anything without an offset."""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime) and value.tzinfo is None:
        raise NaiveTimestamp(f"{column}: {value!r} carries no UTC offset")
    return value


def _date(value: Any, column: str) -> Any:
    """Coerce a calendar date. Dates carry no offset, so nothing is refused here."""
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


#: Per-type coercion applied before Arrow sees a value. Everything else passes through.
COERCE = {"timestamp": _timestamp, "date": _date}

#: Registry column type -> the Arrow type a conforming writer emits (R3 §2.1).
#: Every one is a primitive: no struct, map, or list appears anywhere in the registry.
ARROW: dict[str, pa.DataType] = {
    "string": pa.string(),
    "int32": pa.int32(),
    "int64": pa.int64(),
    "float32": pa.float32(),
    "float64": pa.float64(),
    "bool": pa.bool_(),
    "date": pa.date32(),
    "timestamp": pa.timestamp("us", tz="UTC"),
    "json_string": pa.string(),
}


def schema(spec: Mapping[str, Any], present: set[str]) -> pa.Schema:
    """Build the Arrow schema for one table.

    Optional columns are omitted when no record carries them; required and nullable
    columns are always emitted, nullable ones as nulls. That is R2 §5's three presence
    states expressed physically.

    Parameters
    ----------
    spec : Mapping
        The registry's entry for this table.
    present : set of str
        Column names at least one record carries.

    Returns
    -------
    pyarrow.Schema
        The schema, in the registry's column order.
    """
    return pa.schema(
        [
            pa.field(c["name"], ARROW[c["type"]])
            for c in spec["columns"]
            if c["presence"] != "optional" or c["name"] in present
        ]
    )


def sort_key(spec: Mapping[str, Any]) -> list[str] | None:
    """Return the columns this table is physically ordered by, or None.

    R10 §2 sorts every table by its primary key unless the registry overrides it, which
    `03` does for `core.spike_events` and `core.events`.

    Parameters
    ----------
    spec : Mapping
        The registry's entry for this table.

    Returns
    -------
    list of str or None
        Sort columns, or None if the table declares no key.
    """
    keys = spec.get("sort")
    return list(keys) if keys else (list(spec["primary_key"]) if spec.get("primary_key") else None)


def build(spec: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> pa.Table:
    """Build a sorted Arrow table for one resource.

    Parameters
    ----------
    spec : Mapping
        The registry's entry for this table.
    records : sequence of Mapping
        The rows, in any order.

    Returns
    -------
    pyarrow.Table
        The table, in the registry's declared physical order.

    Raises
    ------
    NaiveTimestamp
        If a wall-clock value carries no UTC offset.
    """
    rows = list(records)
    if keys := sort_key(spec):
        # None sorts first and consistently; a nullable sort column is legal.
        rows.sort(key=lambda r: tuple((r.get(k) is None, r.get(k)) for k in keys))

    present = {name for row in rows for name in row}
    out = schema(spec, present)
    types = {c["name"]: c["type"] for c in spec["columns"]}
    arrays = []
    for field in out:
        coerce = COERCE.get(types[field.name])
        values = [r.get(field.name) for r in rows]
        if coerce is not None:
            values = [coerce(v, field.name) for v in values]
        arrays.append(pa.array(values, type=field.type))
    return pa.table(arrays, schema=out)
