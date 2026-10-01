"""Zarr v3 layout for a real dense array: 6,781 unit waveforms.

`realistic.py` measures codecs on synthetic noise, which is the hard case for compression.
This is the other kind of dense array a packet carries and it behaves oppositely: a unit's
waveform is sparse over channels -- signal on the contacts it sits near, zero elsewhere -- so
93% of the rectangle is exactly zero, and the layout question is chunk shape as much as codec.

Source: `units/waveform_mean` of ecephys_776259_2025-04-09, (6781, 150, 384) float64, which
round-trips through float32 with zero error.
"""

import shutil
import time
from pathlib import Path

import numpy as np
import zarr
from zarr.codecs import BloscCodec, BytesCodec, GzipCodec, ShardingCodec, ZstdCodec

NWB = Path(
    "/mnt/Data/escapewheel/ecephys_776259_2025-04-09_17-25-12_nwb_2026-08-17_09-30-31/"
    "ecephys_776259_2025-04-09_17-25-12_experiment1_recording1.nwb"
)
OUT = Path("/mnt/Data/escapewheel/scratch/waveforms")

#: (label, dtype, chunks, codecs, shard)
LAYOUTS = [
    (
        "source shape, f64, blosc",
        "float64",
        (424, 19, 48),
        [BloscCodec(cname="zstd", shuffle="shuffle")],
        None,
    ),
    (
        "source shape, f32, blosc",
        "float32",
        (424, 19, 48),
        [BloscCodec(cname="zstd", shuffle="shuffle")],
        None,
    ),
    ("unit chunks, f32, none", "float32", (1, 150, 384), [], None),
    ("unit chunks, f32, gzip", "float32", (1, 150, 384), [GzipCodec()], None),
    ("unit chunks, f32, zstd", "float32", (1, 150, 384), [ZstdCodec()], None),
    (
        "unit chunks, f32, blosc",
        "float32",
        (1, 150, 384),
        [BloscCodec(cname="zstd", shuffle="shuffle")],
        None,
    ),
    ("unit chunks + shard 64", "float32", (1, 150, 384), [ZstdCodec()], (64, 150, 384)),
    (
        "unit chunks + shard 512",
        "float32",
        (1, 150, 384),
        [ZstdCodec()],
        (512, 150, 384),
    ),
    ("64-unit chunks, f32, zstd", "float32", (64, 150, 384), [ZstdCodec()], None),
    # int16 with a derived scale, which is what the samples averaged actually were. The step
    # sits 20x below the standard error of the mean it stores, so the discarded bits were
    # never measured; `core.array_assets.conversion` carries the scale back.
    ("unit chunks, i16, zstd", "int16", (1, 150, 384), [ZstdCodec()], None),
    ("i16 + shard 512", "int16", (1, 150, 384), [ZstdCodec()], (512, 150, 384)),
    ("i16 64-unit chunks", "int16", (64, 150, 384), [ZstdCodec()], None),
]

#: Microvolts per LSB when storing int16, derived from the data rather than fixed so that no
#: session can clip. See `bench/wf_int.py` for the error budget.
SCALE = None


def build(label, dtype, chunks, codecs, shard, data):
    path = OUT / label.replace(" ", "_").replace(",", "")
    if path.exists():
        shutil.rmtree(path)
    if shard is None:
        serializer, chunk_shape = [BytesCodec(), *codecs], chunks
    else:
        # Part 03 §6.4 permits sharding_indexed: many small chunks inside few files.
        serializer, chunk_shape = (
            [ShardingCodec(chunk_shape=chunks, codecs=[BytesCodec(), *codecs])],
            shard,
        )
    start = time.perf_counter()
    array = zarr.create_array(
        store=str(path),
        shape=data.shape,
        dtype=dtype,
        chunks=chunk_shape,
        serializer=serializer[0],
        compressors=serializer[1:] or None,
        fill_value=0,
    )
    array[:] = data
    return path, time.perf_counter() - start


def size(path):
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def files(path):
    return sum(1 for f in path.rglob("*") if f.is_file())


def read_patterns(path, picked):
    """What a consumer actually asks a waveform array for."""
    array = zarr.open_array(str(path), mode="r")
    out = {}
    for label, fn in (
        ("1 unit", lambda a: a[picked[0]]),
        ("24 units", lambda a: a[picked]),
        ("1 channel, all units", lambda a: a[:, :, 191]),
    ):
        best = float("inf")
        for _ in range(3):
            start = time.perf_counter()
            fn(array)
            best = min(best, time.perf_counter() - start)
        out[label] = best
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = zarr.open_array(str(NWB / "units" / "waveform_mean"), mode="r", zarr_format=2)
    data = np.asarray(source[:])
    print(f"source {data.shape} {data.dtype}  {data.nbytes / 1e9:.2f} GB raw, {(data == 0).mean() * 100:.1f}% zero\n")
    picked = np.arange(24) * 211  # spread over the array, not one chunk
    global SCALE
    SCALE = float(np.abs(data).max()) / 32767.0
    print(f"int16 scale {SCALE:.6f} uV/LSB, so the peak {np.abs(data).max():.1f} uV just fits\n")

    header = f"{'layout':28s} {'MB':>8s} {'files':>7s} {'write':>7s}"
    for label in ("1 unit", "24 units", "1 channel, all units"):
        header += f" {label:>21s}"
    print(header)
    for label, dtype, chunks, codecs, shard in LAYOUTS:
        payload = np.rint(data / SCALE).astype(dtype) if dtype == "int16" else data.astype(dtype)
        path, wrote = build(label, dtype, chunks, codecs, shard, payload)
        times = read_patterns(path, picked)
        row = f"{label:28s} {size(path) / 1e6:8.1f} {files(path):7,} {wrote:6.1f}s"
        for value in times.values():
            row += f" {value * 1000:18.1f}ms"
        print(row, flush=True)


if __name__ == "__main__":
    main()
