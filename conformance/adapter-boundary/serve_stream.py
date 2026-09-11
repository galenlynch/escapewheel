"""The NWB adapter delivering `stream-v0.1`: concatenated Arrow IPC on standard output.

`argv[1]` is the JSON a build sends for `NEEDS`. One stream per resource, each carrying its
`resource_id`, and a final empty stream named `end` so a truncated delivery is not mistaken for a
finished one.
"""

from __future__ import annotations

import json
import sys

import pyarrow as pa

from serve_nwb import as_table, build

SENTINEL = "end"


def emit(out, resource: str, table: pa.Table) -> None:
    """One resource as a complete stream, ending with its own end-of-stream marker."""
    table = table.replace_schema_metadata({"resource_id": resource})
    with pa.ipc.new_stream(out, table.schema) as writer:
        writer.write_table(table)


if __name__ == "__main__":
    supplied = json.loads(sys.argv[1])
    rows = build(supplied).records()
    out = sys.stdout.buffer
    for resource in supplied.get("wanted") or list(rows):
        emit(out, resource, as_table(rows.get(resource, [])))
    emit(out, SENTINEL, pa.table({}))
    out.flush()
