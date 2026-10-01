"""A dense array is written as Zarr v3 with the shard its size calls for."""

from tests.builders import waveform_values


def test_a_codec_outside_the_reader_floor_is_written(tmp_path):
    """Part 03 §6.4: the Zarr reader floor is not a writer ceiling."""
    from escapewheel_writer.arrays import declared_codecs
    from escapewheel_writer.bindings import StagedArray

    spec = StagedArray(
        values=waveform_values(),
        resource_id="core.wf",
        declaration_id="core.array_asset_instances",
        array_asset_id="wf",
        chunks=(1, 4, 10),
        codecs=("numcodecs.delta", "zstd"),
    )
    assert declared_codecs(spec) == ("numcodecs.delta", "zstd")

    from escapewheel_writer.arrays import write_zarr

    written = write_zarr(tmp_path / "wf.zarr", spec)
    assert written > 0
    import zarr

    assert (zarr.open(tmp_path / "wf.zarr", mode="r")[:] == spec.values).all()


def test_shard_size_follows_the_bandwidth_delay_product():
    """The rule is `S = share/(1-share) * latency * bandwidth`, not a constant.

    A store read from inside the same region has an order less latency and more bandwidth, so
    the object that spends the same fraction of a fetch on transfer is several times smaller.
    A number baked in would be wrong exactly where the data lives.
    """
    from escapewheel_writer.arrays import shard_for, target_object_bytes

    off = target_object_bytes()
    near = target_object_bytes(latency_s=0.005, bandwidth_bps=100e6)
    assert off > near * 2
    far = shard_for((6781, 26, 150), (1, 26, 150), 3850)
    close = shard_for((6781, 26, 150), (1, 26, 150), 3850, target_bytes=near)
    assert far is not None and close is not None
    assert far[0] > close[0]


def test_a_power_of_two_is_preferred_only_inside_the_band():
    from escapewheel_writer.arrays import BAND, shard_for, target_object_bytes

    target = target_object_bytes()
    chosen = shard_for((6781, 26, 150), (1, 26, 150), 3850)
    assert chosen is not None
    per = chosen[0]
    assert per & (per - 1) == 0, "a power of two was available inside the band"
    assert target / BAND <= per * 3850 <= target * BAND


def test_an_array_that_fits_one_object_is_not_sharded():
    """A shard would add an index and buy nothing."""
    from escapewheel_writer.arrays import shard_for

    assert shard_for((100, 26, 150), (1, 26, 150), 3850) is None
