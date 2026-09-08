"""The NWB adapter reads records, refuses guesses, and reports what it dropped."""

import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from escapewheel_reader import open_packet

from escapewheel_writer import Clock, OffGrid, PacketWriter
from escapewheel_writer.clock import HARP_TICK_RATE_HZ
from escapewheel_writer.sources import NWBSource, SourceDefect
from tests import nwbfixture

KIND = "task.trials"
TRIAL_EVENT_TYPES = {"go_cue", "reward_outcome"}
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
    return NWBSource(nwb, clock=harp, zone=PACIFIC, interval_kind=KIND)


@pytest.fixture
def carrying(nwb, harp):
    """A source asked to carry unmapped trial columns, which R54 §2.5 makes an opt-in."""
    return NWBSource(nwb, clock=harp, zone=PACIFIC, interval_kind=KIND, trial_metadata=True)


def only(rows, **match):
    found = [r for r in rows if all(r[k] == v for k, v in match.items())]
    assert len(found) == 1, f"{len(found)} rows match {match}"
    return found[0]


# -- what it reads -------------------------------------------------------------------


def _units(nwb, *, refuses=True):
    """A units table with one ragged column.

    `refuses` writes that column in an encoding this package will not decode, so that reading
    it would leave a note -- which is how a test sees that it was not read.
    """
    units = nwbfixture.group(nwb / "units", neurodata_type="Units", colnames=["spike_times"])
    nwbfixture.array(units / "id", np.array([0], dtype=np.int64))
    nwbfixture.array(units / "ks_unit_id", np.array([7], dtype=np.int64))
    nwbfixture.text(units / "device_name", ["probeA"])
    for axis in ("ccf_ml", "ccf_ap", "ccf_dv"):
        nwbfixture.array(units / axis, np.array([100.0]))
    if refuses:
        nwbfixture.array(units / "spike_times", ["<ref>"], filter_id="pickle")
    else:
        nwbfixture.array(units / "spike_times", np.array([0.1, 0.2, 0.3]))
    nwbfixture.array(units / "spike_times_index", np.array([3], dtype=np.int64))
    return {("probeA", "7"): {"unit_id": 1, "sorting_run_id": "run", "curation_id": "cur"}}


def test_a_ragged_column_is_not_read_with_its_table(nwb, harp):
    """`units/spike_times` is 287 M values against 6,781 rows, and no builder can use it as
    one: it is written here in an encoding that refuses, so reading it would leave a note."""
    units = _units(nwb)
    source = NWBSource(nwb, clock=harp, zone=PACIFIC, units=units, interval_kind=KIND)
    assert source.unit_coordinates() == [
        {
            "session_id": SESSION,
            "unit_id": 1,
            "sorting_run_id": "run",
            "curation_id": "cur",
            "coordinate_frame": "ccf",
            # R58 §2.1: an exported file records where the probe was found, never where it was
            # aimed, so an import can only assert `measured`.
            "coordinate_basis": "measured",
            "x_um": 100.0,
            "y_um": 100.0,
            "z_um": 100.0,
        }
    ]
    assert [note for note in source.notes if "spike_times" in note] == []


def test_the_index_beside_a_ragged_column_is_still_read(nwb, harp):
    """It is one value per row, which is what makes the column beside it ragged."""
    units = _units(nwb, refuses=False)
    source = NWBSource(nwb, clock=harp, zone=PACIFIC, units=units, interval_kind=KIND)
    columns = source._table("units")
    assert "spike_times" not in columns
    assert columns["spike_times_index"].tolist() == [3]


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
        "core.event_streams": 4,
        "core.events": 4,
        "core.intervals": 1,
    }


def test_it_emits_no_units_or_spikes(source):
    """Not an omission: §3.3 measured that this file's spike ticks are unrecoverable."""
    assert "core.units" not in source.records()
    assert "core.spike_events" not in source.records()


def test_it_does_not_offer_the_primary_electrode(source):
    """`extremum_channel_index` counts the channels the sorting kept, which the file never lists.

    Declaring it would let a recipe give this adapter ownership of a relation it can only guess
    at, and the guess is wrong by however many channels were dropped below the index.
    """
    assert "core.unit_electrodes" not in NWBSource.PRODUCES
    assert "core.unit_electrodes" not in source.records()


