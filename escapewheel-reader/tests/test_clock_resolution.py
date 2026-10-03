"""Each coordinate's clock, resolved from its declaration (Part 02 §8.4), and mapping by it."""

import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest
from packet_fixture import (
    CLOCK_BEHAVIOUR,
    CLOCK_PROBE,
    SESSION,
    UNITS,
    core_registry,
    install_registry,
    resource_entry,
    write_table,
)

from escapewheel_reader import NotAligned, NotDeclared, access, attach_clocks, clocks, on_clock, open_packet, seconds
from escapewheel_reader.clocks import clock_columns

REPOSITORY = Path(__file__).resolve().parents[2]

#: The core columns the fixture's registry declares: what the clocks are reached through.
DECLARED = {
    "core.sessions": (
        "session_id",
        "session_name",
        "subject_id",
        "session_start_time",
        "reference_clock_id",
        "t_zero_tick",
    ),
    "core.clocks": ("session_id", "clock_id", "tick_rate_num", "tick_rate_den", "parent_clock_id"),
    "core.clock_anchors": ("session_id", "clock_id", "anchor_index", "t_tick", "parent_tick"),
    "core.intervals": (
        "session_id",
        "interval_id",
        "interval_name",
        "interval_kind",
        "local_interval_label",
        "start_tick",
        "stop_tick",
        "clock_id",
    ),
    "core.units": ("session_id", "unit_id", "unit_name", "sorting_run_id", "curation_id", "quality_label", "clock_id"),
    "core.event_streams": ("event_stream_id", "session_id", "event_stream_name", "event_type", "clock_id"),
    "core.events": ("session_id", "stream_id", "t_tick"),
    "core.spike_events": ("session_id", "unit_id", "t_tick"),
}

#: Ticks the two-clock fixture's anchors place exactly: probe tick `30_000 * k` is harp tick
#: `1_000_000 + 31_250 * k`, the origin is harp 1,000,000, and harp counts 31,250 a second.
PROBE_SECOND = 30_000
HARP_SECOND = 31_250
ORIGIN = 1_000_000
#: Past the last anchor (probe 210,000) by more than the one interval the bound allows.
UNPLACEABLE = 300_000
#: A trial that core.intervals does not hold, so its hop finds no clock.
UNKNOWN_TRIAL = 9

I32, I64 = pa.int32(), pa.int64()


def _lab_registry():
    """An extension with a two-column hop, and a table whose hop is ambiguous."""
    coordinate = {"type": "int64", "presence": "optional", "role": "coordinate", "description": "onset"}
    identifier = {"type": "int32", "presence": "required", "role": "identifier", "identity": "assigned"}
    to_intervals = {
        "columns": ["session_id", "trial_id"],
        "resource": "core.intervals",
        "resource_columns": ["session_id", "interval_id"],
    }

    def table(columns, references):
        return {
            "content_class": "extension",
            "kind": "table",
            "table": {"columns": columns, "primary_key": [], "references": references, "rules": []},
        }

    onset = {"name": "onset_tick", **coordinate, "clock_from": "core.intervals.clock_id"}
    return {
        "registry_id": "lab",
        "registry_version": "0.1.0",
        "resources": {
            "lab.sweeps": table(
                [{"name": "session_id", **identifier}, {"name": "trial_id", **identifier}, onset], [to_intervals]
            ),
            "lab.pairs": table(
                [{"name": "session_id", **identifier}, {"name": "trial_id", **identifier}, onset],
                [to_intervals, {**to_intervals, "columns": ["session_id", "session_id"]}],
            ),
        },
    }


