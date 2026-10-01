"""Each column takes the encoding its values and its declaration call for."""

import pyarrow as pa
import pytest

from escapewheel_writer import PacketWriter
from escapewheel_writer.encoding import (
    DELTA_COLUMNS,
    DICTIONARY_COLUMNS,
    NO_DICTIONARY,
    inefficient,
)


def test_every_encoding_exception_names_a_column_that_exists(registry):
    """An exception no column answers to is a claim nothing tests.

    `_delta_columns` picks a Parquet encoding from two rules and two lists of exceptions, each
    declared with the measurement that justifies it. `check.py` applies the same discipline to
    `NAMING_EXCEPTIONS` — declared with a reason, and checked to still be needed.

    Whether the encoding is the *better* one needs real values, which
    `conformance/parquet-probe/alternatives.py` measures against a built packet. That the column
    exists and has a type its list can encode is decidable here, with no packet in hand.
    """
    tables = {
        name: declaration["table"]
        for name, declaration in registry["resources"].items()
        if declaration["kind"] == "table"
    }
    named = [resource for entries in (DELTA_COLUMNS, NO_DICTIONARY, DICTIONARY_COLUMNS) for resource in entries]
    assert [r for r in named if not r.startswith(("core.", "analysis."))] == [], (
        "core names an extension's table; an extension supplies its own to PacketWriter"
    )
    numeric = {"int32", "int64", "float32", "float64"}
    strings = {"string", "json_string"}
    stale = [
        f"{listed}: {resource}.{column}"
        for listed, entries, types in (
            ("DELTA_COLUMNS", DELTA_COLUMNS, {"int32", "int64"}),
            ("NO_DICTIONARY", NO_DICTIONARY, numeric | strings),
            ("DICTIONARY_COLUMNS", DICTIONARY_COLUMNS, numeric | strings),
        )
        for resource, columns in entries.items()
        for column in columns
        if resource not in tables
        or not any(c["name"] == column and c["type"] in types for c in tables[resource]["columns"])
    ]
    assert stale == []


def _chosen(values, column=None):
    from escapewheel_writer.encoding import choose, count

    column = column or {"name": "x", "role": "data"}
    return choose(pa.field(column["name"], values.type), column, None, count(values))


def test_a_column_holding_no_value_is_plain():
    """A dictionary page costs its bytes before it indexes anything, and here it would index nothing."""
    assert _chosen(pa.array([None] * 12, type=pa.string())) == "plain"


def test_one_value_takes_a_dictionary_only_over_a_long_row_group():
    """A dictionary page repays itself over tens of thousands of rows of one value, not over a dozen."""
    from escapewheel_writer.encoding import ONE_VALUE_ROWS

    assert _chosen(pa.array([7] * 12, type=pa.int32())) == "delta"
    assert _chosen(pa.array(["ccf"] * 12)) == "plain"
    assert _chosen(pa.array([7] * ONE_VALUE_ROWS, type=pa.int32())) is None


def test_a_declared_order_is_seen_where_values_climb_only_within_groups():
    """A tick climbs within each unit and resets, which no count over the whole column can see."""
    sawtooth = pa.array([t for _ in range(10) for t in range(100)], type=pa.int64())
    assert _chosen(sawtooth, {"name": "t_tick", "role": "coordinate"}) == "delta"
    assert _chosen(sawtooth, {"name": "count", "role": "data"}) == "plain", "undeclared, each value covers 10 rows"


def test_a_single_valued_identifier_is_decided_by_its_one_value():
    """`session_id` holds one value in a single-session packet, so the one-value rule decides it first.

    That is why the ordered-integer rule needs no exception for it, declared `assigned` as it is.
    """
    from escapewheel_writer.encoding import ONE_VALUE_ROWS

    session = {"name": "session_id", "role": "identifier", "identity": "assigned"}
    assert _chosen(pa.array([0] * 12, type=pa.int32()), session) == "delta"
    assert _chosen(pa.array([0] * ONE_VALUE_ROWS, type=pa.int32()), session) is None


def test_an_observed_climb_takes_delta_unless_it_climbs_in_long_runs():
    """Delta encodes a step; a run of equal values is a step of zero repeated, which plain compresses too."""
    assert _chosen(pa.array(range(1_000), type=pa.int64())) == "delta"
    assert _chosen(pa.array([i // 100 for i in range(1_000)], type=pa.int64())) == "plain"


def test_repetition_decides_between_a_dictionary_and_plain():
    """Where each value covers fifty rows a dictionary indexes something; where it covers a few it does not."""
    assert _chosen(pa.array(["sua", "mua", "noise"] * 400)) is None
    assert _chosen(pa.array([i / 7 for i in range(1_200)])) == "plain"
    assert _chosen(pa.array([float(i % 5) for i in range(1_200)])) is None


def test_with_no_values_only_the_declaration_decides():
    """A spill opened before its first batch has counts of nothing, and still knows a tick climbs."""
    from escapewheel_writer.encoding import choose

    assert choose(pa.field("t_tick", pa.int64()), {"role": "coordinate"}, None, None) == "delta"
    assert choose(pa.field("label", pa.string()), {"role": "data"}, None, None) is None


def test_an_inefficient_encoding_is_reported(tmp_path, registry, minimal):
    """Part 03 §5.5's rules are good guesses, and a column it guesses wrong about is said aloud.

    Collected and never read is how this mechanism failed first: the notes were appended in two
    places and emitted in none, so the report existed and reached nobody. Both halves are pinned
    here — that `inefficient` finds a column, and that `commit` says what it found.
    """
    said: list[str] = []
    writer = PacketWriter(registry, packet_id="p", session="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    writer._encoding_notes.append("core.pretend.column is plain where dict is 9.9x smaller")
    writer.commit(tmp_path / "packet", say=said.append)
    assert [line for line in said if "9.9x smaller" in line], "a collected note reached nobody"


def test_inefficient_finds_a_column_encoded_worse_than_it_could_be(registry):
    """An ascending integer is what delta exists for, so calling it anything else is reported.

    The check is over what a caller says it chose, not over what a rule would choose, so a writer
    that ignores Part 03 §5.5 entirely still learns what its choice cost.
    """
    ramp = pa.table({"t_tick": pa.array(range(1_000_000, 1_020_000), type=pa.int64())})
    assert inefficient("core.pretend", ramp, delta=[], plain=["t_tick"]), "delta is far smaller"
    assert inefficient("core.pretend", ramp, delta=["t_tick"], plain=[]) == [], "and delta is said to be right"


def test_inefficient_judges_a_small_column_by_its_chunk(registry):
    """A one-column file's footer outweighs a dozen rows, so a comparison of files reports nothing small."""
    ids = pa.table({"sorting_run_id": pa.array(range(12), type=pa.int32())})
    assert inefficient("core.pretend", ids, delta=[], plain=[]), "a dictionary over twelve ascending values"
    assert inefficient("core.pretend", ids, delta=["sorting_run_id"], plain=[]) == []


@pytest.mark.parametrize("held", ["strings", "codes"])
def test_inefficient_reports_a_string_a_dictionary_does_not_pay_for(registry, held):
    """Strings are judged too, between the dictionary and plain; a delta string encoding is no choice."""
    names = pa.array([f"probe.CH{i}" for i in range(4_000)])
    table = pa.table({"electrode_name": names if held == "strings" else names.dictionary_encode()})
    assert inefficient("core.pretend", table, delta=[], plain=[]), "a dictionary of 4,000 distinct names"
    assert inefficient("core.pretend", table, delta=[], plain=["electrode_name"]) == []
