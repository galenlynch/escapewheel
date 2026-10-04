"""Two trial analyses of one session, cold, in every pattern each store's readers offer.

`lick latency` is, per trial, the first lick of either spout after the go cue and before the next
trial's cue; it reads the trials and the lick times. `go-cue spikes` is, for every unit, the spikes
in the closed window [-1, +2] s around each go cue, a spike counting once per window it falls in;
it reads the trials and every spike. Each arm reduces its result to the same few numbers, so
`value` shows whether they agree: for latency, the trials with a lick and the median and mean
latency; for spikes, the (spike, cue) pairs, the units with any, the sum of squared per-unit counts
and the summed time from cue.

The arms are three patterns of analysis and the helpers that do it for the caller:

- `pandas`: each needed table read whole into pandas, then one shared NumPy analysis. The packet's
  arm reads `analysis.spike_events`, every spike already on the reference clock, and adds seconds
  with the reader's `seconds`; `needed columns` does the same reading only the columns used.
- Out of core: the packet through `TableResource.scan_polars`, and through `Packet.scan` with
  PyArrow's default memory pool and with the reader's `read_pool()`; the NWB through lazynwb's
  `scan_nwb`. The packet's work in ticks on its reference clock, as a reader of the format would,
  and convert only the result. The Polars arms search the sorted cues from each spike in a
  streaming plan rather than state a range join, which Polars builds pair by pair in memory.
- SQL: the packet through DuckDB, the NWB through lazynwb's Polars `SQLContext`, and pynwb's
  `to_dataframe` frames through DuckDB. The NWB arms state the range join; the packet's states the
  ASOF join its reader's documentation recommends, falling back to the range join when two cues'
  windows overlap, and reports which it used.
- Helpers, for spikes only: the reader's `aligned_spikes`, whose window is symmetric, so it is
  asked for +-2 s and the result narrowed to -1 s; and lazynwb's `get_spike_times_in_intervals`,
  whose window excludes its end.

The packet's out-of-core and SQL arms read lick and cue ticks as stored, which holds because both
are on the reference clock in the packets measured; the pandas arm maps them anyway. Every
other convention, cold cells, stores and credentials, is `readers.py`'s.

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

ANALYSES = ("lick latency", "go-cue spikes")
# The window around a go cue, in seconds.
BEFORE, AFTER = 1, 2
LICKS = ("left_lick", "right_lick")
NWB_LICKS = ("left_lick_time", "right_lick_time")


# The shared analyses, on NumPy arrays in one unit of time.


def latencies(go, licks):
    """Per cue, the first lick after it and before the next cue, less the cue; NaN where none."""
    import numpy as np

    go, licks = np.sort(np.asarray(go)), np.sort(np.asarray(licks))
    after = np.searchsorted(licks, go, side="right")
    following = np.append(go[1:], np.inf)
    first = licks[np.minimum(after, len(licks) - 1)]
    found = (after < len(licks)) & (first < following)
    out = np.full(len(go), np.nan)
    out[found] = first[found] - go[found]
    return out


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


def window_sums(go, times, before, after):
    """Per spike, how many cue windows hold it and its summed time from those cues."""
    import numpy as np

    lo = np.searchsorted(go, times - after, side="left")
    hi = np.searchsorted(go, times + before, side="right")
    prefix = np.concatenate(([0], np.cumsum(go)))
    counts = hi - lo
    return counts, counts * times - (prefix[hi] - prefix[lo])


def per_unit(units, go, times, before, after):
    """Pairs and summed time from cue per unit, for units with any."""
    import numpy as np

    counts, offsets = window_sums(np.sort(np.asarray(go)), np.asarray(times), before, after)
    inside = counts > 0
    keys, codes = np.unique(np.asarray(units)[inside], return_inverse=True)
    return np.bincount(codes, weights=counts[inside]), np.bincount(codes, weights=offsets[inside])


def spike_summary(pairs, offsets, per_second: float = 1.0) -> dict:
    """Pairs, units with any, sum of squared per-unit pairs, and summed seconds from cue."""
    import numpy as np

    pairs = np.asarray(pairs, dtype=float)
    pairs = pairs[pairs > 0]
    return {
        "pairs": int(pairs.sum()),
        "units": len(pairs),
        "sum_sq": int((pairs**2).sum()),
        "offset_s": round(float(np.sum(offsets)) / per_second, 1),
    }


# The packet.


def open_packet(plan: dict):
    from escapewheel_reader import open_packet as opened

    return opened(plan["packet"])


def run_packet_pandas(plan: dict, analysis: str, pruned: bool = False) -> object:
    """Tables into pandas, ticks through the reader's `on_clock` and `seconds`.

    Whole tables by default; `pruned` names the columns the analysis uses and converts only those.
    """
    import pyarrow as pa
    from escapewheel_reader import on_clock, seconds

    packet = open_packet(plan)

    def read(name: str, columns: list[str]) -> pa.Table:
        return packet.table(name, columns=columns if pruned else None)

    trials = read(plan["trials"], ["go_cue_start_tick"]).to_pandas()
    cue = pa.table({"t_tick": trials["go_cue_start_tick"].to_numpy(), "clock_id": [plan["clock"]] * len(trials)})
    go = seconds(packet, cue)["t_second"].to_numpy()
    if analysis == "lick latency":
        events = on_clock(packet, read("core.events", ["stream_id", "t_tick"]).join(stream_clocks(packet), "stream_id"))
        events = seconds(packet, events)
        events = (events.select(["stream_id", "t_second"]) if pruned else events).to_pandas()
        streams = read("core.event_streams", ["event_stream_id", "event_type"]).to_pandas()
        lick_streams = streams.loc[streams["event_type"].isin(LICKS), "event_stream_id"]
        return lick_summary(latencies(go, events.loc[events["stream_id"].isin(lick_streams), "t_second"]))
    spikes = seconds(packet, read("analysis.spike_events", ["unit_id", "t_tick", "clock_id"]))
    spikes = (spikes.select(["unit_id", "t_second"]) if pruned else spikes).to_pandas()
    return spike_summary(*per_unit(spikes["unit_id"], go, spikes["t_second"].to_numpy(), BEFORE, AFTER))


def stream_clocks(packet):
    """`core.event_streams`' clock per stream, keyed as `core.events` names it."""
    streams = packet.table("core.event_streams", columns=["event_stream_id", "clock_id"])
    return streams.rename_columns(["stream_id", "clock_id"])


