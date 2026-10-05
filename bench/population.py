"""Two population analyses of one session, cold, each arm answering in its own library's idiom.

As in `trials.py`, each analysis is a target, stated here and checked after the clock stops.

`condition psth` counts every unit's spikes in 50 ms bins over [-1, +2) s around each go cue,
summed over the trials of each condition: the choice (left, right or none) and, for a choice,
whether it was rewarded. Its value is the spikes counted, the nonzero (unit, condition, bin) cells,
their summed squares, and the counts summed by bin position.

`cross-correlograms` histograms, for every pair of single units in MD, the lag from each spike of
one to each spike of the other, in 0.5 ms bins centred on 0 and reaching +-10 ms: bin
`floor(lag / 0.5 ms + 0.5)`, kept from -20 to 20. Its value is the spike pairs, the nonzero
(pair, bin) cells, their summed squares, and the counts summed by distance from zero lag; each is
the same whichever unit of a pair comes first.

The arms:

- DuckDB and Polars on the packet join `analysis.spike_events` to cues, or to itself, on bins as
  wide as the window, in ticks. DuckDB on pynwb's frames and Polars on lazynwb's `scan_nwb` do the
  same in seconds.
- aind-ephys-utils takes a list of spike times per unit: from the packet's `analysis.spike_events`,
  already on the reference clock, cut by `ragged` into runs per unit and time bucket and joined per
  unit; from pynwb's ragged column; and from lazynwb's frames. The PSTH is `from_dataframe` binned
  and `psth` summed by condition; the correlograms are `ccg_allpairs_sparse`, whose JIT compilation
  is part of its time.

A library arm's cell times reading its store into the library's inputs. The library's own work is
the same whatever store fed it and, for the PSTH, larger than any read, so it is timed after the
cell's clock stops and reported beside it as `compute_s`.

Packet tick arithmetic is exact, and seconds are floats, so a spike exactly on a bin edge can fall
either side in a float arm: a PSTH edge lands on a whole tick, a correlogram edge never does.

    uv run python population.py --packet P --nwb N [--json-out results/x.json]
    uv run python population.py --child ARM ANALYSIS --plan PLAN   # one cell, as JSON
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import benchkit
import trials

PSTH = "condition psth"
CCG = "cross-correlograms"
ANALYSES = (PSTH, CCG)
# The PSTH window around a go cue, in seconds, and its bins per second.
BEFORE, AFTER, PSTH_BINS = 1, 2, 20
# Correlogram bins per second, and the bins either side of zero lag.
CCG_BINS, LAG_BINS = 2000, 20
# The choice an NWB's `animal_response` codes 0, 1 and 2.
CHOICES = ("left", "right", "no_response")


def psth_summary(found) -> dict:
    """What a PSTH holds, from counts by (unit, condition, time) as a DataArray, or rows of unit, condition, bin, n."""
    import numpy as np
    import polars as pl

    if hasattr(found, "dims"):
        counts = np.rint(found.transpose("unit", "condition", "time").values).astype(np.int64)
        bins = np.broadcast_to(np.arange(counts.shape[-1]), counts.shape)
        kept = counts > 0
        n, position = counts[kept], bins[kept]
    else:
        frame = found if isinstance(found, pl.DataFrame) else pl.from_arrow(found)
        n, position = frame["n"].to_numpy().astype(np.int64), frame["bin"].to_numpy().astype(np.int64)
    return {
        "spikes": int(n.sum()),
        "cells": int((n > 0).sum()),
        "cell_sq": int((n**2).sum()),
        "bin_sum": int((n * position).sum()),
    }


def ccg_summary(found) -> dict:
    """What correlograms hold, from `(lags, C)` with `C[i, j]` a pair's counts, or rows of a < b, lag and n."""
    import numpy as np
    import polars as pl

    if isinstance(found, tuple):
        lags, dense = found
        upper = np.triu_indices(dense.shape[0], 1)
        counts = np.rint(dense[upper]).astype(np.int64)
        lag = np.broadcast_to(np.rint(lags * CCG_BINS).astype(np.int64), counts.shape)
        kept = counts > 0
        n, lag = counts[kept], lag[kept]
    else:
        frame = found if isinstance(found, pl.DataFrame) else pl.from_arrow(found)
        n, lag = frame["n"].to_numpy().astype(np.int64), frame["lag"].to_numpy().astype(np.int64)
    return {
        "pairs": int(n.sum()),
        "cells": int((n > 0).sum()),
        "cell_sq": int((n**2).sum()),
        "abs_lag": int((n * np.abs(lag)).sum()),
    }


