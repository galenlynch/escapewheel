"""The NWB adapter reads records, refuses guesses, and reports what it dropped."""

import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from nwb_lake_reader import open_packet

from nwb_lake_writer import Clock, OffGrid, PacketWriter
from nwb_lake_writer.clock import HARP_TICK_RATE_HZ
from nwb_lake_writer.sources import NWBSource, SourceDefect
from tests import nwbfixture

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
    return NWBSource(nwb, clock=harp, zone=PACIFIC)


def only(rows, **match):
    found = [r for r in rows if all(r[k] == v for k, v in match.items())]
    assert len(found) == 1, f"{len(found)} rows match {match}"
    return found[0]


# -- what it reads -------------------------------------------------------------------


def test_it_reads_the_tables_the_nwb_is_the_authority_for(source):
    counts = {resource: len(rows) for resource, rows in source.records().items()}
    assert counts == {
        "core.subjects": 1,
        "core.sessions": 1,
        "core.clocks": 1,
        "core.devices": 1,
        "core.probes": 1,
        "core.electrodes": 2,
        "core.electrode_coordinates": 3,  # both electrodes in the probe frame, one in CCF
        "core.event_streams": 2,
        "core.events": 2,
        "core.trials": 1,
    }


def test_it_emits_no_units_or_spikes(source):
    """Not an omission: §3.3 measured that this file's spike ticks are unrecoverable."""
    assert "core.units" not in source.records()
    assert "core.spike_events" not in source.records()


def test_the_asset_directory_is_accepted_as_well_as_the_nwb(tmp_path, harp):
    nwbfixture.build(tmp_path)
    assert NWBSource(tmp_path, clock=harp, zone=PACIFIC).session_id == SESSION


# -- time ----------------------------------------------------------------------------


def test_seconds_become_ticks_on_the_declared_clock(source):
    assert [e["t_tick"] for e in source.records()["core.events"]] == [31250, 62500]


def test_a_clock_the_times_are_not_on_is_refused(tmp_path, harp):
    """What the grid check can and cannot catch.

    It discriminates on sub-tick structure, so whole seconds pass every integer-hertz clock
    and say nothing. Real timestamps are not whole seconds -- these are one and two HARP
    ticks -- and there a rate one hertz out is refused.
    """
    nwb = nwbfixture.build(tmp_path, seconds=(0.000032, 0.000064))
    assert [e["t_tick"] for e in NWBSource(nwb, clock=harp, zone=PACIFIC).records()["core.events"]] == [1, 2]
    wrong = Clock("c", session_id=SESSION, name="c", tick_rate_num=31251, origin="e")
    with pytest.raises(OffGrid):
        NWBSource(nwb, clock=wrong, zone=PACIFIC).records()


def test_a_clock_from_another_session_is_refused(nwb):
    stray = Clock("c", session_id="other", name="c", tick_rate_num=HARP_TICK_RATE_HZ, origin="e")
    with pytest.raises(ValueError, match="belongs to session"):
        NWBSource(nwb, clock=stray, zone=PACIFIC)


def test_the_session_start_is_converted_to_utc(source):
    start = source.records()["core.sessions"][0]["session_start_time"]
    assert start.astimezone(timezone.utc) == datetime(2025, 4, 10, 0, 25, 12, tzinfo=timezone.utc)


def test_a_fixed_offset_is_not_a_zone(nwb, harp):
    with pytest.raises(TypeError, match="IANA zone"):
        NWBSource(nwb, clock=harp, zone=timezone.utc)


def test_a_stored_offset_that_disagrees_with_the_zone_is_reported(source):
    """The real file stamps -07:53 -- Pacific Local Mean Time -- on the date of birth."""
    source.records()
    assert any("-07:53" in note and "-07:00" in note for note in source.notes)


def test_a_naive_wall_clock_is_read_in_the_declared_zone(tmp_path, harp):
    nwb = nwbfixture.build(tmp_path, session_offset="")
    source = NWBSource(nwb, clock=harp, zone=PACIFIC)
    assert source.records()["core.sessions"][0]["session_start_time"].utcoffset().total_seconds() == -7 * 3600
    assert any("no offset stored" in note for note in source.notes)


def test_a_date_of_birth_is_the_local_calendar_date(source):
    """Converting a date through UTC could move it by a day; the written date is the fact."""
    assert source.records()["core.subjects"][0]["date_of_birth"] == date(2024, 9, 24)


# -- what it will not decode ---------------------------------------------------------


def test_the_pickled_column_is_skipped_and_reported(source):
    source.records()
    assert any("group: not read" in note and "pickled" in note for note in source.notes)


def test_the_pickled_column_costs_nothing(source):
    """`group_name` carries the same fact, so the probe link survives without unpickling."""
    assert {e["probe_id"] for e in source.records()["core.electrodes"]} == {"probeA"}


