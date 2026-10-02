"""Turn records into Arrow tables with exactly the schema the registry declares.

- :func:`build_table` -- a sorted Arrow table for one resource.
- :func:`schema`, :func:`sort_key` -- a table's Arrow schema, and the columns it is sorted by.
- :func:`number`, :func:`number_batch` -- identifier values numbered as their declarations
  require, over records and over a streamed batch.
- :func:`localize` -- a naive wall-clock value with a declared IANA zone attached.
- :func:`canonical_json` -- a mapping or sequence as canonical JSON.
- :data:`ARROW`, :data:`COERCE` -- mappings from a registry column type to its Arrow type, and to
  the coercion applied before Arrow sees a value.

Every column's type and presence comes from the registry, so a packet cannot disagree with the
registry it embeds.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pyarrow as pa
from escapewheel_reader.ordering import stored_order

from .errors import CarriedNotAnInteger, FixedOffsetZone, NaiveTimestamp, OutOfRange


def localize(value: datetime | str, zone: ZoneInfo) -> datetime:
    """Attach a declared IANA zone to a naive wall-clock value.

    An adapter that knows its source's zone may call this; the writer itself never guesses
    (see :exc:`~escapewheel_writer.errors.NaiveTimestamp`). The zone must be an IANA zone, **not** a fixed offset,
    because a fixed offset is wrong for half the year and the error is silent.

    A session may fall in daylight time while the epoch its free-running clock counts from fell
    in standard time, so a rig constant of either offset misplaces whatever lies on the other
    side of the transition by an hour.

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
    FixedOffsetZone
        If `zone` is a fixed offset rather than an IANA zone.
    """
    if not isinstance(zone, ZoneInfo):
        raise FixedOffsetZone(f"{zone!r} is a fixed offset; pass an IANA zone so DST resolves per date")
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value if value.tzinfo is not None else value.replace(tzinfo=zone)


def _timestamp(value: Any, column: str) -> Any:
    """Coerce a wall-clock value, refusing anything without an offset."""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime) and value.tzinfo is None:
        raise NaiveTimestamp(f"{column}: {value!r} carries no UTC offset")
    return value


def _date(value: Any, column: str) -> Any:
    """Coerce a calendar date. Dates carry no offset, so nothing is refused here."""
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _plain(value: Any) -> Any:
    """Reduce a value to something :func:`json.dumps` can encode.

    NumPy scalars and arrays become their Python equivalents, and a non-finite float becomes
    null. JSON has no NaN, and source data is full of it -- an electrode table may carry NaN
    CCF coordinates -- so the choice is between dropping it and emitting a document no
    conforming JSON parser accepts.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if hasattr(value, "item") and getattr(value, "ndim", None) == 0:  # numpy scalar
        return _plain(value.item())
    if hasattr(value, "tolist"):  # numpy array
        return _plain(value.tolist())
    if isinstance(value, Sequence):
        return [_plain(v) for v in value]
    return value


def canonical_json(value: Any) -> Any:
    """Serialize a mapping or sequence to canonical JSON; pass a string or None through.

    Keys are sorted and separators fixed, so two writers given equal metadata emit equal bytes --
    and so a value encoded where it crosses a process boundary is the value this would have
    written anyway.
    """
    if value is None or isinstance(value, str):
        return value
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _json_string(value: Any, column: str) -> Any:
    """Serialize a mapping or sequence to canonical JSON; pass a string through.

    Adapters build metadata as dictionaries, and JSON encoding is a property of the physical
    profile rather than of any one source, so it happens here.
    """
    del column
    return canonical_json(value)


def _bounded(low: int, high: int, kind: str) -> Any:
    """Return a coercion that refuses a value the declared width cannot hold (Part 02 §5.3).

    NumPy wraps: `np.int32(2**31)` is `-2147483648`, and casting an `int64` array to `int32`
    truncates each element silently. A wrapped identifier is a *valid* `int32` -- it satisfies
    not-null, it satisfies uniqueness unless it happens to collide, and its foreign key resolves
    if the wrapped value happens to name a row -- so no rule in the registry can see it, and by
    the time the rules run the evidence is gone.
    """

    def check(value: Any, column: str) -> Any:
        if value is None or isinstance(value, bool):
            return value
        try:
            number = int(value)
        except (TypeError, ValueError):
            return value
        if not low <= number <= high:
            raise OutOfRange(
                f"{column}: {number} does not fit {kind}; Part 02 §5.3 refuses the write rather than "
                f"wrapping. Declare the wider type (Part 02 §5.3) or assign an identifier and record "
                f"the source's own value as its name (Part 02 §8.2)"
            )
        return value

    return check


#: Per-type coercion applied before Arrow sees a value. Everything else passes through.
COERCE = {
    "timestamp": _timestamp,
    "date": _date,
    "json_string": _json_string,
    "int32": _bounded(-(2**31), 2**31 - 1, "int32"),
    "int64": _bounded(-(2**63), 2**63 - 1, "int64"),
}