@pytest.fixture
def resolved_packet(two_clock_packet):
    """The two-clock packet with the clocks' declarations bound, trials on both clocks, and extensions."""
    root = two_clock_packet
    install_registry(root, core_registry(DECLARED))
    install_registry(root, json.loads((REPOSITORY / "extensions" / "dynamic_foraging.json").read_text()))
    install_registry(root, _lab_registry())
    manifest = json.loads((root / "packet.json").read_text())
    by_id = {r["resource_id"]: r for r in manifest["resources"]}

    # Trial 0 was timed on the probe clock and trial 1 on harp.
    intervals = pa.table(
        {
            "session_id": pa.array([SESSION] * 2, I32),
            "interval_id": pa.array([0, 1], I32),
            "interval_kind": pa.array(["dynamic_foraging.trials"] * 2),
            "start_tick": pa.array([0, ORIGIN + HARP_SECOND], I64),
            "stop_tick": pa.array([4 * PROBE_SECOND, ORIGIN + 5 * HARP_SECOND], I64),
            "clock_id": pa.array([CLOCK_PROBE, CLOCK_BEHAVIOUR], I32),
        }
    )
    by_id["core.intervals"]["uri"] = write_table(root, "intervals", intervals)
    trials = pa.table(
        {
            "session_id": pa.array([SESSION] * 3, I32),
            "trial_id": pa.array([0, 1, UNKNOWN_TRIAL], I32),
            "delay_start_tick": pa.array([PROBE_SECOND, ORIGIN + 2 * HARP_SECOND, 5], I64),
            "go_cue_start_tick": pa.array([2 * PROBE_SECOND, ORIGIN + 3 * HARP_SECOND, 6], I64),
            "reward_outcome_tick": pa.array([UNPLACEABLE, None, 7], I64),
        }
    )
    sweeps = pa.table(
        {
            "session_id": pa.array([SESSION, SESSION, SESSION + 1], I32),
            "trial_id": pa.array([0, 1, 0], I32),
            "onset_tick": pa.array([PROBE_SECOND, ORIGIN, 8], I64),
        }
    )
    for resource_id, table in (("dynamic_foraging.trials", trials), ("lab.sweeps", sweeps), ("lab.pairs", sweeps)):
        namespace, _, name = resource_id.partition(".")
        manifest["resources"].append(resource_entry(resource_id, write_table(root, name, table, namespace)))
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(root)


def _harp(probe_tick):
    return ORIGIN + probe_tick * HARP_SECOND // PROBE_SECOND


# -- naming -----------------------------------------------------------------------------


class _Declares:
    """A packet stub resolving every resource against the registries given."""

    def __init__(self, *documents):
        self._declarations = {rid: d for document in documents for rid, d in document["resources"].items()}

    def resource(self, resource_id):
        declaration = self._declarations[resource_id]
        return type("Resource", (), {"declaration": declaration})()


def _registries():
    paths = [
        REPOSITORY / "spec" / "artifacts" / "logical_schemas.json",
        *sorted((REPOSITORY / "extensions").glob("*.json")),
    ]
    return [json.loads(path.read_text()) for path in paths]


@pytest.mark.parametrize(
    ("resource_id", "expected"),
    [
        ("core.spike_events", {"t_tick": "clock_id"}),
        ("core.events", {"t_tick": "clock_id"}),
        ("core.unit_observation_intervals", {"start_tick": "clock_id", "stop_tick": "clock_id"}),
        ("core.clock_anchors", {"t_tick": "clock_id", "parent_tick": "parent_tick_clock_id"}),
        ("core.clock_phase_steps", {"t_tick": "clock_id", "parent_tick": "parent_tick_clock_id"}),
        ("core.sessions", {"t_zero_tick": "clock_id"}),
        ("core.intervals", {"start_tick": "clock_id", "stop_tick": "clock_id"}),
        (
            "dynamic_foraging.trials",
            {"delay_start_tick": "clock_id", "go_cue_start_tick": "clock_id", "reward_outcome_tick": "clock_id"},
        ),
        (
            "vr_foraging.sites",
            dict.fromkeys(("odor_onset_tick", "choice_cue_tick", "reward_onset_tick", "last_stop_tick"), "clock_id"),
        ),
    ],
)
def test_each_clock_from_form_names_its_clock_column(resource_id, expected):
    assert clock_columns(_Declares(*_registries()), resource_id) == expected


def test_every_declared_coordinate_has_a_clock_column():
    """No table in core or a shipped extension asks for a name it already declares."""
    stub = _Declares(*_registries())
    for document in _registries():
        for resource_id, declaration in document["resources"].items():
            if declaration.get("kind") == "table":
                clock_columns(stub, resource_id)


