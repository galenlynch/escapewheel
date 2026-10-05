"""Two trial analyses of one session, cold, each arm answering in its own library's fastest idiom.

Each analysis is a target, stated here and checked after the clock stops; how an arm reaches it is
its own, so arms differ in algorithm as their libraries do.

`lick latency` is, per trial, the first lick of either spout after the go cue and before the next
trial's cue. Its value is the trials with a lick and the median and mean latency.

`go-cue rasters` is what a raster plot of every unit draws: each spike within the closed window
[-1, +2] s of a go cue, as its unit, its trial and its time from the cue in seconds, one row per
(spike, cue) pair, each unit's together so its raster is drawn without a pass over every unit's,
and trials in any order, since a scatter places a spike by its trial rather than its row. Any
table-like form serves: flat rows, a list of (trial, t) per unit, or a list of t per (unit, trial).
Its value is the pairs, the units with any, the sums of squared counts per unit and per (unit,
trial), the summed seconds from cue, and whether each unit's rows came together.

The arms:

- pandas: the columns each analysis uses read into pandas, and each cue's lick found by
  `merge_asof`. Spikes are stored as ascending runs, so each run is searched for the windows of the
  cues that can reach it, and the slices found, not the spikes, are ordered by unit. The packet's runs are
  `analysis.spike_events`'s, one per unit per time bucket and already on the reference clock, read
  through `Packet.table`; the NWB's are its units' trains. pynwb reads its trials with
  `to_dataframe` and its spikes as the ragged column's flat data and index, and lazynwb reads the
  units' `spike_times` alone with `get_df`.
- PyArrow: the packet through `Packet.scanner`, its batches handed to the pandas arms' run search.
- Polars: the packet through `TableResource.scan_polars` and the NWB through lazynwb's `scan_nwb`.
- SQL: the packet through DuckDB, the NWB through lazynwb's Polars `SQLContext`, and pynwb's frames
  through DuckDB.
- Helpers: the reader's `aligned_spikes`, whose window is symmetric, so it is asked for +-2 s and
  narrowed to -1 s, and which names a trial by its cue's tick; and lazynwb's
  `get_spike_times_in_intervals`, which returns a list per (unit, trial) and whose window excludes
  its end.

The Polars and SQL arms join spikes to cues on bins twice the window's width, each cue entered
under the bin its window opens in and the next, and keep the exact window after: a hash join, where
an ASOF join sorts every spike and a range join tests every pair. Each then gathers a unit's
rows by whichever its engine does faster: DuckDB lists each unit's (trial, t) pairs, Polars sorts
by unit, and Polars SQL, which has no struct constructor, lists the trials and the times side by
side.

The packet's arms read lick and cue ticks as stored, which holds because both are on the reference
clock in the packets measured. Every other convention, cold cells, stores and credentials, is
`readers.py`'s.

    uv run python trials.py --packet P --nwb N [--json-out results/x.json]
    uv run python trials.py --child ARM ANALYSIS --plan PLAN   # one cell, as JSON
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import logging
import os
import sys
import warnings
from collections.abc import Callable
from pathlib import Path

import benchkit

ANALYSES = ("lick latency", "go-cue rasters")
RASTERS = "go-cue rasters"
# The window around a go cue, in seconds.
BEFORE, AFTER = 1, 2
LICKS = ("left_lick", "right_lick")
NWB_LICKS = ("left_lick_time", "right_lick_time")


# What each arm returns is checked here, after its clock stops; how it gets there is its own.


def lick_summary(found, per_second: float = 1.0) -> dict:
    """Trials with a lick, and the median and mean latency in ms."""
    import numpy as np

    found = np.asarray(found, dtype=float)
    found = found[~np.isnan(found)] / per_second
    return {
        "trials": len(found),
        "median_ms": round(1e3 * float(np.median(found)), 3),
        "mean_ms": round(1e3 * float(found.mean()), 3),
    }


def pandas_latencies(go, licks):
    """Per cue, the first lick after it and before the next cue, less the cue, by `merge_asof`."""
    import pandas as pd

    cues = pd.DataFrame({"g": go}).dropna().sort_values("g")
    cues["following"] = cues["g"].shift(-1)
    found = pd.merge_asof(
        cues,
        pd.DataFrame({"t": licks}).sort_values("t"),
        left_on="g",
        right_on="t",
        direction="forward",
        allow_exact_matches=False,
    )
    found = found[found["following"].isna() | (found["t"] < found["following"])]
    return (found["t"] - found["g"]).to_numpy()


def pandas_raster(spikes, trials, before, after, per_second: float = 1.0, runs=("unit",)):
    """The raster as a DataFrame, from `spikes` holding `unit`, `t` and `runs`, and `trials` holding `trial` and `g`.

    A run is a stretch of rows where every `runs` column holds one value, and `t` ascends within it.
    """
    import numpy as np
    import pandas as pd

    trials = trials.dropna(subset="g").sort_values("g")
    keys = [spikes[name].to_numpy() for name in runs]
    starts = np.flatnonzero(np.logical_or.reduce([key[1:] != key[:-1] for key in keys])) + 1
    found = run_raster(
        spikes["t"].to_numpy(),
        spikes["unit"].to_numpy(),
        np.concatenate(([0], starts)),
        trials["g"].to_numpy(),
        trials["trial"].to_numpy(),
        before,
        after,
        per_second,
    )
    return pd.DataFrame(found)


def run_raster(times, units, starts, go, trial, before, after, per_second: float = 1.0) -> dict:
    """The raster from spikes stored as ascending runs beginning at `starts`, with `go` ascending."""
    return grouped_rows(*run_slices(times, units, starts, go, before, after), go, trial, per_second)


def run_slices(times, units, starts, go, before, after):
    """Each run's spikes in each cue window reaching it, as slices: unit, cue position, length, and ticks from cue.

    Each run is searched only for the windows of the cues that can reach it, so a spike outside
    every window is never touched; searching the cues once per spike instead costs more than the
    rest of the analysis.
    """
    import numpy as np

    if not len(times):
        empty = np.zeros(0, dtype=np.int64)
        return units[:0], empty, empty, times[:0]
    stops = np.append(starts[1:], len(times))
    opened, closed = go - before, go + after
    first = np.searchsorted(closed, times[starts], side="left")
    last = np.searchsorted(opened, times[stops - 1], side="right")
    lo, hi, cue = [np.zeros(0, dtype=np.int64)], [np.zeros(0, dtype=np.int64)], [np.zeros(0, dtype=np.int64)]
    for a, b, f, z in zip(starts.tolist(), stops.tolist(), first.tolist(), last.tolist(), strict=True):
        if z > f:
            run = times[a:b]
            lo.append(a + np.searchsorted(run, opened[f:z], side="left"))
            hi.append(a + np.searchsorted(run, closed[f:z], side="right"))
            cue.append(np.arange(f, z))
    lo, cue = np.concatenate(lo), np.concatenate(cue)
    lengths = np.concatenate(hi) - lo
    kept = lengths > 0
    lo, cue, lengths = lo[kept], cue[kept], lengths[kept]
    return units[lo], cue, lengths, times[spans(lo, lengths)] - np.repeat(go[cue], lengths)


def grouped_rows(unit, cue, lengths, offsets, go, trial, per_second: float = 1.0) -> dict:
    """Flat raster rows from :func:`run_slices`, each unit's together: the slices are ordered, not the spikes."""
    import numpy as np

    order = np.argsort(unit, kind="stable")
    starts, lengths = (np.cumsum(lengths) - lengths)[order], lengths[order]
    return {
        "unit": np.repeat(unit[order], lengths),
        "trial": np.repeat(trial[cue[order]], lengths),
        "t": offsets[spans(starts, lengths)] / per_second,
    }