def library_psth(trains: list, go, condition):
    """aind-ephys-utils' PSTH, as summed counts, from each unit's spike times and each trial's cue and condition."""
    import pandas as pd
    from aind_ephys_utils.adapters import from_dataframe
    from aind_ephys_utils.ops import psth

    units = pd.DataFrame({"spike_times": trains})
    # Its trial bounds are only checked; the window decides which spikes count.
    cues = pd.DataFrame({"start_time": go - BEFORE, "end_time": go + AFTER, "go": go, "condition": condition})
    rates = from_dataframe(
        units,
        cues,
        align_to="go",
        bin_size=1 / PSTH_BINS,
        window=(-BEFORE, AFTER),
        unit_coords=[],
        trial_coords=["condition"],
        validate=False,
    )
    return psth(rates, dim="trial", method="sum", group_by="condition") / PSTH_BINS


def library_ccg(trains: list):
    from aind_ephys_utils.metrics import ccg_allpairs_sparse

    return ccg_allpairs_sparse(trains, bin_size=1 / CCG_BINS, max_lag=LAG_BINS / CCG_BINS, include_autocorr=False)


@dataclass
class Inputs:
    """What aind-ephys-utils is handed: each unit's spike times, and for a PSTH each trial's cue and condition."""

    trains: list
    go: object = None
    condition: object = None


def summariser(analysis: str) -> Callable[[object], dict]:
    """The check of an analysis's result, which for a library arm first runs the library on its inputs, timed."""

    def summarise(found) -> dict:
        if not isinstance(found, Inputs):
            return SUMMARIES[analysis](found)
        clock = time.perf_counter()
        found = library_psth(found.trains, found.go, found.condition) if analysis == PSTH else library_ccg(found.trains)
        return {**SUMMARIES[analysis](found), "compute_s": round(time.perf_counter() - clock, 3)}

    return summarise


# The packet.

CONDITION_SQL = (
    "(CASE animal_response WHEN 'left' THEN 0 WHEN 'right' THEN 1 ELSE 2 END) * 2"
    " + (rewarded_history_left OR rewarded_history_right)::INTEGER"
)

MD_SINGLE_UNITS_SQL = """
SELECT u.unit_id FROM core_units u JOIN core_unit_coordinates c USING (session_id, unit_id)
WHERE u.quality_label = 'sua' AND c.coordinate_frame = 'ccf' AND c.region_label = 'MD'
"""

PACKET_PSTH_SQL = """
WITH c AS (SELECT go_cue_start_tick AS g, {condition} AS condition FROM {trials} WHERE go_cue_start_tick IS NOT NULL)
SELECT s.unit_id AS unit, c.condition, (s.t_tick - c.g + {before}) * {bins} // {rate} AS bin, count(*) AS n
FROM analysis_spike_events s
JOIN (SELECT g, condition, (g - {before}) // {width} + k AS bin FROM c, (VALUES (0), (1)) AS shift(k)) c
  ON s.t_tick // {width} = c.bin AND s.t_tick >= c.g - {before} AND s.t_tick < c.g + {after}
GROUP BY ALL
"""

