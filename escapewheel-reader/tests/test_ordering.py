"""The stored order of Part 03 §5.3 and the overriding orders of Part 03 §5.4."""

import pytest

from escapewheel_reader.ordering import overridden, override_errors, stored_order

SPIKES = {
    "columns": [
        {"name": "session_id"},
        {"name": "unit_id"},
        {"name": "t_tick"},
        {"name": "amplitude"},
        {"name": "clock_id", "determined_by": ["session_id"]},
        {"name": "time_bucket_tick", "determined_by": ["t_tick"]},
    ],
    "primary_key": ["session_id", "unit_id", "t_tick"],
}
OVERRIDE = ["session_id", "clock_id", "time_bucket_tick", "unit_id", "t_tick"]


def test_a_table_the_descriptor_names_takes_its_order():
    assert stored_order("analysis.spike_events", SPIKES) == OVERRIDE
    assert overridden("analysis.spike_events") == OVERRIDE


def test_any_other_table_takes_its_primary_keys_order():
    assert stored_order("core.spike_events", SPIKES) == SPIKES["primary_key"]
    assert overridden("core.spike_events") is None


def test_the_portable_override_is_consistent():
    assert override_errors(OVERRIDE, SPIKES) == []


@pytest.mark.parametrize(
    ("order", "table", "error"),
    [
        (OVERRIDE, None, "the core registry declares no such table"),
        ([*OVERRIDE, "spike_count"], SPIKES, "'spike_count' is not a column of the table"),
        (OVERRIDE[:-1], SPIKES, "key column 't_tick' is absent"),
        (
            ["session_id", "amplitude", "unit_id", "t_tick"],
            SPIKES,
            "'amplitude' precedes a key column and is not determined by the key",
        ),
        (["session_id", "unit_id", "t_tick"], SPIKES, "the order is the table's primary key's order"),
    ],
    ids=["undeclared-table", "undeclared-column", "missing-key-column", "undetermined-column", "key-order"],
)
def test_an_inconsistent_override_is_refused(order, table, error):
    assert override_errors(order, table) == [error]
