"""What `WaveformSource` stores, and what it refuses.

The adapter's contract is that both arrays describe one channel axis: the deviation is cut on
the mean's support, so position *k* names the same contact in each and one `core.unit_electrodes`
row serves both. The fixture makes that testable by giving one unit a contact the mean has signal
on and the deviation does not, which is the real file's case -- 52 such cells in 2,603,904.
"""

import json
from pathlib import Path

import numpy as np
import pytest
import zarr

from escapewheel_writer.sources import SourceDefect
from escapewheel_writer.sources.waveforms import WaveformSource
from tests.nwbfixture import array, group

UNITS, CHANNELS, SAMPLES = 3, 5, 4

#: Which source channels each unit has signal on in `waveform_mean`.
SUPPORT = {0: (1, 2), 1: (0, 3, 4), 2: (2,)}

#: Live in the mean and zero in the deviation, as the real file's 52 cells are.
MEAN_ONLY = (1, 4)

#: What the file says the peak is, chosen to be wrong in both of the ways the real one is:
#: unit 0's value names a contact in the support that is not the peak, and unit 1's names one
#: outside the support entirely. Unit 2's is right. The adapter reads none of them.
EXTREMUM = [1, 1, 2]


def _dense(support: dict[int, tuple[int, ...]], skip: tuple[int, int] | None = None) -> np.ndarray:
    """A `(unit, sample, channel)` array, zero off each unit's support as the NWB pads it.

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


def _wide(path: Path, values: np.ndarray) -> None:
    """Write a rank-3 Zarr v2 array, which is the form hdmf-zarr writes and the adapter opens."""
    written = zarr.create_array(
        store=str(path), shape=values.shape, chunks=(2, *values.shape[1:]), dtype="<f8", zarr_format=2
    )
    written[:] = values


@pytest.fixture
def nwb(tmp_path: Path) -> Path:
    """A miniature `units/` group with everything the adapter reads."""
    root = tmp_path / "session.nwb"
    units = group(root / "units")
    _wide(units / "waveform_mean", _dense(SUPPORT))
    _wide(units / "waveform_sd", _dense(SUPPORT, skip=MEAN_ONLY) * 0.1)
    array(units / "device_name", ["probeA"] * UNITS, filter_id="vlen-utf8")
    array(units / "ks_unit_id", np.arange(UNITS, dtype="<i8"))
    array(units / "electrodes", np.arange(UNITS * CHANNELS, dtype="<i8"))
    array(units / "electrodes_index", np.arange(1, UNITS + 1, dtype="<i8") * CHANNELS)
    array(units / "extremum_channel_index", np.array(EXTREMUM, dtype="<i8"))
    # The electrode table the adapter names its contacts from, one row per (unit, channel) cell
    # the ragged `electrodes` region indexes. `channel_name` alone repeats across probes, so the
    # name is the pair, composed as the adapter owning `core.electrodes` composes it.
    contacts = group(root / "general/extracellular_ephys/electrodes")
    array(contacts / "group_name", ["probeA"] * (UNITS * CHANNELS), filter_id="vlen-utf8")
    array(contacts / "channel_name", [str(row) for row in range(UNITS * CHANNELS)], filter_id="vlen-utf8")
    (root / ".zgroup").write_text(json.dumps({"zarr_format": 2}))
    return root


def _source(root: Path, **options) -> WaveformSource:
    return WaveformSource(
        root,
        session_id="s1",
        units={("probeA", str(u)): {"unit_id": u} for u in range(UNITS)},
        **options,
    )


def test_mean_alone_is_one_array(nwb: Path) -> None:
    """Without `sd` the adapter is what it was: one asset, one array, three axes."""
    source = _source(nwb)
    assets = source.array_assets()
    assert [a["array_asset_id"] for a in assets] == ["waveform_mean"]
    assert assets[0]["uri"] == "arrays/core/waveform_mean.zarr"
    assert len(source.array_dimensions()) == 3
    assert [s.array_asset_id for s in source.staged_arrays()] == ["waveform_mean"]


def test_sd_is_a_second_array_of_the_same_shape(nwb: Path) -> None:
    """Both arrays are stored, each with its own scale and its own three axes."""
    source = _source(nwb, sd=True)
    assets = source.array_assets()
    assert [a["array_asset_id"] for a in assets] == ["waveform_mean", "waveform_sd"]
    assert [a["semantic_type"] for a in assets] == ["waveform_mean", "waveform_sd"]
    assert assets[1]["uri"] == "arrays/core/waveform_sd.zarr"
    # Quantised against its own peak, so the smaller quantity keeps its resolution.
    assert assets[1]["conversion"] < assets[0]["conversion"]

    staged = {s.array_asset_id: s for s in source.staged_arrays()}
    assert set(staged) == {"waveform_mean", "waveform_sd"}
    assert staged["waveform_sd"].values.shape == staged["waveform_mean"].values.shape

    axes = source.array_dimensions()
    assert len(axes) == 6
    for asset in ("waveform_mean", "waveform_sd"):
        channel = next(a for a in axes if a["array_asset_id"] == asset and a["axis_index"] == 1)
        assert channel["coordinate_resource"] == "core.unit_electrodes"


def test_sd_is_cut_on_the_means_support(nwb: Path) -> None:
    """A contact the mean has and the deviation does not keeps its position, holding zeros.

    Recomputing the support per array is what would shift every later contact of that unit by
    one, so a `channel_index` would name a different electrode in each array.
    """
    source = _source(nwb, sd=True)
    staged = {s.array_asset_id: s for s in source.staged_arrays()}
    unit, channel = MEAN_ONLY
    position = SUPPORT[unit].index(channel)
    assert staged["waveform_mean"].values[unit, position].any()
    assert not staged["waveform_sd"].values[unit, position].any()
    # The support is the mean's, so it is still this unit's full width in both.
    rows = [r for r in source.unit_electrodes() if r["unit_id"] == unit]
    assert len(rows) == len(SUPPORT[unit])
    assert [r["channel_index"] for r in rows] == list(range(len(SUPPORT[unit])))


def test_sd_asked_for_and_absent_is_refused(nwb: Path) -> None:
    """A recipe that asks for the deviation and does not get it is a defect, not a note."""
    import shutil

    shutil.rmtree(nwb / "units" / "waveform_sd")
    with pytest.raises(SourceDefect, match="waveform_sd"):
        _source(nwb, sd=True).array_assets()


def test_the_primary_contact_is_the_templates_own_trough(nwb: Path) -> None:
    """The deepest trough, per unit, in the channel positions the packet actually stores."""
    rows = _source(nwb).unit_electrodes()
    primary = {r["unit_id"]: r["channel_index"] for r in rows if r["is_primary"]}
    assert primary == {unit: len(channels) - 1 for unit, channels in SUPPORT.items()}


def test_every_unit_gets_exactly_one_primary(nwb: Path) -> None:
    """R81 §2.7 struck `default_electrode_id` on the grounds that this column carries the fact.

    A unit with none is what the real session had for 609 of 6,781 -- the file's index landing
    outside the support, so no row matched it and the fact went missing rather than wrong.
    """
    rows = _source(nwb).unit_electrodes()
    counts = {unit: 0 for unit in SUPPORT}
    for row in rows:
        counts[row["unit_id"]] += bool(row["is_primary"])
    assert counts == {unit: 1 for unit in SUPPORT}


def test_the_files_extremum_column_is_not_read(nwb: Path) -> None:
    """It counts the channels the sorting kept, and the packet's positions count the support.

    Changing it changes nothing, which is the regression: read as a contact it named the wrong
    electrode for 5,071 of 6,781 units on the measured session.
    """
    before = _source(nwb).unit_electrodes()
    array(nwb / "units" / "extremum_channel_index", np.array([0, 0, 0], dtype="<i8"))
    assert _source(nwb).unit_electrodes() == before
