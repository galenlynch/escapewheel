"""What the AIND dialect reads that base NWB does not declare.

Each test here failed against `escapewheel_writer.sources.nwb.NWBSource` once the dialect left it,
which is the point: the base reader ignores a column the schema does not declare, and this adapter
is where knowing what those columns mean lives.
"""

from zoneinfo import ZoneInfo

import numpy as np
import pytest
from escapewheel_writer import Clock
from escapewheel_writer.clock import HARP_TICK_RATE_HZ

from escapewheel_aind.nwb import AindNWBSource
from tests import nwbfixture

KIND = "task.trials"
PACIFIC = ZoneInfo("America/Los_Angeles")
SESSION = "mini_2025-04-09"


@pytest.fixture
def harp():
    return Clock("harp", session_id=SESSION, name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="HARP epoch")


@pytest.fixture
def nwb(tmp_path):
    return nwbfixture.build(tmp_path)


@pytest.fixture
def source(nwb, harp):
    return AindNWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND)


def only(rows, **match):
    found = [r for r in rows if all(r[k] == v for k, v in match.items())]
    assert len(found) == 1, f"{len(found)} rows match {match}"
    return found[0]


def _stream_of(source, event_type):
    """The stream emitting one kind of event, which R91 §3.1 makes the stream's property."""
    return next(s["event_stream_id"] for s in source.event_streams() if s["event_type"] == event_type)


# -- the device's model and serial, packed into a sentence ----------------------------


def test_the_probe_takes_its_model_and_serial_from_the_packed_description(source):
    """Core 2.9.0 declares all three as Device attributes and this exporter sets none of them."""
    probe = source.records()["core.probes"][0]
    assert (probe["probe_type"], probe["serial_number"], probe["manufacturer"]) == (
        "Neuropixels 2.0 - Quad Base",
        "12345",
        "IMEC",
    )


def test_a_description_that_does_not_parse_is_kept_whole(tmp_path, harp):
    """Keeping both a parsed description and the sentence it came from stores one fact twice."""
    root = nwbfixture.build(tmp_path)
    nwbfixture.group(
        root / "general/devices/probeA", neurodata_type="Device", manufacturer="IMEC", description="a probe"
    )
    device = AindNWBSource(root, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND).devices()[0]
    assert device["serial_number"] is None
    assert device["metadata"] == {"description": "a probe"}


# -- the atlas triple and its annotation ----------------------------------------------


def test_a_ccf_frame_is_declared_beside_the_probe_frame(source):
    axes = source.records()["core.coordinate_frame_axes"]
    assert [(a["coordinate_frame"], a["axis_index"], a["axis_name"]) for a in axes] == [
        ("probe", 0, "rel_x"),
        ("probe", 1, "rel_y"),
        ("ccf", 0, "ccf_ml"),
        ("ccf", 1, "ccf_ap"),
        ("ccf", 2, "ccf_dv"),
    ]


def test_a_ccf_position_carries_its_atlas_annotation(source):
    """R59 §2 promoted `ccf_id` and `ccf_acronym` to columns of the coordinate row."""
    ccf = only(source.records()["core.electrode_coordinates"], electrode_id="probeA.CH0", coordinate_frame="ccf")
    assert (ccf["region_id"], ccf["region_label"]) == (382, "CA1")
    assert ccf["coordinate_basis"] == "measured"


def test_an_electrodes_bag_carries_only_what_no_column_holds(source):
    """Part 02 §8.6: R59 §2 declined to model these two, so the bag is where they belong."""
    bag = only(source.records()["core.electrodes"], electrode_id="probeA.CH0")["metadata"]
    assert bag == {"ccf_name": "Field CA1", "ccf_structure_id_path": "/997/8/567/"}


def test_an_unregistered_electrode_gets_no_ccf_row(source):
    """An absent frame is an absent row, which is the whole point of R19's shape."""
    assert not [
        c
        for c in source.records()["core.electrode_coordinates"]
        if c["electrode_id"] == "probeA.CH1" and c["coordinate_frame"] == "ccf"
    ]


