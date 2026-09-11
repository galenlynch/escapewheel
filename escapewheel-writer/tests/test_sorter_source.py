"""The sorter adapter carries the ticks, and must not confuse an offset for an identifier."""

import numpy as np
import pytest

from escapewheel_writer.sources import SorterSource, SourceDefect
from escapewheel_writer.sources.sorter import PROJECTION
from tests import sorterfixture

SESSION = "ecephys_837772_2026-06-27_14-08-21"
SHANK1 = "experiment1.Neuropix-PXI-100.50720-1"
SHANK2 = "experiment1.Neuropix-PXI-100.50720-2"


def named(label, run=SHANK1):
    """The name the adapter composes for one unit, which the writer turns into its number.

    Part 02 §12.1 orders the numbering by `(sorting_run_id, curation_id, local_unit_label)`, so the
    name is those three and the run is part of it rather than a column beside it.
    """
    return f"{run}|{run}.curated|{label:02d}"


def keyed(rows, label, run=SHANK1):
    """Rows for one unit, which `unit_id` alone now identifies (R81 §2.1)."""
    return [r for r in rows if r["unit_id"] == named(label, run)]


@pytest.fixture
def asset(tmp_path):
    return sorterfixture.build(tmp_path)


@pytest.fixture
def source(asset):
    return SorterSource(asset, session_id=SESSION, experiment="experiment1")


def rows_of(source, resource):
    return source.records()[resource]


# -- what a stream is ----------------------------------------------------------------


def test_it_accepts_the_asset_or_the_curated_directory(asset):
    assert SorterSource(asset, session_id=SESSION).streams()
    assert SorterSource(asset / "curated", session_id=SESSION).streams()


def test_a_tree_without_curated_is_a_defect(tmp_path):
    with pytest.raises(SourceDefect, match="holds no curated/"):
        SorterSource(tmp_path, session_id=SESSION)


def test_an_experiment_selects_its_own_streams(asset):
    assert len(SorterSource(asset, session_id=SESSION, experiment="experiment1").streams()) == 2
    assert len(SorterSource(asset, session_id=SESSION).streams()) == 3


def test_an_absent_experiment_is_a_defect(asset):
    with pytest.raises(SourceDefect, match="no streams for experiment"):
        SorterSource(asset, session_id=SESSION, experiment="experiment9").streams()


def test_a_shank_keeps_its_stream_and_shares_a_serial(source):
    one, two = source.streams()
    assert (one.probe, two.probe) == ("Neuropix-PXI-100.50720-1", "Neuropix-PXI-100.50720-2")
    assert one.serial == two.serial == "Neuropix-PXI-100.50720"


def test_quad_base_shanks_are_separate_probes(source):
    """Each shank stream is its own logical probe, and one serial ties them together.

    SpikeInterface sorts each shank separately -- four unit-id spaces that each start at 0 --
    and an NWB writes one electrode group per shank, so `probe_id` follows the shank. The
    physical device is recovered from `serial_number` rather than by parsing an identifier.
    Part 01 §3.5 admits both: several recording entities from one physical object are each a
    Probe, and all name the same Device.
    """
    probes = rows_of(source, "core.probes")
    assert len(probes) == 2
    assert len({p["serial_number"] for p in probes}) == 1
    assert len(rows_of(source, "core.clocks")) == 2
    assert len(rows_of(source, "core.sorting_runs")) == 2


# -- the offset that is not an identifier --------------------------------------------


def test_unit_index_is_resolved_through_unit_ids(source):
    """`unit_ids` has a gap, so offset 3 is unit 5. Storing the offset would be wrong here."""
    labels = [u["local_unit_label"] for u in rows_of(source, "core.units") if u["sorting_run_id"] == SHANK1]
    assert labels == ["0", "1", "2", "5", "12", "40"]


def test_a_unit_name_is_unique_across_runs(source):
    """R81 §1.2: the sorter numbers from zero in each run, so its label names two units.

    Both streams carry every label in the fixture, and the packet keys on `unit_id` alone --
    which works only because what the adapter hands the writer is the run, the curation and the
    label together, giving twelve names where the labels give six.
    """
    units = rows_of(source, "core.units")
    assert len({u["local_unit_label"] for u in units}) == len(sorterfixture.UNIT_IDS) == 6
    assert len({u["unit_id"] for u in units}) == 2 * len(sorterfixture.UNIT_IDS) == 12


