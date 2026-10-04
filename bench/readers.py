"""Cold read cost of one session: a packet against the NWB it was built beside.

Each cell is one operation in a fresh process after the page cache for both stores is evicted,
timed from before the store is opened but after the reader's modules are imported, with that
process's peak RSS. Every reader is driven on
its own documented path and every operation forces a real read: counting spikes through a
ragged index touches no value, so the whole-table question sums them instead.

- `packet` reads through `escapewheel_reader`'s PyArrow path, `packet-sql` through DuckDB.
- `pynwb` reads the NWB through `hdmf-zarr`, projecting columns by name, since
  `units.to_dataframe()` materialises the spike train and both waveform arrays.
- `lazynwb` reads the same NWB without building an object model, through `scan_nwb`.

The packet's units and their metrics are two tables, `core.units` and `aind_unit_qc.metrics`,
where the NWB holds one; the metadata operations read both. A trial is `core.intervals` plus the
task's own table. The window is stated once, in seconds after the packet's time origin, and an
NWB is assumed to hold its spike times in seconds on the packet's reference clock; `value` shows
whether the readers agreed. `region units` counts the units with an electrode in one region and
reads their trains; the NWB has no electrode coordinates of its own, so pynwb and lazynwb reach a
unit's region through `location` where the units table has it and through its electrodes where not.
`one train` asks for the train on the reference clock, which the packet reads from
`analysis.spike_events`; `one train stored` asks for its ticks as recorded, from `core.spike_events`.
DuckDB and the NWB readers hold one form each, so they answer both the same way.

Either store may be an `s3://` URI. A remote cell is cold because its process is fresh, and it
records the bytes the host received. Credentials come from the environment: run
`eval "$(aws configure export-credentials --format env)"` first, so that PyArrow, DuckDB, s3fs and
lazynwb all read the same ones.

    uv run python readers.py --packet P --nwb N [--json-out results/x.json]
    uv run python readers.py --child READER OPERATION --plan PLAN   # one cell, as JSON
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
import warnings
from pathlib import Path

import benchkit

READERS = ("packet", "packet-sql", "pynwb", "lazynwb")
OPERATIONS = (
    "open",
    "units 5 cols",
    "units all meta",
    "trials",
    "every spike",
    "10 s window",
    "one train",
    "one train stored",
    "region units",
)

# The same five facts about a unit under each store's names.
FIVE_PACKET = ["local_unit_label", "probe_id", "firing_rate_hz", "n_spikes", "quality_label"]
FIVE_NWB = ["ks_unit_id", "device_name", "firing_rate", "num_spikes", "default_qc"]
# Ragged and two-dimensional columns of an NWB units table, which are not per-unit metadata.
NWB_ARRAYS = ("spike_times", "electrodes", "extremum_channel", "waveform_mean", "waveform_sd")


def run_packet(plan: dict, operation: str) -> object:
    """One operation through the reader's PyArrow path."""
    import pyarrow.compute as pc
    from escapewheel_reader import STORED, open_packet, spike_times

    packet = open_packet(plan["packet"])
    if operation == "open":
        return len(packet.manifest.resources)
    if operation == "units 5 cols":
        return packet.table("core.units", columns=FIVE_PACKET).num_rows
    if operation == "units all meta":
        return sum(packet.table(name).num_columns for name in plan["unit_tables"])
    if operation == "trials":
        return [packet.table(name).num_rows for name in plan["trial_tables"]]
    if operation == "every spike":
        return pc.sum(packet.table("core.spike_events", columns=["t_tick"])["t_tick"]).as_py()
    if operation == "10 s window":
        lo, hi = plan["window_tick"]
        return packet.table("analysis.spike_events", columns=["t_tick"], t_tick=(lo, hi - 1)).num_rows
    if operation == "one train":
        return spike_times(packet, plan["unit_id"]).num_rows
    if operation == "one train stored":
        return spike_times(packet, plan["unit_id"], clock=STORED).num_rows
    if operation == "region units":
        import pyarrow.dataset as ds

        where = packet.table("core.electrode_coordinates", columns=["electrode_id", "region_label"])
        inside = where.filter(pc.equal(where["region_label"], plan["region"]))["electrode_id"]
        links = packet.table("core.unit_electrodes", columns=["unit_id", "electrode_id"])
        units = pc.unique(links.filter(pc.is_in(links["electrode_id"], value_set=inside))["unit_id"])
        spikes = packet.scan("core.spike_events").to_table(
            columns=["unit_id"], filter=ds.field("unit_id").isin(units.to_pylist())
        )
        return len(units), spikes.num_rows
    raise ValueError(operation)


