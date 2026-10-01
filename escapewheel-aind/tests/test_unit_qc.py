"""What `UnitQCSource` reads from an analyzer's metric frames, and what it refuses.

The fixture is a miniature `SortingAnalyzer` holding only what this adapter opens: a stream folder
named as the pipeline names one, and the `quality_metrics` and `template_metrics` data frames, each
a group of one-dimensional arrays with the unit labels in `index`.

Probe `A` has labels 0, 1 and 5 and the packet holds 0 and 5, so one analyzer unit is skipped and
the tables have two rows. Synchrony sizes are 2, 4 and 16, which a lexical sort would put first.

The analyzer leaves `amplitude_median` NaN for both kept units and `amplitude_cutoff` NaN for unit
5, which is what an NWB units table (`nwb_units`) may fill.
"""

import json
from pathlib import Path

import numpy as np
import pytest
from escapewheel_writer.errors import SourceDefect
from escapewheel_writer.notes import coded, codes

from escapewheel_aind.errors import AindFault
from escapewheel_aind.notes import AindNote
from escapewheel_aind.unit_qc import METRICS, WAVEFORM_METRICS, UnitQCSource
from tests.nwbfixture import array, group, text

LABELS = [0, 1, 5]

REGISTRY = json.loads((Path(__file__).resolve().parents[1] / "extensions" / "aind_unit_qc.json").read_text())

#: The packet's units: the sorter's names for them, which is what the adapter carries on.
UNITS = [
    {"device_name": "A", "local_unit_label": "0", "unit_id": "exp1.A:0"},
    {"device_name": "A", "local_unit_label": "5", "unit_id": "exp1.A:5"},
]


def _frame(path: Path, **columns) -> None:
    group(path, dataframe=True)
    for name, values in columns.items():
        array(path / name, np.asarray(values))


def stream(root: Path, name: str, *, template: bool = True, labels=LABELS, **quality) -> Path:
    """Write one stream's analyzer under `postprocessed/`, `quality` replacing quality metric columns."""
    analyzer = group(root / "postprocessed" / f"{name}.zarr")
    _frame(
        analyzer / "extensions/quality_metrics/metrics",
        **{
            "index": np.asarray(labels, dtype=np.int64),
            "num_spikes": np.asarray([100, 200, 300], dtype=np.int64),
            "snr": np.asarray([5.0, np.nan, 7.5]),
            "rp_violations": np.asarray([0, 1, 2], dtype=np.int64),
            "amplitude_median": np.asarray([np.nan, 40.0, np.nan]),
            "amplitude_cutoff": np.asarray([0.01, 0.02, np.nan]),
            "sync_spike_2": np.asarray([0.2, 0.3, 0.4]),
            "sync_spike_16": np.asarray([0.0, 0.0, np.nan]),
            "sync_spike_4": np.asarray([0.1, 0.2, 0.3]),
        }
        | quality,
    )
    if template:
        _frame(
            analyzer / "extensions/template_metrics/metrics",
            index=np.asarray(labels, dtype=np.int64),
            spread=np.asarray([60.0, 30.0, 90.0]),
            num_positive_peaks=np.asarray([0, 1, 2], dtype=np.int64),
            peak_to_trough_duration=np.asarray([1e-3, 2e-3, 3e-3]),
            main_peak_to_trough_ratio=np.asarray([0.3, 0.4, 0.5]),
            peak_half_width=np.asarray([4e-4, 5e-4, 6e-4]),
            trough_half_width=np.asarray([2e-4, 2.5e-4, np.nan]),
            # A metric the registry does not declare is not carried.
            trough_width=np.asarray([1e-4, 1e-4, 1e-4]),
        )
    return root


