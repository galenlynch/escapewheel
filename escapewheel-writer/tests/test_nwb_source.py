"""The NWB adapter reads records, refuses guesses, and reports what it dropped."""

import json
import shutil
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from escapewheel_reader import open_packet

from escapewheel_writer import Clock, OffGrid, PacketWriter
from escapewheel_writer.clock import HARP_TICK_RATE_HZ
from escapewheel_writer.sources import NWBSource, SourceDefect
from escapewheel_writer.sources.nwb import _sex, ucum_code
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
    return NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND)


@pytest.fixture
def carrying(nwb, harp):
    """A source asked to carry unmapped trial columns, which Part 02 §6 makes an opt-in."""
    return NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND, trial_metadata=True)


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
    if refuses:
        nwbfixture.array(units / "spike_times", ["<ref>"], filter_id="pickle")
    else:
        nwbfixture.array(units / "spike_times", np.array([0.1, 0.2, 0.3]))
    nwbfixture.array(units / "spike_times_index", np.array([3], dtype=np.int64))


def test_a_ragged_column_is_not_read_with_its_table(nwb, harp):
    """`units/spike_times` is 287 M values against 6,781 rows, and no builder can use it as
    one: it is written here in an encoding that refuses, so reading it would leave a note."""
    _units(nwb)
    source = NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND)
    source.records()
    assert [note for note in source.notes if "spike_times" in note] == []


def test_the_index_beside_a_ragged_column_is_still_read(nwb, harp):
    """It is one value per row, which is what makes the column beside it ragged."""
    _units(nwb, refuses=False)
    source = NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND)
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
        # One frame, because `rel_x` and `rel_y` are the only axes core 2.9.0 declares. An atlas
        # triple is a producer's addition and reaches a packet through a dialect.
        "core.electrode_coordinates": 2,
        # Part 01 §3.8: the same positions as one row per axis, two shank axes each.
        "core.electrode_coordinate_values": 4,
        "core.coordinate_frames": 1,
        "core.coordinate_frame_axes": 2,
        # The two acquisition streams. A trial column carrying a moment is this task's, so no
        # stream here comes from `intervals/trials`.
        "core.event_streams": 2,
        "core.events": 2,
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
    assert NWBSource(tmp_path, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND).session_id == SESSION


# -- time ----------------------------------------------------------------------------


def test_seconds_become_ticks_on_the_declared_clock(source):
    """R91 §3.1 puts the kind on the stream, so a tick is found through the stream that emits it."""
    records = source.records()
    kind = {s["event_stream_id"]: s["event_type"] for s in records["core.event_streams"]}
    events = records["core.events"]
    acquisition = [e["t_tick"] for e in events if kind[e["stream_id"]].endswith("lick")]
    assert acquisition == [31250, 62500]


def test_a_clock_the_times_are_not_on_is_refused(tmp_path, harp):
    """What the grid check can and cannot catch.

    It discriminates on sub-tick structure, so whole seconds pass every integer-hertz clock
    and say nothing. Real timestamps are not whole seconds -- these are one and two HARP
    ticks -- and there a rate one hertz out is refused.
    """
    nwb = nwbfixture.build(tmp_path, seconds=(0.000032, 0.000064))
    source = NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND)
    ticks = [e["t_tick"] for e in source.records()["core.events"]]
    assert ticks[:2] == [1, 2]
    wrong = Clock("c", session_id=SESSION, name="c", tick_rate_num=31251, origin="e")
    with pytest.raises(OffGrid):
        NWBSource(nwb, reference_clock=wrong.record(), zone=PACIFIC, interval_kind=KIND).records()


def test_a_clock_from_another_session_is_refused(nwb):
    stray = Clock("c", session_id="other", name="c", tick_rate_num=HARP_TICK_RATE_HZ, origin="e")
    with pytest.raises(ValueError, match="belongs to session"):
        NWBSource(nwb, reference_clock=stray.record(), zone=PACIFIC, interval_kind=KIND)


def test_the_session_start_is_converted_to_utc(source):
    start = source.records()["core.sessions"][0]["session_start_time"]
    assert start.astimezone(timezone.utc) == datetime(2025, 4, 10, 0, 25, 12, tzinfo=timezone.utc)


def test_a_fixed_offset_is_not_a_zone(nwb, harp):
    with pytest.raises(TypeError, match="IANA zone"):
        NWBSource(nwb, reference_clock=harp.record(), zone=timezone.utc, interval_kind=KIND)