def spans(starts, lengths):
    """Positions covering each span `[start, start + length)`, in turn."""
    import numpy as np

    return np.repeat(starts - (np.cumsum(lengths) - lengths), lengths) + np.arange(lengths.sum())


def raster_summary(found) -> dict:
    """What a raster holds, from flat rows, lists of (trial, t) or of each per unit, or lists of t per (unit, trial).

    Counts per unit and per (unit, trial) agree across arms whatever they number units and trials
    by.
    """
    import numpy as np
    import polars as pl

    if isinstance(found, pl.DataFrame):
        frame = found
    elif hasattr(found, "iloc"):
        frame = pl.from_pandas(found)
    elif isinstance(found, dict):
        frame = pl.DataFrame(found)
    else:
        frame = pl.from_arrow(found)
    unit = frame["unit"].to_numpy()
    grouped = len(unit) == 0 or int((unit[1:] != unit[:-1]).sum()) + 1 == len(np.unique(unit))
    if "spikes" in frame.columns:
        frame = frame.explode("spikes").unnest("spikes")
    elif frame.schema["trial"] == pl.List:
        frame = frame.explode("trial", "t")
    if frame.schema["t"] == pl.List:
        frame = frame.filter(pl.col("t").list.len() > 0)
        cells = frame.select("unit", "trial", n=pl.col("t").list.len(), s=pl.col("t").list.sum())
    else:
        cells = frame.group_by("unit", "trial").agg(n=pl.len(), s=pl.col("t").sum())
    per_unit = cells.group_by("unit").agg(pl.col("n").sum())["n"].to_numpy()
    n = cells["n"].to_numpy()
    return {
        "pairs": int(n.sum()),
        "units": len(per_unit),
        "sum_sq": int((per_unit.astype(np.int64) ** 2).sum()),
        "cells": len(n),
        "cell_sq": int((n.astype(np.int64) ** 2).sum()),
        "offset_s": round(float(cells["s"].sum()), 1),
        "grouped": bool(grouped),
    }


