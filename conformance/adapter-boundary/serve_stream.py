"""The NWB adapter delivering `stream-v0.1`: concatenated Arrow IPC on standard output.

Standard input is the JSON a build sends: the terms the adapter declared in `NEEDS`, and
nothing else, since `stream-v0.1` needs no rendezvous of its own. One stream per resource, each carrying its
`resource_id`, and a final empty stream named `end` so a truncated delivery is not mistaken for a
finished one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow as pa
from serve_nwb import as_table, build

SENTINEL = "end"


def emit(out, resource: str, table: pa.Table) -> None:
    """One resource as a complete stream, ending with its own end-of-stream marker."""
    table = table.replace_schema_metadata({"resource_id": resource})
    with pa.ipc.new_stream(out, table.schema) as writer:
        writer.write_table(table)


if __name__ == "__main__":
    # Part 12 §4: what a build supplies crosses on standard input, read to end of file
    # before anything is written.
    supplied = json.loads(sys.stdin.buffer.read())
    source = build(supplied)
    rows = source.records()
    out = sys.stdout.buffer
    for resource in supplied.get("wanted") or list(rows):
        emit(out, resource, as_table(rows.get(resource, [])))
    emit(out, SENTINEL, pa.table({}))
    out.flush()
    if path := supplied.get("report_path"):
        # The one fact a declaration cannot carry: `states` names the recipe fields this source can
        # state, and every value needs the source read. Part 12 §9's report is the channel.
        stated = {field: getattr(source, attr) for field, attr in type(source).STATES.items()}
        Path(path).write_text(json.dumps({"stated": stated}, indent=2, default=str) + "\n")
