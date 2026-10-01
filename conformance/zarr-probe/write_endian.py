"""Write big-endian arrays, which a reader must byte-swap: v3 through the `bytes` codec, v2 by dtype."""

import json
import pathlib
import shutil

import numcodecs
import numpy as np
import zarr
from zarr.codecs import BytesCodec, Crc32cCodec, ShardingCodec, ZstdCodec

root = pathlib.Path(__file__).parent / "endian"
shutil.rmtree(root, ignore_errors=True)
root.mkdir()
shape, chunks = (2000, 384), (500, 384)
# The sum of the unswapped bytes differs from the sum of the values, so a reader that ignores
# the declared order reports WRONG rather than passing.
data = ((np.arange(np.prod(shape), dtype=np.int64) % 4001) - 2000).astype(np.int16).reshape(shape)
big = BytesCodec(endian="big")
sharded = ShardingCodec(chunk_shape=chunks, codecs=[big, ZstdCodec()], index_codecs=[BytesCodec(), Crc32cCodec()])

configs = {
    "v3_big_raw": dict(zarr_format=3, dtype="int16", chunks=chunks, serializer=big, compressors=None),
    "v3_big_zstd": dict(zarr_format=3, dtype="int16", chunks=chunks, serializer=big, compressors=[ZstdCodec()]),
    "v3_big_sharded": dict(zarr_format=3, dtype="int16", chunks=(1000, 384), serializer=sharded, compressors=None),
    "v3_big_float32": dict(zarr_format=3, dtype="float32", chunks=chunks, serializer=big, compressors=None),
    "v2_big_zstd": dict(zarr_format=2, dtype=">i2", chunks=chunks, compressors=numcodecs.Zstd(level=3)),
}
expected = {}
for name, options in configs.items():
    array = zarr.create_array(store=str(root / name), shape=shape, **options)
    array[:] = data
    expected[name] = int(data.astype(np.int64).sum())
    metadata = root / name / ("zarr.json" if options["zarr_format"] == 3 else ".zarray")
    document = json.loads(metadata.read_text())
    print(name, json.dumps(document.get("codecs", document.get("dtype"))))
(root / "expected.json").write_text(json.dumps(expected))
