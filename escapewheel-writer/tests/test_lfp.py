"""The LFP source: external references, and the axes that make them readable."""

import json

import pytest

from escapewheel_writer.sources.lfp import LFPSource
from escapewheel_writer.sources.nwb import SourceDefect

CLOCK = "experiment1.Neuropix-PXI-100.45883-1.samples"
RATES = {CLOCK: 30000.0}


def _array(path, meta):
    path.mkdir(parents=True, exist_ok=True)
    (path / ".zarray").write_text(json.dumps(meta))


def _series(root, probe="45883-1", *, rows=1000, channels=2, compressor=None, step_hz=1250.0):
    """A minimal NWB-Zarr LFP series: data, timestamps, and an electrodes region."""
    import numcodecs
    import numpy as np

    series = root / "processing/ecephys/LFP" / f"ElectricalSeries{probe}-LFP"
    _array(
        series / "data",
        {
            "shape": [rows, channels],
            "chunks": [rows, channels],
            "dtype": "<i2",
            "zarr_format": 2,
            "compressor": compressor if compressor is not None else {"id": "blosc"},
            "filters": None,
            "order": "C",
            "fill_value": 0,
        },
    )
    (series / "data" / "0.0").write_bytes(b"\x00" * 16)
    (series / "data" / ".zattrs").write_text(json.dumps({"conversion": 2.34e-06, "offset": 0.0, "unit": "volts"}))

    stamps = np.arange(4, dtype=np.float64) / step_hz
    _array(
        series / "timestamps",
        {
            "shape": [4],
            "chunks": [4],
            "dtype": "<f8",
            "zarr_format": 2,
            "compressor": {"id": "zstd", "level": 1},
            "filters": None,
            "order": "C",
            "fill_value": 0.0,
        },
    )
    (series / "timestamps" / "0").write_bytes(numcodecs.Zstd(1).encode(stamps.tobytes()))

    region = np.arange(channels, dtype=np.int64)
    _array(
        series / "electrodes",
        {
            "shape": [channels],
            "chunks": [channels],
            "dtype": "<i8",
            "zarr_format": 2,
            "compressor": {"id": "zstd", "level": 1},
            "filters": None,
            "order": "C",
            "fill_value": 0,
        },
    )
    (series / "electrodes" / "0").write_bytes(numcodecs.Zstd(1).encode(region.tobytes()))
    return series


def _contacts(root, probe="45883-1", names=("CH0", "CH4")):
    """The electrode table the adapter names its contacts from, as the owning adapter reads it.

    `channel_name` alone repeats across probes, so a contact's name is the pair -- which is why
    both columns have to be here for a channel row to name an electrode at all.
    """
    from tests.nwbfixture import array, group

    contacts = group(root / "general/extracellular_ephys/electrodes")
    array(contacts / "group_name", [probe] * len(names), filter_id="vlen-utf8")
    array(contacts / "channel_name", list(names), filter_id="vlen-utf8")
    return contacts


@pytest.fixture
def nwb(tmp_path):
    root = tmp_path / "s.nwb"
    _series(root)
    _contacts(root)
    return root


def _source(root, **kwargs):
    kwargs.setdefault("clocks", [CLOCK])
    return LFPSource(root, session_id="s1", **kwargs)


def test_the_time_axis_is_ticks_on_the_probes_own_clock(nwb):
    """R20: three integers replace 7,983,750 float64 timestamps, and 24 is derived not assumed."""
    axis = _source(nwb).records(rates=RATES)["core.array_dimensions"][0]
    assert axis["clock_id"] == CLOCK
    assert (axis["origin_tick"], axis["step_tick_num"], axis["step_tick_den"]) == (0, 24, 1)


def test_the_step_comes_from_the_interval_not_the_values(nwb):
    """The sign fault ruins the timestamps' values; it leaves their spacing alone."""
    root = nwb.parent / "flipped.nwb"
    _series(root)
    _contacts(root)
    source = _source(root)
    # A different decimation must be read off the data rather than assumed.
    other = nwb.parent / "other.nwb"
    _series(other, step_hz=2500.0)
    _contacts(other)
    assert source.records(rates=RATES)["core.array_dimensions"][0]["step_tick_num"] == 24
    assert _source(other).records(rates=RATES)["core.array_dimensions"][0]["step_tick_num"] == 12


def test_a_non_integer_decimation_is_refused(nwb):
    """If a sample is not a whole number of probe ticks, this is not a decimation of it."""
    root = nwb.parent / "odd.nwb"
    _series(root, step_hz=1111.0)
    with pytest.raises(SourceDefect, match="not an integer"):
        _source(root).records(rates=RATES)


def test_the_channel_axis_points_at_the_channel_table(nwb):
    """LFP keeps every fourth contact, so the axis cannot be a range (R20 §2)."""
    axis = _source(nwb).records(rates=RATES)["core.array_dimensions"][1]
    assert axis["coordinate_resource"] == "core.array_channels"
    assert axis["coordinate_position_column"] == "channel_index"


def test_channels_name_electrodes_and_carry_the_acquisition_offset(nwb):
    rows = _source(nwb).records(rates=RATES)["core.array_channels"]
    assert [r["electrode_id"] for r in rows] == ["45883-1.CH0", "45883-1.CH4"]
    assert all(r["axis_index"] == 1 for r in rows)


def test_conversion_stays_on_the_asset(nwb):
    """One value per series here, so repeating it down the channels would buy nothing (Part 02 §6)."""
    got = _source(nwb).records(rates=RATES)
    assert got["core.array_assets"][0]["conversion"] == pytest.approx(2.34e-06)
    assert all(r.get("conversion") is None for r in got["core.array_channels"])