def test_the_asset_directory_is_accepted_as_well_as_the_nwb(tmp_path, harp):
    nwbfixture.build(tmp_path)
    assert NWBSource(tmp_path, clock=harp, zone=PACIFIC, interval_kind=KIND).session_id == SESSION


# -- time ----------------------------------------------------------------------------


def test_seconds_become_ticks_on_the_declared_clock(source):
    """R91 §3.1 puts the kind on the stream, so a tick is found through the stream that emits it."""
    records = source.records()
    kind = {s["event_stream_id"]: s["event_type"] for s in records["core.event_streams"]}
    events = records["core.events"]
    acquisition = [e["t_tick"] for e in events if kind[e["stream_id"]].endswith("lick")]
    assert acquisition == [31250, 62500]
    # The trial columns land on the same clock: 1.2 s and 1.5 s at 31,250 Hz.
    assert {kind[e["stream_id"]]: e["t_tick"] for e in events
            if kind[e["stream_id"]] in TRIAL_EVENT_TYPES} == {
        "go_cue": 37500,
        "reward_outcome": 46875,
    }


def test_a_clock_the_times_are_not_on_is_refused(tmp_path, harp):
    """What the grid check can and cannot catch.

    It discriminates on sub-tick structure, so whole seconds pass every integer-hertz clock
    and say nothing. Real timestamps are not whole seconds -- these are one and two HARP
    ticks -- and there a rate one hertz out is refused.
    """
    nwb = nwbfixture.build(tmp_path, seconds=(0.000032, 0.000064))
    ticks = [e["t_tick"] for e in NWBSource(nwb, clock=harp, zone=PACIFIC, interval_kind=KIND).records()["core.events"]]
    assert ticks[:2] == [1, 2]
    wrong = Clock("c", session_id=SESSION, name="c", tick_rate_num=31251, origin="e")
    with pytest.raises(OffGrid):
        NWBSource(nwb, clock=wrong, zone=PACIFIC, interval_kind=KIND).records()


def test_a_clock_from_another_session_is_refused(nwb):
    stray = Clock("c", session_id="other", name="c", tick_rate_num=HARP_TICK_RATE_HZ, origin="e")
    with pytest.raises(ValueError, match="belongs to session"):
        NWBSource(nwb, clock=stray, zone=PACIFIC, interval_kind=KIND)


def test_the_session_start_is_converted_to_utc(source):
    start = source.records()["core.sessions"][0]["session_start_time"]
    assert start.astimezone(timezone.utc) == datetime(2025, 4, 10, 0, 25, 12, tzinfo=timezone.utc)


def test_a_fixed_offset_is_not_a_zone(nwb, harp):
    with pytest.raises(TypeError, match="IANA zone"):
        NWBSource(nwb, clock=harp, zone=timezone.utc, interval_kind=KIND)


def test_a_stored_offset_that_disagrees_with_the_zone_is_reported(source):
    """The real file stamps -07:53 -- Pacific Local Mean Time -- on the date of birth."""
    source.records()
    assert any("-07:53" in note and "-07:00" in note for note in source.notes)


def test_a_naive_wall_clock_is_read_in_the_declared_zone(tmp_path, harp):
    nwb = nwbfixture.build(tmp_path, session_offset="")
    source = NWBSource(nwb, clock=harp, zone=PACIFIC, interval_kind=KIND)
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
    records = NWBSource(nwb, clock=harp, zone=PACIFIC, prefix="A_", interval_kind=KIND).records()
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


def test_an_interval_carries_its_bounds_and_names_its_kind(source):
    trial = source.records()["core.intervals"][0]
    assert (trial["start_tick"], trial["stop_tick"]) == (31250, 62500)
    assert trial["interval_kind"] == KIND


def test_a_task_column_is_not_a_core_column(source):
    """R54 §2.3 struck them: a task's shape is the extension's, not the format's."""
    trial = source.records()["core.intervals"][0]
    assert not {"choice", "rewarded", "condition_id", "stimulus_id"} & set(trial)


def test_unmapped_trial_columns_travel_as_metadata(carrying):
    carried = carrying.records()["core.intervals"][0]["metadata"]
    assert carried["reward_probabilityL"] == 0.4
    assert "start_time" not in carried  # mapped columns are not duplicated