# The packet.


#: On the reference clock, by time bucket and then unit, so each unit is a sorted run per bucket.
SPIKES = "analysis.spike_events"


def open_packet(plan: dict):
    from escapewheel_reader import open_packet as opened

    return opened(plan["packet"])


def run_packet_pandas(plan: dict, analysis: str) -> object:
    """The columns each analysis uses into pandas, read by `Packet.table`.

    Licks and cues are read onto the reference clock in seconds; spikes come from
    `analysis.spike_events`, already on it, with the bucket that delimits each unit's run.
    """
    import pandas as pd

    packet = open_packet(plan)

    def read(name: str, columns: list[str], **where) -> pd.DataFrame:
        return packet.table(name, columns=columns, on_clock=True, seconds=True, **where).to_pandas()

    trials = read(plan["trials"], ["session_id", "trial_id", "go_cue_start_tick"])
    if analysis == "lick latency":
        licks = read("core.events", ["stream_id", "t_tick"], stream_id=lick_streams(packet))
        return lick_summary(pandas_latencies(trials["go_cue_start_second"], licks["t_second"]))
    rate = plan["rate"]
    cues = packet.table(plan["trials"], columns=["trial_id", "go_cue_start_tick"]).to_pandas()
    spikes = packet.table(SPIKES, columns=["time_bucket_tick", "unit_id", "t_tick"]).to_pandas()
    return pandas_raster(
        spikes.rename(columns={"time_bucket_tick": "bucket", "unit_id": "unit", "t_tick": "t"}),
        cues.rename(columns={"trial_id": "trial", "go_cue_start_tick": "g"}),
        BEFORE * rate,
        AFTER * rate,
        rate,
        runs=("bucket", "unit"),
    )


def lick_streams(packet) -> list[int]:
    streams = packet.table("core.event_streams", columns=["event_stream_id"], event_type=list(LICKS))
    return streams["event_stream_id"].to_pylist()


def run_packet_polars(plan: dict, analysis: str) -> object:
    """Polars lazy frames from `scan_polars`."""
    import polars as pl

    packet = open_packet(plan)

    def scan(name: str) -> pl.LazyFrame:
        return packet.table_resource(name).scan_polars()

    go = scan(plan["trials"]).select(g=pl.col("go_cue_start_tick")).sort("g")
    rate = plan["rate"]
    if analysis == "lick latency":
        licks = (
            scan("core.events")
            .join(scan("core.event_streams"), left_on="stream_id", right_on="event_stream_id")
            .filter(pl.col("event_type").is_in(LICKS))
            .select(t=pl.col("t_tick"))
            .sort("t")
        )
        found = (
            go.with_columns(following=pl.col("g").shift(-1))
            .join_asof(licks, left_on="g", right_on="t", strategy="forward", allow_exact_matches=False)
            .filter(pl.col("t").is_not_null() & (pl.col("following").is_null() | (pl.col("t") < pl.col("following"))))
            .select(latency=pl.col("t") - pl.col("g"))
            .collect()
        )
        return lick_summary(found["latency"].to_numpy(), rate)
    trials = scan(plan["trials"]).select(trial="trial_id", g="go_cue_start_tick").drop_nulls().sort("g").collect()
    spikes = scan("analysis.spike_events").select(unit="unit_id", t="t_tick")
    return polars_raster(spikes, trials, BEFORE * rate, AFTER * rate, rate)


