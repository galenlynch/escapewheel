"""The JSON adapter locates tick zero and declares the windows the NWB cannot."""

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from escapewheel_writer import FixedOffsetZone, NaiveTimestamp, SourceDefect, UsageError, UsageFault
from escapewheel_writer.adapter import HARP_TICK_RATE_HZ, Clock, coded, codes

from escapewheel_aind.errors import AindFault
from escapewheel_aind.notes import AindNote
from tests.builders import (
    BEHAVIOR_START,
    EPHYS_START,
    EPHYS_STOP,
    HARP_ROW,
    PACIFIC,
    SESSION,
    session_asset,
    session_source,
)

#: The first spike, on the HARP clock. Anchors the epoch.
FIRST_SPIKE_TICK = round(11_575_876.219 * HARP_TICK_RATE_HZ)
#: The first and last behaviour event, which the declared window must contain.
FIRST_EVENT_TICK = round(11_576_039.862 * HARP_TICK_RATE_HZ)
LAST_EVENT_TICK = round(11_583_848.938 * HARP_TICK_RATE_HZ)


@pytest.fixture
def asset(tmp_path):
    return session_asset(tmp_path)


@pytest.fixture
def source(asset):
    return session_source(asset)


@pytest.fixture
def harp(source):
    return source.clock(clock_id="harp", at_tick=FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ)


@pytest.fixture
def located(asset, harp):
    """The source as a build hands it over: a reference clock whose tick 0 is already located."""
    return session_source(asset, reference_clock={**HARP_ROW, "tick_zero_utc": harp.tick_zero_utc})


def window(source, clock):
    """The window this source declares it watched the reference clock over, in that clock's ticks.

    It reaches a build as a `core.clock_observation_intervals` row on the reference clock, and the
    build gives it to every event stream another source declares.
    """
    watched = source.records().get("core.clock_observation_intervals", [])
    (declared,) = [row for row in watched if row["clock_id"] == clock.clock_id]
    return int(declared["start_tick"]), int(declared["stop_tick"])


# -- reading -------------------------------------------------------------------------


def test_it_accepts_the_asset_directory_or_the_file(asset):
    assert session_source(asset).streams()
    assert session_source(asset / "session.json").streams()


def test_a_missing_session_json_is_a_defect(tmp_path):
    with pytest.raises(SourceDefect) as refused:
        session_source(tmp_path)
    assert refused.value.code is AindFault.NO_SESSION_JSON
    assert refused.value.where == str(tmp_path)


def test_a_fixed_offset_is_refused(asset):
    """PDT for the session and PST for the epoch it counts from; a constant is wrong half the year."""
    with pytest.raises(FixedOffsetZone):
        session_source(asset, zone=timezone(timedelta(hours=-7)))


def test_the_streams_split_on_ephys_modules(source):
    assert source.ephys().index == 0
    assert source.behavior().index == 1
    assert source.behavior().modalities == ("behavior-videos",)


def test_a_stream_missing_its_window_is_a_defect(tmp_path):
    asset = session_asset(tmp_path, streams=[{"ephys_modules": []}])
    with pytest.raises(SourceDefect) as refused:
        session_source(asset).streams()
    assert refused.value.code is AindFault.STREAM_FIELD_ABSENT
    assert refused.value.where == "data_streams[0]"


def test_the_task_controller_is_the_behaviour_stream_where_the_cameras_are_declared_apart(tmp_path):
    window = {"stream_start_time": EPHYS_START, "stream_end_time": EPHYS_STOP}
    asset = session_asset(
        tmp_path,
        streams=[
            {**window, "ephys_modules": [{}]},
            {**window, "stream_modalities": [{"abbreviation": "behavior"}]},
            {**window, "stream_modalities": [{"abbreviation": "behavior-videos"}]},
        ],
    )
    assert session_source(asset).behavior().index == 1


def test_an_ambiguous_split_is_a_defect(tmp_path):
    asset = session_asset(
        tmp_path,
        streams=[{"stream_start_time": EPHYS_START, "stream_end_time": EPHYS_STOP, "ephys_modules": []}] * 2,
    )
    with pytest.raises(SourceDefect) as refused:
        session_source(asset).behavior()
    assert refused.value.code is AindFault.NO_ONE_STREAM


# -- the offset that is not trusted --------------------------------------------------


def test_the_seven_hour_error_is_corrected_and_reported(source):
    """`+00:00` on a Pacific reading; the naive part is right, so it is re-localized."""
    assert source.ephys().start == datetime.fromisoformat("2025-04-09T17:25:12-07:00")
    assert any("+00:00" in note and "-07:00" in note for note in coded(source.notes, AindNote.OFFSET_REPLACED))