def test_the_reference_declares_zarr_v2_and_its_codec(nwb):
    """Part 03 §6.1: only an external resource may be v2, and Part 03 §6.4 declares its codecs per resource."""
    array = _source(nwb).external_arrays()["core.45883-1.lfp"]
    assert array.physical_profile == "zarr_v2"
    assert array.codecs == ("blosc",)
    assert array.uri.startswith("file://")


def test_a_uri_base_replaces_the_local_path(nwb):
    array = _source(nwb, uri_base="s3://bucket/s.nwb/").external_arrays()["core.45883-1.lfp"]
    assert array.uri == "s3://bucket/s.nwb/processing/ecephys/LFP/ElectricalSeries45883-1-LFP/data"


def test_an_unreachable_store_leaves_the_claim_unmade(nwb):
    """Part 04 §5.2: bytes beside the writer are not the bytes a remote URI names, so a store it
    cannot reach records nothing rather than what it measured of a local copy."""
    source = _source(nwb, uri_base="s3://bucket/s.nwb")
    array = source.external_arrays()["core.45883-1.lfp"]
    assert (array.size_bytes, array.sha256, array.verified_at) == (None, None, None)
    assert any("nothing verified" in n for n in source.notes)


def test_a_reachable_store_is_sized_whole(nwb):
    """Part 04 §5.4: a dense array asset is a prefix, so its size counts the metadata too."""
    array = _source(nwb).external_arrays()["core.45883-1.lfp"]
    on_disk = sum(
        f.stat().st_size
        for f in (nwb / "processing/ecephys/LFP" / "ElectricalSeries45883-1-LFP" / "data").rglob("*")
        if f.is_file()
    )
    assert array.size_bytes == on_disk
    assert array.verified_at is not None
    assert array.sha256 is None, "a digest reads every byte and is asked for separately"


def test_a_digest_is_recorded_when_asked(nwb):
    from escapewheel_validator.stores import digest

    array = _source(nwb, verify="sha256").external_arrays()["core.45883-1.lfp"]
    assert array.sha256 == digest(array.uri)


def test_verify_none_records_nothing(nwb):
    array = _source(nwb, verify="none").external_arrays()["core.45883-1.lfp"]
    assert (array.size_bytes, array.sha256, array.verified_at) == (None, None, None)


def test_an_unknown_verify_mode_is_refused(nwb):
    with pytest.raises(ValueError, match="verify must be"):
        _source(nwb, verify="md5")


def test_a_series_with_no_matching_clock_is_refused(nwb):
    with pytest.raises(SourceDefect, match="clocks end in"):
        _source(nwb, clocks=[]).records(rates=RATES)


def test_an_nwb_with_no_lfp_group_yields_nothing(tmp_path):
    source = _source(tmp_path / "empty.nwb")
    assert source.records(rates=RATES)["core.array_assets"] == []
    assert any("no series found" in n for n in source.notes)


def test_offers_counts_the_channels_it_can_supply(nwb):
    """Part 05 Stage 1 must name every resource a recipe has this source own, and the recipe
    owns `core.array_channels`. It was left out, so `inspect` under-reported the source."""
    source = _source(nwb)
    assert source.offers()["core.array_channels"] == len(source.array_channels())


def test_a_contact_the_source_cannot_name_is_refused(tmp_path):
    """A channel row naming no electrode ties an array axis to nothing, so the adapter refuses.

    Both columns are needed because a contact's name is the pair; the adapter owning
    `core.electrodes` reads them unguarded, so a file missing one fails the build either way.
    """
    root = tmp_path / "unnamed.nwb"
    _series(root)
    from tests.nwbfixture import array, group

    contacts = group(root / "general/extracellular_ephys/electrodes")
    array(contacts / "channel_name", ["CH0", "CH4"], filter_id="vlen-utf8")
    with pytest.raises(SourceDefect, match="group_name"):
        _source(root).records(rates=RATES)


def test_init_can_draft_an_lfp_source(nwb):
    """It is the only kind that produces external resources, so it is the only one whose
    `uri_base` and `verify` a recipe has to set — and it could not be drafted at all."""
    from escapewheel_writer.scripts.cli import HINTS, KINDS, _open

    assert "lfp" in KINDS
    assert _open("lfp", nwb, "s1").offers() == _source(nwb).offers()
    assert any("verify" in hint for hint in HINTS["lfp"])


def test_members_records_what_the_prefix_held(nwb):
    """Part 04 §5.4: the listing already enumerates, so recording it costs no extra request."""
    from escapewheel_validator.stores import listing

    array = _source(nwb, verify="members").external_arrays()["core.45883-1.lfp"]
    held = listing(array.uri)
    assert array.members is not None
    assert [m["key"] for m in array.members] == [m.key for m in held.members]
    assert sum(m["size_bytes"] for m in array.members) == array.size_bytes


def test_a_local_store_offers_no_content_hash(nwb):
    """A filesystem has no ETag, so members record size only and the source says so."""
    source = _source(nwb, verify="members")
    array = source.external_arrays()["core.45883-1.lfp"]
    assert all("store_digest" not in m for m in array.members)
    assert any("offered no content hash" in note for note in source.notes)


def test_size_records_no_members(nwb):
    """The levels are cumulative, so the one below records nothing of the one above."""
    assert _source(nwb, verify="size").external_arrays()["core.45883-1.lfp"].members is None


def test_a_digest_also_records_the_members_it_digested(nwb):
    """Part 04 §5.4: where both are present the digested listing must be the declared one."""
    array = _source(nwb, verify="sha256").external_arrays()["core.45883-1.lfp"]
    assert array.sha256 is not None and array.members is not None
