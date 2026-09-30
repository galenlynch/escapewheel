"""The stored order of Part 03 §5.3 and the overriding orders of Part 03 §5.4."""

from escapewheel_reader.ordering import overridden, stored_order

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
