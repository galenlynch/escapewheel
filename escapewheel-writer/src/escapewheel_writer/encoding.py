"""How a column is encoded in Parquet, and what an extension may say about its own.

The rules extend Part 03 §5.5's, and they reach any table the writer stages -- an extension's as much
as core's, because Part 09 §5.6 lets a writer require no code of an extension. What core does **not**
do is name an extension's tables: the exception tables below carry `core.*` and `analysis.*` alone,
and an extension supplying its own passes them to :class:`~escapewheel_writer.writer.PacketWriter`.

That division follows from where the decision has weight. An extension hands the writer Arrow with
its identifiers as **names**, and Part 05 §8 has the writer mint the integers packet-wide, so the
columns where an encoding is worth 37x to 79x do not exist in their final form until the writer
makes them. What an extension owns is its own measurements, which the rules cover without naming
anything.

`inefficient` closes the loop for what neither reaches: a rule is a good guess, and a column it
guesses wrong about is reported rather than silently paid for.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NamedTuple

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .arrow import sort_key

#: Columns the rules leave off delta that delta serves, each with the measurement that justifies it.
#: `test_writer.py` refuses an entry naming no such column, which is `check.py`'s discipline for a
#: naming exception.
DELTA_COLUMNS: dict[str, tuple[str, ...]] = {
    # A reference climbing through a dozen runs hundreds of rows long, which the run rule gives
    # plain: delta 1.19x to 1.27x over plain.
    "core.electrodes": ("probe_id",),
}

#: Columns the rules give a dictionary or delta that plain serves better, each measured.
NO_DICTIONARY: dict[str, tuple[str, ...]] = {
    # Two values alternating electrode by electrode: plain 1.49x to 2.03x over a dictionary. A
    # structure id in runs of about ten: plain 1.38x to 1.43x.
    "core.electrode_coordinates": ("coordinate_frame", "coordinate_basis", "region_id"),
    # A trailing key component, climbing within each unit and resetting: plain 1.59x to 1.85x over
    # delta.
    "core.unit_electrodes": ("electrode_id",),
    # Eight shifts cycling channel by channel: plain 1.34x to 1.35x over a dictionary.
    "core.array_channels": ("inter_sample_shift",),
    # Ticks in tables of 11 to 24 rows: plain 1.15x to 1.30x over delta.
    "core.clock_phase_steps": ("parent_tick", "t_tick"),
    "core.clock_observation_intervals": ("stop_tick",),
    # Summaries in unit order rather than time order: plain 1.10x to 1.28x over delta.
    "core.units": ("first_spike_tick", "last_spike_tick"),
}

#: Columns keeping the dictionary the rules would take away, each measured.
DICTIONARY_COLUMNS: dict[str, tuple[str, ...]] = {
    # Twenty-six channel positions cycling through every unit's support, declared a structural
    # index: a dictionary 1.39x to 1.41x over delta.
    "core.unit_electrodes": ("channel_index",),
}

#: Rows at which a column of one value repays its dictionary page: a constant is 1.12x smaller
#: under a dictionary than plain at a million rows, and 1.27x larger at seven thousand.
ONE_VALUE_ROWS = 50_000

#: Rows a value covers on average -- per run for an ordered integer, per distinct value otherwise
#: -- from which repetition decides. Over both packaged sessions the exceptions stay at 15 from 32
#: to 50 rows a value and from 50 to 200 a run.
REPEATS = 50


class Counts(NamedTuple):
    """What a writer can count of a column it holds, which is all the ladder reads of the values."""

    rows: int
    distinct: int
    runs: int
    ascending: bool


def count(values: pa.Array[Any] | pa.ChunkedArray[Any]) -> Counts:
    """Count rows, distinct non-null values, runs of equal neighbours, and whether values never fall.

    One pass over values already in memory: the whole table on the records path, the first batch
    when streaming, which is the row group the choice then applies to first.
    """
    if isinstance(values, pa.ChunkedArray):
        values = values.combine_chunks()
    if pa.types.is_dictionary(values.type):
        values = values.cast(values.type.value_type)
    valid = values.drop_null()
    if len(valid) < 2:
        return Counts(len(values), len(valid), len(valid), True)
    head, tail = valid.slice(0, len(valid) - 1), valid.slice(1)
    changes = pc.sum(pc.not_equal(tail, head).cast(pa.int64())).as_py() or 0
    ascending = pa.types.is_integer(values.type) and bool(pc.all(pc.greater_equal(tail, head)).as_py())
    return Counts(len(values), pc.count_distinct(valid).as_py(), changes + 1, ascending)


def leading_identifier(spec: Mapping[str, Any], keys: list[str]) -> str | None:
    """Return the key column whose values ascend across the whole table, if one does.

    A table is sorted by its key (Part 03 §5.3), so the first key column ascends and every later one
    only ascends *within* the group above it. `session_id` is skipped because a packet holds one
    session (R1), which makes it constant rather than ascending.
    """
    roles = {c["name"]: c.get("role") for c in spec.get("columns", ())}
    for name in keys:
        if name == "session_id":
            continue
        return name if roles.get(name) == "identifier" else None
    return None


def _encodable(kind: pa.DataType) -> bool:
    """Whether the rules choose an encoding for this type at all; anything else keeps pyarrow's."""
    return (pa.types.is_integer(kind) or pa.types.is_floating(kind) or pa.types.is_string(kind)
            or pa.types.is_large_string(kind) or pa.types.is_timestamp(kind) or pa.types.is_date(kind))


