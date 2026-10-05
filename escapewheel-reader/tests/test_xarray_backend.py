"""A packet's dense arrays as xarray objects, their axes as coordinates."""

from fractions import Fraction

import numpy as np
import pytest
import xarray as xr
import zarr
from packet_fixture import CLOCK_PROBE, SESSION

from escapewheel_reader.resources import ArrayResource
from escapewheel_reader.xarray_backend import EscapewheelBackend, TickIndex, Ticks

from .conftest import LFP, WAVE

ENGINE = "escapewheel"


def _write(packet, resource_id, values):
    zarr.open_array(packet.array_resource(resource_id).path, mode="r+")[...] = values
    return values


def _open(packet, resource_id, **kwargs):
    return xr.open_dataset(packet, engine=ENGINE, resource_id=resource_id, **kwargs)


@pytest.fixture
def waves(array_packet):
    packet = array_packet()
    return packet, _write(packet, "core.waveform_mean", np.arange(24, dtype=np.int16).reshape(2, 3, 4))


@pytest.fixture
def lfp(array_packet):
    packet = array_packet()
    return packet, _write(packet, "core.lfp", np.arange(12, dtype=np.int16).reshape(4, 3))


def test_the_engine_is_registered():
    assert isinstance(xr.backends.list_engines()[ENGINE], EscapewheelBackend)


def test_opening_reads_no_values(waves, monkeypatch):
    packet, stored = waves
    reads = []
    real = ArrayResource.open
    monkeypatch.setattr(ArrayResource, "open", lambda self: reads.append(self.resource_id) or real(self))
    dataset = _open(packet, "core.waveform_mean")
    unit = dataset.waveform_mean.sel(unit_id=12)
    assert reads == []
    assert unit.values[:2].tolist() == stored[1, :2].tolist()
    assert reads == ["core.waveform_mean"]


# -- labelled axes -------------------------------------------------------------------------


def test_an_independent_axis_is_indexed_by_its_labels(waves):
    dataset = _open(waves[0], "core.waveform_mean")
    assert dataset.waveform_mean.dims == ("unit", "channel", "sample")
    assert "unit_id" in dataset.xindexes and dataset.unit_id.values.tolist() == [11, 12]
    assert dataset.unit_id.attrs["resource"] == "core.units"


def test_a_dependent_axis_labels_each_units_own_contacts(waves):
    """The labels vary along the unit axis, and the padded position is marked absent."""
    dataset = _open(waves[0], "core.waveform_mean")
    assert dataset.electrode_id.dims == ("unit", "channel")
    assert dataset.electrode_id.values[0].tolist() == [102, 100, 103]
    assert dataset.electrode_id.values[1, :2].tolist() == [101, 103]
    assert dataset.channel_present.values.tolist() == [[True, True, True], [True, True, False]]
    assert "electrode_id" not in dataset.xindexes


def test_padding_reads_as_nan(waves):
    """Every integer is a stored value, so only a float can say a position holds none."""
    packet, stored = waves
    second = _open(packet, "core.waveform_mean").waveform_mean.sel(unit_id=12)
    assert second.dtype == np.float64
    assert np.isnan(second.values[2]).all()
    assert second.values[:2].tolist() == stored[1, :2].tolist()
    assert np.isnan(second.isel(channel=2, sample=1).item())


def test_padding_is_stored_values_without_mask_and_scale(waves):
    packet, stored = waves
    dataset = _open(packet, "core.waveform_mean", mask_and_scale=False)
    assert dataset.waveform_mean.dtype == np.int16
    assert dataset.waveform_mean.values.tolist() == stored.tolist()


def test_columns_of_the_labelled_rows_become_coordinates(waves):
    dataset = _open(waves[0], "core.waveform_mean", columns={"channel": "electrode_name"})
    assert dataset.electrode_name.dims == ("unit", "channel")
    names = dataset.electrode_name.values
    assert names[0].tolist() == ["e102", "e100", "e103"] and names[1, :2].tolist() == ["e101", "e103"]
    assert dataset.electrode_name.isnull().values.tolist() == [[False, False, False], [False, False, True]]


