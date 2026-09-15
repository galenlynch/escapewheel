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

from collections.abc import Mapping, Sequence
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .arrow import sort_key

#: Columns the rules leave off delta that delta serves, each with the measurement that justifies it.
#: `test_writer.py` refuses an entry naming no such column, or naming what the rules already choose,
#: which is `check.py`'s discipline for a naming exception.
DELTA_COLUMNS: dict[str, tuple[str, ...]] = {
    # A per-unit spike count in unit order, which climbs more often than it repeats: delta 1.09x
    # over plain and 1.7x over a dictionary.
    "core.units": ("n_spikes",),
    # A frame timeline advancing by a constant step (Part 01 §3.18), declared `data`: delta is 144x
    # smaller than plain.
    "core.media_frames": ("pts",),
    # A carried identifier that still ascends, the table being keyed on where an interval starts:
    # delta 11.7x to 16.9x over plain.
    "core.intervals": ("interval_id",),
    # One rational step or rate repeated down a table of a few dozen rows: delta 1.32x to 1.42x
    # over plain.
    "core.array_dimensions": ("step_tick_num", "step_tick_den"),
    "core.clocks": ("tick_rate_den",),
}

#: Columns the rules give a dictionary or delta that plain serves better, each measured.
NO_DICTIONARY: dict[str, tuple[str, ...]] = {
    # Two ticks summarising each unit, in unit order rather than time order: plain 1.10x to 1.28x
    # over delta. Four references copied from the unit's run, one value a run: plain 1.15x to 1.18x
    # over delta. Two strings holding one value in every row: plain 1.20x to 1.25x.
    "core.units": ("first_spike_tick", "last_spike_tick", "probe_id", "sorting_run_id", "curation_id",
                   "clock_id", "amplitude_unit", "quality_label_source"),
    # A trailing key component, so it climbs within each unit and resets: plain 1.59x to 1.85x over
    # delta.
    "core.unit_electrodes": ("electrode_id",),
    # Bucketed by time rather than clustered by unit (Part 03 §5.4), so a unit's runs are short:
    # plain 1.11x to 1.16x over delta.
    "analysis.spike_events": ("unit_id",),
    # Two values alternating electrode by electrode: plain 1.49x to 2.03x over a dictionary.
    "core.electrode_coordinates": ("coordinate_frame", "coordinate_basis"),
    # One frame and one basis in every row: plain 1.19x to 1.24x.
    "core.unit_coordinates": ("coordinate_frame", "coordinate_basis"),
    "core.unit_coordinate_values": ("coordinate_frame",),
    # A thousand rows declaring no unit: plain 1.62x.
    "core.array_channels": ("unit",),
    # Strings in tables of 2 to 30 rows describing a session's instruments, assets and runs, holding
    # one value, a handful or none, which a dictionary page outweighs: plain 1.17x to 1.67x.
    "core.array_assets": ("band", "format", "semantic_type", "unit"),
    "core.array_dimensions": ("coordinate_resource", "coordinate_unit"),
    "core.calibrations": ("calibration_type", "detail_kind", "input_unit", "metadata", "output_unit"),
    "core.coordinate_frame_axes": ("axis_direction", "axis_name", "unit"),
    "core.coordinate_frames": ("atlas", "atlas_version", "coordinate_frame"),
    "core.devices": ("device_kind", "manufacturer", "parent_port"),
    "core.event_streams": ("detail_kind", "event_type"),
    "core.media_assets": ("format", "semantic_type"),
    "core.probes": ("manufacturer", "probe_type", "target_region"),
    "core.processing_runs": ("activity_type", "scope_kind", "status"),
    # Ticks in tables of 11 to 24 rows: plain 1.15x to 1.30x over delta.
    "core.clock_observation_intervals": ("stop_tick",),
    "core.clock_phase_steps": ("parent_tick", "t_tick"),
    # References holding a dozen values or fewer in runs hundreds long: plain 1.18x to 1.19x over
    # delta.
    "core.events": ("stream_id",),
    "core.sorting_run_channels": ("sorting_run_id",),
}

#: Columns keeping the dictionary the rules would take away, each measured.
DICTIONARY_COLUMNS: dict[str, tuple[str, ...]] = {
    # Quantised to the sorter's amplitude step, so hundreds of millions of rows hold few distinct
    # values: a dictionary 1.75x over plain on ~200 MB, the largest single encoding decision in a
    # packet. A unit's spikes run for thousands of rows: a dictionary 1.18x over delta.
    "core.spike_events": ("amplitude", "unit_id"),
    # Twenty-six channel positions repeating through every unit's support: a dictionary 1.39x to
    # 1.41x over delta.
    "core.unit_electrodes": ("channel_index",),
}


