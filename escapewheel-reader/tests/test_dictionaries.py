"""Joining and filtering on keys that may be dictionary-encoded."""

import pyarrow as pa
import pyarrow.dataset as pads
import pytest

from escapewheel_reader.dictionaries import key_filter, lookup, within

I32 = pa.int32()
ROWS = pa.table(
    {
        "session_id": pa.array([1, 1, 2, 2], I32),
        "unit_id": pa.array([1, 2, 1, 2], I32),
        "t_tick": pa.array([10, 20, 30, 40], pa.int64()),
    }
)


def test_per_key_membership_is_inexact_across_sessions_and_within_restores_it():
    """Asking for (1, 1) and (2, 2) must not return (1, 2) or (2, 1)."""
    wanted = pa.table({"session_id": pa.array([1, 2], I32), "unit_id": pa.array([1, 2], I32)})
    test, exact = key_filter(wanted, ["session_id", "unit_id"])
    assert not exact
    pruned = pads.dataset(ROWS).to_table(filter=test)
    assert pruned.num_rows == 4
    assert within(pruned, wanted, ["session_id", "unit_id"]).column("t_tick").to_pylist() == [10, 40]


def test_every_combination_wanted_is_exact():
    wanted = pa.table({"session_id": pa.array([1, 1], I32), "unit_id": pa.array([1, 2], I32)})
    assert key_filter(wanted, ["session_id", "unit_id"])[1]


def test_a_dictionary_of_integers_filters_as_its_values():
    wanted = pa.table({"unit_id": pa.array([2], I32).dictionary_encode()})
    test, exact = key_filter(wanted, ["unit_id"])
    assert exact
    assert pads.dataset(ROWS).to_table(filter=test).column("t_tick").to_pylist() == [20, 40]


def test_lookup_keeps_row_order_and_nulls_an_unmatched_key():
    parent = pa.table(
        {"session_id": pa.array([2, 1], I32), "unit_id": pa.array([2, 1], I32), "clock_id": pa.array([7, 5], I32)}
    )
    keys = [ROWS.column("session_id").combine_chunks().dictionary_encode(), ROWS.column("unit_id")]
    assert lookup(keys, parent, ["session_id", "unit_id"], "clock_id").to_pylist() == [5, None, None, 7]


def test_lookup_refuses_a_parent_holding_a_key_twice():
    parent = pa.table({"unit_id": pa.array([1, 1], I32), "clock_id": pa.array([5, 6], I32)})
    with pytest.raises(ValueError, match="more than one row"):
        lookup([ROWS.column("unit_id")], parent, ["unit_id"], "clock_id")
