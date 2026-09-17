import shutil, pathlib
import numpy as np, zarr
from zarr.codecs import GzipCodec, ZstdCodec, BloscCodec

root = pathlib.Path(__file__).parent / "realistic"
if root.exists():
    shutil.rmtree(root)
root.mkdir(parents=True)

# realistic-ish ephys: correlated gaussian noise + sparse spikes, int16
rng = np.random.default_rng(0)
nt, nch = 30000, 384
noise = rng.normal(0, 180, size=(nt, nch))
common = rng.normal(0, 60, size=(nt, 1))  # shared reference noise
data = noise + common
for _ in range(4000):  # sparse spikes
    t, c = rng.integers(0, nt - 40), rng.integers(0, nch)
    data[t : t + 40, max(0, c - 3) : c + 4] -= rng.normal(700, 150)
data = np.clip(data, -32768, 32767).astype(np.int16)

raw = data.nbytes
for name, comp in [
    ("gzip", [GzipCodec(level=5)]),
    ("zstd", [ZstdCodec(level=3)]),
    ("zstd_l9", [ZstdCodec(level=9)]),
    ("blosc_zstd_shuffle", [BloscCodec(cname="zstd", clevel=3, shuffle="shuffle")]),
    (
        "blosc_zstd_bitshuffle",
        [BloscCodec(cname="zstd", clevel=3, shuffle="bitshuffle")],
    ),
]:
    a = zarr.create_array(
        store=str(root / name),
        shape=(nt, nch),
        dtype="int16",
        chunks=(6000, 384),
        compressors=comp,
        zarr_format=3,
    )
    a[:] = data
    n = sum(p.stat().st_size for p in (root / name).rglob("*") if p.is_file())
    print(f"{name:24s} {n / 1e6:7.2f} MB   ratio {raw / n:5.2f}x")
print(f"{'uncompressed':24s} {raw / 1e6:7.2f} MB")