def test_a_zone_is_accepted_as_the_name_a_recipe_wrote(nwb, harp):
    """An option crosses to an adapter as data (Part 12 §4), so a zone arrives as a string.

    The adapter used to require a `ZoneInfo` and the build's per-kind branch converted on the way
    in; once every source was constructed from its declaration the conversion had nowhere to live,
    and a real recipe failed on its own `zone` where every fixture passed an object.
    """
    named = NWBSource(nwb, reference_clock=harp.record(), zone=str(PACIFIC), interval_kind=KIND)
    assert named.zone == PACIFIC


def test_a_stored_offset_that_disagrees_with_the_zone_is_reported(source):
    """The real file stamps -07:53 -- Pacific Local Mean Time -- on the date of birth."""
    source.records()
    assert any("-07:53" in note and "-07:00" in note for note in source.notes)


def test_a_naive_wall_clock_is_read_in_the_declared_zone(tmp_path, harp):
    nwb = nwbfixture.build(tmp_path, session_offset="")
    source = NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND)
    assert source.records()["core.sessions"][0]["session_start_time"].utcoffset().total_seconds() == -7 * 3600
    assert any("no offset stored" in note for note in source.notes)


def test_a_date_of_birth_is_the_local_calendar_date(source):
    """Converting a date through UTC could move it by a day; the written date is the fact."""
    assert source.records()["core.subjects"][0]["date_of_birth"] == date(2024, 9, 24)


def test_a_subjects_sex_lands_inside_the_closed_vocabulary(source):
    """Part 02 §9.3 closes `sex` to four values, and a source states its own spelling.

    Both packaged sessions state `Male`, which reached a committed packet verbatim and is outside
    the set, so the mapping is what stands between a source's spelling and a Tier 1 failure.
    """
    assert source.records()["core.subjects"][0]["sex"] == "male"
    assert [_sex(v) for v in ("M", "Male", "male", "F", "Female", "H", "O")] == [
        "male",
        "male",
        "male",
        "female",
        "female",
        "hermaphrodite",
        "other",
    ]
    # `U` is unknown, and Part 02 §9.3 makes that a null rather than `other`: recording it as `other`
    # asserts a sex the source never claimed, where a null says the source did not say.
    assert [_sex(v) for v in ("U", "unknown", "", None)] == [None, None, None, None]


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
    """`group_name` repeats down a probe and `channel_name` restarts per probe; the pair does not."""
    electrodes = source.records()["core.electrodes"]
    assert sorted(e["electrode_id"] for e in electrodes) == ["probeA.CH0", "probeA.CH1"]
    # Base NWB names a contact's group and nothing else, so there is no label left to carry.
    assert [e["local_electrode_label"] for e in electrodes] == [None, None]
    assert [e["local_channel_label"] for e in electrodes] == ["CH0", "CH1"]


def test_a_contact_falls_back_to_its_row_id_where_the_file_names_no_channel(tmp_path, harp):
    """`channel_name` is the ecosystem's convention, not the schema's, so it can be absent.

    Every `DynamicTable` has an `id`, so the pair is always available; what it loses is the
    source's own spelling, which `local_channel_label` then has nothing to carry.
    """
    root = nwbfixture.build(tmp_path)
    shutil.rmtree(root / "general/extracellular_ephys/electrodes/channel_name")
    source = NWBSource(root, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND)
    electrodes = source.records()["core.electrodes"]
    assert sorted(e["electrode_id"] for e in electrodes) == ["probeA.0", "probeA.1"]
    assert [e["local_channel_label"] for e in electrodes] == [None, None]
    assert any("no channel_name" in note for note in source.notes)


def test_a_prefix_disambiguates_ids_for_a_multi_session_packet(nwb, harp):
    records = NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, prefix="A_", interval_kind=KIND).records()
    assert records["core.electrodes"][0]["electrode_id"].startswith("A_probeA.")
    assert records["core.probes"][0]["probe_id"] == "A_probeA"


def _more_devices(nwb):
    """Add a Device with no serial and two sharing one, each recorded by its own group.

    The first reaches its probe only by name and the pair only by serial, so together they exercise
    both halves of the lookup a probe finds its device through.
    """
    devices, ephys = nwb / "general/devices", nwb / "general/extracellular_ephys"
    for name, serial in (("probeB", None), ("probeC-1", "999"), ("probeC-2", "999")):
        stated = {"serial_number": serial} if serial else {}
        nwbfixture.group(devices / name, neurodata_type="Device", manufacturer="IMEC", **stated)
        nwbfixture.group(
            ephys / name,
            neurodata_type="ElectrodeGroup",
            location="CA1",
            zarr_link=[{"name": "device", "path": f"/general/devices/{name}", "source": "."}],
        )


