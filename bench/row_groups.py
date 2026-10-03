"""Cold reads of `analysis.spike_events` at several row-group sizes.

No available reader prunes below a row group, so the group size multiplies what a narrow
predicate reads. This rewrites the packet's table in its stored order at each size and times two
predicates against each copy, and against the table as the writer cut it, in a fresh process
after evicting the copy: a short time window, which the table's time buckets serve, and one unit
over the whole session, which only a group short enough to hold part of a bucket can prune.
Only the group size differs between copies; each column keeps the stored codec and encoding,
though not the codec's level, which Parquet does not record.

With `--store-packet` and `--store-scratch`, the copies are uploaded under the scratch prefix and
every cell reads from the store instead: the staged packet's own table and the uploaded copies.
Credentials come from the environment, as for `readers.py`.

    uv run python row_groups.py --packet P --scratch DIR [--sizes 131072 1048576 4194304]
    uv run python row_groups.py --packet P --scratch DIR --store-packet s3://.../packet \
        --store-scratch s3://.../rowgroups
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import benchkit

TABLE = "tables/analysis/spike_events.parquet"
ENGINES = ("pyarrow", "duckdb")
QUERIES = ("window", "one unit")


def rewrite(source: Path, target: Path, rows: int) -> None:
    """Copy a Parquet file at a fixed row-group size, keeping its codec and column encodings."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    stored = pq.ParquetFile(source)
    first = stored.metadata.row_group(0)
    columns = [first.column(index) for index in range(first.num_columns)]
    delta = [column.path_in_schema for column in columns if "DELTA_BINARY_PACKED" in column.encodings]
    plain = {column.path_in_schema for column in columns if not any("DICTIONARY" in e for e in column.encodings)}
    options = {
        "compression": columns[0].compression.lower(),
        "use_dictionary": [name for name in stored.schema_arrow.names if name not in plain],
        "column_encoding": dict.fromkeys(delta, "DELTA_BINARY_PACKED"),
        "store_schema": False,
    }
    with pq.ParquetWriter(target, stored.schema_arrow, **options) as writer:
        pending: list[pa.RecordBatch] = []
        held = 0
        # A source batch never spans a source row group, so batches are gathered to the size.
        for batch in stored.iter_batches(batch_size=rows):
            pending.append(batch)
            held += batch.num_rows
            while held >= rows:
                table = pa.Table.from_batches(pending)
                writer.write_table(table.slice(0, rows), row_group_size=rows)
                rest = table.slice(rows)
                pending, held = rest.to_batches(), rest.num_rows
        if held:
            writer.write_table(pa.Table.from_batches(pending), row_group_size=rows)


def predicate(query: str, plan: dict) -> tuple[str, int, int]:
    """The column and closed-open bounds a query constrains."""
    if query == "window":
        return "t_tick", *plan["window_tick"]
    return "unit_id", plan["unit_id"], plan["unit_id"] + 1


def read(engine: str, path: str, column: str, lo: int, hi: int) -> int:
    """Rows within the bounds, read the way each engine prunes."""
    if engine == "pyarrow":
        import pyarrow.dataset as ds

        field = ds.field(column)
        return ds.dataset(path).to_table(columns=[column], filter=(field >= lo) & (field < hi)).num_rows
    import duckdb

    connection = duckdb.connect()
    if benchkit.is_remote(path):
        region = os.environ.get("AWS_REGION", "us-west-2")
        connection.execute("LOAD httpfs")
        connection.execute(f"CREATE SECRET store (TYPE s3, PROVIDER credential_chain, CHAIN 'env', REGION '{region}')")
    query = f"SELECT count(*) FROM read_parquet('{path}') WHERE {column} >= {lo} AND {column} < {hi}"
    return connection.sql(query).fetchone()[0]


def upload(source: Path, target: str) -> None:
    """Copy one local file to a store URI, unless an object of the same size is already there."""
    from pyarrow import fs

    filesystem, key = fs.FileSystem.from_uri(target)
    found = filesystem.get_file_info(key)
    if found.type == fs.FileType.File and found.size == source.stat().st_size:
        return
    fs.copy_files(str(source), key, destination_filesystem=filesystem)