def test_trial_metadata_is_off_unless_asked(source, carrying):
    """R54 §2.5: filling it routinely puts the extension's typed columns back into JSON."""
    assert "metadata" not in source.records()["core.intervals"][0]
    assert "metadata" in carrying.records()["core.intervals"][0]


def test_a_trial_without_an_interval_is_a_defect_not_a_dropped_row(tmp_path, harp):
    nwb = nwbfixture.build(tmp_path, trial_stop=np.nan)
    with pytest.raises(SourceDefect, match="stop_time"):
        NWBSource(nwb, clock=harp, zone=PACIFIC, interval_kind=KIND).records()


# -- end to end ----------------------------------------------------------------------


#: The minimum an interval kind needs to resolve: R54 §2.1 makes `interval_kind` resolve
#: `required`, so a packet carrying intervals and no table saying what they were is refused.
#: One table, one column, and the reference R55 §2.3.1 requires of a named resource.
TASK_EXTENSION = {
    "registry_version": "0.1.0",
    "logical_standard_version": "0.1",
    "extension_id": "task",
    "extends": "escapewheel-logical-v0.1",
    "tables": {
        "task.trials": {
            "columns": [
                {"name": "session_id", "type": "int32", "presence": "required",
                 "role": "identifier", "identity": "assigned"},
                {"name": "interval_kind", "type": "string", "presence": "required",
                 "role": "discriminator", "resolves": "required"},
                {"name": "interval_id", "type": "int32", "presence": "required",
                 "role": "identifier", "identity": "carried"},
            ],
            "primary_key": ["session_id", "interval_id"],
            "references": [{"columns": ["session_id", "interval_kind", "interval_id"],
                            "resource": "core.intervals",
                            "resource_columns": ["session_id", "interval_kind", "interval_id"]}],
            "sort": ["session_id", "interval_id"],
            "rules": [],
        }
    },
}


def test_the_records_commit_as_a_valid_packet(carrying, registry, tmp_path):
    # Carrying, because the assertions below are about how metadata survives the round trip --
    # verbatim, with NumPy's scalars coerced to JSON's. R54 §2.5 makes that an opt-in.
    source = carrying
    writer = PacketWriter(registry, packet_id=SESSION, extensions=[TASK_EXTENSION])
    counted = source.into(writer)
    writer.add("task.trials", [{"session_id": SESSION, "interval_kind": KIND,
                                "interval_id": t["interval_id"]}
                               for t in source.records()["core.intervals"]])
    report = writer.commit(tmp_path / "packet")
    assert report.passed, [f.check for f in report.findings]
    assert counted["core.electrodes"] == 2

    packet = open_packet(tmp_path / "packet")
    assert list(packet.sessions) == [SESSION]
    # R91 §3.2 keys and sorts events `(session_id, stream_id, t_tick)`, so ticks ascend within a
    # stream and not across them -- the layout a filter on one stream prunes.
    written = packet.table("core.events")
    assert sorted(written.column("t_tick").to_pylist()) == [31250, 37500, 46875, 62500]
    by_stream: dict[str, list[int]] = {}
    for stream, tick in zip(written.column("stream_id").to_pylist(),
                            written.column("t_tick").to_pylist(), strict=True):
        by_stream.setdefault(stream, []).append(tick)
    assert all(ticks == sorted(ticks) for ticks in by_stream.values())
    carried = json.loads(packet.table("core.intervals").column("metadata").to_pylist()[0])
    assert carried["auto_train_stage"] == "None"  # metadata is verbatim, not normalized
    # NumPy's integers and booleans are not Python's, and JSON knows only Python's.
    assert carried["laser_on_trial"] == 0
    assert carried["auto_train_engaged"] is False


def test_notes_do_not_grow_when_a_builder_is_called_twice(source):
    """`notes` describes the source, not how many times a caller read it."""
    source.events()
    once = list(source.notes)
    source.events()
    assert source.notes == once


# -- a moment recorded as a trial column is still an event ---------------------------------


def _stream_of(source, event_type):
    """The stream emitting one kind of event, which R91 §3.1 makes the stream's property."""
    return next(s["event_stream_id"] for s in source.event_streams()
                if s["event_type"] == event_type)