def test_a_name_carries_the_prefix_its_identifier_does(nwb, harp):
    """R53 §2.5 and R85: a name is the string its identifier is minted from, so it is unique in a
    packet holding two sessions under different prefixes only if it carries the prefix too."""
    _more_devices(nwb)
    records = NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, prefix="A_", interval_kind=KIND).records()
    for stem in ("device", "probe", "event_stream"):
        rows = records[f"core.{stem}s"]
        assert rows, stem
        assert [r[f"{stem}_name"] for r in rows] == [r[f"{stem}_id"] for r in rows]
        assert all(r[f"{stem}_id"].startswith("A_") for r in rows)
    assert "A_probeC" in {d["device_name"] for d in records["core.devices"]}


def test_a_probe_finds_its_device_under_a_prefix(nwb, harp):
    """By serial where the Device states one and by name where it does not, both prefixed."""
    _more_devices(nwb)
    records = NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, prefix="A_", interval_kind=KIND).records()
    attached = {p["probe_id"]: p["device_id"] for p in records["core.probes"]}
    assert attached == {
        "A_probeA": "A_probeA",
        "A_probeB": "A_probeB",
        "A_probeC-1": "A_probeC",
        "A_probeC-2": "A_probeC",
    }
    assert set(attached.values()) == {d["device_id"] for d in records["core.devices"]}


#: One probe, `probeA`, on the headstage in slot 3 port 2, docked at 1.
SETTINGS = """<SETTINGS><NP_PROBE slot="3" port="2" dock="1" custom_probe_name="probeA"
  bs_part_number="NP2_QBSC" bsc_part_number="NP2_CONN" headstage_part_number="NPM_HS_30"/></SETTINGS>"""


def test_a_probe_attaches_to_the_headstage_under_the_same_prefix(nwb, harp, tmp_path):
    """The headstage row is the acquisition source's, so the link resolves only if both carry the prefix."""
    from escapewheel_writer.sources import OpenEphysSource

    settings = tmp_path / "settings.xml"
    settings.write_text(SETTINGS)
    source = NWBSource(
        nwb, reference_clock=harp.record(), zone=PACIFIC, prefix="A_", interval_kind=KIND, attachments=settings
    )
    (device,) = source.records()["core.devices"]
    assert (device["parent_device_id"], device["parent_port"]) == ("A_headstage.slot3.port2", "1")
    chain = OpenEphysSource(settings, session_id=source.session_id, prefix="A_").devices()
    assert device["parent_device_id"] in {row["device_id"] for row in chain}


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
    values = source.records()["core.electrode_coordinate_values"]
    on_shank = [v for v in values if v["electrode_id"] == "probeA.CH1" and v["coordinate_frame"] == "probe"]
    assert [(v["axis_index"], v["axis_value"]) for v in on_shank] == [(0, 32.0), (1, 0.0)]
    assert {v["coordinate_frame"] for v in values} == {"probe"}


def test_a_frame_declares_its_axes_by_the_names_it_read_them_from(source):
    """Part 01 §3.24: the source's column name becomes a value, verbatim and undirected."""
    axes = source.records()["core.coordinate_frame_axes"]
    assert [(a["coordinate_frame"], a["axis_index"], a["axis_name"]) for a in axes] == [
        ("probe", 0, "rel_x"),
        ("probe", 1, "rel_y"),
    ]
    assert {a["axis_direction"] for a in axes} == {None}
    assert {a["unit"] for a in axes} == {"um"}
    # Part 01 §3.24: no artifact of these sessions names the atlas, so neither column is filled.
    frames = source.records()["core.coordinate_frames"]
    assert {(f["atlas"], f["atlas_version"]) for f in frames} == {(None, None)}


def test_an_electrodes_bag_is_empty_where_every_column_is_mapped(source):
    """Part 02 §8.6: only what no column holds may travel in the bag, and base NWB leaves nothing."""
    assert only(source.records()["core.electrodes"], electrode_id="probeA.CH0")["metadata"] is None


# -- trials --------------------------------------------------------------------------


def test_an_interval_carries_its_bounds_and_names_its_kind(source):
    trial = source.records()["core.intervals"][0]
    assert (trial["start_tick"], trial["stop_tick"]) == (31250, 62500)
    assert trial["interval_kind"] == KIND


def test_the_nwb_id_is_a_label_and_the_name_is_unique_in_the_packet(source):
    """Part 02 §12.9: the NWB numbers only its trials, so its `id` labels an interval and does not identify one."""
    trial = source.records()["core.intervals"][0]
    assert trial["local_interval_label"] == "0"
    assert trial["interval_id"] == f"{SESSION}/{KIND}/0"


