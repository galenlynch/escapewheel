"""Write arrays through the reference writer's array path: its default, sharded, and delta outputs."""

import json
import pathlib
import shutil

import numpy as np
from escapewheel_writer.arrays import write_zarr
from escapewheel_writer.writer import StagedArray

root = pathlib.Path(__file__).parent / "writer_arrays"
shutil.rmtree(root, ignore_errors=True)
root.mkdir()
matrix = (np.arange(2000 * 384) % 4001 - 2000).astype(np.int16).reshape(2000, 384)
signal = np.cumsum(np.ones(200_000, dtype=np.int32))
ids = dict(resource_id="r", declaration_id="d", array_asset_id="a")
cases = {
    "default": StagedArray(values=matrix, chunks=(500, 384), **ids),
    "sharded": StagedArray(values=matrix, chunks=(1, 384), shard=(1000, 384), **ids),
    "delta": StagedArray(values=signal, chunks=(1 << 20,), codecs=("numcodecs.delta", "blosc"), **ids),
}
expected = {}
for name, spec in cases.items():
    write_zarr(root / name, spec)
    print(name, json.dumps(json.loads((root / name / "zarr.json").read_text())["codecs"]))
    expected[name] = int(spec.values.astype(np.int64).sum())
(root / "expected.json").write_text(json.dumps(expected))
