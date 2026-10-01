import json
import pathlib
import shutil

import numcodecs
import numpy as np
import zarr
from zarr.codecs import BloscCodec, GzipCodec, ZstdCodec

root = pathlib.Path(__file__).parent / "arrays"
if root.exists():
    shutil.rmtree(root)
root.mkdir(parents=True)

# ephys-shaped int16: (time, channel)
shape, chunks = (2000, 384), (500, 384)
data = ((np.arange(np.prod(shape), dtype=np.int64) % 4001) - 2000).astype(np.int16).reshape(shape)
expected = int(data.astype(np.int64).sum())

configs = [
    ("v3_raw", dict(zarr_format=3, compressors=None)),
    ("v3_gzip", dict(zarr_format=3, compressors=[GzipCodec(level=5)])),
    ("v3_zstd", dict(zarr_format=3, compressors=[ZstdCodec(level=3)])),
    (
        "v3_blosc_zstd_shuffle",
        dict(
            zarr_format=3,
            compressors=[BloscCodec(cname="zstd", clevel=3, shuffle="shuffle")],
        ),
    ),
    (
        "v3_sharded_zstd",
        dict(zarr_format=3, compressors=[ZstdCodec(level=3)], shards=(1000, 384)),
    ),
    ("v2_zstd", dict(zarr_format=2, compressors=numcodecs.Zstd(level=3))),
    (
        "v2_blosc_zstd_shuffle",
        dict(
            zarr_format=2,
            compressors=numcodecs.Blosc(cname="zstd", clevel=3, shuffle=numcodecs.Blosc.SHUFFLE),
        ),
    ),
]

results = {}
for name, kw in configs:
    try:
        a = zarr.create_array(store=str(root / name), shape=shape, dtype="int16", chunks=chunks, **kw)
        a[:] = data
        nfiles = sum(1 for p in (root / name).rglob("*") if p.is_file())
        nbytes = sum(p.stat().st_size for p in (root / name).rglob("*") if p.is_file())
        results[name] = dict(written=True, files=nfiles, bytes=nbytes)
        print(f"{name:26s} OK   files={nfiles:5d}  bytes={nbytes:9d}")
    except Exception as e:
        results[name] = dict(written=False, error=f"{type(e).__name__}: {e}")
        print(f"{name:26s} FAIL {type(e).__name__}: {e}")

(root / "expected.json").write_text(json.dumps({"sum": expected, "shape": list(shape), "configs": results}, indent=2))
print("\nexpected int64 sum of all elements:", expected)
