"""Build a miniature NWB-Zarr LFP series, and the electrode table its contacts are named from."""

import json

import numcodecs
import numpy as np
from nwbfixture import array, group

from escapewheel_writer.sources.lfp import LFPSource

CLOCK = "experiment1.Neuropix-PXI-100.45883-1.samples"
#: The clock's own `core.clocks` row, which is what a build supplies (Part 12 §4).
CLOCK_ROW = {"clock_id": CLOCK, "session_id": "s1", "origin": "sample 0", "tick_rate_num": 30000, "tick_rate_den": 1}


def _array(path, meta):
    path.mkdir(parents=True, exist_ok=True)
    (path / ".zarray").write_text(json.dumps(meta))


def series(root, probe="45883-1", *, rows=1000, channels=2, compressor=None, step_hz=1250.0):
    """A minimal NWB-Zarr LFP series: data, timestamps, and an electrodes region."""
    folder = root / "processing/ecephys/LFP" / f"ElectricalSeries{probe}-LFP"
    _array(
        folder / "data",
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
    (folder / "data" / "0.0").write_bytes(b"\x00" * 16)
    (folder / "data" / ".zattrs").write_text(json.dumps({"conversion": 2.34e-06, "offset": 0.0, "unit": "volts"}))

    stamps = np.arange(4, dtype=np.float64) / step_hz
    _array(
        folder / "timestamps",
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
    (folder / "timestamps" / "0").write_bytes(numcodecs.Zstd(1).encode(stamps.tobytes()))

    region = np.arange(channels, dtype=np.int64)
    _array(
        folder / "electrodes",
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
    (folder / "electrodes" / "0").write_bytes(numcodecs.Zstd(1).encode(region.tobytes()))
    return folder


def contacts(root, probe="45883-1", names=("CH0", "CH4")):
    """The electrode table the adapter names its contacts from, as the owning adapter reads it.

    `channel_name` alone repeats across probes, so a contact's name is the pair -- which is why
    both columns have to be here for a channel row to name an electrode at all.
    """
    table = group(root / "general/extracellular_ephys/electrodes")
    array(table / "group_name", [probe] * len(names), filter_id="vlen-utf8")
    array(table / "channel_name", list(names), filter_id="vlen-utf8")
    return table


def source(root, **kwargs):
    """The LFP adapter over `root`, supplied the one clock unless `clocks` says otherwise."""
    kwargs.setdefault("clocks", [CLOCK_ROW])
    return LFPSource(root, session_id="s1", **kwargs)