def test_a_unit_name_sorts_as_the_numbering_must(source):
    """Part 02 §12.1 numbers by ascending `(sorting_run_id, curation_id, local_unit_label)`.

    `PacketWriter._preassign` assigns in sorted-name order, so the name has to sort that way --
    which is what the zero padding is for: unpadded, label 40 would precede label 5 as text.
    """
    units = rows_of(source, "core.units")
    ordered = sorted(units, key=lambda u: (u["sorting_run_id"], u["curation_id"], int(u["local_unit_label"])))
    assert [u["unit_id"] for u in ordered] == sorted(u["unit_id"] for u in units)


def test_unit_ids_out_of_order_are_a_defect(tmp_path):
    """`unit_index` offsets into `unit_ids`, which is only meaningful if they increase."""
    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=[(0, 1)], unit_ids=[5, 1, 2, 3, 4, 6])
    source = SorterSource(tmp_path, session_id=SESSION)
    with pytest.raises(SourceDefect, match="not strictly increasing"):
        source.units()


# -- the spike summary ----------------------------------------------------------------


def test_the_spike_summary_is_computed_not_copied(source):
    """`n_spikes` and the tick bounds are the validated denormalization the spec asks for."""
    first = keyed(rows_of(source, "core.units"), 0)[0]
    assert (first["n_spikes"], first["first_spike_tick"], first["last_spike_tick"]) == (3, 10, 41)
    gapped = keyed(rows_of(source, "core.units"), 5)[0]
    assert (gapped["n_spikes"], gapped["first_spike_tick"], gapped["last_spike_tick"]) == (2, 11, 26)


def test_a_unit_with_no_spikes_gets_null_bounds(tmp_path):
    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=[(0, 1)])
    units = SorterSource(tmp_path, session_id=SESSION).units()
    assert units[0]["n_spikes"] == 1
    assert [u["first_spike_tick"] for u in units[1:]] == [None] * 5


# -- quality labels --------------------------------------------------------------------


def test_every_source_gets_a_row(source):
    labels = keyed(rows_of(source, "core.unit_quality_labels"), 0)
    assert {q["source"] for q in labels} == {"kilosort", "bombcell", "decoder", "unitrefine"}


def test_non_soma_projects_to_null_not_noise(source):
    """Part 02 §9.3: "recorded off-soma" is a different claim from "not a unit"."""
    row = next(q for q in keyed(rows_of(source, "core.unit_quality_labels"), 2) if q["source"] == "bombcell")
    assert (row["label"], row["normalized_label"]) == ("non_soma", None)


def test_the_source_label_survives_verbatim(source):
    """The open label is what the source said; the closed one is the declared projection."""
    for row in rows_of(source, "core.unit_quality_labels"):
        assert row["normalized_label"] == PROJECTION.get(row["label"])


def test_confidence_travels_where_the_source_reports_one(source):
    labels = {q["source"]: q for q in keyed(rows_of(source, "core.unit_quality_labels"), 0)}
    assert labels["decoder"]["confidence"] == pytest.approx(0.5)
    assert labels["kilosort"]["confidence"] is None


def test_the_designated_label_comes_from_the_decoder(source):
    """R11 §3 closed the column to sua/mua/noise, which is what the decoder emits natively."""
    unit = keyed(rows_of(source, "core.units"), 0)[0]
    assert (unit["quality_label"], unit["quality_label_source"]) == ("sua", "decoder")


# -- clocks ---------------------------------------------------------------------------


def test_each_stream_gets_its_own_clock(source):
    """Every experiment restarts sample_index, so a clock belongs to one stream."""
    clocks = rows_of(source, "core.clocks")
    assert {c["clock_id"] for c in clocks} == {
        f"{SHANK1}.samples",
        "experiment1.Neuropix-PXI-100.50720-2.samples",
    }
    assert {c["tick_rate_num"] for c in clocks} == {30000}


def test_a_clock_claims_no_epoch_and_no_alignment(source):
    """A curated sorting records neither, and R27 §4 refuses a packet that pretends otherwise."""
    for clock in rows_of(source, "core.clocks"):
        assert clock.get("tick_zero_utc") is None
        assert clock.get("transform_slope") is None
        assert clock.get("parent_clock_id") is None