# Each spike of the second unit is entered under its bin and both neighbours, so a hash join on
# bins as wide as the reach finds every pair in reach.
PACKET_CCG_SQL = """
WITH s AS (SELECT unit_id AS unit, t_tick AS t, t_tick // {width} AS bin FROM analysis_spike_events
           WHERE unit_id IN ({units})),
pairs AS (SELECT a.unit AS a, b.unit AS b, floor((2 * {bins} * (b.t - a.t) + {rate}) / (2 * {rate}))::BIGINT AS lag
          FROM s a JOIN (SELECT unit, t, bin + k AS bin FROM s, (VALUES (-1), (0), (1)) AS shift(k)) b
            ON a.bin = b.bin AND a.unit < b.unit)
SELECT a, b, lag, count(*) AS n FROM pairs WHERE lag BETWEEN -{lags} AND {lags} GROUP BY ALL
"""


def tick_reach(rate: int) -> int:
    """The widest lag a correlogram keeps, in whole ticks, plus one."""
    import math

    return math.ceil((LAG_BINS + 0.5) * rate / CCG_BINS) + 1


def run_packet_duckdb(plan: dict, analysis: str) -> object:
    """DuckDB over the packet's tables, in ticks."""
    packet = trials.open_packet(plan)
    con = trials.connection(plan)
    rate = plan["rate"]
    if analysis == PSTH:
        before, after = BEFORE * rate, AFTER * rate
        query = PACKET_PSTH_SQL.format(
            trials=plan["trials"].replace(".", "_"),
            condition=CONDITION_SQL,
            before=before,
            after=after,
            width=before + after,
            bins=PSTH_BINS,
            rate=rate,
        )
        packet.duckdb(connection=con, tables=("analysis.spike_events", plan["trials"]))
        return con.sql(query).to_arrow_table()
    packet.duckdb(connection=con, tables=("analysis.spike_events", "core.units", "core.unit_coordinates"))
    query = PACKET_CCG_SQL.format(
        units=MD_SINGLE_UNITS_SQL, width=tick_reach(rate), bins=CCG_BINS, rate=rate, lags=LAG_BINS
    )
    return con.sql(query).to_arrow_table()


def packet_md_units(packet) -> list[int]:
    return packet.sql(MD_SINGLE_UNITS_SQL)["unit_id"].to_pylist()


def run_packet_polars(plan: dict, analysis: str) -> object:
    """Polars lazy frames from `scan_polars`, in ticks."""
    import polars as pl

    packet = trials.open_packet(plan)
    rate = plan["rate"]
    spikes = packet.table_resource("analysis.spike_events").scan_polars().select(unit="unit_id", t="t_tick")
    if analysis == PSTH:
        cues = (
            packet.table_resource(plan["trials"])
            .scan_polars()
            .filter(pl.col("go_cue_start_tick").is_not_null())
            .select(
                g="go_cue_start_tick",
                condition=pl.col("animal_response").replace_strict(CHOICES, range(3), return_dtype=pl.Int64) * 2
                + (pl.col("rewarded_history_left") | pl.col("rewarded_history_right")).cast(pl.Int64),
            )
        )
        return polars_psth(spikes, cues, BEFORE * rate, AFTER * rate, rate)
    return polars_ccg(spikes.filter(pl.col("unit").is_in(packet_md_units(packet))), tick_reach(rate), rate)