def lick_streams(packet) -> list[int]:
    return [
        row["event_stream_id"]
        for row in packet.table("core.event_streams", columns=["event_stream_id", "event_type"]).to_pylist()
        if row["event_type"] in LICKS
    ]


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
    spikes = scan("analysis.spike_events").select(unit="unit_id", t="t_tick")
    found = polars_windows(spikes, go.collect()["g"], BEFORE * rate, AFTER * rate)
    return spike_summary(found["pairs"].to_numpy(), found["offset"].to_numpy(), rate)


def polars_windows(spikes, go, before, after):
    """`window_sums` as a streaming Polars plan over (unit, t), the cues held as a sorted literal.

    `join_where`, the range join Polars SQL plans for the same question, builds every pair before
    grouping them; this streams.
    """
    import numpy as np
    import polars as pl

    go = go.sort()
    prefix = pl.lit(pl.Series(np.concatenate(([0], np.cumsum(go.to_numpy())))))
    t, lo, hi = pl.col("t"), pl.col("lo"), pl.col("hi")
    return (
        spikes.with_columns(
            lo=pl.lit(go).search_sorted(t - after, side="left"), hi=pl.lit(go).search_sorted(t + before, side="right")
        )
        .filter(hi > lo)
        .with_columns(pairs=(hi - lo).cast(pl.Int64))
        .with_columns(offset=pl.col("pairs") * t - (prefix.gather(hi) - prefix.gather(lo)))
        .group_by("unit")
        .agg(pl.col("pairs").sum(), pl.col("offset").sum())
        .collect(engine="streaming")
    )