def test_a_fractional_sample_rate_is_a_defect(tmp_path):
    import json

    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=[(0, 1)])
    info = tmp_path / "curated" / sorterfixture.NAMES[0] / "numpysorting_info.json"
    info.write_text(json.dumps({**json.loads(info.read_text()), "sampling_frequency": 30000.5}))
    with pytest.raises(SourceDefect, match="not a whole number of hertz"):
        SorterSource(tmp_path, session_id=SESSION).clocks()


# -- the sorter's own timestamp -------------------------------------------------------


def test_the_naive_sorter_datetime_does_not_become_a_column(source):
    """It came off the sorting machine, whose zone nothing records."""
    run = rows_of(source, "core.sorting_runs")[0]
    assert "started_at" not in run
    assert run["metadata"]["sorted_at_naive"] == "2026-08-26T23:25:57.061395"
    assert any("no UTC offset" in note for note in source.notes)


def test_the_sorter_is_identified(source):
    run = rows_of(source, "core.sorting_runs")[0]
    assert (run["sorter_name"], run["sorter_version"]) == ("kilosort4", "4.1.7")
    assert run["parameters"] == {"Th_universal": 9}
    assert run["metadata"]["spikeinterface_version"] == "0.104.7"


# -- spikes ----------------------------------------------------------------------------


def test_batches_come_out_in_the_registry_sort_order(source):
    """Stream by stream, then unit, then tick -- which is Part 03's ordering for this table."""
    seen = []
    for batch in source.spike_batches(batch_rows=3):
        table = batch.to_pydict()
        seen += list(zip(table["unit_id"], table["t_tick"], strict=True))
    assert seen == sorted(seen)


def test_a_spike_carries_the_resolved_unit_id(source):
    """The source's unit_index 3 is unit 5; a spike must not be filed under the offset."""
    first = next(source.spike_batches(batch_rows=1000)).to_pydict()
    assert sorted(t for u, t in zip(first["unit_id"], first["t_tick"], strict=True) if u == named(5)) == [11, 26]


def test_every_spike_survives_the_sort(source):
    total = sum(b.num_rows for b in source.spike_batches(batch_rows=4))
    assert total == 2 * len(sorterfixture.SPIKES)


def test_batches_are_bounded_by_the_requested_size(source):
    assert all(b.num_rows <= 4 for b in source.spike_batches(batch_rows=4))


def test_amplitudes_arrive_with_their_unit(source):
    """R11 §2: the unit belongs to the sorting context, not the spike."""
    assert rows_of(source, "core.units")[0]["amplitude_unit"] == "uV"
    assert "amplitude" in next(source.spike_batches()).schema.names


def test_adc_counts_are_declared_as_such(tmp_path):
    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=[(0, 1)], return_in_uv=False)
    source = SorterSource(tmp_path, session_id=SESSION)
    assert source.units()[0]["amplitude_unit"] == "adc"


def test_without_an_analyzer_there_are_no_amplitudes_and_no_unit(tmp_path):
    """Which is consistent: `amplitude_unit_declared` binds only where amplitudes exist."""
    sorterfixture.build(tmp_path, analyzer=False)
    source = SorterSource(tmp_path, session_id=SESSION, experiment="experiment1")
    assert source.units()[0]["amplitude_unit"] is None
    assert "amplitude" not in next(source.spike_batches()).schema.names


def test_amplitudes_that_do_not_align_are_a_defect(tmp_path):
    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=sorterfixture.SPIKES)
    zarr = tmp_path / "postprocessed" / f"{sorterfixture.NAMES[0]}.zarr"
    sorterfixture.zarr_array(zarr / "extensions" / "spike_amplitudes" / "amplitudes", np.zeros(3, dtype=np.float32))
    source = SorterSource(tmp_path, session_id=SESSION)
    with pytest.raises(SourceDefect, match="index-aligned or nothing"):
        list(source.spike_batches())


# -- what a person decided --------------------------------------------------------------


def test_manual_labels_become_a_fifth_source(source):
    """They live in curation.json, not properties/, and are the only record of a decision."""
    labels = rows_of(source, "core.unit_quality_labels")
    assert {q["source"] for q in labels} == {"kilosort", "bombcell", "decoder", "unitrefine", "manual"}


def test_a_manual_label_is_projected_like_any_other(source):
    """The fixture labels unit 1 `noise`, which is already in the closed set."""
    row = next(q for q in keyed(rows_of(source, "core.unit_quality_labels"), 1) if q["source"] == "manual")
    assert (row["label"], row["normalized_label"]) == ("noise", "noise")


