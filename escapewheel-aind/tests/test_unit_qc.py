"""What `UnitQCSource` reads from an analyzer's metric frames, and what it refuses.

The fixture is a miniature `SortingAnalyzer` holding only what this adapter opens: a stream folder
named as the pipeline names one, and the `quality_metrics` and `template_metrics` data frames, each
a group of one-dimensional arrays with the unit labels in `index`.

Probe `A` has labels 0, 1 and 5 and the packet holds 0 and 5, so one analyzer unit is skipped and
the tables have two rows. Synchrony sizes are 2, 4 and 16, which a lexical sort would put first.
"""

from pathlib import Path

import numpy as np
import pytest
from escapewheel_writer.sources.defect import SourceDefect

from escapewheel_aind.unit_qc import UnitQCSource
from tests.nwbfixture import array, group

LABELS = [0, 1, 5]

#: The packet's units: the sorter's names for them, which is what the adapter carries on.
UNITS = [
    {"device_name": "A", "local_unit_label": "0", "unit_id": "exp1.A:0"},
    {"device_name": "A", "local_unit_label": "5", "unit_id": "exp1.A:5"},
]


def _frame(path: Path, **columns) -> None:
    group(path, dataframe=True)
    for name, values in columns.items():
        array(path / name, np.asarray(values))


def stream(root: Path, name: str, *, template: bool = True, labels=LABELS) -> Path:
    """Write one stream's analyzer under `postprocessed/`."""
    analyzer = group(root / "postprocessed" / f"{name}.zarr")
    _frame(
        analyzer / "extensions/quality_metrics/metrics",
        index=np.asarray(labels, dtype=np.int64),
        num_spikes=np.asarray([100, 200, 300], dtype=np.int64),
        snr=np.asarray([5.0, np.nan, 7.5]),
        rp_violations=np.asarray([0, 1, 2], dtype=np.int64),
        sync_spike_2=np.asarray([0.2, 0.3, 0.4]),
        sync_spike_16=np.asarray([0.0, 0.0, np.nan]),
        sync_spike_4=np.asarray([0.1, 0.2, 0.3]),
    )
    if template:
        _frame(
            analyzer / "extensions/template_metrics/metrics",
            index=np.asarray(labels, dtype=np.int64),
            spread=np.asarray([60.0, 30.0, 90.0]),
            num_positive_peaks=np.asarray([0, 1, 2], dtype=np.int64),
            # A metric the registry does not declare is not carried.
            peak_to_trough_duration=np.asarray([1e-3, 2e-3, 3e-3]),
        )
    return root


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
    assert source.notes == ["units: 1 analyzer unit(s) match no unit in the packet's sorting; skipped"]


def test_a_metric_keeps_its_name_except_num_spikes_and_a_nan_is_null(asset: Path) -> None:
    metrics = _by_unit(UnitQCSource(asset, session_id="s1", units=UNITS).records()["aind_unit_qc.metrics"])
    assert metrics["exp1.A:5"] == {
        "session_id": "s1",
        "unit_id": "exp1.A:5",
        "num_spikes_used": 300,
        "snr": 7.5,
        "rp_violations": 2,
    }
    assert metrics["exp1.A:0"]["snr"] == 5.0
    assert "num_spikes" not in metrics["exp1.A:0"]


def test_synchrony_is_one_row_per_size_in_numeric_order(asset: Path) -> None:
    rows = UnitQCSource(asset, session_id="s1", units=UNITS).records()["aind_unit_qc.synchrony"]
    unit5 = [(r["synchrony_size"], r["sync_spike"]) for r in rows if r["unit_id"] == "exp1.A:5"]
    assert unit5 == [(2, 0.4), (4, 0.3), (16, None)]
    assert len(rows) == 6


def test_a_template_metric_the_analyzer_lacks_is_absent_rather_than_null(asset: Path) -> None:
    """An absent column says the source stated nothing for it (Part 03 §11.3)."""
    rows = _by_unit(UnitQCSource(asset, session_id="s1", units=UNITS).records()["aind_unit_qc.waveform_metrics"])
    assert rows["exp1.A:0"] == {"session_id": "s1", "unit_id": "exp1.A:0", "spread": 60.0, "num_positive_peaks": 0}


def test_a_stream_without_template_metrics_leaves_that_table_empty_and_says_so(tmp_path: Path) -> None:
    root = stream(tmp_path / "sorted", "experiment1_Record Node 109#Neuropix-PXI-100.A_recording1", template=False)
    source = UnitQCSource(root, session_id="s1", units=UNITS)
    built = source.records()
    assert built["aind_unit_qc.waveform_metrics"] == []
    assert set(built) == set(UnitQCSource.PRODUCES)
    assert any("template_metrics" in note for note in source.notes)
    assert source.offers()["aind_unit_qc.metrics"] == 2


def test_two_experiments_on_one_probe_are_refused_until_one_is_chosen(asset: Path) -> None:
    """Probe names repeat across experiments, so an unscoped read would give one unit two rows."""
    stream(asset, "experiment2_Record Node 109#Neuropix-PXI-100.A_recording1")
    with pytest.raises(SourceDefect, match="experiment"):
        UnitQCSource(asset, session_id="s1", units=UNITS).records()
    scoped = UnitQCSource(asset, session_id="s1", units=UNITS, experiment="experiment1")
    assert len(scoped.records()["aind_unit_qc.metrics"]) == 2


def test_an_analyzer_matching_no_unit_is_refused(asset: Path) -> None:
    with pytest.raises(SourceDefect, match="no unit"):
        UnitQCSource(asset, session_id="s1", units=[]).records()


def test_a_root_without_postprocessed_is_refused(tmp_path: Path) -> None:
    (tmp_path / "sorted").mkdir()
    with pytest.raises(SourceDefect, match="postprocessed"):
        UnitQCSource(tmp_path / "sorted", session_id="s1", units=UNITS)


def test_the_postprocessed_directory_is_accepted_as_well_as_the_asset(asset: Path) -> None:
    whole = UnitQCSource(asset, session_id="s1", units=UNITS).offers()
    assert UnitQCSource(asset / "postprocessed", session_id="s1", units=UNITS).offers() == whole