@pytest.mark.parametrize(
    "columns",
    [{"channel": ["no_such"]}, {"sample": ["electrode_name"]}, {"time": ["x"]}],
    ids=["column", "axis", "dim"],
)
def test_a_column_the_axis_cannot_carry_is_refused(waves, columns):
    with pytest.raises(ValueError):
        _open(waves[0], "core.waveform_mean", columns=columns)


# -- numeric and irregular axes --------------------------------------------------------------


def test_a_numeric_axis_is_selected_by_value(waves):
    packet, stored = waves
    dataset = _open(packet, "core.waveform_mean")
    assert dataset.sample.values.tolist() == [-1.0, 0.0, 1.0, 2.0]
    assert dataset.sample.attrs["units"] == "{sample}"
    assert dataset.waveform_mean.sel(unit_id=11, sample=0).values.tolist() == stored[0, :, 1].tolist()


def test_an_irregular_axis_reads_its_coordinate_array_scaled(array_packet):
    """The sample axis names a 1-D array whose stored values are half-milliseconds."""

    def irregular(rows):
        session = {"session_id": SESSION, "array_asset_id": 40}
        rows["core.array_assets"].append(
            {**session, "resource_id": "core.sample_times", "unit": "ms", "conversion": 0.5}
        )
        rows["core.array_dimensions"].append(
            {**session, "axis_index": 0, "dimension_name": "sample", "origin_value": 0.0, "step_value": 1.0}
            | {"coordinate_unit": "1"}
        )
        (sample,) = [r for r in rows["core.array_dimensions"] if r["array_asset_id"] == WAVE and r["axis_index"] == 2]
        sample.update(origin_value=None, step_value=None, coordinate_unit=None, coordinate_array_asset_id=40)

    packet = array_packet(irregular, {"core.sample_times": ("core", (4,))})
    _write(packet, "core.sample_times", np.array([0, 2, 5, 9], dtype=np.int16))
    sample = _open(packet, "core.waveform_mean").sample
    assert sample.values.tolist() == [0.0, 1.0, 2.5, 4.5]
    assert sample.attrs["units"] == "ms"


# -- tick axes -------------------------------------------------------------------------------


def test_a_tick_axis_computes_its_ticks(lfp):
    """937.5 ticks per sample puts every other sample between ticks, so the ticks are floats."""
    tick = _open(lfp[0], "core.lfp").tick
    assert isinstance(tick.to_index().array, object)
    assert tick.values.tolist() == [1000, 1937.5, 2875, 3812.5]
    assert tick.attrs["clock_id"] == CLOCK_PROBE
    assert isinstance(_open(lfp[0], "core.lfp").xindexes["tick"], TickIndex)


def test_a_tick_window_is_closed_and_exact(lfp):
    dataset = _open(lfp[0], "core.lfp")
    assert dataset.sel(tick=slice(1000, 2875)).tick.values.tolist() == [1000, 1937.5, 2875]
    assert dataset.sel(tick=slice(1000.5, 2874.99)).tick.values.tolist() == [1937.5]
    assert dataset.sel(tick=slice(5000, None)).sizes["time"] == 0


def test_a_tick_selects_only_the_position_it_names(lfp):
    dataset = _open(lfp[0], "core.lfp")
    assert dataset.sel(tick=1937.5).tick.item() == 1937.5
    assert dataset.sel(tick=[2875, 1000]).tick.values.tolist() == [2875, 1000]
    assert dataset.sel(tick=1001, method="nearest").tick.item() == 1000
    with pytest.raises(KeyError):
        dataset.sel(tick=1001)


def test_a_slice_keeps_the_tick_index(lfp):
    sliced = _open(lfp[0], "core.lfp").isel(time=slice(1, None, 2))
    assert isinstance(sliced.xindexes["tick"], TickIndex)
    assert sliced.tick.values.tolist() == [1937.5, 3812.5]
    assert sliced.sel(tick=slice(3000, None)).tick.values.tolist() == [3812.5]


def test_a_whole_step_far_from_its_origin_stays_exact():
    """Ticks are int64 where they can be, and a window bound is compared exactly at any distance."""
    origin, size = 2**53 + 1, 1_000_000_000
    ticks = Ticks("tick", "time", size, Fraction(origin), Fraction(3))
    index = TickIndex(ticks)
    assert ticks.dtype == np.int64
    assert ticks.forward({"time": np.array([0, size - 1])})["tick"].tolist() == [origin, origin + 3 * (size - 1)]
    window = index.sel({"tick": slice(origin + 3, origin + 8)}).dim_indexers["time"]
    assert (window.start, window.stop) == (1, 3)