REGION_UNITS = (
    "SELECT count(DISTINCT s.unit_id) AS units, count(*) AS spikes FROM core_spike_events s "
    "WHERE s.unit_id IN (SELECT link.unit_id FROM core_unit_electrodes link "
    "JOIN core_electrode_coordinates c USING (session_id, electrode_id) WHERE c.region_label = '{region}')"
)


def run_packet_sql(plan: dict, operation: str) -> object:
    """One operation through DuckDB over the packet's tables."""
    from escapewheel_reader import open_packet

    packet = open_packet(plan["packet"])

    def sql(query: str):
        if not benchkit.is_remote(plan["packet"]):
            return packet.sql(query)
        import duckdb

        # The reader leaves credentials to its caller; these are the environment's.
        connection = duckdb.connect()
        connection.execute(
            f"CREATE SECRET store (TYPE s3, PROVIDER credential_chain, CHAIN 'env', REGION '{plan['region_aws']}')"
        )
        return packet.duckdb(connection=connection, for_query=query).sql(query).to_arrow_table()

    if operation == "open":
        return sql("SELECT count(*) AS n FROM core_sessions")["n"][0].as_py()
    if operation == "units 5 cols":
        return sql(f"SELECT {', '.join(FIVE_PACKET)} FROM core_units").num_rows
    if operation == "units all meta":
        return sum(sql(f"SELECT * FROM {name.replace('.', '_')}").num_columns for name in plan["unit_tables"])
    if operation == "trials":
        return [sql(f"SELECT * FROM {name.replace('.', '_')}").num_rows for name in plan["trial_tables"]]
    if operation == "every spike":
        return sql("SELECT sum(t_tick) AS s FROM core_spike_events")["s"][0].as_py()
    if operation == "10 s window":
        lo, hi = plan["window_tick"]
        query = f"SELECT count(*) AS n FROM analysis_spike_events WHERE t_tick >= {lo} AND t_tick < {hi}"
        return sql(query)["n"][0].as_py()
    if operation in ("one train", "one train stored"):
        return sql(f"SELECT t_tick FROM core_spike_events WHERE unit_id = {plan['unit_id']}").num_rows
    if operation == "region units":
        found = sql(REGION_UNITS.format(region=plan["region"])).to_pylist()[0]
        return found["units"], found["spikes"]
    raise ValueError(operation)


def run_pynwb(plan: dict, operation: str) -> object:
    """One operation through pynwb and hdmf-zarr, each column read by name."""
    import numpy as np
    from hdmf_zarr.nwb_zarrv2 import NWBZarrV2IO

    # An AIND NWB-Zarr stores its object-reference columns with the pickle codec.
    options = {"anon": False} if benchkit.is_remote(plan["nwb"]) else None
    nwb = NWBZarrV2IO(plan["nwb"], "r", allow_pickle=True, storage_options=options).read()
    units = nwb.units
    lo, hi = plan["window_s"]

    def column(name: str):
        return np.asarray(units[name].data[:])

    def metadata_columns() -> list[str]:
        ragged = {name[: -len("_index")] for name in units.colnames if name.endswith("_index")}
        return [
            name
            for name in units.colnames
            if name not in ragged and name not in NWB_ARRAYS and not name.endswith("_index")
        ]

    if operation == "open":
        return len(units.colnames)
    if operation == "units 5 cols":
        five = {name: column(name) for name in FIVE_NWB}
        return len(five[FIVE_NWB[0]])
    if operation == "units all meta":
        return len([column(name) for name in metadata_columns()])
    if operation == "trials":
        return len(nwb.intervals["trials"].to_dataframe())
    if operation == "every spike":
        return float(np.asarray(units.spike_times.data[:]).sum())
    if operation == "10 s window":
        times = np.asarray(units.spike_times.data[:])
        return int(np.count_nonzero((times >= lo) & (times < hi)))
    if operation in ("one train", "one train stored"):
        # No index on the identifying columns, so finding a named unit is a scan of them.
        labels, probes = column("ks_unit_id"), column("device_name")
        found = np.flatnonzero((labels.astype(str) == plan["unit_label"]) & (probes == plan["probe_name"]))
        return len(units["spike_times"][int(found[0])]) if len(found) else "absent"
    if operation == "region units":
        rows = nwb_region_rows(
            column("location") if "location" in units.colnames else None,
            np.asarray(nwb.electrodes["location"].data[:]),
            np.asarray(units["electrodes_index"].data[:]) if "electrodes" in units.colnames else None,
            np.asarray(units["electrodes"].data[:]) if "electrodes" in units.colnames else None,
            plan["region"],
        )
        return len(rows), sum(len(units["spike_times"][int(row)]) for row in rows)
    raise ValueError(operation)