def run_packet_dataset(plan: dict, analysis: str, pool: bool = False) -> object:
    """`Packet.scan` datasets streamed in batches into the shared NumPy analysis."""
    import numpy as np
    import pyarrow.dataset as ds
    from escapewheel_reader.resources import read_pool

    packet = open_packet(plan)
    memory = {"memory_pool": read_pool()} if pool else {}
    go = packet.scan(plan["trials"]).to_table(columns=["go_cue_start_tick"], **memory)["go_cue_start_tick"]
    go = np.sort(go.to_numpy())
    rate = plan["rate"]
    if analysis == "lick latency":
        licks = packet.scan("core.events").to_table(
            columns=["t_tick"], filter=ds.field("stream_id").isin(lick_streams(packet)), **memory
        )
        return lick_summary(latencies(go, licks["t_tick"].to_numpy()), rate)
    units, pairs, offsets = [], [], []
    for batch in packet.scan("analysis.spike_events").to_batches(columns=["unit_id", "t_tick"], **memory):
        counts, offset = window_sums(go, batch["t_tick"].to_numpy(), BEFORE * rate, AFTER * rate)
        inside = counts > 0
        units.append(batch["unit_id"].to_numpy()[inside])
        pairs.append(counts[inside])
        offsets.append(offset[inside])
    _, codes = np.unique(np.concatenate(units), return_inverse=True)
    return spike_summary(
        np.bincount(codes, weights=np.concatenate(pairs)), np.bincount(codes, weights=np.concatenate(offsets)), rate
    )


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
SELECT s.unit_id, count(*) AS pairs, sum(s.t_tick - t.go_cue_start_tick) AS offset
FROM analysis_spike_events s JOIN {trials} t
  ON s.t_tick BETWEEN t.go_cue_start_tick - {before} AND t.go_cue_start_tick + {after}
GROUP BY s.unit_id
"""

# The same pairs while no spike lies in two windows: each spike meets the latest cue whose window
# has opened, and is dropped if that window has closed.
SPIKE_ASOF_SQL = """
SELECT s.unit_id, count(*) AS pairs, sum(s.t_tick - t.go_cue_start_tick) AS offset
FROM analysis_spike_events s
ASOF JOIN (SELECT go_cue_start_tick FROM {trials} WHERE go_cue_start_tick IS NOT NULL) t
  ON s.t_tick + {before} >= t.go_cue_start_tick
WHERE s.t_tick <= t.go_cue_start_tick + {after}
GROUP BY s.unit_id
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
    # Two cues closer than the window's width put a spike in both windows, which ASOF cannot pair.
    join = "asof" if gap is None or gap > before + after else "range"
    query = (SPIKE_ASOF_SQL if join == "asof" else SPIKE_SQL).format(trials=trials, before=before, after=after)
    found = con.sql(query).to_arrow_table()
    return {**spike_summary(found["pairs"].to_numpy(), found["offset"].to_numpy(), rate), "join": join}


def run_packet_aligned(plan: dict, analysis: str) -> object:
    """The reader's `aligned_spikes`, asked for the symmetric window that covers ours."""
    from escapewheel_reader import aligned_spikes, windows_disjoint

    packet = open_packet(plan)
    rate = plan["rate"]
    half = max(BEFORE, AFTER) * rate
    con = connection(plan)
    join = "asof" if windows_disjoint(packet, "go_cue", half) else "range"
    found = (
        aligned_spikes(packet, "go_cue", half, connection=con)
        .filter(f"t_rel_tick BETWEEN {-BEFORE * rate} AND {AFTER * rate}")
        .aggregate("unit_id, count(*) AS pairs, sum(t_rel_tick) AS offset", "unit_id")
        .to_arrow_table()
    )
    return {**spike_summary(found["pairs"].to_numpy(), found["offset"].to_numpy(), rate), "join": join}


# The NWB.


def read_nwb(plan: dict):
    from hdmf_zarr.nwb_zarrv2 import NWBZarrV2IO

    # An AIND NWB-Zarr stores its object-reference columns with the pickle codec.
    options = {"anon": False} if benchkit.is_remote(plan["nwb"]) else None
    return NWBZarrV2IO(plan["nwb"], "r", allow_pickle=True, storage_options=options).read()