def test_a_correct_offset_is_left_alone_and_unreported(source):
    assert source.behavior().start == datetime.fromisoformat(BEHAVIOR_START)
    assert not [note for note in source.notes if "stream_start_time" in note and "data_streams[1]" in note]


def test_the_ephys_duration_survives_the_correction(source):
    """Both ends shift together, so the span is unchanged -- it is what cross-checks the NWB."""
    assert source.ephys().duration == timedelta(seconds=6387)


# -- tick zero -----------------------------------------------------------------------


def test_the_epoch_lands_on_the_measured_instant(source):
    """Derived from the ephys start and the first spike; verified against the real asset."""
    assert source.epoch(FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ) == datetime(
        2024, 11, 27, 0, 53, 55, 780992, tzinfo=UTC
    )


def test_the_epoch_crosses_the_dst_boundary_correctly(source):
    """The session is PDT and the epoch 134 days earlier is PST; naive subtraction loses an hour."""
    assert source.epoch(FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ).astimezone(PACIFIC).hour == 16


def test_the_epoch_says_it_was_derived(source):
    source.epoch(FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ)
    (derived,) = coded(source.notes, AindNote.TICK_ZERO_DERIVED)
    assert "data_streams[0]" in derived


def test_the_clock_carries_the_epoch_and_the_session(harp):
    assert harp.tick_zero_utc == datetime(2024, 11, 27, 0, 53, 55, 780992, tzinfo=UTC)
    assert (harp.clock_id, harp.session_id, harp.tick_rate_num) == ("harp", SESSION, HARP_TICK_RATE_HZ)


def test_the_clock_round_trips_its_own_anchor(harp):
    """tick_at inverts epoch: the ephys start maps back to the tick it was derived from."""
    assert harp.tick_at(datetime.fromisoformat("2025-04-09T17:25:12-07:00")) == FIRST_SPIKE_TICK


def test_a_clock_without_an_epoch_locates_nothing():
    bare = Clock("harp", session_id=SESSION, name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="epoch")
    with pytest.raises(UsageError) as refused:
        bare.tick_at(datetime.now(UTC))
    assert refused.value.code is UsageFault.NO_TICK_ZERO
    assert refused.value.where == "harp"


def test_a_naive_instant_locates_nothing(harp):
    with pytest.raises(NaiveTimestamp):
        harp.tick_at(datetime(2025, 4, 9, 17, 25, 12))  # noqa: DTZ001 -- the point


# -- observation intervals -----------------------------------------------------------


def test_it_declares_one_window_on_the_reference_clock(located, harp):
    assert window(located, harp) == (361_751_236_188, 361_996_511_468)


def test_the_window_contains_the_events_it_declares(located, harp):
    """The independent check on the epoch: the events must fall inside the declared window."""
    start, stop = window(located, harp)
    assert start <= FIRST_EVENT_TICK
    assert stop >= LAST_EVENT_TICK


def test_the_window_is_wider_than_the_events(located, harp):
    """Deriving it from the events instead would lose this slack and bias every rate upward."""
    start, stop = window(located, harp)
    leading = (FIRST_EVENT_TICK - start) / HARP_TICK_RATE_HZ
    trailing = (stop - LAST_EVENT_TICK) / HARP_TICK_RATE_HZ
    assert 0 < leading < 1
    assert 39 < trailing < 40


def test_it_uses_the_behaviour_window_not_the_ephys_one(located, harp):
    start, stop = window(located, harp)
    assert (stop - start) / HARP_TICK_RATE_HZ == pytest.approx(7848.8, abs=0.1)


def test_the_ephys_window_is_the_other_one_this_source_declares(source):
    """Which is why the behaviour window is named rather than taken as the first declared."""
    ephys = source.ephys()
    assert (ephys.stop - ephys.start).total_seconds() == pytest.approx(6387.0, abs=0.1)


def test_an_inverted_window_is_a_defect(tmp_path, harp):
    asset = session_asset(
        tmp_path,
        streams=[{"stream_start_time": EPHYS_STOP, "stream_end_time": EPHYS_START, "ephys_modules": []}],
    )
    source = session_source(asset, reference_clock={**HARP_ROW, "tick_zero_utc": harp.tick_zero_utc})
    with pytest.raises(SourceDefect) as refused:
        source.records()
    assert refused.value.code is AindFault.STREAM_REVERSED