#: Registry column type -> the Arrow type a conforming writer emits (Part 03 §5.5).
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
    columns are always emitted, nullable ones as nulls. That is Part 02 §6's three presence
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


def sort_key(resource: str, spec: Mapping[str, Any]) -> list[str] | None:
    """Return the columns this table is physically ordered by, or None.

    Part 03 §5.3 sorts every table by its primary key except where the descriptor overrides it
    (Part 03 §5.4).

    Parameters
    ----------
    spec : Mapping
        The registry's entry for this table.

    Returns
    -------
    list of str or None
        Sort columns, or None if the table declares no key.
    """
    return stored_order(resource, spec) or None


def _is_string_carried_identifier(column: Mapping[str, Any]) -> bool:
    """Return whether the column is the catalog binding's string identifier (Part 02 §2.6)."""
    return (
        column["name"] == "resource_id"
        and column.get("role") == "identifier"
        and column.get("identity") == "carried"
        and column.get("type") == "string"
    )


#: For an identifier paired value, the map a row's value is numbered in, or None where its row
#: names no kind (Part 02 §8.3).
Paired = Mapping[str, Callable[[Mapping[str, Any]], str | None]]


def owned_names(spec: Mapping[str, Any]) -> dict[str, str]:
    """Return each assigned identifier a table owns with the declared `*_name` column `number` fills.

    Owned means in the primary key and exported through no reference (Part 02 §8.2).
    """
    exported = {c for ref in spec.get("references", []) for c in ref["columns"]}
    primary = set(spec.get("primary_key") or [])
    declared = {c["name"] for c in spec["columns"]}
    return {
        c["name"]: named
        for c in spec["columns"]
        if c.get("role") == "identifier"
        and c.get("identity") == "assigned"
        and c["name"] in primary
        and c["name"] not in exported
        and (named := f"{c['name'].removesuffix('_id')}_name") in declared
    }


def number(spec: Mapping[str, Any], rows: list[dict[str, Any]], keys: Any, paired: Paired | None = None) -> None:
    """Normalize identifier values as their declarations require, in place.

    Done here rather than in each adapter because the invariant is cross-adapter: the recipe
    exists because four sources can each produce `core.probes`, and two of them numbering the
    same probe differently is a defect no foreign key could see -- both values resolve, to
    different rows. One `Keys` shared by one `build` cannot get that wrong.

    An **assigned** identifier's incoming value is its *name*, which `Keys` maps to a number and
    remembers. A **carried** one is already the source's own number and is only coerced. Where
    the table owns an assigned identifier -- it is in the primary key and is not exported through
    a reference -- the matching `*_name` is filled in with the name that was mapped, which is
    what Part 02 §8.2 requires and what nothing else could supply by the time the row is written.
    An identifier paired value in `paired` is numbered in the map its row's kind names, since it
    holds the key of whichever resource that is.
    """
    names = owned_names(spec)
    # A foreign key is numbered in the map of the column it points at, not its own. Otherwise
    # `parent_clock_id` and `clock_id` -- both clocks -- get separate numbering and the parent
    # chain names a clock that does not exist, which `core.clocks.parent_chain_well_founded`
    # reports. Same for `default_electrode_id` into electrodes and `supersedes_run_id` into runs.
    target = {
        column: referenced
        for ref in spec.get("references", [])
        for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
    }
    identifiers = [c for c in spec["columns"] if c.get("role") == "identifier"]
    # Read before any column is numbered: a row reaches its kind through its own references, and
    # once those hold numbers the kind is lost and the value falls into a map of its own.
    kinds = {name: [reader(row) for row in rows] for name, reader in (paired or {}).items()}

    def kind_of(name: str, index: int) -> str:
        return (kinds[name][index] if name in kinds else None) or target.get(name, name)

    _number_names([c["name"] for c in identifiers if c.get("identity") == "assigned"], rows, kind_of, keys)

    for column in identifiers:
        name = column["name"]
        assigned = column.get("identity") == "assigned"
        named = names.get(name)
        for index, row in enumerate(rows):
            value = row.get(name)
            if value is None:
                continue
            if assigned:
                row[name] = keys.of(kind_of(name, index), str(value))
                if named is not None and row.get(named) is None:
                    row[named] = str(value)
            elif _is_string_carried_identifier(column):
                row[name] = str(value)
            else:
                try:
                    row[name] = int(value)
                except (TypeError, ValueError):
                    raise CarriedNotAnInteger(
                        f"{name} is a carried identifier, so it holds the source's own "
                        f"number -- but this row carries {value!r}. Either the source supplies an "
                        f"integer and the adapter is composing a string from it, or the column is "
                        f"assigned rather than carried and the registry says otherwise."
                    ) from None


