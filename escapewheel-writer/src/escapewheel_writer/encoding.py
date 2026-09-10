"""How a column is encoded in Parquet, and what an extension may say about its own.

The rules are `03` §5.5's, and they reach any table the writer stages -- an extension's as much as
core's, because R17 §3 gives an extension no second code path. What core does **not** do is name an
extension's tables: the exception tables below carry `core.*` and `analysis.*` alone, and an
extension supplying its own passes them to :class:`~escapewheel_writer.writer.PacketWriter`.

That division follows from where the decision has weight. An extension hands the writer Arrow with
its identifiers as **names**, and R53 §2.5 has the writer mint the integers packet-wide, so the
columns where an encoding is worth 37x to 79x do not exist in their final form until the writer
makes them. What an extension owns is its own measurements, which the float rule covers without
naming anything.

`inefficient` closes the loop for what neither reaches: a rule is a good guess, and a column it
guesses wrong about is reported rather than silently paid for.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .arrow import sort_key

#: Columns the rules below miss, each with the measurement that justifies it. `test_writer.py`
#: refuses an entry naming no such column, which is `check.py`'s discipline for a naming exception.
DELTA_COLUMNS: dict[str, tuple[str, ...]] = {
    "core.clock_anchors": ("anchor_index",),
    "core.units": ("n_spikes",),
    # Contiguous 0..n-1 within one asset, and 2.5 M distinct values per camera: the worst case
    # for a dictionary, whose entries then outnumber nothing and cost 1.54 B/row where delta
    # costs 0.01. `pts` is the same shape once R68 §2.1 makes it an integer -- a frame timeline
    # advancing by a constant step -- and takes the column from 1.50 B/row to 0.006.
    "core.media_frames": ("frame_index", "pts"),
    # Ascending without being a key column: a run lists its channels in the order it kept them
    # (R83 §2.1) and a channel map lists its contacts, so both climb through the contact numbers
    # with gaps. Measured 11.1x and 7.4x over the dictionary they would otherwise get.
    "core.sorting_run_channels": ("electrode_id", "channel_index"),
    "core.array_channels": ("electrode_id",),
    # An interval's identifier is not in its key -- R47 §2 keys on where it starts and R54 §2.1
    # on its kind -- so the leading-identifier rule cannot see it, and it still ascends. 5.6x.
    "core.intervals": ("interval_id",),
}

#: Columns written PLAIN: no dictionary, no delta. Integers only -- a float takes this by rule.
NO_DICTIONARY: dict[str, tuple[str, ...]] = {
    # Summaries, not coordinates on a timeline: one row per unit in `unit_id` order, so the ticks
    # arrive unordered and delta encodes noise while a dictionary of 6,781 distinct ticks pays for
    # itself twice. Plain is 1.44x both, which is the `_tick` rule being a good guess and no more.
    "core.units": ("first_spike_tick", "last_spike_tick"),
    # A trailing key component (R28 §2), so it climbs within each unit and resets: a sawtooth,
    # which neither delta nor a dictionary reads well. 1.7x.
    "core.unit_electrodes": ("electrode_id",),
    # 56 distinct structure ids over 8,832 rows, already run-length friendly; the dictionary is
    # a second index over what RLE alone encodes. 1.3x.
    "core.electrode_coordinates": ("region_id",),
    # One unit per spike and a few hundred distinct per batch, but the derived table is bucketed
    # by time (R30 §3.2) rather than clustered by unit, so the runs are short. 1.2x.
    "analysis.spike_events": ("unit_id",),
}

#: Columns keeping the dictionary the rules would take away, each measured. The float rule below
#: is the one this mostly answers: a float is plain unless its values repeat.
DICTIONARY_COLUMNS: dict[str, tuple[str, ...]] = {
    # Quantised to the sorter's amplitude step, so 287 M rows hold few distinct values and the
    # dictionary is exactly right. **1.85x on ~200 MB**, the largest single encoding decision in
    # a packet, and the one a blanket float rule would have got wrong.
    "core.spike_events": ("amplitude", "unit_id"),
}


def leading_identifier(spec: Mapping[str, Any], keys: list[str]) -> str | None:
    """Return the key column whose values ascend across the whole table, if one does.

    A table is sorted by its key (R10 §2), so the first key column ascends and every later one
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