def nwb_region_rows(unit_location, electrode_location, electrode_ends, electrode_rows, region: str):
    """Units rows in a region: by their own `location` where there is one, else by their electrodes."""
    import numpy as np

    if unit_location is not None:
        return np.flatnonzero(unit_location.astype(str) == region)
    if electrode_rows is None:
        return np.array([], dtype=int)
    inside = set(np.flatnonzero(electrode_location.astype(str) == region).tolist())
    rows, start = [], 0
    for row, end in enumerate(electrode_ends):
        if inside.intersection(electrode_rows[start:end].tolist()):
            rows.append(row)
        start = end
    return np.array(rows, dtype=int)


def run_lazynwb(plan: dict, operation: str) -> object:
    """One operation through lazynwb's lazy frames."""
    import lazynwb
    import polars as pl

    logging.disable(logging.WARNING)
    frame = lazynwb.scan_nwb(plan["nwb"], "/units")
    lo, hi = plan["window_s"]
    if operation == "open":
        return len(frame.collect_schema().names())
    if operation == "units 5 cols":
        return frame.select(FIVE_NWB).collect().height
    if operation == "units all meta":
        names = [name for name in frame.collect_schema().names() if not name.startswith("_") and name not in NWB_ARRAYS]
        return frame.select(names).collect().width
    if operation == "trials":
        return lazynwb.scan_nwb(plan["nwb"], "/intervals/trials").collect().height
    if operation == "every spike":
        return float(frame.select(pl.col("spike_times").list.sum().sum()).collect().item())
    if operation == "10 s window":
        inside = pl.element().filter((pl.element() >= lo) & (pl.element() < hi))
        return int(frame.select(pl.col("spike_times").list.eval(inside).list.len().sum()).collect().item())
    if operation in ("one train", "one train stored"):
        # The documented pattern: scalar predicates push down, then the ragged column is fetched.
        picked = frame.filter(
            pl.col("ks_unit_id") == int(plan["unit_label"]), pl.col("device_name") == plan["probe_name"]
        )
        trains = picked.select("spike_times").collect()["spike_times"]
        return int(trains.list.len().item()) if len(trains) else "absent"
    if operation == "region units":
        names = frame.collect_schema().names()
        if "location" in names:
            picked = frame.filter(pl.col("location") == plan["region"])
        else:
            electrodes = lazynwb.scan_nwb(plan["nwb"], "/general/extracellular_ephys/electrodes")
            inside = electrodes.with_row_index("row").filter(pl.col("location") == plan["region"])
            rows = inside.select("row").collect()["row"].to_list()
            picked = frame.filter(pl.col("electrodes").list.eval(pl.element().is_in(rows)).list.any())
        found = picked.select(pl.col("spike_times").list.len()).collect()["spike_times"]
        return found.len(), int(found.sum())
    raise ValueError(operation)


RUNNERS = {"packet": run_packet, "packet-sql": run_packet_sql, "pynwb": run_pynwb, "lazynwb": run_lazynwb}


def make_plan(
    packet_path: str, nwb_path: str, window: tuple[float, float], unit: str | None, probe: str | None, region: str
) -> dict:
    """Settle, from the packet, every value a child would otherwise read before its clock starts."""
    from escapewheel_reader import open_packet

    packet = open_packet(packet_path)
    origin = packet.sql(
        "SELECT s.t_zero_tick AS t0, c.tick_rate_num AS num, c.tick_rate_den AS den "
        "FROM core_sessions s JOIN core_clocks c ON c.clock_id = s.reference_clock_id"
    )
    t_zero, rate = origin["t0"][0].as_py(), origin["num"][0].as_py() / origin["den"][0].as_py()
    lo_tick, hi_tick = (t_zero + round(offset * rate) for offset in window)
    where = (
        f"WHERE u.local_unit_label = '{unit}' AND p.probe_name = '{probe}'"
        if unit and probe
        else "ORDER BY u.n_spikes DESC"
    )
    chosen = packet.sql(
        "SELECT u.unit_id, u.local_unit_label, p.probe_name, u.n_spikes FROM core_units u "
        f"JOIN core_probes p USING (session_id, probe_id) {where} LIMIT 1"
    ).to_pylist()
    if not chosen:
        sys.exit(f"no unit {unit} on probe {probe}")
    present = {resource.resource_id for resource in packet.manifest.resources}
    return {
        "packet": packet_path,
        "nwb": nwb_path,
        "region": region,
        "region_aws": os.environ.get("AWS_REGION", "us-west-2"),
        "window_tick": [lo_tick, hi_tick],
        "window_s": [lo_tick / rate, hi_tick / rate],
        "unit_id": chosen[0]["unit_id"],
        "unit_label": chosen[0]["local_unit_label"],
        "probe_name": chosen[0]["probe_name"],
        "unit_spikes": chosen[0]["n_spikes"],
        "unit_tables": [name for name in ("core.units", "aind_unit_qc.metrics") if name in present],
        "trial_tables": ["core.intervals"] + [name for name in present if name.endswith(".trials")],
    }