def flat_spikes(trains):
    """A ragged column of trains as (row, time) arrays."""
    import numpy as np

    lengths = np.fromiter((len(train) for train in trains), dtype=np.int64, count=len(trains))
    return np.repeat(np.arange(len(trains)), lengths), np.concatenate([np.asarray(train) for train in trains])


def nwb_frames(plan: dict, analysis: str):
    """pynwb's frames for an analysis: trials by `to_dataframe`, licks or units beside them."""
    import numpy as np
    import pandas as pd

    nwb = read_nwb(plan)
    trials = nwb.intervals["trials"].to_dataframe()
    if analysis == "lick latency":
        licks = np.concatenate([np.asarray(nwb.acquisition[name].timestamps[:]) for name in NWB_LICKS])
        return trials, pd.DataFrame({"t": licks})
    rows, times = flat_spikes(nwb.units.to_dataframe()["spike_times"].to_numpy())
    return trials, pd.DataFrame({"unit": rows, "t": times})


def run_pynwb_pandas(plan: dict, analysis: str) -> object:
    """pynwb's `to_dataframe` frames and the shared NumPy analysis."""
    trials, other = nwb_frames(plan, analysis)
    go = trials["goCue_start_time"].to_numpy()
    if analysis == "lick latency":
        return lick_summary(latencies(go, other["t"].to_numpy()))
    return spike_summary(*per_unit(other["unit"].to_numpy(), go, other["t"].to_numpy(), BEFORE, AFTER))


NWB_LICK_SQL = """
WITH go AS (
    SELECT goCue_start_time AS g, lead(goCue_start_time) OVER (ORDER BY goCue_start_time) AS following FROM trials)
SELECT min(licks.t) - g AS latency FROM go JOIN licks ON licks.t > g AND (following IS NULL OR licks.t < following)
GROUP BY g
"""

NWB_SPIKE_SQL = """
SELECT s.unit, count(*) AS pairs, sum(s.t - trials.goCue_start_time) AS offset
FROM spikes s JOIN trials ON s.t BETWEEN trials.goCue_start_time - {before} AND trials.goCue_start_time + {after}
GROUP BY s.unit
"""


def run_pynwb_duckdb(plan: dict, analysis: str) -> object:
    """DuckDB over pynwb's `to_dataframe` frames."""
    import duckdb

    trials, other = nwb_frames(plan, analysis)
    con = duckdb.connect()
    con.register("trials", trials[["goCue_start_time"]])
    if analysis == "lick latency":
        con.register("licks", other)
        return lick_summary(con.sql(NWB_LICK_SQL).fetchnumpy()["latency"])
    con.register("spikes", other)
    found = con.sql(NWB_SPIKE_SQL.format(before=BEFORE, after=AFTER)).fetchnumpy()
    return spike_summary(found["pairs"], found["offset"])


def quiet_lazynwb():
    import lazynwb

    logging.disable(logging.WARNING)
    return lazynwb


def run_lazynwb_pandas(plan: dict, analysis: str) -> object:
    """lazynwb's `get_df` frames and the shared NumPy analysis."""
    lazynwb = quiet_lazynwb()
    trials = lazynwb.get_df(plan["nwb"], "/intervals/trials", exact_path=True, as_polars=False)
    go = trials["goCue_start_time"].to_numpy()
    if analysis == "lick latency":
        import numpy as np

        licks = [
            lazynwb.get_df(plan["nwb"], f"/acquisition/{name}", exact_path=True, as_polars=False)["timestamps"]
            for name in NWB_LICKS
        ]
        return lick_summary(latencies(go, np.concatenate([frame.to_numpy() for frame in licks])))
    units = lazynwb.get_df(plan["nwb"], "/units", exact_path=True, exclude_array_columns=False, as_polars=False)
    rows, times = flat_spikes(units["spike_times"].to_numpy())
    return spike_summary(*per_unit(rows, go, times, BEFORE, AFTER))


def run_lazynwb_polars(plan: dict, analysis: str) -> object:
    """lazynwb's `scan_nwb` lazy frames."""
    import polars as pl

    lazynwb = quiet_lazynwb()
    go = lazynwb.scan_nwb(plan["nwb"], "/intervals/trials").select(g=pl.col("goCue_start_time")).sort("g")
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
    found = polars_windows(spikes, go.collect()["g"], BEFORE, AFTER)
    return spike_summary(found["pairs"].to_numpy(), found["offset"].to_numpy())