def test_only_labelled_units_get_a_manual_row(source):
    manual = [q for q in rows_of(source, "core.unit_quality_labels") if q["source"] == "manual"]
    assert {q["unit_id"] for q in manual} == {named(1), named(1, SHANK2)}


def test_a_removal_with_no_label_is_reported(tmp_path):
    """Then the packet cannot say the unit was removed, and 02 has no column for it."""
    import json

    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=sorterfixture.SPIKES)
    path = tmp_path / "curated" / sorterfixture.NAMES[0] / "curation.json"
    doc = json.loads(path.read_text())
    doc["removed"] = [*doc["removed"], sorterfixture.UNIT_IDS[2]]  # removed, never labelled
    path.write_text(json.dumps(doc))
    source = SorterSource(tmp_path, session_id=SESSION)
    source.unit_quality_labels()
    assert any("carry no manual label" in note for note in source.notes)


def test_a_non_quality_category_gets_its_own_source(tmp_path):
    import json

    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=sorterfixture.SPIKES)
    path = tmp_path / "curated" / sorterfixture.NAMES[0] / "curation.json"
    doc = json.loads(path.read_text())
    doc["manual_labels"] = [{"unit_id": sorterfixture.UNIT_IDS[0], "labels": {"artefact": ["ringing"]}}]
    doc["removed"] = []
    path.write_text(json.dumps(doc))
    rows = SorterSource(tmp_path, session_id=SESSION).unit_quality_labels()
    row = next(q for q in rows if q["source"].startswith("manual"))
    assert (row["source"], row["label"], row["normalized_label"]) == ("manual:artefact", "ringing", None)


def test_two_labels_in_one_category_are_kept_unprojected(tmp_path):
    """A closed vocabulary holds one value, so a pair is verbatim and normalizes to nothing."""
    import json

    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=sorterfixture.SPIKES)
    path = tmp_path / "curated" / sorterfixture.NAMES[0] / "curation.json"
    doc = json.loads(path.read_text())
    doc["manual_labels"] = [{"unit_id": sorterfixture.UNIT_IDS[0], "labels": {"quality": ["noise", "MUA"]}}]
    doc["removed"] = []
    path.write_text(json.dumps(doc))
    source = SorterSource(tmp_path, session_id=SESSION)
    row = next(q for q in source.unit_quality_labels() if q["source"] == "manual")
    assert (row["label"], row["normalized_label"]) == ("noise|MUA", None)
    assert any("2 labels in category" in note for note in source.notes)


# -- observation windows (Part 01 §2.2) ----------------------------------------------------


def test_a_sample_clock_declares_the_recording_it_counts(source):
    """The window is `[0, length - 1]`, from the analyzer's `recording_info`.

    It comes from the recording rather than from the spikes on purpose: a denominator taken
    from the numerator makes every firing rate identical (R25 §3), and a unit that fired
    nothing was still observed.
    """
    rows = source.observation_intervals()
    assert {r["clock_id"] for r in rows} == {c["clock_id"] for c in source.clocks()}
    for row in rows:
        assert (row["start_tick"], row["stop_tick"]) == (0, sorterfixture.N_SAMPLES[0] - 1)


def test_the_window_contains_every_spike_on_its_clock(source):
    """R38 §2.5's claim, which is what makes `within_observation` worth inheriting."""
    stop = {r["clock_id"]: r["stop_tick"] for r in source.observation_intervals()}
    for row in source.units():
        clock = f"{row['sorting_run_id']}.samples"
        assert row["last_spike_tick"] <= stop[clock]


def test_a_stream_with_no_analyzer_declares_no_window(tmp_path):
    root = sorterfixture.build(tmp_path / "sorted", analyzer=False)
    assert SorterSource(root, session_id=SESSION).observation_intervals() == []


def test_a_multi_segment_recording_declares_no_window(tmp_path):
    """Each segment restarts the counter, so its length is not one interval on one clock."""
    root = sorterfixture.build(tmp_path / "sorted", n_samples=(100, 200))
    source = SorterSource(root, session_id=SESSION)
    assert source.observation_intervals() == []
    assert any("2 recording segments" in note for note in source.notes)


# -- provenance the currency mechanism needs (R41 §2.1) ---------------------------------