def polars_raster(spikes, trials, before, after, per_second: float = 1.0):
    """The raster as a Polars plan over (unit, t), joined to the (trial, g) cues on bins."""
    import polars as pl

    # Twice the window, so a float rounding at a bin's edge cannot carry a window into a third bin.
    width = 2 * (before + after)
    t, g = pl.col("t"), pl.col("g")
    cues = pl.concat([trials.lazy().with_columns(bin=((g - before) // width).cast(pl.Int64) + k) for k in (0, 1)])
    return (
        spikes.with_columns(bin=(t // width).cast(pl.Int64))
        .join(cues, on="bin")
        .filter(t.is_between(g - before, g + after))
        .select("unit", "trial", t=(t - g) / per_second)
        .sort("unit")
        .collect(engine="streaming")
    )


def run_packet_scanner(plan: dict, analysis: str) -> object:
    """`Packet.scanner` narrowed scans, the spikes streamed in batches into NumPy."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.compute as pc

    packet = open_packet(plan)
    rate = plan["rate"]
    trials = (
        packet.scanner(plan["trials"], columns=["session_id", "trial_id", "go_cue_start_tick"])
        .to_table()
        .filter(pc.is_valid(pc.field("go_cue_start_tick")))
        .sort_by("go_cue_start_tick")
    )
    go = trials["go_cue_start_tick"].to_numpy()
    if analysis == "lick latency":
        licks = packet.scanner("core.events", columns=["t_tick"], stream_id=lick_streams(packet)).to_table()
        licks = np.sort(licks["t_tick"].to_numpy())
        # The first lick after each cue, kept where it comes before the next.
        after = np.searchsorted(licks, go, side="right")
        first = licks[np.minimum(after, len(licks) - 1)]
        found = (after < len(licks)) & (first < np.append(go[1:], np.iinfo(np.int64).max))
        return lick_summary(first[found] - go[found], rate)
    trial = trials["trial_id"].to_numpy()
    found = []
    # A run cut across two batches yields two slices of one window, which the grouping keeps together.
    for batch in packet.scanner(SPIKES, columns=["time_bucket_tick", "unit_id", "t_tick"]).to_batches():
        if batch.num_rows:
            bucket, unit = batch["time_bucket_tick"].to_numpy(), batch["unit_id"].to_numpy()
            starts = np.flatnonzero((bucket[1:] != bucket[:-1]) | (unit[1:] != unit[:-1])) + 1
            starts = np.concatenate(([0], starts))
            found.append(run_slices(batch["t_tick"].to_numpy(), unit, starts, go, BEFORE * rate, AFTER * rate))
    parts = [np.concatenate(part) for part in zip(*found, strict=True)]
    return pa.table(grouped_rows(*parts, go, trial, rate))


LICK_SQL = """
WITH go AS (
    SELECT go_cue_start_tick AS g, lead(go_cue_start_tick) OVER (ORDER BY go_cue_start_tick) AS following
    FROM {trials}),
licks AS (
    SELECT e.t_tick AS t FROM core_events e JOIN core_event_streams s ON e.stream_id = s.event_stream_id
    WHERE s.event_type IN ('left_lick', 'right_lick'))
SELECT min(t) - g AS latency FROM go JOIN licks ON t > g AND (following IS NULL OR t < following) GROUP BY g
"""

SPIKE_SQL = """
SELECT s.unit_id AS unit, c.trial_id AS trial, (s.t_tick - c.g) / {rate} AS t
FROM analysis_spike_events s
JOIN (SELECT trial_id, go_cue_start_tick AS g, (go_cue_start_tick - {before}) // {width} + k AS bin
      FROM {trials}, (VALUES (0), (1)) AS shift(k)) c
  ON s.t_tick // {width} = c.bin AND s.t_tick BETWEEN c.g - {before} AND c.g + {after}
"""


# Each unit's (trial, t) pairs as one list: faster than sorting the rows by unit, and one list
# keeps each pair together where two would leave their orders to the engine.
BY_UNIT = "SELECT unit, list({{'trial': trial, 't': t}}) AS spikes FROM ({query}) GROUP BY unit"


def connection(plan: dict):
    """A DuckDB connection, holding the environment's credentials when the packet is remote."""
    import duckdb

    con = duckdb.connect()
    if benchkit.is_remote(plan["packet"]):
        # The reader leaves credentials to its caller.
        con.execute(benchkit.duckdb_s3_secret(plan["region_aws"]))
    return con


def run_packet_duckdb(plan: dict, analysis: str) -> object:
    """DuckDB over the packet's tables."""
    packet = open_packet(plan)
    trials, rate = plan["trials"].replace(".", "_"), plan["rate"]
    con = connection(plan)
    if analysis == "lick latency":
        query = LICK_SQL.format(trials=trials)
        found = packet.duckdb(connection=con, for_query=query).sql(query).to_arrow_table()
        return lick_summary(found["latency"].to_numpy(), rate)
    before, after = BEFORE * rate, AFTER * rate
    packet.duckdb(connection=con, tables=("analysis.spike_events", plan["trials"]))
    width = 2 * (before + after)
    query = SPIKE_SQL.format(trials=trials, before=before, after=after, width=width, rate=rate)
    return con.sql(BY_UNIT.format(query=query)).to_arrow_table()


def run_packet_aligned(plan: dict, analysis: str) -> object:
    """The reader's `aligned_spikes`, asked for the symmetric window that covers ours."""
    from escapewheel_reader import aligned_spikes

    packet = open_packet(plan)
    rate = plan["rate"]
    half = max(BEFORE, AFTER) * rate
    con = connection(plan)
    # An event has no identifier of its own, so its tick names the trial.
    found = (
        aligned_spikes(packet, "go_cue", half, connection=con)
        .filter(f"t_rel_tick BETWEEN {-BEFORE * rate} AND {AFTER * rate}")
        .aggregate(f"unit_id AS unit, list({{'trial': event_tick, 't': t_rel_tick / {rate}}}) AS spikes", "unit_id")
        .to_arrow_table()
    )
    return found


# The NWB.


def read_nwb(plan: dict):
    return benchkit.open_nwb(plan["nwb"])


def nwb_frames(plan: dict, analysis: str):
    """pynwb's frames for an analysis: trials by `to_dataframe`, licks or every spike beside them."""
    import numpy as np
    import pandas as pd

    nwb = read_nwb(plan)
    trials = nwb.intervals["trials"].to_dataframe()
    if analysis == "lick latency":
        licks = np.concatenate([np.asarray(nwb.acquisition[name].timestamps[:]) for name in NWB_LICKS])
        return trials, pd.DataFrame({"t": licks})
    # The ragged column read whole, as its flat data and the end of each unit's run. Reading it
    # through `to_dataframe` instead takes one slice per unit, each a fresh request from a store.
    ends = np.asarray(nwb.units.spike_times_index.data[:])
    times = np.asarray(nwb.units.spike_times.data[:])
    return trials, pd.DataFrame({"unit": np.repeat(np.arange(len(ends)), np.diff(ends, prepend=0)), "t": times})


def run_pynwb_pandas(plan: dict, analysis: str) -> object:
    """pynwb's frames, read whole, and the shared NumPy analysis."""
    import pandas as pd

    trials, other = nwb_frames(plan, analysis)
    if analysis == "lick latency":
        return lick_summary(pandas_latencies(trials["goCue_start_time"], other["t"]))
    # Stored unit by unit, each train ascending, so a unit is a run.
    trials = pd.DataFrame({"trial": trials.index, "g": trials["goCue_start_time"].to_numpy()})
    return pandas_raster(other, trials, BEFORE, AFTER)


NWB_LICK_SQL = """
WITH go AS (
    SELECT goCue_start_time AS g, lead(goCue_start_time) OVER (ORDER BY goCue_start_time) AS following FROM trials)
SELECT min(licks.t) - g AS latency FROM go JOIN licks ON licks.t > g AND (following IS NULL OR licks.t < following)
GROUP BY g
"""

NWB_SPIKE_SQL = """
SELECT s.unit, c.trial, s.t - c.g AS t
FROM spikes s
JOIN (SELECT trial, goCue_start_time AS g, floor((goCue_start_time - {before}) / {width})::BIGINT + k AS bin
      FROM trials, (VALUES (0), (1)) AS shift(k)) c
  ON floor(s.t / {width})::BIGINT = c.bin AND s.t BETWEEN c.g - {before} AND c.g + {after}
"""


def run_pynwb_duckdb(plan: dict, analysis: str) -> object:
    """DuckDB over pynwb's frames, read whole, joined as the packet's DuckDB arm joins."""
    import duckdb

    trials, other = nwb_frames(plan, analysis)
    con = duckdb.connect()
    con.register("trials", trials[["goCue_start_time"]].rename_axis("trial").reset_index())
    if analysis == "lick latency":
        con.register("licks", other)
        return lick_summary(con.sql(NWB_LICK_SQL).fetchnumpy()["latency"])
    con.register("spikes", other)
    width = 2 * (BEFORE + AFTER)
    return con.sql(BY_UNIT.format(query=NWB_SPIKE_SQL.format(before=BEFORE, after=AFTER, width=width))).to_arrow_table()


def quiet_lazynwb():
    import lazynwb

    logging.disable(logging.WARNING)
    # Not taken from the environment, unlike s3fs's and PyArrow's credentials.
    lazynwb.config.anon = benchkit.anonymous()
    return lazynwb


def run_lazynwb_pandas(plan: dict, analysis: str) -> object:
    """lazynwb's `get_df` frames and the shared NumPy analysis."""
    lazynwb = quiet_lazynwb()
    import numpy as np
    import pandas as pd

    trials = lazynwb.get_df(plan["nwb"], "/intervals/trials", exact_path=True, as_polars=False)
    go = trials["goCue_start_time"].to_numpy()
    if analysis == "lick latency":
        licks = [
            lazynwb.get_df(plan["nwb"], f"/acquisition/{name}", exact_path=True, as_polars=False)["timestamps"]
            for name in NWB_LICKS
        ]
        return lick_summary(pandas_latencies(go, np.concatenate([frame.to_numpy() for frame in licks])))
    units = lazynwb.get_df(
        plan["nwb"],
        "/units",
        exact_path=True,
        include_column_names=["spike_times"],
        exclude_array_columns=False,
        as_polars=False,
    )
    trains = list(units["spike_times"])
    unit = np.repeat(np.arange(len(trains)), [len(train) for train in trains])
    spikes = pd.DataFrame({"unit": unit, "t": np.concatenate(trains)})
    return pandas_raster(spikes, pd.DataFrame({"trial": trials["_table_index"].to_numpy(), "g": go}), BEFORE, AFTER)


def run_lazynwb_polars(plan: dict, analysis: str) -> object:
    """lazynwb's `scan_nwb` lazy frames."""
    import polars as pl

    lazynwb = quiet_lazynwb()
    trials = lazynwb.scan_nwb(plan["nwb"], "/intervals/trials")
    go = trials.select(g=pl.col("goCue_start_time")).sort("g")
    if analysis == "lick latency":
        licks = pl.concat(
            [lazynwb.scan_nwb(plan["nwb"], f"/acquisition/{name}").select(t=pl.col("timestamps")) for name in NWB_LICKS]
        ).sort("t")
        found = (
            go.with_columns(following=pl.col("g").shift(-1))
            .join_asof(licks, left_on="g", right_on="t", strategy="forward", allow_exact_matches=False)
            .filter(pl.col("t").is_not_null() & (pl.col("following").is_null() | (pl.col("t") < pl.col("following"))))
            .select(latency=pl.col("t") - pl.col("g"))
            .collect()
        )
        return lick_summary(found["latency"].to_numpy())
    spikes = (
        lazynwb.scan_nwb(plan["nwb"], "/units")
        .with_row_index("unit")
        .select("unit", t=pl.col("spike_times"))
        .explode("t")
    )
    cue = trials.select(trial="_table_index", g="goCue_start_time").drop_nulls().drop_nans().sort("g").collect()
    return polars_raster(spikes, cue, BEFORE, AFTER)


POLARS_LICK_SQL = """
WITH go AS (
    SELECT goCue_start_time AS g, LEAD(goCue_start_time) OVER (ORDER BY goCue_start_time) AS following FROM trials),
licks AS (SELECT timestamps AS t FROM left_lick_time UNION ALL SELECT timestamps AS t FROM right_lick_time)
SELECT min(licks.t - go.g) AS latency FROM go JOIN licks ON licks.t > go.g
WHERE go.following IS NULL OR licks.t < go.following GROUP BY go.g
"""

# Polars SQL has no VALUES list to cross with, so each cue's two bins are a UNION.
POLARS_SPIKE_SQL = """
SELECT s.unit, c.trial, s.t - c.g AS t
FROM (SELECT unit, t, CAST(FLOOR(t / {width}) AS BIGINT) AS bin
      FROM (SELECT _table_index AS unit, UNNEST(spike_times) AS t FROM units)) s
JOIN (SELECT _table_index AS trial, goCue_start_time AS g,
             CAST(FLOOR((goCue_start_time - {before}) / {width}) AS BIGINT) AS bin
      FROM trials
      UNION ALL
      SELECT _table_index AS trial, goCue_start_time AS g,
             CAST(FLOOR((goCue_start_time - {before}) / {width}) AS BIGINT) + 1 AS bin
      FROM trials) c
  ON s.bin = c.bin
WHERE s.t >= c.g - {before} AND s.t <= c.g + {after}
"""

POLARS_BY_UNIT = "SELECT unit, ARRAY_AGG(trial) AS trial, ARRAY_AGG(t) AS t FROM ({query}) GROUP BY unit"


def run_lazynwb_sql(plan: dict, analysis: str) -> object:
    """lazynwb's Polars `SQLContext` over the NWB."""
    lazynwb = quiet_lazynwb()
    names = ["trials", *NWB_LICKS] if analysis == "lick latency" else ["trials", "units"]
    context = lazynwb.get_sql_context(
        plan["nwb"], exclude_array_columns=False, table_names=names, disable_progress=True
    )
    if analysis == "lick latency":
        return lick_summary(context.execute(POLARS_LICK_SQL).collect()["latency"].to_numpy())
    query = POLARS_SPIKE_SQL.format(before=BEFORE, after=AFTER, width=2 * (BEFORE + AFTER))
    return context.execute(POLARS_BY_UNIT.format(query=query)).collect()


def run_lazynwb_intervals(plan: dict, analysis: str) -> object:
    """lazynwb's `get_spike_times_in_intervals`, with no observation intervals to apply: a list per (unit, trial)."""
    import polars as pl

    lazynwb = quiet_lazynwb()
    units = lazynwb.get_df(plan["nwb"], "/units", exact_path=True, as_polars=True)
    cue = pl.col("goCue_start_time")
    found = lazynwb.get_spike_times_in_intervals(
        units,
        {"spikes": (cue - BEFORE, cue + AFTER)},
        apply_obs_intervals=False,
        disable_progress=True,
        as_polars=True,
    )
    return found.select(unit="_units_table_index", trial="_intervals_table_index", t=pl.col("spikes") - cue)


#: Each arm: its runner, the analyses it offers, and the modules it imports before its clock starts.
ARMS: dict[str, tuple[Callable[[dict, str], object], tuple[str, ...], tuple[str, ...]]] = {
    "packet pandas": (run_packet_pandas, ANALYSES, ("escapewheel_reader", "pandas", "numpy")),
    "pynwb pandas": (run_pynwb_pandas, ANALYSES, ("hdmf_zarr.nwb_zarrv2", "h5py", "remfile", "numpy", "pandas")),
    "lazynwb pandas": (run_lazynwb_pandas, ANALYSES, ("lazynwb", "pandas", "numpy")),
    "packet polars": (run_packet_polars, ANALYSES, ("escapewheel_reader", "polars")),
    "packet scanner": (run_packet_scanner, ANALYSES, ("escapewheel_reader", "pyarrow.dataset", "numpy")),
    "lazynwb polars": (run_lazynwb_polars, ANALYSES, ("lazynwb", "polars")),
    "packet duckdb": (run_packet_duckdb, ANALYSES, ("escapewheel_reader", "duckdb")),
    "lazynwb sql": (run_lazynwb_sql, ANALYSES, ("lazynwb", "polars", "numpy")),
    "pynwb duckdb": (
        run_pynwb_duckdb,
        ANALYSES,
        ("hdmf_zarr.nwb_zarrv2", "h5py", "remfile", "numpy", "pandas", "duckdb"),
    ),
    "packet aligned_spikes": (run_packet_aligned, (RASTERS,), ("escapewheel_reader", "duckdb")),
    "lazynwb intervals": (run_lazynwb_intervals, (RASTERS,), ("lazynwb", "polars")),
}


def make_plan(packet_path: str, nwb_path: str) -> dict:
    """Settle, from the packet, every value a child would otherwise read before its clock starts."""
    from escapewheel_reader import open_packet as opened
    from escapewheel_reader import reference_clock

    packet = opened(packet_path)
    origin = packet.sql(
        "SELECT c.tick_rate_num AS num, c.tick_rate_den AS den "
        "FROM core_sessions s JOIN core_clocks c ON c.clock_id = s.reference_clock_id"
    ).to_pylist()[0]
    if origin["num"] % origin["den"]:
        sys.exit("the reference clock's rate is not a whole number of ticks per second")
    trials = [
        resource.resource_id for resource in packet.manifest.resources if resource.resource_id.endswith(".trials")
    ]
    if len(trials) != 1:
        sys.exit(f"want one task trials table, found {trials}")
    return {
        "packet": packet_path,
        "nwb": nwb_path,
        "region_aws": os.environ.get("AWS_REGION", "us-west-2"),
        "trials": trials[0],
        "clock": reference_clock(packet),
        "rate": origin["num"] // origin["den"],
    }


def child(arm: str, analysis: str, plan: dict) -> None:
    """One cold cell, printed as JSON."""
    warnings.filterwarnings("ignore")
    runner, _, modules = ARMS[arm]
    for module in modules:
        importlib.import_module(module)
    benchkit.cold_child(
        [plan["packet"], plan["nwb"]], lambda: runner(plan, analysis), raster_summary if analysis == RASTERS else None
    )


def agreement(cells: list[dict], analysis: str) -> list[str]:
    """The arms of an analysis grouped by the counts they returned, when they differ.

    Summed seconds depend on the order of a float sum, so they group nothing and are shown as a range.
    """
    groups: dict[str, list[tuple[str, float | None]]] = {}
    for cell in cells:
        if cell["analysis"] == analysis and cell.get("runs"):
            value = ast.literal_eval(cell["value"])
            key = {name: found for name, found in value.items() if name not in ("join", "offset_s")}
            groups.setdefault(str(key), []).append((cell["arm"], value.get("offset_s")))
    if len(groups) < 2:
        return []
    notes = []
    for key, members in groups.items():
        offsets = [offset for _, offset in members if offset is not None]
        spread = f", offset_s {min(offsets)}-{max(offsets)}" if offsets else ""
        notes.append(f"{analysis}: {key}{spread} from {', '.join(arm for arm, _ in members)}")
    return notes


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
    plan = make_plan(packet, nwb)
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
    print(f"{'arm':28s}" + "".join(f"{analysis:>24s}" for analysis in args.analyses))
    for arm in args.arms:
        texts = []
        for analysis in args.analyses:
            if analysis not in ARMS[arm][1]:
                texts.append("-")
                continue
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
        print(f"{arm:28s}" + "".join(f"{text:>24s}" for text in texts), flush=True)
    print("\nwhat each returned:")
    for cell in result["cells"]:
        print(f"  {cell['analysis']:14s} {cell['arm']:28s} {cell.get('value', cell.get('error'))}")
    result["disagreements"] = [note for analysis in args.analyses for note in agreement(result["cells"], analysis)]
    print("\n" + ("\n".join(result["disagreements"]) or "every arm agreed"))
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