def test_a_window_cannot_be_placed_on_a_clock_whose_tick_zero_is_unknown(source):
    """A wall clock locates no tick without one, so the window is omitted and said to be."""
    assert "core.clock_observation_intervals" not in source.records()
    assert AindNote.NO_OBSERVATION_INTERVAL in codes(source.notes)


def test_notes_do_not_grow_when_the_file_is_read_twice(source):
    """Deriving a clock and then asking for a window must not report the offset twice."""
    source.clock(clock_id="harp", at_tick=FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ)
    offsets = coded(source.notes, AindNote.OFFSET_REPLACED)
    source.behavior()
    assert coded(source.notes, AindNote.OFFSET_REPLACED) == offsets


# -- what the build asks for --------------------------------------------------------


def test_records_emit_the_clock_row_the_build_supplied(source):
    """Everything a build supplies is data, so the row crosses and comes back unrewritten."""
    got = source.records()
    assert got["core.clocks"] == [HARP_ROW]


def test_a_located_tick_zero_reaches_the_row_unchanged(asset):
    """A build that located tick 0 from the record nodes' stamps knows better than this JSON."""
    located = datetime(2024, 11, 27, 0, 53, 55, 855_000, tzinfo=UTC)
    source = session_source(asset, reference_clock={**HARP_ROW, "tick_zero_utc": located})
    assert source.records()["core.clocks"][0]["tick_zero_utc"] == located
    assert "aind.tick_zero_from_stream_start" not in source.compensations


def test_locating_tick_zero_here_is_recorded_as_a_compensation(source):
    """Where a caller has nothing better, this source derives it -- and says so."""
    source.epoch(FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ)
    assert "aind.tick_zero_from_stream_start" in source.compensations


def test_the_extent_spans_every_stream(source):
    """Acquisition is staggered, so the session ends when its last stream does."""
    start, stop = source.extent()
    windows = source.streams()
    assert start == min(w.start for w in windows) and stop == max(w.stop for w in windows)
    assert start.tzinfo is not None and stop > start


# -- calibrations --------------------------------------------------------------------

TRANSFORM = "behavior/calibration_info_np2_2025_04_09T10_00_00.npy"
CALIBRATED = "2025-04-09T10:00:00+00:00"

#: One `rig.json` water calibration, in the shape the two packaged sessions carry it: two
#: parallel lists under labels naming the quantity and its unit of measure.
WATER = {
    "device_name": "Lick spout Left",
    "calibration_date": "2024-11-27T00:00:00-08:00",
    "description": "Water calibration for Lick spout Left.",
    "input": {"valve open time (s):": [0.02, 0.03, 0.04]},
    "output": {"water volume (ul):": [2.35, 3.1, 4.0]},
    "notes": None,
}


def rig(asset, calibrations):
    (asset / "rig.json").write_text(json.dumps({"calibrations": calibrations}))
    return session_source(asset)


def modules(*names, transform=TRANSFORM, date=CALIBRATED):
    """One stream whose modules all cite one calibration, as six of them do in `ecephys_776259`."""
    return [
        {
            "stream_start_time": EPHYS_START,
            "stream_end_time": EPHYS_STOP,
            "ephys_modules": [
                {"assembly_name": n, "coordinate_transform": transform, "calibration_date": date} for n in names
            ],
        }
    ]


def test_a_water_calibration_becomes_a_row_with_both_units(asset):
    (row,) = rig(asset, [WATER]).calibrations()
    assert row["calibration_name"] == "Lick spout Left"
    assert (row["input_unit"], row["output_unit"]) == ("s", "ul")
    # Open (Part 02 §9.3): the type is what the source called the quantity it measured.
    assert row["calibration_type"] == "water_volume"
    assert row["calibrated_at"] == datetime(2024, 11, 27, 8, tzinfo=UTC)


def test_the_curve_becomes_points_in_the_order_stated(asset):
    points = rig(asset, [WATER]).calibration_points()
    assert [p["point_index"] for p in points] == [0, 1, 2]
    assert [p["input_value"] for p in points] == [0.02, 0.03, 0.04]
    assert [p["output_value"] for p in points] == [2.35, 3.1, 4.0]
    assert {p["calibration_id"] for p in points} == {"Lick spout Left"}


def test_a_series_with_unequal_sides_is_refused(asset):
    """A point needs both halves, and truncating one would invent a curve nothing measured."""
    lopsided = WATER | {"output": {"water volume (ul):": [2.35]}}
    with pytest.raises(SourceDefect) as refused:
        rig(asset, [lopsided]).calibration_points()
    assert refused.value.code is AindFault.CALIBRATION_MISALIGNED