def test_each_stream_declares_the_runs_that_made_it(source):
    runs = rows_of(source, "core.processing_runs")
    kinds = {r["activity_type"] for r in runs}
    assert kinds == {"spike_sorting", "curation"}
    assert len(runs) == 2 * len(source.streams())
    assert all(r["session_id"] == SESSION for r in runs)
    assert all(r["status"] == "succeeded" for r in runs)


def test_the_sorting_and_the_curation_name_their_runs(source):
    known = {r["processing_run_id"] for r in rows_of(source, "core.processing_runs")}
    for resource in ("core.sorting_runs", "core.curation_versions"):
        named = [r["processing_run_id"] for r in rows_of(source, resource)]
        assert named and all(n in known for n in named), resource


def test_a_sorting_and_its_curation_name_different_runs(source):
    """Re-curating without re-sorting is the common case, so they cannot share a run."""
    sorting = {r["sorting_run_id"]: r["processing_run_id"] for r in rows_of(source, "core.sorting_runs")}
    for cur in rows_of(source, "core.curation_versions"):
        assert cur["processing_run_id"] != sorting[cur["sorting_run_id"]]


def test_every_run_declares_its_scope(source):
    """R44 §2.1: without it, twelve probes sorted once each look like twelve alternatives."""
    runs = rows_of(source, "core.processing_runs")
    assert all(r.get("scope") for r in runs), "a run with no scope is undeterminable (Part 01 §2.4)"

    sorting = [r for r in runs if r["activity_type"] == "spike_sorting"]
    probes = {r["probe_id"] for r in rows_of(source, "core.sorting_runs")}
    assert {r["scope"] for r in sorting} == probes
    # One run per scope is what makes the packet unambiguous by computation.
    assert len({r["scope"] for r in sorting}) == len(sorting)


def test_a_curation_is_scoped_to_its_sorting_not_its_probe(source):
    """Choosing the sorting already narrows the curation, so scoping to the probe would only
    restate that ambiguity instead of composing with it."""
    curations = [r for r in rows_of(source, "core.processing_runs") if r["activity_type"] == "curation"]
    sortings = {r["sorting_run_id"] for r in rows_of(source, "core.sorting_runs")}
    assert {r["scope"] for r in curations} == sortings


def test_supersedes_is_left_unset(source):
    """Part 01 §3.20: a first import supersedes nothing, and a writer must not guess."""
    assert all(r.get("supersedes") is None for r in rows_of(source, "core.processing_runs"))


# -- the channels a run used -------------------------------------------------------------


def test_a_run_declares_the_channels_it_used(source):
    """R83 §2.1: the analyzer's list, in its own order, naming the contact at each position."""
    rows = [r for r in rows_of(source, "core.sorting_run_channels") if r["sorting_run_id"] == SHANK1]
    assert [r["channel_index"] for r in rows] == [0, 1, 2, 3]
    assert [r["electrode_id"] for r in rows] == [f"50720-1.{c}" for c in sorterfixture.CHANNEL_IDS]


def test_a_channel_index_is_not_a_contact_position(source):
    """R83 §1.1's whole point, in four rows: `CH2` was dropped, so index 2 is `CH3`."""
    rows = [r for r in rows_of(source, "core.sorting_run_channels") if r["sorting_run_id"] == SHANK1]
    at = {r["channel_index"]: r["electrode_id"] for r in rows}
    assert at[2] == "50720-1.CH3"


def test_an_electrode_is_named_as_the_nwb_names_it(source):
    """The two adapters meet on `<group>.<channel>`, which is what lets the writer number once.

    `NWBSource._electrode_ids` composes the same string for `core.electrodes`, so the shared
    `Keys` resolves both to one integer without this adapter running after that one.
    """
    rows = rows_of(source, "core.sorting_run_channels")
    assert all(r["electrode_id"].count(".") == 1 for r in rows)
    assert {r["electrode_id"].split(".")[0] for r in rows} == {"50720-1", "50720-2"}


def test_a_stream_without_a_channel_list_contributes_nothing(tmp_path):
    """Part 02 §12.2 forbids inferring one, so silence is the only other answer -- and it is reported."""
    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=[(0, 1)], channel_ids=None)
    source = SorterSource(tmp_path, session_id=SESSION)
    assert source.sorting_run_channels() == []
    assert any("states no channel list" in note for note in source.notes)