def _number_names(
    columns: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
    kind_of: Callable[[str, int], str],
    keys: Any,
) -> None:
    """Assign every name the columns hold before any is written, in sorted order within each map.

    Otherwise the numbers depend on which column the loop reaches first: `parent_clock_id` and
    `clock_id` share a map, and whichever was seen first would decide the numbering.
    """
    pending: dict[str, set[str]] = {}
    for name in columns:
        for index, row in enumerate(rows):
            if row.get(name) is not None:
                pending.setdefault(kind_of(name, index), set()).add(str(row[name]))
    for kind in sorted(pending):
        for known in sorted(pending[kind]):
            keys.of(kind, known)


def _number_dictionary(values: pa.Array, column: Mapping[str, Any], kind: str, keys: Any) -> pa.Array:
    """Return a dictionary-encoded identifier numbered through its dictionary, indices unchanged."""
    dictionary = values.dictionary.to_pylist()
    if column.get("identity") == "assigned":
        numbered = [None if v is None else keys.of(kind, str(v)) for v in dictionary]
        value_type = pa.int32()
    elif _is_string_carried_identifier(column):
        numbered = [None if v is None else str(v) for v in dictionary]
        value_type = pa.string()
    else:
        numbered = [None if v is None else int(v) for v in dictionary]
        value_type = pa.int32()
    return pa.array(numbered, type=value_type).take(values.indices)


def number_batch(spec: Mapping[str, Any], batch: pa.RecordBatch, keys: Any) -> pa.RecordBatch:
    """Return a streamed batch with its identifier columns numbered, as `number` does for records.

    The streaming path exists so a table of 10^8 rows never becomes Python objects, so this maps
    through the batch's *distinct* values rather than per row. A dictionary-encoded column is
    mapped through its dictionary and re-indexed, which is what keeps `core.spike_events`
    affordable: its `unit_id` names one unit per row and holds a few hundred distinct names, so
    expanding it to compare row by row would cost a million Python strings a batch.

    A batch cannot supply a `*_name`: it has no room for a column the caller did not yield, and
    the table it streams is a fact table, which owns no identifier a name pairs with.
    """
    columns = dict(zip(batch.schema.names, batch.columns, strict=True))
    target = {
        column: referenced
        for ref in spec.get("references", [])
        for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
    }
    changed = False
    for column in spec["columns"]:
        name = column["name"]
        if column.get("role") != "identifier" or name not in columns:
            continue
        kind = target.get(name, name)
        values = columns[name]
        if pa.types.is_integer(values.type):
            continue
        if pa.types.is_dictionary(values.type):
            columns[name] = _number_dictionary(values, column, kind, keys)
            changed = True
            continue
        if column.get("identity") == "assigned":
            seen = [v for v in set(values.to_pylist()) if v is not None]
            mapping = {v: keys.of(kind, str(v)) for v in sorted(seen)}
            columns[name] = pa.array([None if v is None else mapping[v] for v in values.to_pylist()])
        elif _is_string_carried_identifier(column):
            columns[name] = pa.array([None if v is None else str(v) for v in values.to_pylist()], type=pa.string())
        else:
            columns[name] = pa.array([None if v is None else int(v) for v in values.to_pylist()])
        changed = True
    if not changed:
        return batch
    return pa.RecordBatch.from_arrays(list(columns.values()), names=list(columns))


def build_table(
    resource: str,
    spec: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    keys: Any = None,
    paired: Paired | None = None,
) -> pa.Table:
    """Build a sorted Arrow table for one resource.

    Parameters
    ----------
    spec : Mapping
        The registry's entry for this table.
    records : sequence of Mapping
        The rows, in any order.
    keys : Keys, optional
        Assigns the integers identifier columns hold. Absent, identifiers are left as
        given -- which only a caller building a table with no identifier in it can want.
    paired : Mapping, optional
        For each identifier paired value, the map its row's kind numbers it in (see `number`).

    Returns
    -------
    pyarrow.Table
        The table, in the registry's declared physical order.

    Raises
    ------
    NaiveTimestamp
        If a wall-clock value carries no UTC offset.
    """
    rows = [dict(r) for r in records]
    if keys is not None:
        # Before the sort, not after: Part 03 §5.3 orders by the primary key, and the key is the
        # number. Sorting the names would order `unit_10` between `unit_1` and `unit_2`.
        number(spec, rows, keys, paired)
    if order := sort_key(resource, spec):
        # None sorts first and consistently; a nullable sort column is legal.
        rows.sort(key=lambda r: tuple((r.get(k) is None, r.get(k)) for k in order))

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


__all__ = [
    "ARROW",
    "COERCE",
    "Paired",
    "build_table",
    "canonical_json",
    "localize",
    "number",
    "number_batch",
    "owned_names",
    "schema",
    "sort_key",
]
