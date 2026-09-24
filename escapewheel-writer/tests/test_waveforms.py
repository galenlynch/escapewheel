"""What `WaveformSource` stores, and what it refuses.

The adapter reads the analyzer that computed the templates rather than the NWB exported from it,
so the fixture is a miniature `SortingAnalyzer`: templates, the sparsity mask beside them, the
unit ids, and the two attribute blocks that say what the values are in and where the spike sits.

The contract those buy is what most of these test. The support is the **mask**, not the values, so
a contact whose template happens to be flat keeps its row and a non-zero outside the mask is not
stored -- neither of which a reader of the padded export could get right.
"""

import json
from pathlib import Path

import numpy as np
import pytest
import zarr

from escapewheel_writer.sources import SourceDefect
from escapewheel_writer.sources.waveforms import WaveformSource

UNITS, CHANNELS, SAMPLES = 3, 5, 4
STREAM = "experiment1_Record Node 109#probeA_recording1.zarr"

#: Which channels the analyzer says each unit was computed on.
SUPPORT = {0: (1, 2), 1: (0, 3, 4), 2: (2,)}

#: The contacts, named as the sorting analyzer lists them.
CHANNEL_IDS = [f"CH{c}" for c in range(CHANNELS)]

#: A rate and a window that make `nbefore` a small round number: 2.0 ms at 1 kHz is 2 samples.
RATE, MS_BEFORE = 1000.0, 2.0
NBEFORE = 2