def nwb_units(root: Path, **overrides) -> Path:
    """Write an NWB units table stating the analyzer's metrics for units 0 and 5, and return the NWB.

    `amplitude_median` and `amplitude_cutoff` carry values where the analyzer has NaN, and a
    different `amplitude_cutoff` for unit 0, which the analyzer does state.
    """
    columns = {
        "ks_unit_id": np.asarray([0, 5], dtype=np.int64),
        "num_spikes": np.asarray([100, 300], dtype=np.int64),
        "snr": np.asarray([5.0, 7.5]),
        "rp_violations": np.asarray([0, 2], dtype=np.int64),
        "sync_spike_2": np.asarray([0.2, 0.4]),
        "sync_spike_4": np.asarray([0.1, 0.3]),
        "sync_spike_16": np.asarray([0.0, np.nan]),
        "amplitude_median": np.asarray([11.0, 33.0]),
        "amplitude_cutoff": np.asarray([0.5, 0.03]),
    } | overrides
    nwb = group(root / "session.nwb", neurodata_type="NWBFile")
    units = group(nwb / "units", neurodata_type="Units")
    text(units / "device_name", ["A"] * len(columns["ks_unit_id"]))
    for name, values in columns.items():
        array(units / name, values)
    return nwb


@pytest.fixture
def asset(tmp_path: Path) -> Path:
    return stream(tmp_path / "sorted", "experiment1_Record Node 109#Neuropix-PXI-100.A_recording1")


def _by_unit(rows):
    return {row["unit_id"]: row for row in rows}


def test_units_resolve_to_the_sorters_names_and_the_rest_are_skipped(asset: Path) -> None:
    source = UnitQCSource(asset, session_id="s1", units=UNITS)
    metrics = source.records()["aind_unit_qc.metrics"]
    assert sorted(_by_unit(metrics)) == ["exp1.A:0", "exp1.A:5"]
    assert {row["session_id"] for row in metrics} == {"s1"}
    assert codes(source.notes) == [AindNote.UNIT_UNMATCHED]
    assert source.notes[0].startswith("units: 1 analyzer unit(s)")


def test_a_metric_keeps_its_name_except_num_spikes_and_a_nan_is_null(asset: Path) -> None:
    metrics = _by_unit(UnitQCSource(asset, session_id="s1", units=UNITS).records()["aind_unit_qc.metrics"])
    assert metrics["exp1.A:5"] == {
        "session_id": "s1",
        "unit_id": "exp1.A:5",
        "num_spikes_used": 300,
        "snr": 7.5,
        "rp_violations": 2,
        "amplitude_median": None,
        "amplitude_cutoff": None,
    }
    assert metrics["exp1.A:0"]["snr"] == 5.0
    assert "num_spikes" not in metrics["exp1.A:0"]


def test_an_infinite_metric_is_null(tmp_path: Path) -> None:
    """Part 02 §5.4: every `aind_unit_qc` float column is declared finite, so an infinity is not carried."""
    root = stream(
        tmp_path / "sorted",
        "experiment1_Record Node 109#Neuropix-PXI-100.A_recording1",
        snr=np.asarray([np.inf, 1.0, -np.inf]),
    )
    metrics = _by_unit(UnitQCSource(root, session_id="s1", units=UNITS).records()["aind_unit_qc.metrics"])
    assert metrics["exp1.A:0"]["snr"] is None and metrics["exp1.A:5"]["snr"] is None


def test_synchrony_is_one_row_per_size_in_numeric_order(asset: Path) -> None:
    rows = UnitQCSource(asset, session_id="s1", units=UNITS).records()["aind_unit_qc.synchrony"]
    unit5 = [(r["synchrony_size"], r["sync_spike"]) for r in rows if r["unit_id"] == "exp1.A:5"]
    assert unit5 == [(2, 0.4), (4, 0.3), (16, None)]
    assert len(rows) == 6


def test_the_template_metrics_carry_the_names_spikeinterface_0104_computes(asset: Path) -> None:
    rows = _by_unit(UnitQCSource(asset, session_id="s1", units=UNITS).records()["aind_unit_qc.waveform_metrics"])
    assert rows["exp1.A:5"] == {
        "session_id": "s1",
        "unit_id": "exp1.A:5",
        "spread": 90.0,
        "num_positive_peaks": 2,
        "peak_to_trough_duration": 3e-3,
        "main_peak_to_trough_ratio": 0.5,
        "peak_half_width": 6e-4,
        "trough_half_width": None,
    }