def declared_order(name: str, column: Mapping[str, Any], leading: str | None) -> bool:
    """Whether a column's declarations mark an integer likely to climb, if only within the groups above it."""
    role = column.get("role")
    return (name.endswith("_tick") or name == leading or role in ("structural_index", "sequence_position")
            or (role == "identifier" and column.get("identity") == "assigned"))


def choose(field: pa.Field[Any], column: Mapping[str, Any], leading: str | None,
           counts: Counts | None) -> str | None:
    """Return the encoding one column takes: `"delta"`, `"plain"`, or None for a dictionary.

    Four rules over what the writer holds when it chooses, the first that applies deciding. Measured
    over both packaged sessions' columns they leave 15 of 381 more than 1.15x off their best
    encoding, and each of those is an exception above or in a recipe.

    **No value is plain**: a dictionary page costs 27 bytes before it indexes anything.

    **One value takes a dictionary from `ONE_VALUE_ROWS` rows, and below that delta for an integer
    and plain for anything else.** The page repays itself only over a long row group. Delta on one
    integer is never more than 6 bytes larger than plain, and plain can be 5.9x larger than delta.

    **An ordered integer takes delta, or plain where its runs average `REPEATS` rows.** Order is
    declared -- a `*_tick`, the leading identifier, a `structural_index`, a `sequence_position`, an
    `assigned` identifier -- or observed, the values never falling. A declaration states no
    distribution, but it marks a column likely to climb within groups, which no count over the whole
    column sees: `core.spike_events.t_tick` climbs within each unit and nowhere else, and plain costs
    it 1.24x.

    **Anything else takes a dictionary where each value covers `REPEATS` rows, and plain otherwise.**
    That is what a dictionary indexes: `core.spike_events.amplitude` repeats and is 1.75x smaller
    under one, `core.unit_quality_labels.confidence` does not and is 1.47x larger.

    With no counts, as for a spill opened before its first batch, only the declaration is known: an
    ordered integer takes delta and anything else a dictionary.
    """
    kind = field.type.value_type if pa.types.is_dictionary(field.type) else field.type
    if not _encodable(kind):
        return None
    integer = pa.types.is_integer(kind)
    ordered = integer and declared_order(field.name, column, leading)
    if counts is None:
        return "delta" if ordered else None
    if counts.distinct == 0:
        return "plain"
    if counts.distinct == 1:
        if counts.rows >= ONE_VALUE_ROWS:
            return None
        return "delta" if integer else "plain"
    if ordered or (integer and counts.ascending):
        return "plain" if counts.rows >= REPEATS * counts.runs else "delta"
    return None if counts.rows >= REPEATS * counts.distinct else "plain"