def leading_identifier(spec: Mapping[str, Any], keys: list[str]) -> str | None:
    """Return the key column whose values ascend across the whole table, if one does.

    A table is sorted by its key (Part 03 §5.3), so the first key column ascends and every later one
    only ascends *within* the group above it. `session_id` is skipped because a packet holds one
    session (R1), which makes it constant rather than ascending -- RLE already stores it in
    0.03 bits/row.
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


def by_rule(field: pa.Field[Any], column: Mapping[str, Any], primary_key: Sequence[str],
            leading: str | None) -> str | None:
    """Return the encoding the rules choose for one column: `"delta"`, `"plain"`, or None for a dictionary.

    Each rule reads a declaration and none reads the values, so each is a guess the exceptions above
    correct. The first that applies decides, and every figure is a column's chunks with their
    Zstandard, measured over both packaged sessions.

    **A `*_tick` column, and the leading identifier of the key, take delta.** A tick climbs on a
    monotonic clock and the first key column across the table (Part 03 §5.3): delta takes
    `core.clock_anchors.t_tick` from 268.8 KB to 5.2 KB and `core.units.unit_id` down 57x.

    **A float takes no dictionary**: 27 of 32 float columns above 2 kB are smaller plain.

    **A `free` string takes no dictionary**, its values being drawn from no vocabulary: plain is
    1.16x to 2.99x smaller on the electrode and unit names and labels. `DELTA_BYTE_ARRAY` is smaller
    again, and hyparquet and fastparquet refuse it while reading every other encoding a packet uses.

    **`session_id`, and every column of a table keyed by `session_id` or `subject_id` alone, take no
    dictionary.** A single-session packet holds one such value and one such row, which a dictionary
    page outweighs: plain 1.23x to 1.39x on `session_id` in the small tables, and within 1.12x of the
    dictionary in the spike tables, where both cost 0.03 bits a row.

    **A timestamp or a date takes no dictionary**, a moment rarely recurring in a table: plain 1.19x
    to 1.67x.

    **An integer declared `structural_index` or `sequence_position`, or an `assigned` identifier,
    takes delta**, each climbing more than it repeats: `core.clock_anchors.anchor_index` 188x over a
    dictionary, `core.media_frames.frame_index` 192x over plain, and a reference such as
    `core.curation_versions.sorting_run_id` 1.88x to 1.99x over a dictionary.

    **A `carried` identifier and an integer declared `data` take no dictionary**, a source's label
    and a count repeating too rarely to pay for one: a dictionary is 1.67x to 1.77x plain on
    `core.units.n_spikes`.

    Everything else keeps pyarrow's dictionary, which is what an `open` or `closed` vocabulary is
    declared to draw from: `core.electrode_coordinate_values.coordinate_frame` is 29x to 79x smaller
    under one than plain. Choosing by measuring the values would do better and is refused, since it
    records no reason and differs between a `--sample` build and a full one.
    """
    kind = field.type.value_type if pa.types.is_dictionary(field.type) else field.type
    name, role = field.name, column.get("role")
    integer = pa.types.is_integer(kind)
    if integer and (name.endswith("_tick") or name == leading):
        return "delta"
    if pa.types.is_floating(kind):
        return "plain"
    if (pa.types.is_string(kind) or pa.types.is_large_string(kind)) and column.get("vocabulary") == "free":
        return "plain"
    if name == "session_id" or list(primary_key) in (["session_id"], ["subject_id"]):
        return "plain"
    if pa.types.is_timestamp(kind) or pa.types.is_date(kind):
        return "plain"
    if not integer:
        return None
    assigned = role == "identifier" and column.get("identity") == "assigned"
    if role in ("structural_index", "sequence_position") or assigned:
        return "delta"
    if role in ("identifier", "data"):
        return "plain"
    return None


def encodings(resource_id: str, spec: Mapping[str, Any], out: pa.Schema,
              extra: Mapping[str, Mapping[str, tuple[str, ...]]] | None = None,
              ) -> tuple[list[str], list[str]]:
    """Which columns take `DELTA_BINARY_PACKED` and which take no dictionary. Returns `(delta, plain)`.

    A declared exception decides first, then `by_rule`. pyarrow never picks delta itself and defaults
    to a dictionary on everything, which is wrong in both directions here.
    """
    # An extension's own exceptions, merged over core's rather than into them: core names no
    # extension table, and an extension names no core one, so neither can quietly override the
    # other. `extra` is keyed the same way -- list name to resource to columns.
    listed = extra or {}
    forced_delta = set(DELTA_COLUMNS.get(resource_id, ())) | set(listed.get("delta", {}).get(resource_id, ()))
    forced_plain = set(NO_DICTIONARY.get(resource_id, ())) | set(listed.get("plain", {}).get(resource_id, ()))
    forced_dict = set(DICTIONARY_COLUMNS.get(resource_id, ())) | set(listed.get("dictionary", {}).get(resource_id, ()))
    keys = sort_key(resource_id, spec) or list(spec.get("primary_key") or [])
    leading = leading_identifier(spec, keys)
    declared = {c["name"]: c for c in spec.get("columns", ())}
    primary_key = list(spec.get("primary_key") or [])
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
        elif (choice := by_rule(field, declared.get(name, {}), primary_key, leading)) == "delta":
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

    A report rather than a choice. Measuring each column and keeping the smallest was tried and
    costs about 0.4 s a packet, so cost is not what refuses it: a measured choice records nothing
    about why a column got its encoding, and it would differ between a `--sample` build and a full
    one, where a rule with a declared exception says both. So the rule decides and this says what
    the decision cost, which is how an author learns that their table wants an exception.

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