def test_a_template_metric_the_analyzer_lacks_is_absent_rather_than_null(asset: Path) -> None:
    """An absent column says the source stated nothing for it (Part 12 §5)."""
    rows = _by_unit(UnitQCSource(asset, session_id="s1", units=UNITS).records()["aind_unit_qc.waveform_metrics"])
    assert "repolarization_slope" not in rows["exp1.A:0"]
    assert "trough_width" not in rows["exp1.A:0"]


@pytest.mark.parametrize(
    ("resource", "mapping"),
    [("aind_unit_qc.metrics", METRICS), ("aind_unit_qc.waveform_metrics", WAVEFORM_METRICS)],
)
def test_every_declared_metric_is_one_the_adapter_reads(resource, mapping) -> None:
    """A declared column the adapter maps from nothing stays null on every packet."""
    declared = {column["name"] for column in REGISTRY["resources"][resource]["table"]["columns"]}
    assert set(mapping) == declared - {"session_id", "unit_id"}


def test_a_template_metric_arrives_as_its_declared_type(asset: Path) -> None:
    """SpikeInterface computes `spread` as a float even where every value is integral."""
    columns = REGISTRY["resources"]["aind_unit_qc.waveform_metrics"]["table"]["columns"]
    declared = {column["name"]: {"float64": float, "int64": int}.get(column["type"]) for column in columns}
    rows = UnitQCSource(asset, session_id="s1", units=UNITS).records()["aind_unit_qc.waveform_metrics"]
    arrived = {(name, type(row[name])) for row in rows for name in WAVEFORM_METRICS.keys() & row.keys()}
    assert "spread" in {name for name, _ in arrived}
    assert {(name, kind) for name, kind in arrived if kind is not type(None)} <= set(declared.items())


def test_a_stream_without_template_metrics_leaves_that_table_empty_and_says_so(tmp_path: Path) -> None:
    root = stream(tmp_path / "sorted", "experiment1_Record Node 109#Neuropix-PXI-100.A_recording1", template=False)
    source = UnitQCSource(root, session_id="s1", units=UNITS)
    built = source.records()
    assert built["aind_unit_qc.waveform_metrics"] == []
    assert set(built) == set(UnitQCSource.PRODUCES)
    (absent,) = coded(source.notes, AindNote.NO_METRIC_GROUP)
    assert "template_metrics" in absent
    assert source.offers()["aind_unit_qc.metrics"] == 2


def test_two_experiments_on_one_probe_are_refused_until_one_is_chosen(asset: Path) -> None:
    """Probe names repeat across experiments, so an unscoped read would give one unit two rows."""
    stream(asset, "experiment2_Record Node 109#Neuropix-PXI-100.A_recording1")
    with pytest.raises(SourceDefect) as refused:
        UnitQCSource(asset, session_id="s1", units=UNITS).records()
    assert refused.value.code is AindFault.UNIT_IN_TWO_STREAMS
    scoped = UnitQCSource(asset, session_id="s1", units=UNITS, experiment="experiment1")
    assert len(scoped.records()["aind_unit_qc.metrics"]) == 2


def test_an_analyzer_matching_no_unit_is_refused(asset: Path) -> None:
    with pytest.raises(SourceDefect) as refused:
        UnitQCSource(asset, session_id="s1", units=[]).records()
    assert refused.value.code is AindFault.NO_UNIT_MATCHES


def test_a_root_without_postprocessed_is_refused(tmp_path: Path) -> None:
    (tmp_path / "sorted").mkdir()
    with pytest.raises(SourceDefect) as refused:
        UnitQCSource(tmp_path / "sorted", session_id="s1", units=UNITS)
    assert refused.value.code is AindFault.NO_ANALYZER_DIRECTORY


def test_the_postprocessed_directory_is_accepted_as_well_as_the_asset(asset: Path) -> None:
    whole = UnitQCSource(asset, session_id="s1", units=UNITS).offers()
    assert UnitQCSource(asset / "postprocessed", session_id="s1", units=UNITS).offers() == whole