def make_plan(packet: Path, window: tuple[float, float], unit_id: int | None) -> dict:
    """The window's ticks and the unit, settled before any child's clock starts."""
    from escapewheel_reader import open_packet

    opened = open_packet(packet)
    origin = opened.sql(
        "SELECT s.t_zero_tick AS t0, c.tick_rate_num AS num, c.tick_rate_den AS den "
        "FROM core_sessions s JOIN core_clocks c ON c.clock_id = s.reference_clock_id"
    )
    rate = origin["num"][0].as_py() / origin["den"][0].as_py()
    lo, hi = (origin["t0"][0].as_py() + round(offset * rate) for offset in window)
    if unit_id is None:
        unit_id = opened.sql("SELECT unit_id FROM core_units ORDER BY n_spikes DESC LIMIT 1")["unit_id"][0].as_py()
    return {"window_s": list(window), "window_tick": [lo, hi], "unit_id": unit_id}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--packet", help="packet directory (else BENCH_PACKET)")
    parser.add_argument(
        "--scratch", help="directory for the rewritten copies, on the disk being measured (else BENCH_SCRATCH)"
    )
    parser.add_argument("--store-packet", help="the same packet staged in a store; cells then read the store")
    parser.add_argument("--store-scratch", help="store prefix the rewritten copies are uploaded under")
    parser.add_argument("--sizes", nargs="+", type=int, default=[131_072, 1_048_576, 4_194_304])
    parser.add_argument(
        "--window",
        nargs=2,
        type=float,
        default=(100.0, 101.0),
        metavar=("FROM_S", "TO_S"),
        help="window in seconds after the packet's time origin",
    )
    parser.add_argument("--unit-id", type=int, help="unit for the unit query; default the packet's largest")
    parser.add_argument("--repeat", type=int, default=3, help="cold runs per cell; the median is reported")
    parser.add_argument("--json-out", type=Path, help="write the result here as JSON")
    parser.add_argument("--child", nargs=5, metavar=("ENGINE", "PATH", "COLUMN", "LO", "HI"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        engine, path, column, lo, hi = args.child
        # Imported before the clock starts, so a cell times the read and not the engine's import.
        import duckdb  # noqa: F401
        import pyarrow.dataset  # noqa: F401

        return benchkit.cold_child([path], lambda: read(engine, path, column, int(lo), int(hi)))

    import pyarrow.parquet as pq

    packet = benchkit.required_path(args.packet, "BENCH_PACKET", "the packet")
    scratch = benchkit.required_path(args.scratch, "BENCH_SCRATCH", "the scratch directory")
    remote = bool(args.store_packet)
    if remote != bool(args.store_scratch):
        sys.exit("name both --store-packet and --store-scratch, or neither")
    plan = make_plan(packet, tuple(args.window), args.unit_id)
    copies = {"as stored": packet / TABLE}
    for rows in args.sizes:
        target = scratch / f"{packet.name}.spike_events.{rows}.parquet"
        if not target.exists():
            clock = time.perf_counter()
            rewrite(packet / TABLE, target, rows)
            print(f"wrote {target.name} in {time.perf_counter() - clock:.1f} s", file=sys.stderr)
        copies[f"{rows:,} rows"] = target
    # Each layout's local file supplies its metadata; `read_from` is what a cell reads.
    read_from = {name: str(path) for name, path in copies.items()}
    if remote:
        read_from["as stored"] = f"{args.store_packet.rstrip('/')}/{TABLE}"
        for name, path in copies.items():
            if name != "as stored":
                read_from[name] = f"{args.store_scratch.rstrip('/')}/{path.name}"
                upload(path, read_from[name])

    stores = [args.store_packet, args.store_scratch] if remote else [packet, scratch]
    result = {
        "environment": benchkit.environment(stores),
        "core_version": benchkit.core_version(packet),
        "plan": plan,
        "cells": [],
    }
    where = args.store_packet if remote else packet
    print(f"analysis.spike_events of {where} (core {result['core_version']}), cold, median of {args.repeat}")
    print(f"window {args.window[0]:g}-{args.window[1]:g} s after the origin; unit {plan['unit_id']}\n")
    header = "".join(f"{f'{query}, {engine}':>22s}" for query in QUERIES for engine in ENGINES)
    print(f"{'layout':>16s} {'groups':>7s} {'MB':>7s}{header}")
    for name, path in copies.items():
        meta = pq.ParquetFile(path).metadata
        texts = []
        for query in QUERIES:
            column, lo, hi = predicate(query, plan)
            for engine in ENGINES:
                runs = [
                    benchkit.run_child([__file__, "--child", engine, read_from[name], column, str(lo), str(hi)])
                    for _ in range(args.repeat)
                ]
                good = sorted((run for run in runs if "error" not in run), key=lambda run: run["seconds"])
                cell = good[len(good) // 2] if good else runs[-1]
                result["cells"].append(
                    {
                        "layout": name,
                        "row_groups": meta.num_row_groups,
                        "bytes": path.stat().st_size,
                        "read_from": read_from[name],
                        "query": query,
                        "engine": engine,
                        "runs": len(good),
                        **cell,
                    }
                )
                texts.append(f"{cell['seconds']:8.3f}s {cell['value']:>9s}" if good else f"{'failed':>19s}")
        size = path.stat().st_size / 1e6
        print(f"{name:>16s} {meta.num_row_groups:>7,} {size:>7.0f}" + "".join(f"{text:>22s}" for text in texts))
        if any("error" in cell for cell in result["cells"][-len(texts) :]):
            print("  " + "; ".join(cell.get("error", "") for cell in result["cells"][-len(texts) :]))
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