def encodings(resource_id: str, spec: Mapping[str, Any], out: pa.Schema,
              extra: Mapping[str, Mapping[str, tuple[str, ...]]] | None = None,
              sample: pa.Table | pa.RecordBatch | None = None) -> tuple[list[str], list[str]]:
    """Which columns take `DELTA_BINARY_PACKED` and which take no dictionary. Returns `(delta, plain)`.

    A declared exception decides first, then `choose` over the counts of `sample`, which is the
    table being written or its first batch. pyarrow never picks delta itself and defaults to a
    dictionary on everything, which is wrong in both directions here.
    """
    # An extension's own exceptions, merged over core's rather than into them: core names no
    # extension table, and an extension names no core one, so neither can quietly override the
    # other. `extra` is keyed the same way -- list name to resource to columns.
    listed = extra or {}
    forced_delta = set(DELTA_COLUMNS.get(resource_id, ())) | set(listed.get("delta", {}).get(resource_id, ()))
    forced_plain = set(NO_DICTIONARY.get(resource_id, ())) | set(listed.get("plain", {}).get(resource_id, ()))
    forced_dict = set(DICTIONARY_COLUMNS.get(resource_id, ())) | set(listed.get("dictionary", {}).get(resource_id, ()))
    leading = leading_identifier(spec, sort_key(resource_id, spec) or list(spec.get("primary_key") or []))
    declared = {c["name"]: c for c in spec.get("columns", ())}
    present = set(sample.schema.names) if sample is not None else set()
    delta, plain = [], []
    for field in out:
        name = field.name
        # A string held as dictionary codes is a string column in Parquet all the same, so every
        # choice is made on the value type.
        kind = field.type.value_type if pa.types.is_dictionary(field.type) else field.type
        if name in forced_dict or not _encodable(kind):
            continue
        if name in forced_delta and pa.types.is_integer(kind):
            delta.append(name)
        elif name in forced_plain:
            plain.append(name)
        else:
            counts = count(sample.column(name)) if sample is not None and name in present else None
            choice = choose(field, declared.get(name, {}), leading, counts)
            if choice == "delta":
                delta.append(name)
            elif choice == "plain":
                plain.append(name)
    return delta, plain


#: Part 03 §5.5's threshold: a column costing more than this times the smallest encoding the writer
#: could have chosen for it is reported.
TOLERANCE = 1.5

#: Rows sampled when reporting. Enough that a page boundary and a run of repeats both appear.
SAMPLE = 65_536


def _cost(sample: pa.Table, name: str, how: str) -> int | None:
    """Compressed bytes of one column's chunks under one encoding, as a packet compresses them.

    The chunks and not the file: a one-column file's footer runs to a few hundred bytes, as much as
    a small table's whole column, so comparing files hides every column of a few thousand rows.
    """
    options: dict[str, Any] = {"compression": "zstd"}
    if how == "delta":
        options |= {"use_dictionary": False, "column_encoding": {name: "DELTA_BINARY_PACKED"}}
    elif how == "plain":
        options |= {"use_dictionary": False}
    else:
        options |= {"use_dictionary": [name]}
    buffer = pa.BufferOutputStream()
    try:
        pq.write_table(sample.select([name]), buffer, **options)
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError, OSError):
        return None
    metadata = pq.ParquetFile(pa.BufferReader(buffer.getvalue())).metadata
    return sum(metadata.row_group(g).column(0).total_compressed_size for g in range(metadata.num_row_groups))


def inefficient(resource_id: str, sample: pa.Table, delta: list[str], plain: list[str]) -> list[str]:
    """Report each column the rules encoded more than `TOLERANCE` worse than they could.

    A report rather than a choice. Keeping the smallest of three written encodings costs about 0.4 s
    a packet, and cost is not what refuses it: a choice made that way records nothing about why a
    column got its encoding, where a rule over counts and a declared exception say both. So the
    rules decide and this says what the decision cost, which is how an author learns that their
    table wants an exception.

    Every figure is the encoding and its Zstandard together, Part 03 §5.1 putting one over the other.
    """
    said = []
    head = sample.slice(0, SAMPLE)
    for field in head.schema:
        held = field.type.value_type if pa.types.is_dictionary(field.type) else field.type
        integer, floating = pa.types.is_integer(held), pa.types.is_floating(held)
        # A string or a wall-clock value is judged between the two encodings the rules choose from.
        # The delta string encodings are smaller on a sorted name and refused by hyparquet and
        # fastparquet, so measuring against them would report a choice made on purpose.
        other = (pa.types.is_string(held) or pa.types.is_large_string(held)
                 or pa.types.is_timestamp(held) or pa.types.is_date(held))
        if not (integer or floating or other):
            continue
        chosen = "delta" if field.name in delta else "plain" if field.name in plain else "dict"
        got = {how: n for how in (("dict", "delta", "plain") if integer else ("dict", "plain"))
               if (n := _cost(head, field.name, how)) is not None}
        if not got or chosen not in got:
            continue
        best = min(got, key=got.__getitem__)
        if got[chosen] > got[best] * TOLERANCE:
            said.append(
                f"{resource_id}.{field.name} is {chosen} where {best} is "
                f"{got[chosen] / got[best]:.1f}x smaller on {head.num_rows:,} sampled rows"
            )
    return said
