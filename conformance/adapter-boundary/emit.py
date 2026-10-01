"""Three resources with three schemas on standard output, for `probe.py`."""

import sys

import pyarrow as pa

TABLES = {
    "core.sessions": pa.table({"session_id": pa.array([0], "int32")}),
    "core.units": pa.table({"unit_id": pa.array([1, 2], "int32"), "quality": pa.array(["sua", "mua"])}),
    "core.intervals": pa.table({"start_tick": pa.array([10, 20], "int64")}),
}

if __name__ == "__main__":
    out = sys.stdout.buffer
    for resource_id, table in TABLES.items():
        table = table.replace_schema_metadata({"resource_id": resource_id})
        with pa.ipc.new_stream(out, table.schema) as writer:
            writer.write_table(table)
    out.flush()