# -- attaching ---------------------------------------------------------------------------


def test_a_spike_takes_its_units_clock_and_an_unknown_unit_none(resolved_packet):
    spikes = pa.table({"unit_id": pa.array([UNITS[0], UNITS[2], 99], I32), "t_tick": pa.array([1, 2, 3], I64)})
    attached = attach_clocks(resolved_packet, "core.spike_events", spikes)
    assert attached.column("clock_id").to_pylist() == [CLOCK_PROBE, CLOCK_BEHAVIOUR, None]


def test_an_event_takes_its_streams_clock(resolved_packet):
    attached = attach_clocks(resolved_packet, "core.events", resolved_packet.table("core.events"))
    assert attached.column("clock_id").to_pylist() == [CLOCK_BEHAVIOUR]


def test_an_anchors_parent_tick_takes_its_clocks_parent(resolved_packet):
    attached = attach_clocks(resolved_packet, "core.clock_anchors", resolved_packet.table("core.clock_anchors"))
    assert set(attached.column("clock_id").to_pylist()) == {CLOCK_PROBE}
    assert set(attached.column("parent_tick_clock_id").to_pylist()) == {CLOCK_BEHAVIOUR}


def test_the_origin_takes_the_reference_clock(resolved_packet):
    attached = attach_clocks(resolved_packet, "core.sessions", resolved_packet.table("core.sessions"))
    assert attached.column("clock_id").to_pylist() == [CLOCK_BEHAVIOUR]
    assert seconds(resolved_packet, attached, resource_id="core.sessions").column("t_zero_second").to_pylist() == [0.0]


def test_an_extension_trial_takes_its_intervals_clock(resolved_packet):
    trials = resolved_packet.table("dynamic_foraging.trials")
    attached = attach_clocks(resolved_packet, "dynamic_foraging.trials", trials)
    assert attached.column("clock_id").to_pylist() == [CLOCK_PROBE, CLOCK_BEHAVIOUR, None]


def test_a_two_column_hop_matches_on_both(resolved_packet):
    attached = attach_clocks(resolved_packet, "lab.sweeps", resolved_packet.table("lab.sweeps"))
    assert attached.column("clock_id").to_pylist() == [CLOCK_PROBE, CLOCK_BEHAVIOUR, None]


def test_attaching_twice_is_attaching_once(resolved_packet):
    trials = attach_clocks(resolved_packet, "dynamic_foraging.trials", resolved_packet.table("dynamic_foraging.trials"))
    assert attach_clocks(resolved_packet, "dynamic_foraging.trials", trials).equals(trials)


def test_a_hop_through_two_references_is_refused(resolved_packet):
    with pytest.raises(NotDeclared, match="2 references to core.intervals"):
        attach_clocks(resolved_packet, "lab.pairs", resolved_packet.table("lab.pairs"))


def test_a_hop_without_its_key_is_refused(resolved_packet):
    trials = resolved_packet.table("dynamic_foraging.trials", columns=["go_cue_start_tick"])
    with pytest.raises(ValueError, match="trial_id"):
        attach_clocks(resolved_packet, "dynamic_foraging.trials", trials)


# -- mapping -----------------------------------------------------------------------------


def test_several_coordinates_null_what_cannot_be_placed(resolved_packet):
    """A trial keeps its row, and loses only the tick the anchors cannot place or that has no clock."""
    mapped = on_clock(
        resolved_packet, resolved_packet.table("dynamic_foraging.trials"), resource_id="dynamic_foraging.trials"
    )
    assert mapped.num_rows == 3
    assert mapped.column("go_cue_start_tick").to_pylist() == [_harp(2 * PROBE_SECOND), ORIGIN + 3 * HARP_SECOND, None]
    assert mapped.column("delay_start_tick").to_pylist() == [_harp(PROBE_SECOND), ORIGIN + 2 * HARP_SECOND, None]
    assert mapped.column("reward_outcome_tick").to_pylist() == [None, None, None]
    assert mapped.column("clock_id").to_pylist() == [CLOCK_BEHAVIOUR, CLOCK_BEHAVIOUR, None]