#: Modules each reader uses, imported before the clock starts: an import costs the same whatever
#: store is read.
IMPORTS = {
    "packet": ("escapewheel_reader", "pyarrow.compute", "pyarrow.dataset", "pyarrow.fs"),
    "packet-sql": ("escapewheel_reader", "duckdb"),
    "pynwb": ("hdmf_zarr.nwb_zarrv2", "numpy", "pandas"),
    "lazynwb": ("lazynwb", "polars"),
}


def child(reader: str, operation: str, plan: dict) -> None:
    """One cold cell, printed as JSON."""
    warnings.filterwarnings("ignore")
    for module in IMPORTS[reader]:
        importlib.import_module(module)
    benchkit.cold_child([plan["packet"], plan["nwb"]], lambda: RUNNERS[reader](plan, operation))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--packet", help="packet directory (else BENCH_PACKET)")
    parser.add_argument("--nwb", help="the session's NWB-Zarr directory (else BENCH_NWB)")
    parser.add_argument("--readers", nargs="+", default=list(READERS), choices=READERS)
    parser.add_argument("--operations", nargs="+", default=list(OPERATIONS), choices=OPERATIONS)
    parser.add_argument(
        "--window",
        nargs=2,
        type=float,
        default=(100.0, 110.0),
        metavar=("FROM_S", "TO_S"),
        help="window in seconds after the packet's time origin",
    )
    parser.add_argument("--unit", help="unit label within its probe; default the packet's largest unit")
    parser.add_argument("--probe", help="probe name of --unit")
    parser.add_argument("--region", default="MD", help="region label for `region units`")
    parser.add_argument("--repeat", type=int, default=1, help="cold runs per cell; the median is reported")
    parser.add_argument("--json-out", type=Path, help="write the result here as JSON")
    parser.add_argument("--child", nargs=2, metavar=("READER", "OPERATION"), help=argparse.SUPPRESS)
    parser.add_argument("--plan", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child(*args.child, json.loads(args.plan))

    packet = benchkit.required_store(args.packet, "BENCH_PACKET", "the packet")
    nwb = benchkit.required_store(args.nwb, "BENCH_NWB", "the NWB")
    plan = make_plan(packet, nwb, tuple(args.window), args.unit, args.probe, args.region)
    result = {
        "environment": benchkit.environment([packet, nwb]),
        "plan": plan,
        "core_version": benchkit.core_version(packet),
        "packet_bytes": benchkit.tree_bytes(packet),
        "nwb_bytes": benchkit.tree_bytes(nwb),
        "cells": [],
    }
    print(f"packet {packet} (core {result['core_version']}, {result['packet_bytes'] / 1e9:.2f} GB)")
    print(f"nwb    {nwb} ({result['nwb_bytes'] / 1e9:.2f} GB)")
    print(
        f"window {args.window[0]:g}-{args.window[1]:g} s; unit {plan['unit_label']} on probe "
        f"{plan['probe_name']} ({plan['unit_spikes']:,} spikes in the packet)\n"
    )
    print(f"{'operation':16s}" + "".join(f"{reader:>22s}" for reader in args.readers))
    for operation in args.operations:
        cells = []
        for reader in args.readers:
            runs = [
                benchkit.run_child([__file__, "--child", reader, operation, "--plan", json.dumps(plan)])
                for _ in range(args.repeat)
            ]
            good = sorted((run for run in runs if "error" not in run), key=lambda run: run["seconds"])
            cell = good[len(good) // 2] if good else runs[-1]
            cell = {"reader": reader, "operation": operation, "runs": len(good), **cell}
            result["cells"].append(cell)
            cells.append(f"{cell['seconds']:8.3f}s {cell['peak_mib']:7.0f}MiB" if good else f"{'failed':>21s}")
            if good and benchkit.is_remote(packet) and cell.get("received_bytes") is not None:
                cells[-1] = f"{cell['seconds']:7.2f}s {cell['received_bytes'] / 1e6:7.1f}MB"
        print(f"{operation:16s}" + "".join(f"{text:>22s}" for text in cells))
    print("\nwhat each returned, to show the readers were asked the same question:")
    for operation in args.operations:
        values = [
            cell.get("value", cell.get("error", "?"))[:21] for cell in result["cells"] if cell["operation"] == operation
        ]
        print(f"  {operation:14s}" + "".join(f"{value:>22s}" for value in values))
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
