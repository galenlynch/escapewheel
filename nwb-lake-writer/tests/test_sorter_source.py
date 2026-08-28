"""The sorter adapter carries the ticks, and must not confuse an offset for an identifier."""

import numpy as np
import pytest

from nwb_lake_writer.sources import SorterSource, SourceDefect
from nwb_lake_writer.sources.sorter import PROJECTION
from tests import sorterfixture

SESSION = "ecephys_837772_2026-06-27_14-08-21"
SHANK1 = "experiment1.Neuropix-PXI-100.50720-1"


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


def test_quad_base_shanks_collapse_to_one_probe(source):
    """Four shank streams are one physical device, with a sorting run and a clock each."""
    assert len(rows_of(source, "core.probes")) == 1
    assert len(rows_of(source, "core.clocks")) == 2
    assert len(rows_of(source, "core.sorting_runs")) == 2


# -- the offset that is not an identifier --------------------------------------------


def test_unit_index_is_resolved_through_unit_ids(source):
    """`unit_ids` has a gap, so offset 3 is unit 5. Storing the offset would be wrong here."""
    labels = [u["local_unit_label"] for u in rows_of(source, "core.units") if SHANK1 in u["unit_id"]]
    assert labels == ["0", "1", "2", "5", "12", "40"]


def test_a_unit_id_is_stream_qualified(source):
    """A Kilosort id is unique within a stream and not across them."""
    ids = {u["unit_id"] for u in rows_of(source, "core.units")}
    assert f"{SHANK1}.u05" in ids
    assert "experiment1.Neuropix-PXI-100.50720-2.u05" in ids
    assert len(ids) == 12


def test_unit_ids_are_padded_so_string_order_matches_numeric(source):
    """`core.spike_events` sorts by this column as a string; unpadded, u12 would precede u5."""
    ids = sorted(u["unit_id"] for u in rows_of(source, "core.units") if SHANK1 in u["unit_id"])
    assert [i.rsplit(".u", 1)[1] for i in ids] == ["00", "01", "02", "05", "12", "40"]


def test_unit_ids_out_of_order_are_a_defect(tmp_path):
    """`unit_index` offsets into `unit_ids`, which is only meaningful if they increase."""
    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=[(0, 1)], unit_ids=[5, 1, 2, 3, 4, 6])
    source = SorterSource(tmp_path, session_id=SESSION)
    with pytest.raises(SourceDefect, match="not strictly increasing"):
        source.units()


# -- the spike summary ----------------------------------------------------------------


def test_the_spike_summary_is_computed_not_copied(source):
    """`n_spikes` and the tick bounds are the validated denormalization the spec asks for."""
    units = {u["unit_id"]: u for u in rows_of(source, "core.units")}
    first = units[f"{SHANK1}.u00"]
    assert (first["n_spikes"], first["first_spike_tick"], first["last_spike_tick"]) == (3, 10, 41)
    gapped = units[f"{SHANK1}.u05"]
    assert (gapped["n_spikes"], gapped["first_spike_tick"], gapped["last_spike_tick"]) == (2, 11, 26)


def test_a_unit_with_no_spikes_gets_null_bounds(tmp_path):
    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=[(0, 1)])
    units = SorterSource(tmp_path, session_id=SESSION).units()
    assert units[0]["n_spikes"] == 1
    assert [u["first_spike_tick"] for u in units[1:]] == [None] * 5


# -- quality labels --------------------------------------------------------------------


def test_every_source_gets_a_row(source):
    labels = [q for q in rows_of(source, "core.unit_quality_labels") if q["unit_id"] == f"{SHANK1}.u00"]
    assert {q["source"] for q in labels} == {"kilosort", "bombcell", "decoder", "unitrefine"}