def test_one_coordinate_drops_what_cannot_be_placed(resolved_packet):
    """As `analysis.spike_events` omits it: the tick is the row's whole content."""
    spikes = pa.table(
        {
            "unit_id": pa.array([UNITS[0], UNITS[0], 99], I32),
            "t_tick": pa.array([PROBE_SECOND, UNPLACEABLE, PROBE_SECOND], I64),
        }
    )
    mapped = on_clock(resolved_packet, spikes, resource_id="core.spike_events")
    assert mapped.column("t_tick").to_pylist() == [_harp(PROBE_SECOND)]
    assert mapped.column("clock_id").to_pylist() == [CLOCK_BEHAVIOUR]


def test_coordinates_on_different_clocks_meet_on_one(resolved_packet):
    """An anchor's own tick, mapped, is its parent tick."""
    mapped = on_clock(resolved_packet, resolved_packet.table("core.clock_anchors"), resource_id="core.clock_anchors")
    assert mapped.column("t_tick").equals(mapped.column("parent_tick"))
    assert set(mapped.column("clock_id").to_pylist()) == {CLOCK_BEHAVIOUR}
    assert set(mapped.column("parent_tick_clock_id").to_pylist()) == {CLOCK_BEHAVIOUR}


def test_a_clock_with_no_path_is_refused(resolved_packet):
    """Harp has no anchors onto the probe, so a harp-timed trial cannot be put on it."""
    trials = resolved_packet.table("dynamic_foraging.trials")
    with pytest.raises(NotAligned, match="not an ancestor"):
        on_clock(resolved_packet, trials, CLOCK_PROBE, resource_id="dynamic_foraging.trials")


def test_the_resource_path_maps_events_as_the_accessor_does(resolved_packet):
    mapped = on_clock(resolved_packet, resolved_packet.table("core.events"), resource_id="core.events")
    expected = access.events(resolved_packet)
    assert mapped.select(["t_tick", "clock_id"]).equals(expected.select(["t_tick", "clock_id"]))


def test_the_resource_path_maps_spikes_as_the_accessor_does(resolved_packet):
    stored = resolved_packet.table("core.spike_events", columns=["unit_id", "t_tick"])
    mapped = on_clock(resolved_packet, stored, resource_id="core.spike_events").select(
        ["unit_id", "t_tick", "clock_id"]
    )
    assert mapped.equals(access.spike_times(resolved_packet, units=access.units(resolved_packet)))


# -- reading in one call -----------------------------------------------------------------


def test_a_trial_table_reads_in_seconds(resolved_packet):
    """`table(on_clock=True, seconds=True)` is mapping each tick by hand and dividing."""
    read = resolved_packet.table("dynamic_foraging.trials", on_clock=True, seconds=True)
    anchor_t, anchor_p = clocks.anchors(resolved_packet)[CLOCK_PROBE]
    probe, _ = clocks.align(np.array([2 * PROBE_SECOND], np.int64), anchor_t, anchor_p)
    by_hand = [(int(probe[0]) - ORIGIN) / HARP_SECOND, 3.0, None]
    assert read.column("go_cue_start_second").to_pylist() == by_hand
    assert read.column("delay_start_second").to_pylist() == [1.0, 2.0, None]
    assert read.column("reward_outcome_second").to_pylist() == [None, None, None]


def test_seconds_off_the_reference_clock_are_refused(resolved_packet):
    with pytest.raises(NotAligned, match="map them with on_clock first"):
        resolved_packet.table("dynamic_foraging.trials", seconds=True)


def test_a_table_read_without_options_is_as_stored(resolved_packet):
    read = resolved_packet.table("dynamic_foraging.trials")
    assert "clock_id" not in read.column_names
    assert read.column("go_cue_start_tick").to_pylist() == [2 * PROBE_SECOND, ORIGIN + 3 * HARP_SECOND, 6]


def test_a_table_maps_onto_a_named_clock(resolved_packet):
    read = resolved_packet.table("core.spike_events", on_clock=CLOCK_BEHAVIOUR)
    assert set(read.column("clock_id").to_pylist()) == {CLOCK_BEHAVIOUR}