def polars_psth(spikes, cues, before, after, per_second) -> object:
    """Counts by (unit, condition, bin) from (unit, t) spikes and (g, condition) cues, integer or float alike."""
    import polars as pl

    width = before + after
    t, g = pl.col("t"), pl.col("g")
    cues = pl.concat([cues.with_columns(bin=((g - before) // width).cast(pl.Int64) + k) for k in (0, 1)])
    return (
        spikes.with_columns(bin=(t // width).cast(pl.Int64))
        .join(cues, on="bin")
        .filter((t >= g - before) & (t < g + after))
        .group_by("unit", "condition", bin=((t - g + before) * PSTH_BINS // per_second).cast(pl.Int64))
        .agg(n=pl.len())
        .collect(engine="streaming")
    )


def polars_ccg(spikes, width, per_second) -> object:
    """Correlogram counts by (a, b, lag) from (unit, t) spikes, integer or float alike."""
    import polars as pl

    binned = spikes.with_columns(bin=(pl.col("t") // width).cast(pl.Int64))
    shifted = pl.concat([binned.with_columns(pl.col("bin") + k) for k in (-1, 0, 1)])
    lag = ((2 * CCG_BINS * (pl.col("t_b") - pl.col("t")) + per_second) // (2 * per_second)).cast(pl.Int64)
    return (
        binned.join(shifted, on="bin", suffix="_b")
        .filter(pl.col("unit") < pl.col("unit_b"))
        .select(a="unit", b="unit_b", lag=lag)
        .filter(pl.col("lag").abs() <= LAG_BINS)
        .group_by("a", "b", "lag")
        .agg(n=pl.len())
        .collect(engine="streaming")
    )


def packet_trains(packet, **where) -> list:
    """Each unit's spike times in seconds on the reference clock, from `analysis.spike_events`.

    The table is already on the reference clock, so seconds are one affine step in the scan, where
    `core.spike_events`, stored by unit, would need every tick mapped from its probe's clock. Its
    rows run by time bucket and then unit, so `ragged` gives each unit's train in pieces, one per
    bucket, and ordering the pieces by unit, not the spikes, joins them.
    """
    import numpy as np
    import pyarrow.compute as pc
    from escapewheel_reader import ragged, seconds_expression

    columns = {name: pc.field(name) for name in ("session_id", "time_bucket_tick", "unit_id")}
    timed = packet.scanner(
        "analysis.spike_events", columns={**columns, "t_second": seconds_expression(packet)}, **where
    ).to_table()
    pieces = ragged(packet, timed, "analysis.spike_events")
    lists = pieces["t_second"].combine_chunks()
    offsets = lists.offsets.to_numpy() - lists.offsets[0].as_py()
    unit = pieces["unit_id"].to_numpy()
    # Stable, so each unit's pieces stay in time order.
    order = np.argsort(unit, kind="stable")
    times = lists.values.to_numpy()[trials.spans(offsets[:-1][order], np.diff(offsets)[order])]
    lengths = np.bincount(np.unique(unit, return_inverse=True)[1], weights=np.diff(offsets)).astype(np.int64)
    return np.split(times, np.cumsum(lengths)[:-1])


def run_packet_library(plan: dict, analysis: str) -> object:
    """aind-ephys-utils on the packet's trains, gathered by `ragged`."""
    import pyarrow.compute as pc

    packet = trials.open_packet(plan)
    if analysis == CCG:
        return Inputs(packet_trains(packet, unit_id=packet_md_units(packet)))
    columns = ["session_id", "trial_id", "go_cue_start_tick", "animal_response"]
    cues = packet.table(
        plan["trials"],
        columns=[*columns, "rewarded_history_left", "rewarded_history_right"],
        on_clock=True,
        seconds=True,
    )
    cues = cues.filter(pc.is_valid(cues["go_cue_start_second"]))
    choice = pc.index_in(cues["animal_response"], value_set=pa_strings(CHOICES)).to_numpy()
    rewarded = pc.or_(cues["rewarded_history_left"], cues["rewarded_history_right"]).to_numpy(zero_copy_only=False)
    return Inputs(packet_trains(packet), cues["go_cue_start_second"].to_numpy(), choice * 2 + rewarded)


def pa_strings(values):
    import pyarrow as pa

    return pa.array(values, type=pa.string())


# The NWB.


def nwb_cues(nwb):
    """Each trial with a cue: its time and condition."""
    import numpy as np

    table = nwb.intervals["trials"]
    go = np.asarray(table["goCue_start_time"].data[:])
    choice = np.asarray(table["animal_response"].data[:]).astype(np.int64)
    rewarded = np.asarray(table["rewarded_historyL"].data[:]) | np.asarray(table["rewarded_historyR"].data[:])
    kept = ~np.isnan(go)
    return go[kept], (choice * 2 + rewarded)[kept]


def nwb_md_units(nwb):
    """Positions in the units table of the single units in MD."""
    import numpy as np

    label = np.asarray(nwb.units["decoder_label"].data[:]).astype(str)
    location = np.asarray(nwb.units["location"].data[:]).astype(str)
    return np.flatnonzero((label == "sua") & (location == "MD"))


def nwb_trains(nwb, units=None) -> list:
    """Each unit's spike times: the ragged column read whole, or, for `units`, each one's own slice."""
    import numpy as np

    if units is None:
        ends = np.asarray(nwb.units.spike_times_index.data[:])
        return np.split(np.asarray(nwb.units.spike_times.data[:]), ends[:-1])
    return [np.asarray(nwb.units.spike_times_index[int(unit)]) for unit in units]


def run_pynwb_library(plan: dict, analysis: str) -> object:
    """aind-ephys-utils on pynwb's trains."""
    nwb = trials.read_nwb(plan)
    if analysis == CCG:
        return Inputs(nwb_trains(nwb, nwb_md_units(nwb)))
    go, condition = nwb_cues(nwb)
    return Inputs(nwb_trains(nwb), go, condition)


NWB_PSTH_SQL = """
SELECT s.unit, c.condition, floor((s.t - c.g + {before}) * {bins})::BIGINT AS bin, count(*) AS n
FROM spikes s
JOIN (SELECT g, condition, floor((g - {before}) / {width})::BIGINT + k AS bin
      FROM cues, (VALUES (0), (1)) AS shift(k)) c
  ON floor(s.t / {width})::BIGINT = c.bin AND s.t >= c.g - {before} AND s.t < c.g + {after}
GROUP BY ALL
"""

NWB_CCG_SQL = """
WITH s AS (SELECT unit, t, floor(t / {width})::BIGINT AS bin FROM spikes),
pairs AS (SELECT a.unit AS a, b.unit AS b, floor((b.t - a.t) * {bins} + 0.5)::BIGINT AS lag
          FROM s a JOIN (SELECT unit, t, bin + k AS bin FROM s, (VALUES (-1), (0), (1)) AS shift(k)) b
            ON a.bin = b.bin AND a.unit < b.unit)
SELECT a, b, lag, count(*) AS n FROM pairs WHERE lag BETWEEN -{lags} AND {lags} GROUP BY ALL
"""


def seconds_reach() -> float:
    """The widest lag a correlogram keeps, in seconds, with a margin for float rounding."""
    return 1.01 * (LAG_BINS + 0.5) / CCG_BINS


def flat_spikes(trains: list, units):
    import numpy as np
    import pandas as pd

    return pd.DataFrame(
        {"unit": np.repeat(np.asarray(units), [len(train) for train in trains]), "t": np.concatenate(trains)}
    )


def run_pynwb_duckdb(plan: dict, analysis: str) -> object:
    """DuckDB over pynwb's arrays, in seconds."""
    import duckdb
    import pandas as pd

    nwb = trials.read_nwb(plan)
    con = duckdb.connect()
    if analysis == CCG:
        units = nwb_md_units(nwb)
        con.register("spikes", flat_spikes(nwb_trains(nwb, units), units))
        return con.sql(NWB_CCG_SQL.format(width=seconds_reach(), bins=CCG_BINS, lags=LAG_BINS)).to_arrow_table()
    go, condition = nwb_cues(nwb)
    trains = nwb_trains(nwb)
    con.register("spikes", flat_spikes(trains, range(len(trains))))
    con.register("cues", pd.DataFrame({"g": go, "condition": condition}))
    query = NWB_PSTH_SQL.format(before=BEFORE, after=AFTER, width=BEFORE + AFTER, bins=PSTH_BINS)
    return con.sql(query).to_arrow_table()


def lazynwb_md_units(lazynwb, plan):
    """The units table's single units in MD, with each one's position in it, as a lazy frame.

    The position is lazynwb's own `_table_index`: a row index added before the filter would stop it
    reaching the reader, which would then fetch every unit's train.
    """
    import polars as pl

    return (
        lazynwb.scan_nwb(plan["nwb"], "/units")
        .filter((pl.col("decoder_label") == "sua") & (pl.col("location") == "MD"))
        .rename({"_table_index": "unit"})
    )


def lazynwb_cues(lazynwb, plan):
    import polars as pl

    return (
        lazynwb.scan_nwb(plan["nwb"], "/intervals/trials")
        .filter(pl.col("goCue_start_time").is_not_nan())
        .select(
            g="goCue_start_time",
            condition=pl.col("animal_response").cast(pl.Int64) * 2
            + (pl.col("rewarded_historyL") | pl.col("rewarded_historyR")).cast(pl.Int64),
        )
    )


def run_lazynwb_polars(plan: dict, analysis: str) -> object:
    """lazynwb's `scan_nwb` lazy frames, in seconds."""
    import polars as pl

    lazynwb = trials.quiet_lazynwb()
    if analysis == CCG:
        spikes = lazynwb_md_units(lazynwb, plan).select("unit", t=pl.col("spike_times")).explode("t")
        return polars_ccg(spikes, seconds_reach(), 1.0)
    spikes = (
        lazynwb.scan_nwb(plan["nwb"], "/units")
        .with_row_index("unit")
        .select("unit", t=pl.col("spike_times"))
        .explode("t")
    )
    return polars_psth(spikes, lazynwb_cues(lazynwb, plan), BEFORE, AFTER, 1.0)


def run_lazynwb_library(plan: dict, analysis: str) -> object:
    """aind-ephys-utils on lazynwb's trains."""
    lazynwb = trials.quiet_lazynwb()
    if analysis == CCG:
        units = lazynwb_md_units(lazynwb, plan).select("spike_times").collect()
        return Inputs([train.to_numpy() for train in units["spike_times"]])
    frame = lazynwb.get_df(
        plan["nwb"],
        "/units",
        exact_path=True,
        include_column_names=["spike_times"],
        exclude_array_columns=False,
        as_polars=False,
    )
    cues = lazynwb_cues(lazynwb, plan).collect()
    return Inputs(list(frame["spike_times"]), cues["g"].to_numpy(), cues["condition"].to_numpy())


NWB_MODULES = ("hdmf_zarr.nwb_zarrv2", "h5py", "remfile", "numpy", "pandas")
LIBRARY = ("aind_ephys_utils.adapters", "aind_ephys_utils.ops", "aind_ephys_utils.metrics")

#: Each arm: its runner and the modules it imports before its clock starts.
ARMS: dict[str, tuple[Callable[[dict, str], object], tuple[str, ...]]] = {
    "packet duckdb": (run_packet_duckdb, ("escapewheel_reader", "duckdb")),
    "packet polars": (run_packet_polars, ("escapewheel_reader", "polars")),
    "packet aind-ephys-utils": (run_packet_library, ("escapewheel_reader", "pyarrow.compute", *LIBRARY)),
    "pynwb aind-ephys-utils": (run_pynwb_library, (*NWB_MODULES, *LIBRARY)),
    "pynwb duckdb": (run_pynwb_duckdb, (*NWB_MODULES, "duckdb")),
    "lazynwb polars": (run_lazynwb_polars, ("lazynwb", "polars")),
    "lazynwb aind-ephys-utils": (run_lazynwb_library, ("lazynwb", "polars", "pandas", *LIBRARY)),
}

SUMMARIES = {PSTH: psth_summary, CCG: ccg_summary}


def child(arm: str, analysis: str, plan: dict) -> None:
    """One cold cell, printed as JSON."""
    warnings.filterwarnings("ignore")
    runner, modules = ARMS[arm]
    for module in modules:
        importlib.import_module(module)
    benchkit.cold_child([plan["packet"], plan["nwb"]], lambda: runner(plan, analysis), summariser(analysis))


def agreement(cells: list[dict], analysis: str) -> list[str]:
    """The arms of an analysis grouped by the summary they returned, when they differ."""
    groups: dict[str, list[str]] = {}
    for cell in cells:
        if cell["analysis"] == analysis and cell.get("runs"):
            value = ast.literal_eval(cell["value"])
            value.pop("compute_s", None)
            groups.setdefault(str(value), []).append(cell["arm"])
    if len(groups) < 2:
        return []
    return [f"{analysis}: {key} from {', '.join(arms)}" for key, arms in groups.items()]


def compute_seconds(cell: dict) -> float | None:
    return ast.literal_eval(cell["value"]).get("compute_s") if cell.get("value") else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--packet", help="packet directory (else BENCH_PACKET)")
    parser.add_argument("--nwb", help="the session's NWB-Zarr directory or NWB-HDF5 file (else BENCH_NWB)")
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=ARMS)
    parser.add_argument("--analyses", nargs="+", default=list(ANALYSES), choices=ANALYSES)
    parser.add_argument("--repeat", type=int, default=1, help="cold runs per cell; the median is reported")
    parser.add_argument(
        "--once-above", type=float, metavar="SECONDS", help="stop repeating a cell whose run took longer than this"
    )
    parser.add_argument("--memory-max", help="kill a cell above this size, in systemd's form, such as 64G")
    parser.add_argument("--json-out", type=Path, help="write the result here as JSON")
    parser.add_argument("--child", nargs=2, metavar=("ARM", "ANALYSIS"), help=argparse.SUPPRESS)
    parser.add_argument("--plan", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child(*args.child, json.loads(args.plan))

    packet = benchkit.required_store(args.packet, "BENCH_PACKET", "the packet")
    nwb = benchkit.required_store(args.nwb, "BENCH_NWB", "the NWB")
    plan = trials.make_plan(packet, nwb)
    result = {
        "environment": benchkit.environment([packet, nwb]),
        "plan": plan,
        "core_version": benchkit.core_version(packet),
        "memory_max": args.memory_max,
        "once_above": args.once_above,
        "cells": [],
    }
    remote = benchkit.is_remote(packet)
    print(f"packet {packet} (core {result['core_version']}); nwb {nwb}\n")
    print(f"{'arm':28s}" + "".join(f"{analysis:>36s}" for analysis in args.analyses))
    for arm in args.arms:
        texts = []
        for analysis in args.analyses:
            runs = []
            for _ in range(args.repeat):
                runs.append(
                    benchkit.run_child(
                        [__file__, "--child", arm, analysis, "--plan", json.dumps(plan)], args.memory_max
                    )
                )
                if args.once_above is not None and runs[-1].get("seconds", 0) > args.once_above:
                    break
            good = sorted((run for run in runs if "error" not in run), key=lambda run: run["seconds"])
            cell = good[len(good) // 2] if good else runs[-1]
            result["cells"].append({"arm": arm, "analysis": analysis, "runs": len(good), **cell})
            if not good:
                texts.append("failed")
            elif remote and cell.get("received_bytes") is not None:
                texts.append(f"{cell['seconds']:7.2f}s {cell['received_bytes'] / 1e6:8.1f}MB")
            else:
                texts.append(f"{cell['seconds']:8.3f}s {cell['peak_mib']:7.0f}MiB")
            if good and (computed := compute_seconds(cell)) is not None:
                texts[-1] += f" +{computed:6.2f}s lib"
        print(f"{arm:28s}" + "".join(f"{text:>36s}" for text in texts), flush=True)
    print("\nwhat each returned:")
    for cell in result["cells"]:
        print(f"  {cell['analysis']:18s} {cell['arm']:28s} {cell.get('value', cell.get('error'))}")
    result["disagreements"] = [note for analysis in args.analyses for note in agreement(result["cells"], analysis)]
    print("\n" + ("\n".join(result["disagreements"]) or "every arm agreed"))
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