def test_trial_timing_columns_become_events(source):
    """A task writes the go cue into its trials table because it happens once a trial. It is
    still a moment on a clock, and a query should find it without knowing the task's shape.

    The kind is the stream's since R91 §3.1, so finding one means finding its stream."""
    kinds = {s["event_type"] for s in source.event_streams()}
    assert {"go_cue", "reward_outcome"} <= kinds
    emitting = {s["event_stream_id"] for s in source.event_streams()
                if s["event_type"] in {"go_cue", "reward_outcome"}}
    assert emitting <= {e["stream_id"] for e in source.events()}


def test_a_trial_event_does_not_name_its_interval(source):
    """R11 §5 struck the column; carrying it as JSON would keep the letter and lose the point."""
    go = next(e for e in source.events() if e["stream_id"] == _stream_of(source, "go_cue"))
    assert "payload" not in go or "trial_id" not in (go.get("payload") or {})
    assert go["stream_id"] in {s["event_stream_id"] for s in source.event_streams()}


def test_a_trial_event_is_on_the_declared_clock(source, harp):
    """R91 §3.2 struck `core.events.clock_id`: the tick is on the clock its stream declares."""
    stream = _stream_of(source, "go_cue")
    go = next(e for e in source.events() if e["stream_id"] == stream)
    assert "clock_id" not in go
    assert next(s for s in source.event_streams()
                if s["event_stream_id"] == stream)["clock_id"] == harp.clock_id
    assert go["t_tick"] == harp.ticks(np.array([1.2]))[0]


def test_a_trial_that_never_reached_the_moment_emits_no_event(tmp_path, harp):
    """Absence is a fact about the trial, not a null to carry -- which is why these are events
    rather than columns on `core.trials`."""
    root = nwbfixture.build(tmp_path)
    nwbfixture.array(root / "intervals/trials/goCue_start_time", np.array([np.nan]))
    source = NWBSource(root, clock=harp, zone=PACIFIC, session_id=SESSION, units={})
    assert not [e for e in source.events() if e["stream_id"] == _stream_of(source, "go_cue")]
    assert "go_cue" in {s["name"] for s in source.event_streams()}


def test_a_condition_is_named_where_the_task_varies_one(source):
    """A foraging session has no stimulus; what it varies is the reward probability pair."""
    assert {t.get("condition_id") for t in source.intervals()} == {None}, "one trial cannot vary"



def test_a_trial_event_column_is_not_repeated_in_metadata(source):
    """It is in core.events now, so carrying it again would be the duplication R3 §3.0 bans."""
    metadata = next(t for t in source.intervals()).get("metadata") or {}
    assert "goCue_start_time" not in metadata


# -- R3 §3.0: a parameter constant across every trial is recorded once ----------------------


def _split(source, columns, n):
    """Ask the adapter which of these columns vary across `n` trials."""
    varying = source._trial_parameters(columns, list(columns), n)
    return varying, source._constants


def test_a_constant_trial_column_moves_to_the_session(source):
    columns = {
        "laser_wavelength": np.array([473.0, 473.0, 473.0]),
        "reward_probabilityL": np.array([0.4, 0.7, 0.4]),
    }
    varying, constant = _split(source, columns, 3)
    assert varying == ["reward_probabilityL"]
    assert constant == {"laser_wavelength": 473.0}


def test_an_all_nan_column_is_constant_not_varying(source):
    """`nan != nan` would make every absent parameter look like per-trial data."""
    varying, constant = _split(source, {"unset": np.array([np.nan, np.nan])}, 2)
    assert varying == []
    assert "unset" in constant


def test_one_trial_splits_nothing(source):
    """One value is no evidence that a parameter never changes."""
    varying, constant = _split(source, {"laser_wavelength": np.array([473.0])}, 1)
    assert varying == ["laser_wavelength"]
    assert constant == {}


def test_the_session_carries_what_the_trials_no_longer_repeat(source, carrying):
    """The two halves agree: nothing is dropped between them."""
    session = source.sessions()[0]["metadata"]
    trial = carrying.records()["core.intervals"][0].get("metadata", {})
    assert not (set(session) & set(trial)), "a key is on the session or on the trial, never both"
    assert "auto_train_stage" in session or "auto_train_stage" in trial