def test_scaling_declared_on_the_array_is_applied(lfp):
    """Stored 3 becomes 3 * 2.0 + 0.5 uV."""
    packet, stored = lfp
    values = _open(packet, "core.lfp").lfp
    assert values.attrs["units"] == "uV"
    assert values.values.tolist() == (stored * 2.0 + 0.5).tolist()
    raw = _open(packet, "core.lfp", mask_and_scale=False).lfp
    assert raw.values.tolist() == stored.tolist()
    assert (raw.attrs["scale_factor"], raw.attrs["add_offset"]) == (2.0, 0.5)


def test_scaling_declared_per_channel_follows_the_selection(array_packet):
    """Each channel's own conversion, however the channel axis is selected."""

    def per_channel(rows):
        rows["core.array_channels"] = [
            {"session_id": SESSION, "array_asset_id": LFP, "axis_index": 1, "channel_index": i, "unit": "uV"}
            | {"conversion": float(i + 1)}
            for i in range(3)
        ]
        (asset,) = [r for r in rows["core.array_assets"] if r["array_asset_id"] == LFP]
        asset.update(unit=None, conversion=None, offset=None)

    packet = array_packet(per_channel)
    stored = _write(packet, "core.lfp", np.arange(12, dtype=np.int16).reshape(4, 3))
    values = _open(packet, "core.lfp").lfp
    assert values.attrs["units"] == "uV"
    assert values.values.tolist() == (stored * [1.0, 2.0, 3.0]).tolist()
    assert values.isel(channel=2).values.tolist() == (stored[:, 2] * 3.0).tolist()
    assert values.isel(time=1, channel=[2, 0]).values.tolist() == [stored[1, 2] * 3.0, stored[1, 0] * 1.0]
    raw = _open(packet, "core.lfp", mask_and_scale=False)
    assert raw.conversion.values.tolist() == [1.0, 2.0, 3.0]


# -- several arrays ------------------------------------------------------------------------


def test_arrays_disagreeing_on_a_dimension_are_refused(waves):
    """The rates order the units 12, 11 and the waveforms 11, 12, so no exact alignment exists."""
    with pytest.raises(ValueError):
        _open(waves[0], ["core.waveform_mean", "analysis.unit_rates"])


def test_arrays_sharing_their_axes_open_as_one_dataset(array_packet):
    def with_sd(rows):
        for table in ("core.array_dimensions", "core.array_labels"):
            rows[table] += [{**r, "array_asset_id": 32} for r in rows[table] if r["array_asset_id"] == WAVE]
        rows["core.array_assets"].append(
            {"session_id": SESSION, "array_asset_id": 32, "resource_id": "core.waveform_sd"}
        )

    packet = array_packet(with_sd, {"core.waveform_sd": ("core", (2, 3, 4))})
    dataset = _open(packet, ["core.waveform_mean", "core.waveform_sd"])
    assert set(dataset.data_vars) == {"waveform_mean", "waveform_sd"}
    assert dataset.waveform_sd.attrs["resource_id"] == "core.waveform_sd"


def test_a_tree_has_a_node_per_array(waves):
    tree = xr.open_datatree(waves[0], engine=ENGINE)
    assert sorted(node.path for node in tree.leaves) == ["/analysis/unit_rates", "/core/lfp", "/core/waveform_mean"]
    assert tree["core/waveform_mean"].unit_id.values.tolist() == [11, 12]


def test_a_packet_root_opens_by_path(waves):
    root = waves[0].array_resource("core.lfp").path.parents[1]
    assert EscapewheelBackend().guess_can_open(root)
    assert not EscapewheelBackend().guess_can_open(root / "arrays")
    assert not EscapewheelBackend().guess_can_open("s3://bucket/packet")
    assert _open(str(root), "core.lfp").lfp.shape == (4, 3)


def test_naming_no_array_lists_them(waves):
    with pytest.raises(ValueError, match="core.waveform_mean"):
        xr.open_dataset(waves[0], engine=ENGINE)
