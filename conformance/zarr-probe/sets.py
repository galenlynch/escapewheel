"""The written array sets and each array's expected int64 element sum, shared by the Python readers."""

import json
import pathlib

HERE = pathlib.Path(__file__).parent
SETS = ("arrays", "more", "writer_arrays")


def arrays():
    """Yield (set, name, path, zarr_format, expected sum) for every array a writer has produced."""
    for name in SETS:
        if not (index := HERE / name / "expected.json").exists():
            continue
        expected = json.loads(index.read_text())
        # write.py records one sum for all its arrays and a per-config outcome.
        sums = {d: expected["sum"] for d in expected["configs"]} if "configs" in expected else expected
        for array, total in sums.items():
            path = HERE / name / array
            yield name, array, path, 3 if (path / "zarr.json").exists() else 2, total