def _write(path: Path, values: np.ndarray, chunks: tuple[int, ...]) -> None:
    """Write a Zarr v2 array by path.

    A `LocalStore` rather than a string: a stream folder carries a `#`, which zarr reads as a URL
    fragment and which silently truncates the store root.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    written = zarr.create_array(
        store=zarr.storage.LocalStore(path), shape=values.shape, chunks=chunks, dtype=values.dtype, zarr_format=2
    )
    written[:] = values


def _attrs(path: Path, **payload) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".zattrs").write_text(json.dumps(payload))


def _templates(support: dict[int, tuple[int, ...]], skip: tuple[int, int] | None = None) -> np.ndarray:
    """A `(unit, sample, channel)` array, zero off each unit's support.

    A spike goes down, so the trough identifies the peak contact. It deepens along each unit's
    support, which puts the peak on the last contact rather than the first.
    """
    values = np.zeros((UNITS, SAMPLES, CHANNELS), dtype=np.float64)
    for unit, channels in support.items():
        for ordinal, channel in enumerate(channels):
            if skip == (unit, channel):
                continue
            trough = -3.0 * (ordinal + 1) * (unit + 1)
            values[unit, :, channel] = [1.0, 2.0, trough, 1.0][:SAMPLES]
    return values


def build(root: Path, *, mask: dict[int, tuple[int, ...]] | None = None, sd: bool = True) -> Path:
    """Write a miniature analyzer under `postprocessed/` and return the asset root."""
    an = root / "postprocessed" / STREAM
    _attrs(an, settings={"return_in_uV": True})
    _write(an / "sorting/unit_ids", np.arange(UNITS, dtype=np.int64), (UNITS,))
    held = SUPPORT if mask is None else mask
    sparsity = np.zeros((UNITS, CHANNELS), dtype=bool)
    for unit, channels in held.items():
        for channel in channels:
            sparsity[unit, channel] = True
    _write(an / "sparsity_mask", sparsity, (UNITS, CHANNELS))
    _write(an / "extensions/templates/average", _templates(SUPPORT), (2, SAMPLES, CHANNELS))
    if sd:
        _write(an / "extensions/templates/std", _templates(SUPPORT) * 0.1, (2, SAMPLES, CHANNELS))
    _attrs(an / "extensions/templates", params={"ms_before": MS_BEFORE, "ms_after": 2.0})
    _attrs(an / "recording_info", recording_attributes={"channel_ids": CHANNEL_IDS, "sampling_frequency": RATE})
    return root


@pytest.fixture
def asset(tmp_path: Path) -> Path:
    return build(tmp_path / "sorted")


def _source(root: Path, *, units: int = UNITS, **options) -> WaveformSource:
    return WaveformSource(
        root,
        session_id="s1",
        units=[{"device_name": "probeA", "local_unit_label": str(u), "unit_id": u} for u in range(units)],
        **options,
    )


# -- the arrays ------------------------------------------------------------------------


def test_mean_alone_is_one_array(asset: Path) -> None:
    source = _source(asset)
    assets = source.array_assets()
    assert [a["array_asset_id"] for a in assets] == ["waveform_mean"]
    assert len(source.array_dimensions()) == 3
    (staged,) = source.staged_arrays()
    # The build places and binds the array by this alone (Part 03 §11.3).
    assert assets[0]["resource_id"] == staged.resource_id == "core.waveform_mean"


def test_sd_is_a_second_array_of_the_same_shape(asset: Path) -> None:
    source = _source(asset, sd=True)
    assets = source.array_assets()
    assert [a["array_asset_id"] for a in assets] == ["waveform_mean", "waveform_sd"]
    # Quantised against its own peak, so the smaller quantity keeps its resolution.
    assert assets[1]["conversion"] < assets[0]["conversion"]
    staged = {s.array_asset_id: s for s in source.staged_arrays()}
    assert staged["waveform_sd"].values.shape == staged["waveform_mean"].values.shape


def test_sd_asked_for_and_absent_is_refused(tmp_path: Path) -> None:
    """A recipe that asks for the deviation and does not get it is a defect, not a note."""
    root = build(tmp_path / "sorted", sd=False)
    with pytest.raises(SourceDefect, match="std"):
        _source(root, sd=True).array_assets()


def test_an_asset_directory_is_accepted_as_well_as_postprocessed(asset: Path) -> None:
    assert _source(asset).offers() == _source(asset / "postprocessed").offers()


# -- the support is what the analyzer says, not what the values show --------------------


def test_a_contact_inside_the_mask_keeps_its_row_though_its_template_is_flat(tmp_path: Path) -> None:
    """The export cannot represent this: padded to every channel, a flat contact reads as absent.

    Unit 0 is masked on a third contact it has no signal on. The analyzer says the template was
    computed there, so the packet stores it -- a zero the sorter measured, not a gap.
    """
    root = build(tmp_path / "sorted", mask={**SUPPORT, 0: (1, 2, 3)})
    rows = [r for r in _source(root).unit_electrodes() if r["unit_id"] == 0]
    assert [r["electrode_id"] for r in rows] == ["probeA.CH1", "probeA.CH2", "probeA.CH3"]


def test_a_contact_outside_the_mask_is_not_stored_though_its_template_is_not_zero(tmp_path: Path) -> None:
    """The converse: scanning for non-zeros would keep a contact the analyzer excluded."""
    root = build(tmp_path / "sorted", mask={**SUPPORT, 1: (0, 3)})
    rows = [r for r in _source(root).unit_electrodes() if r["unit_id"] == 1]
    assert [r["electrode_id"] for r in rows] == ["probeA.CH0", "probeA.CH3"]


def test_contacts_are_named_as_the_sorting_run_names_them(asset: Path) -> None:
    """`<probe>.<channel>` is what `SorterSource.sorting_run_channels` composes, so the two agree."""
    rows = [r for r in _source(asset).unit_electrodes() if r["unit_id"] == 2]
    assert [r["electrode_id"] for r in rows] == ["probeA.CH2"]


def test_the_primary_contact_is_the_templates_own_trough(asset: Path) -> None:
    """The deepest trough, per unit, in the channel positions the packet actually stores."""
    rows = _source(asset).unit_electrodes()
    primary = {r["unit_id"]: r["channel_index"] for r in rows if r["is_primary"]}
    assert primary == {unit: len(channels) - 1 for unit, channels in SUPPORT.items()}


def test_every_unit_gets_exactly_one_primary(asset: Path) -> None:
    rows = _source(asset).unit_electrodes()
    counts = {unit: 0 for unit in SUPPORT}
    for row in rows:
        counts[row["unit_id"]] += bool(row["is_primary"])
    assert counts == {unit: 1 for unit in SUPPORT}


# -- what the analyzer states and the export does not ----------------------------------


def test_the_sample_axis_begins_where_the_analyzer_says_the_spike_is(asset: Path) -> None:
    """`ms_before` puts sample 0 at the spike. Reading the export, an importer can only assume
    the window is centred, which it is not: 3 ms before and 4 ms after on the measured session."""
    axis = next(a for a in _source(asset).array_dimensions() if a["axis_index"] == 2)
    assert axis["origin_value"] == -float(NBEFORE)
    assert axis["coordinate_unit"] == "{sample}"


def test_the_values_are_in_what_return_in_uv_declares(asset: Path) -> None:
    """The export writes `unit: volts` with no conversion on values that are microvolts."""
    asset_row = _source(asset).array_assets()[0]
    assert asset_row["unit"] == "uV"
    assert asset_row["sample_rate_hz"] == RATE


def test_adc_counts_are_a_ucum_annotation(tmp_path: Path) -> None:
    """Part 02 §8.4: `adc` is no UCUM code, and `{adc}` is a dimensionless one."""
    root = build(tmp_path / "sorted")
    _attrs(root / "postprocessed" / STREAM, settings={"return_in_uV": False})
    assert _source(root).array_assets()[0]["unit"] == "{adc}"


def test_an_analyzer_that_declares_no_unit_says_so(tmp_path: Path) -> None:
    root = build(tmp_path / "sorted")
    _attrs(root / "postprocessed" / STREAM)
    source = _source(root)
    assert source.array_assets()[0]["unit"] is None
    assert any("return_in_uV" in note for note in source.notes)


# -- units the build did not mint ------------------------------------------------------


def test_a_unit_matching_nothing_and_a_unit_masked_nowhere_are_counted_apart(tmp_path: Path) -> None:
    """One count for both would report a disagreement about which units exist as an empty mask."""
    root = build(tmp_path / "sorted", mask={**SUPPORT, 2: ()})
    source = WaveformSource(
        root,
        session_id="s1",
        units=[
            {"device_name": "probeA", "local_unit_label": "0", "unit_id": 0},
            {"device_name": "probeA", "local_unit_label": "2", "unit_id": 2},
        ],
    )
    source.array_assets()
    assert source.notes == [
        "units: 1 analyzer unit(s) match no unit in the packet's sorting; skipped",
        "units: 1 analyzer unit(s) are sparse on no contact at all; skipped",
    ]


@pytest.mark.parametrize("prefix", ["", "A_"])
def test_a_unit_the_build_harvested_resolves_under_a_prefix(tmp_path: Path, prefix: str) -> None:
    """The `units` term keys on the stream's own probe name, which a recipe's prefix does not reach.

    The prefix goes on identifiers and the names minted with them; `device_name` here is the
    source's label, so it matches `stream.device` bare however the sorter's rows were prefixed.
    """
    from types import SimpleNamespace

    from escapewheel_writer.session import Context, _harvest, _rows
    from escapewheel_writer.sources.sorter import SorterSource
    from tests import sorterfixture

    root = tmp_path / "sorted"
    labels = list(range(UNITS))
    sorterfixture.stream(
        root, STREAM.removesuffix(".zarr"), spikes=[(u, 10 * (u + 1)) for u in labels], unit_ids=labels, analyzer=False
    )
    build(root)
    sorter = SorterSource(root, session_id="s1", prefix=prefix)
    context = Context(session_id="s1")
    recipe = SimpleNamespace(session={}, subject={}, overrides={}, declared_facts={})
    _harvest(SimpleNamespace(kind="sorter"), sorter, context, recipe, _rows(sorter, sorter.records()))
    minted = {row["unit_id"] for row in sorter.units()}
    assert {row["unit_id"] for row in context.units} == minted

    source = WaveformSource(root, session_id="s1", prefix=prefix, units=context.units)
    assert {row["unit_id"] for row in source.records()["core.unit_electrodes"]} == minted
    assert source.notes == []


def test_no_unit_matching_at_all_is_a_defect(asset: Path) -> None:
    """An array of nothing is not an array, so the build stops rather than committing one."""
    source = WaveformSource(asset, session_id="s1", units=[])
    with pytest.raises(SourceDefect, match="matches the packet's sorting"):
        source.array_assets()


def test_an_asset_with_no_analyzer_is_a_defect(tmp_path: Path) -> None:
    with pytest.raises(SourceDefect, match="postprocessed"):
        _source(tmp_path / "empty")