POLARS_LICK_SQL = """
WITH go AS (
    SELECT goCue_start_time AS g, LEAD(goCue_start_time) OVER (ORDER BY goCue_start_time) AS following FROM trials),
licks AS (SELECT timestamps AS t FROM left_lick_time UNION ALL SELECT timestamps AS t FROM right_lick_time)
SELECT min(licks.t - go.g) AS latency FROM go JOIN licks ON licks.t > go.g
WHERE go.following IS NULL OR licks.t < go.following GROUP BY go.g
"""

POLARS_SPIKE_SQL = """
SELECT s.unit, count(*) AS pairs, sum(s.t - trials.goCue_start_time) AS offset
FROM (SELECT _table_index AS unit, UNNEST(spike_times) AS t FROM units) s
JOIN trials ON s.t >= trials.goCue_start_time - {before} AND s.t <= trials.goCue_start_time + {after}
GROUP BY s.unit
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
    found = context.execute(POLARS_SPIKE_SQL.format(before=BEFORE, after=AFTER)).collect()
    return spike_summary(found["pairs"].to_numpy(), found["offset"].to_numpy())


def run_lazynwb_intervals(plan: dict, analysis: str) -> object:
    """lazynwb's `get_spike_times_in_intervals`, with no observation intervals to apply."""
    import numpy as np
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
    found = found.select(
        unit=pl.col("_units_table_index"),
        pairs=pl.col("spikes").list.len(),
        offset=(pl.col("spikes").list.sum() - pl.col("spikes").list.len() * cue),
    )
    grouped = found.group_by("unit").agg(pl.col("pairs").sum(), pl.col("offset").sum())
    return spike_summary(grouped["pairs"].to_numpy(), np.nan_to_num(grouped["offset"].to_numpy()))


#: Each arm: its runner, the analyses it offers, and the modules it imports before its clock starts.
ARMS: dict[str, tuple[Callable[[dict, str], object], tuple[str, ...], tuple[str, ...]]] = {
    "packet pandas": (run_packet_pandas, ANALYSES, ("escapewheel_reader", "pandas", "numpy")),
    "packet pandas, needed columns": (
        lambda plan, analysis: run_packet_pandas(plan, analysis, pruned=True),
        ANALYSES,
        ("escapewheel_reader", "pandas", "numpy"),
    ),
    "pynwb pandas": (run_pynwb_pandas, ANALYSES, ("hdmf_zarr.nwb_zarrv2", "numpy", "pandas")),
    "lazynwb pandas": (run_lazynwb_pandas, ANALYSES, ("lazynwb", "pandas", "numpy")),
    "packet polars": (run_packet_polars, ANALYSES, ("escapewheel_reader", "polars")),
    "packet dataset": (run_packet_dataset, ANALYSES, ("escapewheel_reader", "pyarrow.dataset", "numpy")),
    "packet dataset, read_pool": (
        lambda plan, analysis: run_packet_dataset(plan, analysis, pool=True),
        ANALYSES,
        ("escapewheel_reader", "pyarrow.dataset", "numpy"),
    ),
    "lazynwb polars": (run_lazynwb_polars, ANALYSES, ("lazynwb", "polars")),
    "packet duckdb": (run_packet_duckdb, ANALYSES, ("escapewheel_reader", "duckdb")),
    "lazynwb sql": (run_lazynwb_sql, ANALYSES, ("lazynwb", "polars", "numpy")),
    "pynwb duckdb": (run_pynwb_duckdb, ANALYSES, ("hdmf_zarr.nwb_zarrv2", "numpy", "pandas", "duckdb")),
    "packet aligned_spikes": (run_packet_aligned, ("go-cue spikes",), ("escapewheel_reader", "duckdb")),
    "lazynwb intervals": (run_lazynwb_intervals, ("go-cue spikes",), ("lazynwb", "polars", "numpy")),
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
    benchkit.cold_child([plan["packet"], plan["nwb"]], lambda: runner(plan, analysis))


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