def test_six_modules_citing_one_file_are_one_calibration(tmp_path):
    """A `device_id` on the calibration would record six where the rig performed one."""
    asset = session_asset(tmp_path, streams=modules("46100", "46122", "50209", "46113", "45883", "46116"))
    source = session_source(asset)
    (row,) = source.calibrations()
    assert row["calibration_type"] == "manipulator_transform"
    assert row["calibrated_at"] == datetime(2025, 4, 9, 10, tzinfo=UTC)
    covered = source.calibration_devices()
    assert [d["device_id"] for d in covered] == ["46100", "46122", "50209", "46113", "45883", "46116"]
    assert {d["calibration_id"] for d in covered} == {TRANSFORM}


def test_an_array_calibration_records_that_its_content_is_elsewhere(tmp_path):
    """Part 02 §12.3: this adapter does not read the `.npy`, so the row is unrecorded, not absent."""
    source = session_source(session_asset(tmp_path, streams=modules("46100")))
    (row,) = source.calibrations()
    assert (row["array_asset_id"], row["detail_kind"], row["metadata"]) == (None, None, None)
    assert source.calibration_points() == []


def test_a_module_stating_no_transform_yields_no_calibration(tmp_path):
    source = session_source(session_asset(tmp_path, streams=modules("46100", transform=None)))
    assert source.calibrations() == [] and source.calibration_devices() == []


def test_a_transform_with_no_date_is_null_rather_than_invented(tmp_path):
    """Part 01 §3.23. Three `stick_microscopes` state a calibration and no date for it."""
    source = session_source(session_asset(tmp_path, streams=modules("46100", date=None)))
    assert source.calibrations()[0]["calibrated_at"] is None


def test_an_asset_with_no_rig_document_states_no_calibration(source):
    """A packet holding none is conforming, so an absent file is not a defect."""
    assert source.calibrations() == [] and source.calibration_points() == []


def test_the_calibration_resources_are_omitted_when_empty(source):
    """A resource staged with no rows is a manifest entry the packet cannot answer for."""
    got = source.records()
    assert not [r for r in got if r.startswith("core.calibration")]


def test_the_calibration_resources_are_staged_when_present(tmp_path):
    asset = session_asset(tmp_path, streams=modules("46100", "46122"))
    source = rig(asset, [WATER])
    got = source.records()
    assert len(got["core.calibrations"]) == 2
    assert len(got["core.calibration_points"]) == 3
    assert len(got["core.calibration_devices"]) == 2
    assert source.offers() == {
        "core.clocks": 1,
        "core.calibrations": 2,
        "core.calibration_points": 3,
        "core.calibration_devices": 2,
    }


# -- prefix -----------------------------------------------------------------------------


def test_a_prefix_reaches_every_calibration_and_the_device_it_covers(tmp_path):
    """Each ID this source mints, and its name, carries the prefix; the clock and subject are given."""
    asset = session_asset(tmp_path, streams=modules("46100", "46122"))
    (asset / "rig.json").write_text(json.dumps({"calibrations": [WATER]}))
    got = session_source(asset, prefix="A_").records()
    assert [(c["calibration_id"], c["calibration_name"]) for c in got["core.calibrations"]] == [
        ("A_Lick spout Left", "A_Lick spout Left"),
        (f"A_{TRANSFORM}", f"A_{TRANSFORM}"),
    ]
    assert {p["calibration_id"] for p in got["core.calibration_points"]} == {"A_Lick spout Left"}
    assert [(d["calibration_id"], d["device_id"]) for d in got["core.calibration_devices"]] == [
        (f"A_{TRANSFORM}", "A_46100"),
        (f"A_{TRANSFORM}", "A_46122"),
    ]
    assert got["core.clocks"] == [HARP_ROW]


def test_a_calibrated_device_is_the_nwb_device_under_one_prefix(tmp_path):
    """The reference crosses sources, so it resolves only if both mint the device under one prefix."""
    from escapewheel_aind.nwb import AindNWBSource
    from tests import nwbfixture

    nwb = nwbfixture.build(tmp_path / "nwb")
    clock = {**HARP_ROW, "session_id": "mini_2025-04-09"}
    devices = AindNWBSource(nwb, reference_clock=clock, zone=PACIFIC, prefix="A_").devices()
    asset = session_asset(tmp_path, streams=modules("probeA"))
    (covered,) = session_source(asset, prefix="A_").calibration_devices()
    assert covered["device_id"] in {d["device_id"] for d in devices}
