"""Write the v3 arrays that bound the floor: Blosc shuffle modes and codecs, and sharded pipelines."""

import json
import pathlib
import shutil

import numpy as np
import zarr
from zarr.codecs import (
    BloscCodec,
    BytesCodec,
    Crc32cCodec,
    GzipCodec,
    ShardingCodec,
    ZstdCodec,
)

root = pathlib.Path(__file__).parent / "more"
shutil.rmtree(root, ignore_errors=True)
root.mkdir()
shape, chunks = (2000, 384), (500, 384)
data = ((np.arange(np.prod(shape), dtype=np.int64) % 4001) - 2000).astype(np.int16).reshape(shape)


def shard(inner, index=None, location="end"):
    # `compressors=None`: zarr-python otherwise wraps the whole shard in a default compressor.
    index = [BytesCodec(), Crc32cCodec()] if index is None else list(index)
    codec = ShardingCodec(
        chunk_shape=chunks, codecs=[BytesCodec(), *inner], index_codecs=index, index_location=location
    )
    return dict(serializer=codec, chunks=(1000, 384), compressors=None)


configs = {
    "blosc_noshuffle": dict(compressors=[BloscCodec(cname="zstd", shuffle="noshuffle")]),
    "blosc_bitshuffle": dict(compressors=[BloscCodec(cname="zstd", shuffle="bitshuffle")]),
    "blosc_lz4": dict(compressors=[BloscCodec(cname="lz4", shuffle="shuffle")]),
    "shard_raw": shard([]),
    "shard_gzip": shard([GzipCodec()]),
    "shard_blosc": shard([BloscCodec(cname="zstd", shuffle="shuffle")]),
    "shard_index_bytes": shard([ZstdCodec()], index=(BytesCodec(),)),
    "shard_index_start": shard([ZstdCodec()], location="start"),
}
expected = {}
for name, options in configs.items():
    options.setdefault("chunks", chunks)
    array = zarr.create_array(store=str(root / name), shape=shape, dtype="int16", zarr_format=3, **options)
    array[:] = data
    expected[name] = int(data.astype(np.int64).sum())
    print(name, json.dumps(json.loads((root / name / "zarr.json").read_text())["codecs"]))
(root / "expected.json").write_text(json.dumps(expected))