# -- filling the analyzer's NaN from the NWB ---------------------------------------------


def _filled(asset: Path, nwb: Path) -> tuple[dict, list[str]]:
    source = UnitQCSource(asset, session_id="s1", units=UNITS, nwb=nwb)
    return _by_unit(source.records()["aind_unit_qc.metrics"]), source.notes


def test_a_nan_the_nwb_states_is_filled_from_it(asset: Path, tmp_path: Path) -> None:
    metrics, notes = _filled(asset, nwb_units(tmp_path))
    assert metrics["exp1.A:0"]["amplitude_median"] == 11.0
    assert metrics["exp1.A:5"]["amplitude_median"] == 33.0
    assert metrics["exp1.A:5"]["amplitude_cutoff"] == 0.03
    assert "nwb: filled 2 amplitude_median and 1 amplitude_cutoff value(s) the analyzer left NaN" in notes
    assert "nwb: 0 unit(s) disagree with the analyzer on a metric both state; not filled" in notes


def test_a_value_the_analyzer_states_is_never_overwritten(asset: Path, tmp_path: Path) -> None:
    metrics, _ = _filled(asset, nwb_units(tmp_path))
    assert metrics["exp1.A:0"]["amplitude_cutoff"] == 0.01


def test_a_unit_whose_other_metrics_disagree_is_left_unfilled_and_counted(asset: Path, tmp_path: Path) -> None:
    """A mismatched file would otherwise fill one unit's amplitude with another's."""
    metrics, notes = _filled(asset, nwb_units(tmp_path, snr=np.asarray([5.0, 7.6])))
    assert metrics["exp1.A:0"]["amplitude_median"] == 11.0
    assert metrics["exp1.A:5"]["amplitude_median"] is None
    assert metrics["exp1.A:5"]["amplitude_cutoff"] is None
    assert "nwb: filled 1 amplitude_median and 0 amplitude_cutoff value(s) the analyzer left NaN" in notes
    assert "nwb: 1 unit(s) disagree with the analyzer on a metric both state; not filled" in notes


def test_a_nan_on_one_side_only_is_a_disagreement(asset: Path, tmp_path: Path) -> None:
    metrics, notes = _filled(asset, nwb_units(tmp_path, sync_spike_16=np.asarray([0.0, 0.5])))
    assert metrics["exp1.A:5"]["amplitude_median"] is None
    assert "nwb: 1 unit(s) disagree with the analyzer on a metric both state; not filled" in notes


def test_a_unit_missing_from_the_nwb_is_left_null(asset: Path, tmp_path: Path) -> None:
    nwb = nwb_units(
        tmp_path,
        ks_unit_id=np.asarray([0], dtype=np.int64),
        num_spikes=np.asarray([100], dtype=np.int64),
        snr=np.asarray([5.0]),
        rp_violations=np.asarray([0], dtype=np.int64),
        sync_spike_2=np.asarray([0.2]),
        sync_spike_4=np.asarray([0.1]),
        sync_spike_16=np.asarray([0.0]),
        amplitude_median=np.asarray([11.0]),
        amplitude_cutoff=np.asarray([0.5]),
    )
    metrics, notes = _filled(asset, nwb)
    assert metrics["exp1.A:0"]["amplitude_median"] == 11.0
    assert metrics["exp1.A:5"]["amplitude_median"] is None
    assert "nwb: 1 unit(s) with a NaN to fill are absent from the NWB; left null" in notes


def test_an_nwb_naming_no_unit_is_refused(asset: Path, tmp_path: Path) -> None:
    nwb = group(tmp_path / "session.nwb", neurodata_type="NWBFile")
    group(nwb / "units", neurodata_type="Units")
    with pytest.raises(SourceDefect) as refused:
        UnitQCSource(asset, session_id="s1", units=UNITS, nwb=nwb).records()
    assert refused.value.code is AindFault.NO_UNIT_NAMES


def test_the_nwb_is_an_option_a_recipe_may_set() -> None:
    assert "nwb" in UnitQCSource.ACCEPTS