def encodings(resource_id: str, spec: Mapping[str, Any], out: pa.Schema,
              extra: Mapping[str, Mapping[str, tuple[str, ...]]] | None = None,
              ) -> tuple[list[str], list[str]]:
    """Which columns take `DELTA_BINARY_PACKED` and which take no dictionary. Returns `(delta, plain)`.

    Three rules and three lists of exceptions, in the shape `check.py` uses for naming: an
    exception is declared with the measurement that justifies it, and a test refuses one naming a
    column that does not exist. pyarrow never picks delta itself and defaults to a dictionary on
    everything, which is wrong in both directions here.

    **A `*_tick` column takes delta.** A tick is a large integer on a monotonic clock, so its
    residuals bit-pack far smaller than the eight bytes PLAIN spends. Measured, delta takes
    `core.clock_anchors.t_tick` from 268.8 KB to 5.2 KB and `core.spike_events.t_tick` from
    660.9 MB to 462.1 MB.

    **The leading identifier of the key takes delta.** R10 §2 sorts a table by its key, so that
    column ascends across the whole table where every later key column only ascends within the
    group above it. Measured: `core.units.unit_id` **57x**, `core.unit_coordinates.unit_id` 53x,
    `core.electrode_coordinates.electrode_id` 48x, `core.unit_coordinate_values.unit_id` **75x**.

    **A float takes no dictionary.** Of 32 float columns above 2 kB across both packaged sessions,
    **27 are smaller plain**, by 1.15x to 1.76x: a dictionary over values that barely repeat is an
    index nobody reads. The five that do repeat are listed, and one of them decides ~200 MB --
    `core.spike_events.amplitude` is quantised to the sorter's step and is **1.85x** better with
    the dictionary, which a blanket rule would have thrown away.

    None of the three is monotonicity or cardinality itself, which is what the encodings actually
    exploit and what nothing declares. Deriving the choice from the sort key alone was measured and
    refused: it regresses `core.media_frames.pts` **195x** and `core.clock_anchors.t_tick` 57x,
    both monotone without being key columns. Every column is zstd-compressed on top of its
    encoding, so each number here is the pair measured end to end.
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
    delta, plain = [], []
    for field in out:
        name = field.name
        integer, floating = pa.types.is_integer(field.type), pa.types.is_floating(field.type)
        if name in forced_dict or not (integer or floating):
            continue
        if name in forced_delta and integer:
            delta.append(name)
        elif name in forced_plain:
            plain.append(name)
        elif integer and (name.endswith("_tick") or name == leading):
            delta.append(name)
        elif floating:
            plain.append(name)
    return delta, plain


#: How much worse than the best available encoding a column may be before `inefficient` says so.
#: Chosen so both packaged sessions report nothing: after the rules and their exceptions the worst
#: column is `aind_unit_qc.metrics.isi_violations_count` at 1.15x.
TOLERANCE = 1.5

#: Rows sampled when reporting. Enough that a page boundary and a run of repeats both appear.
SAMPLE = 65_536


def _cost(sample: pa.Table, name: str, how: str) -> int | None:
    """Bytes one column costs under one encoding, compressed as a packet compresses it."""
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
    return buffer.getvalue().size


def inefficient(resource_id: str, sample: pa.Table, delta: list[str], plain: list[str]) -> list[str]:
    """Report each column the rules encoded more than `TOLERANCE` worse than they could.

    A report rather than a choice. Measuring each column and keeping the smallest was tried and
    costs about 0.4 s a packet, so cost is not what refuses it: a measured choice records nothing
    about why a column got its encoding, and it would differ between a `--sample` build and a full
    one, where a rule with a declared exception says both. So the rule decides and this says what
    the decision cost, which is how an author learns that their table wants an exception.

    Every figure is the encoding and its Zstandard together, `03` §5.1 putting one over the other.
    """
    said = []
    head = sample.slice(0, SAMPLE)
    for field in head.schema:
        integer, floating = pa.types.is_integer(field.type), pa.types.is_floating(field.type)
        if not (integer or floating):
            continue
        chosen = "delta" if field.name in delta else "plain" if field.name in plain else "dict"
        got = {how: n for how in (("dict", "delta", "plain") if integer else ("dict", "plain"))
               if (n := _cost(head, field.name, how)) is not None}
        if not got or chosen not in got:
            continue
        best = min(got, key=got.get)
        if got[chosen] > got[best] * TOLERANCE:
            said.append(
                f"{resource_id}.{field.name} is {chosen} where {best} is "
                f"{got[chosen] / got[best]:.1f}x smaller on {head.num_rows:,} sampled rows"
            )
    return said