def test_non_soma_projects_to_null_not_noise(source):
    """R22 §3: "recorded off-soma" is a different claim from "not a unit"."""
    row = next(
        q
        for q in rows_of(source, "core.unit_quality_labels")
        if q["unit_id"] == f"{SHANK1}.u02" and q["source"] == "bombcell"
    )
    assert (row["label"], row["normalized_label"]) == ("non_soma", None)


def test_the_source_label_survives_verbatim(source):
    """The open label is what the source said; the closed one is the declared projection."""
    for row in rows_of(source, "core.unit_quality_labels"):
        assert row["normalized_label"] == PROJECTION.get(row["label"])


def test_confidence_travels_where_the_source_reports_one(source):
    labels = {q["source"]: q for q in rows_of(source, "core.unit_quality_labels") if q["unit_id"] == f"{SHANK1}.u00"}
    assert labels["decoder"]["confidence"] == pytest.approx(0.5)
    assert labels["kilosort"]["confidence"] is None


def test_the_designated_label_comes_from_the_decoder(source):
    """R11 §3 closed the column to sua/mua/noise, which is what the decoder emits natively."""
    unit = next(u for u in rows_of(source, "core.units") if u["unit_id"] == f"{SHANK1}.u00")
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
    """Stream by stream, then unit, then tick -- which is `03`'s ordering for this table."""
    seen = []
    for batch in source.spike_batches(batch_rows=3):
        table = batch.to_pydict()
        seen += list(zip(table["sorting_run_id"], table["unit_id"], table["t_tick"], strict=True))
    assert seen == sorted(seen)


def test_a_spike_carries_the_resolved_unit_id(source):
    """The source's unit_index 3 is unit 5; a spike must not be filed under u03."""
    first = next(source.spike_batches(batch_rows=1000)).to_pydict()
    ticks = {u: t for u, t in zip(first["unit_id"], first["t_tick"], strict=True) if u.endswith("u05")}
    assert set(ticks) == {f"{SHANK1}.u05"}
    assert sorted(t for u, t in zip(first["unit_id"], first["t_tick"], strict=True) if u.endswith("u05")) == [11, 26]


def test_every_spike_survives_the_sort(source):
    total = sum(b.num_rows for b in source.spike_batches(batch_rows=4))
    assert total == 2 * len(sorterfixture.SPIKES)


def test_batches_are_bounded_by_the_requested_size(source):
    assert all(b.num_rows <= 4 for b in source.spike_batches(batch_rows=4))


def test_amplitudes_arrive_with_their_unit(source):
    """R11 §2: the unit belongs to the sorting context, not the spike."""
    assert rows_of(source, "core.sorting_runs")[0]["amplitude_unit"] == "uV"
    assert "amplitude" in next(source.spike_batches()).schema.names


def test_adc_counts_are_declared_as_such(tmp_path):
    sorterfixture.stream(tmp_path, sorterfixture.NAMES[0], spikes=[(0, 1)], return_in_uv=False)
    source = SorterSource(tmp_path, session_id=SESSION)
    assert source.sorting_runs()[0]["amplitude_unit"] == "adc"


def test_without_an_analyzer_there_are_no_amplitudes_and_no_unit(tmp_path):
    """Which is consistent: `amplitude_unit_declared` binds only where amplitudes exist."""
    sorterfixture.build(tmp_path, analyzer=False)
    source = SorterSource(tmp_path, session_id=SESSION, experiment="experiment1")
    assert source.sorting_runs()[0]["amplitude_unit"] is None
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
    row = next(
        q
        for q in rows_of(source, "core.unit_quality_labels")
        if q["source"] == "manual" and q["unit_id"] == f"{SHANK1}.u01"
    )
    assert (row["label"], row["normalized_label"]) == ("noise", "noise")


def test_only_labelled_units_get_a_manual_row(source):
    manual = [q for q in rows_of(source, "core.unit_quality_labels") if q["source"] == "manual"]
    assert {q["unit_id"] for q in manual} == {f"{SHANK1}.u01", "experiment1.Neuropix-PXI-100.50720-2.u01"}


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