def test_a_task_column_is_not_a_core_column(source):
    """R54 §2.3 struck them: a task's shape is the extension's, not the format's."""
    trial = source.records()["core.intervals"][0]
    assert not {"choice", "rewarded", "condition_id", "stimulus_id"} & set(trial)


def test_unmapped_trial_columns_travel_as_metadata(carrying):
    carried = carrying.records()["core.intervals"][0]["metadata"]
    assert carried["reward_probabilityL"] == 0.4
    assert "start_time" not in carried  # mapped columns are not duplicated


def test_trial_metadata_is_off_unless_asked(source, carrying):
    """Part 02 §6: filling it routinely puts the extension's typed columns back into JSON."""
    assert "metadata" not in source.records()["core.intervals"][0]
    assert "metadata" in carrying.records()["core.intervals"][0]


def test_a_trial_without_an_interval_is_a_defect_not_a_dropped_row(tmp_path, harp):
    nwb = nwbfixture.build(tmp_path, trial_stop=np.nan)
    with pytest.raises(SourceDefect, match="stop_time"):
        NWBSource(nwb, reference_clock=harp.record(), zone=PACIFIC, interval_kind=KIND).records()


# -- end to end ----------------------------------------------------------------------


#: The minimum an interval kind needs to resolve: Part 01 §3.10 makes `interval_kind` resolve
#: `required`, so a packet carrying intervals and no table saying what they were is refused.
#: One table, one column, and the reference Part 02 §8.3 requires of a named resource.
TASK_EXTENSION = {
    "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
    "registry_id": "task",
    "registry_version": "0.1.0",
    "logical_standard_version": "escapewheel-logical-v0.1",
    "rule_language": "escapewheel-rule-sql-v0.2",
    "extension_id": "task",
    "resources": {
        "task.trials": {
            "content_class": "extension",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {
                "columns": [
                    {
                        "name": "session_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "Session identity.",
                    },
                    {
                        "name": "trial_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "The trial, and the interval it occupies in core.",
                    },
                ],
                "primary_key": ["trial_id"],
                "amendment_groups": [["trial_id"]],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                    {
                        "columns": ["trial_id"],
                        "resource": "core.intervals",
                        "resource_columns": ["interval_id"],
                        "specialises": "core.intervals.interval_kind",
                    },
                ],
                "rules": [],
            },
        }
    },
}


def test_the_records_commit_as_a_valid_packet(carrying, registry, tmp_path):
    # Carrying, because the assertions below are about how metadata survives the round trip --
    # verbatim, with NumPy's scalars coerced to JSON's. Part 02 §6 makes that an opt-in.
    source = carrying
    writer = PacketWriter(registry, packet_id=SESSION, extensions=[TASK_EXTENSION])
    counted = source.into(writer)
    writer.add(
        "task.trials",
        [
            {"session_id": SESSION, "trial_id": t["interval_id"]}
            for t in source.records()["core.intervals"]
        ],
    )
    report = writer.commit(tmp_path / "packet")
    assert report.passed, [f.check for f in report.findings]
    assert counted["core.electrodes"] == 2

    packet = open_packet(tmp_path / "packet")
    assert list(packet.sessions) == [SESSION]
    # R91 §3.2 keys and sorts events `(session_id, stream_id, t_tick)`, so ticks ascend within a
    # stream and not across them -- the layout a filter on one stream prunes.
    written = packet.table("core.events")
    assert sorted(written.column("t_tick").to_pylist()) == [31250, 62500]
    by_stream: dict[str, list[int]] = {}
    for stream, tick in zip(written.column("stream_id").to_pylist(), written.column("t_tick").to_pylist(), strict=True):
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


# -- trial columns a base reader does not interpret ----------------------------------------


def test_no_stream_comes_from_a_trial_column(source):
    """`TimeIntervals` declares `start_time`, `stop_time` and tags, so every other column is a
    task's own. A moment recorded in one is still an event, and naming which columns those are
    takes a dialect."""
    assert {s["event_stream_name"] for s in source.event_streams()} == {
        "left_lick_time",
        "FIP_rising_time",
    }


def test_a_condition_is_named_where_the_task_varies_one(source):
    """A foraging session has no stimulus; what it varies is the reward probability pair."""
    assert {t.get("condition_id") for t in source.intervals()} == {None}, "one trial cannot vary"


# -- Part 02 §6: a parameter constant across every trial is recorded once ----------------------


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


@pytest.mark.parametrize(("stated", "code"), [("volts", "V"), ("uV", "uV"), ("furlongs", "furlongs"), (None, None)])
def test_an_nwb_unit_is_mapped_to_ucum_or_left_for_validation(stated, code):
    """Part 02 §8.4. An unlisted spelling passes through, so validation rejects it visibly."""
    assert ucum_code(stated) == code
