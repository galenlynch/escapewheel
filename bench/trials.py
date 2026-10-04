"""Two trial analyses of one session, cold, each arm answering in its own library's fastest idiom.

Each analysis is a target, stated here and checked after the clock stops; how an arm reaches it is
its own, so arms differ in algorithm as their libraries do.

`lick latency` is, per trial, the first lick of either spout after the go cue and before the next
trial's cue. Its value is the trials with a lick and the median and mean latency.

`go-cue rasters` is what a raster plot of every unit draws: each spike within the closed window
[-1, +2] s of a go cue, as its unit, its trial and its time from the cue in seconds, one row per
(spike, cue) pair, grouped by unit and then trial so each unit's raster is one stretch of rows. Any
table-like form serves, flat or a list per (unit, trial). No two cues in the sessions measured lie
within a window's width, so no spike belongs to two windows; an arm relying on that checks it and
refuses otherwise. Its value is the pairs, the units with any, the sums of squared counts per unit
and per (unit, trial), the summed seconds from cue, and whether the rows came grouped.

The arms:

- pandas: the columns each analysis uses read into pandas, each spike's cue found by
  `np.searchsorted` and each cue's lick by `merge_asof`. The packet's arm reads
  `core.spike_events` through `Packet.table` onto the reference clock in seconds; it and the NWB
  are stored unit by unit, so the raster comes out grouped. pynwb reads its trials with
  `to_dataframe` and its spikes as the ragged column's flat data and index, and lazynwb reads the
  units' `spike_times` alone with `get_df`.
- PyArrow: the packet through `Packet.scanner`, its batches handed to NumPy. Spikes come from
  `analysis.spike_events`, already on the reference clock, where each unit is an ascending run per
  time bucket: every run is searched for the cues near it at once, and the slices found, not the
  spikes, are ordered into the raster.
- Polars: the packet through `TableResource.scan_polars` and the NWB through lazynwb's `scan_nwb`.
- SQL: the packet through DuckDB, the NWB through lazynwb's Polars `SQLContext`, and pynwb's frames
  through DuckDB.

The Polars and SQL arms join spikes to cues on bins twice the window's width, each cue entered
under the bin its window opens in and the next, and keep the exact window after: a hash join, where
an ASOF join sorts every spike and a range join tests every pair. Each orders by unit and trial.
- Helpers, for rasters only: the reader's `aligned_spikes`, whose window is symmetric, so it is
  asked for +-2 s and narrowed to -1 s, and which names a trial by its cue's tick; and lazynwb's
  `get_spike_times_in_intervals`, which returns a list per (unit, trial) and whose window excludes
  its end.

The packet's Polars, PyArrow and SQL arms read lick and cue ticks as stored, which holds because
both are on the reference clock in the packets measured. Every other convention, cold cells,
stores and credentials, is `readers.py`'s.

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


def disjoint(go, before, after) -> None:
    """Refuse cues whose windows overlap, where a spike would belong to two and an as-of match finds one."""
    import numpy as np

    go = np.sort(np.asarray(go, dtype=float))
    gaps = np.diff(go[~np.isnan(go)])
    if len(gaps) and gaps.min() <= before + after:
        raise ValueError(f"two go cues lie {gaps.min()} apart, inside one window's width")


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


def pandas_raster(spikes, trials):
    """Each spike's cue found by `np.searchsorted`, the spikes' own order kept.

    `spikes` holds `unit` and `t`, `trials` holds `trial` and `g`, all in seconds. The latest cue
    whose window has opened is the only one that can hold a spike, since windows do not overlap.
    An `IntervalIndex` lookup answers the same a hundred times slower.
    """
    import numpy as np
    import pandas as pd

    trials = trials.dropna(subset="g").sort_values("g")
    go = trials["g"].to_numpy()
    disjoint(go, BEFORE, AFTER)
    t = spikes["t"].to_numpy()
    cue = np.searchsorted(go, t + BEFORE, side="right") - 1
    hit = (cue >= 0) & (t <= go[np.maximum(cue, 0)] + AFTER)
    cue = cue[hit]
    return pd.DataFrame(
        {
            "unit": spikes["unit"].to_numpy()[hit],
            "trial": trials["trial"].to_numpy()[cue],
            "t": t[hit] - go[cue],
        }
    )


def raster_summary(found) -> dict:
    """What a raster holds, from any table-like form with `unit`, `trial` and `t`, flat or a list per (unit, trial).

    Counts per unit and per (unit, trial) agree across arms whatever they number units and trials
    by; `ordered` says each unit's raster is one stretch of rows, its trials ascending.
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
    if frame.schema["t"] == pl.List:
        frame = frame.filter(pl.col("t").list.len() > 0)
        cells = frame.select("unit", "trial", n=pl.col("t").list.len(), s=pl.col("t").list.sum())
        unit, trial = cells["unit"].to_numpy(), cells["trial"].to_numpy()
    else:
        unit, trial = frame["unit"].to_numpy(), frame["trial"].to_numpy()
        cells = frame.group_by("unit", "trial").agg(n=pl.len(), s=pl.col("t").sum())
    step = (unit[1:] > unit[:-1]) | ((unit[1:] == unit[:-1]) & (trial[1:] >= trial[:-1]))
    per_unit = cells.group_by("unit").agg(pl.col("n").sum())["n"].to_numpy()
    n = cells["n"].to_numpy()
    return {
        "pairs": int(n.sum()),
        "units": len(per_unit),
        "sum_sq": int((per_unit.astype(np.int64) ** 2).sum()),
        "cells": len(n),
        "cell_sq": int((n.astype(np.int64) ** 2).sum()),
        "offset_s": round(float(cells["s"].sum()), 1),
        "ordered": bool(step.all()),
    }