def test_a_placeholder_stream_keeps_its_stream_and_loses_its_nan(source):
    records = source.records()
    assert only(records["core.event_streams"], event_stream_id="FIP_rising_time")
    assert not [e for e in records["core.events"] if e["stream_id"] == "FIP_rising_time"]
    assert any("FIP_rising_time" in note and "not finite" in note for note in source.notes)


def test_notes_are_not_repeated_when_a_table_is_read_by_two_builders(source):
    source.records()
    assert len(source.notes) == len(set(source.notes))


# -- identity ------------------------------------------------------------------------


def test_electrode_ids_are_composed_because_no_single_column_is_unique(source):
    """`electrode_name` repeats across the shanks of a quad-base probe; (group, channel) does not."""
    electrodes = source.records()["core.electrodes"]
    assert [e["local_electrode_label"] for e in electrodes] == ["e0", "e0"]
    assert sorted(e["electrode_id"] for e in electrodes) == ["probeA.CH0", "probeA.CH1"]


def test_a_prefix_disambiguates_ids_for_a_multi_session_packet(nwb, harp):
    records = NWBSource(nwb, clock=harp, zone=PACIFIC, prefix="A_").records()
    assert records["core.electrodes"][0]["electrode_id"].startswith("A_probeA.")
    assert records["core.probes"][0]["probe_id"] == "A_probeA"


def test_the_probe_takes_its_model_and_serial_from_the_linked_device(source):
    probe = source.records()["core.probes"][0]
    assert (probe["probe_type"], probe["serial_number"], probe["manufacturer"]) == (
        "Neuropixels 2.0 - Quad Base",
        "12345",
        "IMEC",
    )
    assert probe["target_region"] == "CA1"


# -- coordinates ---------------------------------------------------------------------


def test_coordinates_are_rows_per_frame_not_a_padded_triple(source):
    coordinates = source.records()["core.electrode_coordinates"]
    assert only(coordinates, electrode_id="probeA.CH1", coordinate_frame="probe")["x_um"] == 32.0
    ccf = only(coordinates, electrode_id="probeA.CH0", coordinate_frame="ccf")
    # R19 §3 fixes the order: CCF ml, ap, dv occupy x, y, z.
    assert (ccf["x_um"], ccf["y_um"], ccf["z_um"]) == (100.0, 200.0, 300.0)


def test_an_unregistered_electrode_gets_no_ccf_row(source):
    """An absent frame is an absent row, which is the whole point of R19's shape."""
    assert not [
        c
        for c in source.records()["core.electrode_coordinates"]
        if c["electrode_id"] == "probeA.CH1" and c["coordinate_frame"] == "ccf"
    ]


# -- trials --------------------------------------------------------------------------


def test_a_trial_carries_its_interval_choice_and_reward(source):
    trial = source.records()["core.trials"][0]
    assert (trial["start_tick"], trial["stop_tick"]) == (31250, 62500)
    assert (trial["choice"], trial["rewarded"]) == ("right", True)


def test_unmapped_trial_columns_travel_as_metadata(source):
    carried = source.records()["core.trials"][0]["metadata"]
    assert carried["reward_probabilityL"] == 0.4
    assert "start_time" not in carried  # mapped columns are not duplicated


def test_trial_metadata_can_be_declined(nwb, harp):
    records = NWBSource(nwb, clock=harp, zone=PACIFIC, trial_metadata=False).records()
    assert "metadata" not in records["core.trials"][0]


def test_a_trial_without_an_interval_is_a_defect_not_a_dropped_row(tmp_path, harp):
    nwb = nwbfixture.build(tmp_path, trial_stop=np.nan)
    with pytest.raises(SourceDefect, match="stop_time"):
        NWBSource(nwb, clock=harp, zone=PACIFIC).records()


# -- end to end ----------------------------------------------------------------------


def test_the_records_commit_as_a_valid_packet(source, registry, tmp_path):
    writer = PacketWriter(registry, packet_id=SESSION)
    counted = source.into(writer)
    report = writer.commit(tmp_path / "packet")
    assert report.passed, [f.check for f in report.findings]
    assert counted["core.electrodes"] == 2

    packet = open_packet(tmp_path / "packet")
    assert list(packet.sessions) == [SESSION]
    assert packet.table("core.events").column("t_tick").to_pylist() == [31250, 62500]
    carried = json.loads(packet.table("core.trials").column("metadata").to_pylist()[0])
    assert carried["auto_train_stage"] == "None"  # metadata is verbatim, not normalized
    # NumPy's integers and booleans are not Python's, and JSON knows only Python's.
    assert carried["laser_on_trial"] == 0
    assert carried["auto_train_engaged"] is False