def test_this_pipelines_contact_label_repeats_and_so_is_not_an_identity(source):
    """1,920 distinct `electrode_name` values over 4,608 rows; the pair (group, channel) is the id."""
    electrodes = source.records()["core.electrodes"]
    assert [e["local_electrode_label"] for e in electrodes] == ["e0", "e0"]
    assert sorted(e["electrode_id"] for e in electrodes) == ["probeA.CH0", "probeA.CH1"]


# -- a unit's position, which needs the sorter's own label ----------------------------


def test_a_unit_coordinate_needs_the_pipelines_unit_identity(nwb, harp):
    """The join is `(device_name, ks_unit_id)`: the probe plus the sorter's label (R83, R81)."""
    units = nwbfixture.units(nwb)
    source = AindNWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, units=units, interval_kind=KIND)
    assert source.unit_coordinates() == [
        {
            "session_id": SESSION,
            "unit_id": 1,
            "coordinate_frame": "ccf",
            "coordinate_basis": "measured",
        }
    ]
    assert [(v["axis_index"], v["axis_value"]) for v in source.unit_coordinate_values()] == [
        (0, 100.0),
        (1, 100.0),
        (2, 100.0),
    ]
    assert [note for note in source.notes if "spike_times" in note] == []


def test_a_unit_row_matching_no_unit_is_skipped_and_counted(nwb, harp):
    """A wrong key is a build defect, so it is reported rather than passed over in silence."""
    nwbfixture.units(nwb)
    source = AindNWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, units=(), interval_kind=KIND)
    assert source.unit_coordinates() == []


def test_the_declared_resources_include_the_unit_coordinates():
    """The base reader declares neither, which is what a recipe arbitrates between them on."""
    from escapewheel_writer.sources.nwb import NWBSource

    added = AindNWBSource.PRODUCES - NWBSource.PRODUCES
    assert added == {"core.unit_coordinates", "core.unit_coordinate_values"}
    assert "units" in AindNWBSource.NEEDS and "units" not in NWBSource.NEEDS


# -- a moment recorded as a trial column is still an event ----------------------------


def test_trial_timing_columns_become_events(source):
    """A task writes the go cue into its trials table because it happens once a trial. It is still
    a moment on a clock, and a query should find it without knowing the task's shape."""
    kinds = {s["event_type"] for s in source.event_streams()}
    assert {"go_cue", "reward_outcome"} <= kinds
    emitting = {
        s["event_stream_id"] for s in source.event_streams() if s["event_type"] in {"go_cue", "reward_outcome"}
    }
    assert emitting <= {e["stream_id"] for e in source.events()}


def test_a_trial_event_lands_on_the_declared_clock(source, harp):
    """R91 §3.2 struck `core.events.clock_id`: the tick is on the clock its stream declares."""
    stream = _stream_of(source, "go_cue")
    go = next(e for e in source.events() if e["stream_id"] == stream)
    assert "clock_id" not in go
    assert next(s for s in source.event_streams() if s["event_stream_id"] == stream)["clock_id"] == harp.clock_id
    assert go["t_tick"] == harp.ticks(np.array([1.2]))[0]


def test_a_trial_event_does_not_name_its_interval(source):
    """R11 §5 struck the column; carrying it as JSON would keep the letter and lose the point."""
    go = next(e for e in source.events() if e["stream_id"] == _stream_of(source, "go_cue"))
    assert "payload" not in go or "trial_id" not in (go.get("payload") or {})


def test_a_trial_that_never_reached_the_moment_emits_no_event(tmp_path, harp):
    """Absence is a fact about the trial, not a null to carry."""
    root = nwbfixture.build(tmp_path)
    nwbfixture.array(root / "intervals/trials/goCue_start_time", np.array([np.nan]))
    source = AindNWBSource(root, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND)
    assert not [e for e in source.events() if e["stream_id"] == _stream_of(source, "go_cue")]
    assert "go_cue" in {s["event_stream_name"] for s in source.event_streams()}


def test_a_mapped_task_column_is_not_repeated_in_metadata(nwb, harp):
    """It is in core.events now, so carrying it again would be the duplication Part 02 §6 bans."""
    carrying = AindNWBSource(
        nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND, trial_metadata=True
    )
    metadata = carrying.intervals()[0].get("metadata") or {}
    assert "goCue_start_time" not in metadata
    assert "animal_response" not in metadata