# The packet.


#: On the reference clock, by time bucket and then unit, so each unit is a sorted run per bucket.
SPIKES = "analysis.spike_events"


def open_packet(plan: dict):
    from escapewheel_reader import open_packet as opened

    return opened(plan["packet"])


def run_packet_pandas(plan: dict, analysis: str) -> object:
    """The columns each analysis uses into pandas, read by `Packet.table` onto the reference clock and in seconds.

    Spikes come from `analysis.spike_events`, already on the reference clock.
    """
    import pandas as pd

    packet = open_packet(plan)

    def read(name: str, columns: list[str], **where) -> pd.DataFrame:
        return packet.table(name, columns=columns, on_clock=True, seconds=True, **where).to_pandas()

    trials = read(plan["trials"], ["session_id", "trial_id", "go_cue_start_tick"])
    if analysis == "lick latency":
        licks = read("core.events", ["stream_id", "t_tick"], stream_id=lick_streams(packet))
        return lick_summary(pandas_latencies(trials["go_cue_start_second"], licks["t_second"]))
    # Stored by unit and then time, so the raster comes out grouped with no sort.
    spikes = read("core.spike_events", ["unit_id", "t_tick"])
    return pandas_raster(
        spikes.rename(columns={"unit_id": "unit", "t_second": "t"}),
        trials.rename(columns={"trial_id": "trial", "go_cue_start_second": "g"}),
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

    disjoint(trials["g"], before, after)
    # Twice the window, so a float rounding at a bin's edge cannot carry a window into a third bin.
    width = 2 * (before + after)
    t, g = pl.col("t"), pl.col("g")
    cues = pl.concat([trials.lazy().with_columns(bin=((g - before) // width).cast(pl.Int64) + k) for k in (0, 1)])
    return (
        spikes.with_columns(bin=(t // width).cast(pl.Int64))
        .join(cues, on="bin")
        .filter(t.is_between(g - before, g + after))
        .select("unit", "trial", t=(t - g) / per_second)
        .sort("unit", "trial")
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
    found = [
        windows(batch["unit_id"].to_numpy(), batch["t_tick"].to_numpy(), go, BEFORE * rate, AFTER * rate)
        for batch in packet.scanner(SPIKES, columns=["unit_id", "t_tick"]).to_batches()
    ]
    return pa.table(
        raster(*(np.concatenate(part) for part in zip(*found, strict=True)), trials["trial_id"].to_numpy(), rate)
    )


def spans(starts, lengths):
    """Positions covering each span `[start, start + length)`, in turn."""
    import numpy as np

    return np.repeat(starts - (np.cumsum(lengths) - lengths), lengths) + np.arange(lengths.sum())


def windows(units, times, go, before, after):
    """Each run's spikes in each cue window reaching it, as slices: unit, cue position, length, and ticks from cue.

    `analysis.spike_events` holds each unit as an ascending run per time bucket. A key offsetting
    each run past the last searches every run's windows in one call, and ordering the slices
    rather than the spikes groups the raster.
    """
    import numpy as np

    if not len(times):
        empty = np.zeros(0, dtype=np.int64)
        return empty, empty, empty, empty
    starts = np.concatenate(([0], np.flatnonzero((units[1:] != units[:-1]) | (times[1:] < times[:-1])) + 1))
    ends = np.append(starts[1:], len(times))
    first = np.searchsorted(go, times[starts] - after, side="left")
    near = np.maximum(np.searchsorted(go, times[ends - 1] + before, side="right") - first, 0)
    run, cue = np.repeat(np.arange(len(starts)), near), spans(first, near)
    origin = int(times.min())
    width = int(times.max()) - origin + 1
    key = np.repeat(np.arange(len(starts)) * width, ends - starts) + (times - origin)
    lo = np.searchsorted(key, run * width + np.clip(go[cue] - before - origin, 0, width - 1), side="left")
    hi = np.searchsorted(key, run * width + np.clip(go[cue] + after - origin, 0, width - 1), side="right")
    lengths = hi - lo
    kept = lengths > 0
    lo, lengths, run, cue = lo[kept], lengths[kept], run[kept], cue[kept]
    return units[starts][run], cue, lengths, times[spans(lo, lengths)] - np.repeat(go[cue], lengths)


def raster(unit, cue, lengths, offsets, trial, per_second):
    """The slices of :func:`windows` ordered by unit and then trial, a stable sort keeping each unit's runs in time."""
    import numpy as np

    order = np.lexsort((cue, unit))
    starts, lengths = (np.cumsum(lengths) - lengths)[order], lengths[order]
    return {
        "unit": np.repeat(unit[order], lengths),
        "trial": np.repeat(trial[cue[order]], lengths),
        "t": offsets[spans(starts, lengths)] / per_second,
    }


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
ORDER BY unit, trial
"""

CUE_GAP_SQL = """
SELECT min(d) FROM (
  SELECT go_cue_start_tick - lag(go_cue_start_tick) OVER (ORDER BY go_cue_start_tick) AS d FROM {trials})
"""


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
    gap = con.sql(CUE_GAP_SQL.format(trials=trials)).fetchone()[0]
    if gap is not None and gap <= before + after:
        raise ValueError(f"two go cues lie {gap} ticks apart, inside one window's width")
    width = 2 * (before + after)
    query = SPIKE_SQL.format(trials=trials, before=before, after=after, width=width, rate=rate)
    return con.sql(query).to_arrow_table()


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
        .select(f"unit_id AS unit, event_tick AS trial, t_rel_tick / {rate} AS t")
        .order("unit, trial")
        .to_arrow_table()
    )
    return found


# The NWB.


def read_nwb(plan: dict):
    from hdmf_zarr.nwb_zarrv2 import NWBZarrV2IO

    # An AIND NWB-Zarr stores its object-reference columns with the pickle codec.
    options = {"anon": benchkit.anonymous()} if benchkit.is_remote(plan["nwb"]) else None
    return NWBZarrV2IO(plan["nwb"], "r", allow_pickle=True, storage_options=options).read()


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
    # Stored unit by unit and in time within each, so the raster comes out grouped with no sort.
    return pandas_raster(other, pd.DataFrame({"trial": trials.index, "g": trials["goCue_start_time"].to_numpy()}))


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
ORDER BY s.unit, c.trial
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
    gap = con.sql(CUE_GAP_SQL.format(trials="trials").replace("go_cue_start_tick", "goCue_start_time")).fetchone()[0]
    if gap is not None and gap <= BEFORE + AFTER:
        raise ValueError(f"two go cues lie {gap} s apart, inside one window's width")
    width = 2 * (BEFORE + AFTER)
    return con.sql(NWB_SPIKE_SQL.format(before=BEFORE, after=AFTER, width=width)).to_arrow_table()


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
    return pandas_raster(spikes, pd.DataFrame({"trial": trials["_table_index"].to_numpy(), "g": go}))


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
ORDER BY s.unit, c.trial
"""


def run_lazynwb_sql(plan: dict, analysis: str) -> object:
    """lazynwb's Polars `SQLContext` over the NWB."""
    lazynwb = quiet_lazynwb()
    names = ["trials", *NWB_LICKS] if analysis == "lick latency" else ["trials", "units"]
    context = lazynwb.get_sql_context(
        plan["nwb"], exclude_array_columns=False, table_names=names, disable_progress=True
    )
    if analysis == "lick latency":
        return lick_summary(context.execute(POLARS_LICK_SQL).collect()["latency"].to_numpy())
    return context.execute(POLARS_SPIKE_SQL.format(before=BEFORE, after=AFTER, width=2 * (BEFORE + AFTER))).collect()


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
    "pynwb pandas": (run_pynwb_pandas, ANALYSES, ("hdmf_zarr.nwb_zarrv2", "numpy", "pandas")),
    "lazynwb pandas": (run_lazynwb_pandas, ANALYSES, ("lazynwb", "pandas", "numpy")),
    "packet polars": (run_packet_polars, ANALYSES, ("escapewheel_reader", "polars")),
    "packet scanner": (run_packet_scanner, ANALYSES, ("escapewheel_reader", "pyarrow.dataset", "numpy")),
    "lazynwb polars": (run_lazynwb_polars, ANALYSES, ("lazynwb", "polars")),
    "packet duckdb": (run_packet_duckdb, ANALYSES, ("escapewheel_reader", "duckdb")),
    "lazynwb sql": (run_lazynwb_sql, ANALYSES, ("lazynwb", "polars", "numpy")),
    "pynwb duckdb": (run_pynwb_duckdb, ANALYSES, ("hdmf_zarr.nwb_zarrv2", "numpy", "pandas", "duckdb")),
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
    parser.add_argument("--nwb", help="the session's NWB-Zarr directory (else BENCH_NWB)")
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
