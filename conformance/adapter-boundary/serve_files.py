"""The NWB adapter delivering `files-v0.1`: one Parquet file per resource under a named root.

`argv[1]` is one JSON object: the terms the adapter declared in `NEEDS`, and `delivery_root`, the
one `files-v0.1` requires. Every resource asked for is written, empty where the source has none, so
a file that is not there means the run failed rather than that the source had nothing to say.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
from serve_nwb import as_table, build

if __name__ == "__main__":
    supplied = json.loads(sys.argv[1])
    root = Path(supplied["delivery_root"])
    source = build(supplied)
    rows = source.records()
    for resource in supplied.get("wanted") or list(rows):
        pq.write_table(as_table(rows.get(resource, [])), root / f"{resource}.parquet")
