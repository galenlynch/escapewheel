"""What a reader function should return: the clock mapping stated relationally against the kernel.

The reader maps a stored tick onto the reference clock with `clocks.mapped`: NumPy's `interp`
between the two anchors around it, `rint` to an integer, the globally fitted rate from the nearer
terminal anchor beyond the ends, and a tick placed only within the bound of its nearest anchor.
Each relational arm states the same arithmetic as an ASOF join of the spikes to the anchors:

    interior   rint(p0 + (p1 - p0) / (t1 - t0) * (t - t0))    as NumPy's interp evaluates it
    beyond     p_end + rint(slope * (t - t_end))              slope from `clocks.rate`
    placed     distance to the nearest anchor <= bound * median anchor interval

with `rint` half to even, which DuckDB spells `round_even` and Polars `round(mode="half_to_even")`;
Narwhals has no rounding mode, so its arms round by `floor` and a tie test. The per-clock rate and
span come from the reader's own `clocks.rate` and anchors, a dozen rows, except in `map duckdb, sql
parameters`, which fits them in SQL too. Every packet here maps one hop, each probe clock onto the
reference; a deeper chain is the same join once per hop.

Three questions, each a group of arms:

- `map ...`: every spike of `core.spike_events` onto the reference clock, materialised, then
  dumped by stored row and compared with the kernel row by row (`map kernel` is the reference).
  The `, aggregate` arms run the same plan to a count and a sum, so the engine may stream.
- `cue ...`: the go-cue analysis of `trials.py`, spikes within [-1, +2] s of each cue, per unit,
  from the reader's eager table, from a lazy DuckDB or Polars mapping with the window added after
  it, and from a `RecordBatchReader` mapped batch by batch.
- `slice ...`: 60 s of reference-clock ticks applied after the lazy mapping, against the reader's
  widened pushdown and against `analysis.spike_events`, which is already on the reference clock.

Each cell runs in its own process under `--memory-max`, cold after eviction unless `--warm`, and
reports seconds and peak RSS at the end of the timed operation; a dump for the comparison is
written after that.

    uv run python lazy_spike.py --packet P --scratch DIR [--arms ...] [--json-out results/x.json]
    uv run python lazy_spike.py --child ARM --plan PLAN   # one cell, as JSON
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
import warnings
from pathlib import Path

import benchkit

#: Marks an unplaced row in a dump.
UNPLACED = -(2**63)
#: Seconds before and after a go cue, as `trials.py` takes them.
BEFORE, AFTER = 1, 2
#: Composite key stride for the search-sorted arm: clock_id * STRIDE + tick, with ticks below it.
STRIDE = 1 << 40


# -- shared inputs ---------------------------------------------------------------------------


def open_packet(plan: dict):
    from escapewheel_reader import open_packet as opened

    return opened(plan["packet"])


def anonymous() -> bool:
    """Whether a store is read unsigned: no keys in the environment, as for a public bucket."""
    return not os.environ.get("AWS_ACCESS_KEY_ID")


def uri(packet, resource_id: str) -> str:
    resource = packet.table_resource(resource_id)
    return str(resource.path) if resource.is_local else resource.location.uri


def edge_tables(packet, target: int, bound: float):
    """The anchors with their successors, and each clock's ends, rate and span, as Arrow tables.

    Built from the reader's memoised anchors and `clocks.rate`, as a reader handing the mapping to
    an engine would; refuses a clock whose parent is not the target, which this spike does not
    state.
    """
    import numpy as np
    import pyarrow as pa
    from escapewheel_reader import clocks

    graph = clocks.clock_graph(packet)
    rows: dict[str, list] = {k: [] for k in ("clock_id", "t0", "p0", "t1", "p1")}
    params: dict[str, list] = {k: [] for k in ("clock_id", "first_t", "first_p", "last_t", "last_p", "slope", "span")}
    for clock, (t, p) in sorted(graph.anchors.items()):
        if graph.parents.get(clock) != target:
            raise SystemExit(f"clock {clock} maps onto {graph.parents.get(clock)}, not {target}: more than one hop")
        n = t.size
        rows["clock_id"].append(np.full(n, clock, dtype=np.int32))
        rows["t0"].append(t)
        rows["p0"].append(p)
        rows["t1"].append(np.append(t[1:], 0))
        rows["p1"].append(np.append(p[1:], 0))
        slope, _ = clocks.rate(t, p)
        for name, value in zip(
            params,
            (clock, int(t[0]), int(p[0]), int(t[-1]), int(p[-1]), slope, float(np.median(np.diff(t))) * bound),
            strict=True,
        ):
            params[name].append(value)
    last = np.concatenate([np.arange(len(t)) == len(t) - 1 for t in rows["t0"]])
    anchors = pa.table(
        {
            "clock_id": pa.array(np.concatenate(rows["clock_id"])),
            "t0": pa.array(np.concatenate(rows["t0"])),
            "p0": pa.array(np.concatenate(rows["p0"])),
            "t1": pa.array(np.concatenate(rows["t1"]), mask=last),
            "p1": pa.array(np.concatenate(rows["p1"]), mask=last),
        }
    )
    return anchors, pa.table({**params, "clock_id": pa.array(params["clock_id"], pa.int32())})


def unit_clocks(packet):
    """`core.units`' clock per unit, the only route from a spike to its clock."""
    return packet.table("core.units", columns=["unit_id", "clock_id"])


def cues(packet, plan: dict):
    import numpy as np

    go = packet.table(plan["trials"], columns=["go_cue_start_tick"]).column(0).drop_null().to_numpy()
    return np.sort(go)


def summary(pairs, offsets) -> dict:
    """Pairs, units with any, sum of squared per-unit pairs, summed ticks from cue: all exact."""
    import numpy as np

    pairs = np.asarray(pairs, dtype=np.int64)
    offsets = np.asarray(offsets, dtype=np.int64)
    inside = pairs > 0
    return {
        "pairs": int(pairs.sum()),
        "units": int(inside.sum()),
        "sum_sq": int((pairs[inside] ** 2).sum()),
        "offset_ticks": int(offsets[inside].sum()),
    }


# -- DuckDB ----------------------------------------------------------------------------------


def duck(plan: dict, default: bool = False):
    """A DuckDB connection; `default` is the module's own, the one Narwhals' joins query through."""
    import duckdb

    con = duckdb.default_connection() if default else duckdb.connect()
    spill = Path(plan["scratch"], "duckdb-spill")
    spill.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory = '{spill}'")
    con.execute(f"SET memory_limit = '{plan['duckdb_memory']}'")
    if benchkit.is_remote(plan["packet"]):
        # Without keys in the environment the store is read unsigned, as a public bucket needs.
        provider = "config" if plan["anonymous"] else "credential_chain, CHAIN 'env'"
        con.execute(f"CREATE SECRET store (TYPE s3, PROVIDER {provider}, REGION '{plan['region_aws']}')")
    return con


def duck_spikes(packet, stored_span: tuple[int, int] | None = None) -> str:
    where = "" if stored_span is None else f"WHERE sp.t_tick BETWEEN {stored_span[0]} AND {stored_span[1]}"
    return (
        "SELECT sp.file_row_number AS row, sp.unit_id, sp.t_tick, u.clock_id "
        f"FROM read_parquet('{uri(packet, 'core.spike_events')}', file_row_number = true) sp "
        f"JOIN units u USING (unit_id) {where}"
    )


def duck_mapping(spikes: str, target: int, rounding: str = "round_even") -> str:
    """The mapping as SQL over a relation of (row, unit_id, t_tick, clock_id), adding `placed`.

    `rounding` is applied as `rounding(x, 0)`; SQL's `round` is half away from zero, kept to count
    what it changes.
    """
    r = rounding
    return f"""
SELECT s.row, s.unit_id,
  CASE WHEN s.clock_id = {target} THEN s.t_tick
       WHEN a.t0 IS NULL THEN m.first_p + CAST({r}(m.slope * CAST(s.t_tick - m.first_t AS DOUBLE), 0) AS BIGINT)
       WHEN s.t_tick > m.last_t THEN m.last_p + CAST({r}(m.slope * CAST(s.t_tick - m.last_t AS DOUBLE), 0) AS BIGINT)
       WHEN s.t_tick = a.t0 THEN a.p0
       ELSE CAST({r}(CAST(a.p1 - a.p0 AS DOUBLE) / CAST(a.t1 - a.t0 AS DOUBLE)
                     * CAST(s.t_tick - a.t0 AS DOUBLE) + CAST(a.p0 AS DOUBLE), 0) AS BIGINT)
  END AS t_tick,
  coalesce(s.clock_id = {target} OR CAST(
    CASE WHEN a.t0 IS NULL THEN m.first_t - s.t_tick
         WHEN a.t1 IS NULL THEN s.t_tick - a.t0
         ELSE least(s.t_tick - a.t0, a.t1 - s.t_tick) END AS DOUBLE) <= m.span, false) AS placed
FROM ({spikes}) s
ASOF LEFT JOIN anchors a ON s.clock_id = a.clock_id AND s.t_tick >= a.t0
LEFT JOIN params m ON s.clock_id = m.clock_id
"""


#: The anchors and each clock's parameters fitted in SQL from `core.clock_anchors` alone.
SQL_PARAMETERS = """
CREATE TEMP TABLE anchors AS
SELECT clock_id, t_tick AS t0, parent_tick AS p0,
       lead(t_tick) OVER w AS t1, lead(parent_tick) OVER w AS p1
FROM read_parquet('{path}') WHERE parent_tick IS NOT NULL
WINDOW w AS (PARTITION BY clock_id ORDER BY t_tick);
CREATE TEMP TABLE params AS
WITH c AS (SELECT clock_id, avg(t0) AS ct, avg(p0) AS cp FROM anchors GROUP BY clock_id)
SELECT a.clock_id, min(t0) AS first_t, arg_min(p0, t0) AS first_p, max(t0) AS last_t, arg_max(p0, t0) AS last_p,
       sum((t0 - ct) * (p0 - cp)) / sum((t0 - ct) * (t0 - ct)) AS slope,
       quantile_cont(t1 - t0, 0.5) * {bound} AS span
FROM anchors a JOIN c USING (clock_id) GROUP BY a.clock_id;
"""


def duck_setup(plan: dict, packet, sql_parameters: bool = False, default: bool = False):
    con = duck(plan, default)
    con.register("units_arrow", unit_clocks(packet))
    con.execute("CREATE TEMP TABLE units AS SELECT * FROM units_arrow")
    if sql_parameters:
        con.execute(SQL_PARAMETERS.format(path=uri(packet, "core.clock_anchors"), bound=plan["bound"]))
    else:
        anchors, params = edge_tables(packet, plan["clock"], plan["bound"])
        con.register("anchors", anchors)
        con.register("params", params)
    return con


def scan_filters(plan_text: str) -> list[str]:
    """The lines under each Parquet scan of an EXPLAIN that state a pushed filter."""
    found, inside = [], False
    for line in plan_text.splitlines():
        if "READ_PARQUET" in line or "PARQUET_SCAN" in line or "TABLE_SCAN" in line:
            inside = True
        elif inside and ("Filters" in line or "t_tick" in line or "File Filters" in line):
            found.append(" ".join(line.replace("│", " ").split()))
        elif inside and "└" in line:
            inside = False
    return found


# -- Polars ----------------------------------------------------------------------------------


def polars_spikes(packet, with_row: bool = True):
    import polars as pl

    path = uri(packet, "core.spike_events")
    options = None
    if benchkit.is_remote(path) and anonymous():
        options = {"skip_signature": "true", "aws_region": os.environ.get("AWS_REGION", "us-west-2")}
    spikes = pl.scan_parquet(path, row_index_name="row" if with_row else None, storage_options=options)
    units = pl.from_arrow(unit_clocks(packet)).lazy()
    columns = ["row", "unit_id", "t_tick"] if with_row else ["unit_id", "t_tick"]
    return spikes.select(columns).join(units, on="unit_id", how="left")


def polars_formula(frame, target: int):
    """Add `mapped` and `placed` to a frame carrying t_tick, clock_id, t0..p1 and the parameters."""
    import polars as pl

    f64, i64 = pl.Float64, pl.Int64
    t, t0, t1, p0, p1 = (pl.col(c) for c in ("t_tick", "t0", "t1", "p0", "p1"))

    def rint(x):
        return x.round(0, mode="half_to_even").cast(i64)

    interior = rint((p1 - p0).cast(f64) / (t1 - t0).cast(f64) * (t - t0).cast(f64) + p0.cast(f64))
    before = pl.col("first_p") + rint(pl.col("slope") * (t - pl.col("first_t")).cast(f64))
    after = pl.col("last_p") + rint(pl.col("slope") * (t - pl.col("last_t")).cast(f64))
    on_target = pl.col("clock_id") == target
    mapped = (
        pl.when(on_target)
        .then(t)
        .when(t0.is_null())
        .then(before)
        .when(t > pl.col("last_t"))
        .then(after)
        .when(t == t0)
        .then(p0)
        .otherwise(interior)
    )
    distance = (
        pl.when(t0.is_null())
        .then(pl.col("first_t") - t)
        .when(t1.is_null())
        .then(t - t0)
        .otherwise(pl.min_horizontal(t - t0, t1 - t))
    )
    placed = (on_target | (distance.cast(f64) <= pl.col("span"))).fill_null(False)
    return frame.with_columns(mapped=mapped, placed=placed)


def polars_asof(packet, plan: dict, spikes=None):
    """The mapping through `join_asof`, which needs the spikes sorted by tick first."""
    import polars as pl

    anchors, params = edge_tables(packet, plan["clock"], plan["bound"])
    spikes = polars_spikes(packet) if spikes is None else spikes
    joined = (
        spikes.sort("t_tick")
        .join_asof(pl.from_arrow(anchors).lazy().sort("t0"), left_on="t_tick", right_on="t0", by="clock_id")
        .join(pl.from_arrow(params).lazy(), on="clock_id", how="left")
    )
    return polars_formula(joined, plan["clock"])


def polars_search(packet, plan: dict, spikes=None):
    """The mapping as a search of one sorted (clock, tick) key per spike, which needs no sort."""
    import numpy as np
    import polars as pl

    anchors, params = edge_tables(packet, plan["clock"], plan["bound"])
    a = pl.from_arrow(anchors)
    keys = pl.Series((a["clock_id"].cast(pl.Int64) * STRIDE + a["t0"]).to_numpy())
    assert bool(np.all(np.diff(keys.to_numpy()) > 0))
    spikes = polars_spikes(packet) if spikes is None else spikes
    # The search returns an unsigned index, so it is widened before the subtraction can go below zero.
    at = pl.lit(keys).search_sorted(pl.col("clock_id").cast(pl.Int64) * STRIDE + pl.col("t_tick"), side="right")
    found = spikes.with_columns(_j=at.cast(pl.Int64) - 1)
    j = pl.col("_j").clip(0)
    same = (pl.col("_j") >= 0) & (pl.lit(a["clock_id"]).gather(j) == pl.col("clock_id"))
    found = found.with_columns(
        **{name: pl.when(same).then(pl.lit(a[name]).gather(j)) for name in ("t0", "p0", "t1", "p1")}
    ).join(pl.from_arrow(params).lazy(), on="clock_id", how="left")
    return polars_formula(found, plan["clock"])


# -- Narwhals --------------------------------------------------------------------------------


def narwhals_mapping(spikes, anchors, params, target: int):
    """The mapping through Narwhals' expression API over any backend it wraps.

    Narwhals' `round` takes no mode and rounds as its backend does, so `rint` is a floor and an
    exact tie test, which hold for |x| < 2**52.
    """
    import narwhals as nw

    f64, i64 = nw.Float64, nw.Int64
    t, t0, t1, p0, p1 = (nw.col(c) for c in ("t_tick", "t0", "t1", "p0", "p1"))

    def rint(x):
        f = x.floor()
        d = x - f
        up = (d > 0.5) | ((d == 0.5) & ((f % 2) != 0))
        return (f + nw.when(up).then(nw.lit(1.0)).otherwise(nw.lit(0.0))).cast(i64)

    # Joined on a copy of t0: Narwhals keeps the right key on Polars and drops it on DuckDB.
    anchors = anchors.with_columns(key=nw.col("t0"))
    joined = spikes.join_asof(anchors, left_on="t_tick", right_on="key", by="clock_id").join(
        params, on="clock_id", how="left"
    )
    interior = rint((p1 - p0).cast(f64) / (t1 - t0).cast(f64) * (t - t0).cast(f64) + p0.cast(f64))
    before = nw.col("first_p") + rint(nw.col("slope") * (t - nw.col("first_t")).cast(f64))
    after = nw.col("last_p") + rint(nw.col("slope") * (t - nw.col("last_t")).cast(f64))
    mapped = (
        nw.when(nw.col("clock_id") == target)
        .then(t)
        .otherwise(
            nw.when(t0.is_null())
            .then(before)
            .otherwise(
                nw.when(t > nw.col("last_t")).then(after).otherwise(nw.when(t == t0).then(p0).otherwise(interior))
            )
        )
    )
    distance = (
        nw.when(t0.is_null())
        .then(nw.col("first_t") - t)
        .otherwise(nw.when(t1.is_null()).then(t - t0).otherwise(nw.min_horizontal(t - t0, t1 - t)))
    )
    placed = ((nw.col("clock_id") == target) | (distance.cast(f64) <= nw.col("span"))).fill_null(False)
    return joined.with_columns(mapped=mapped, placed=placed).select("row", "unit_id", "mapped", "placed")


# -- arms ------------------------------------------------------------------------------------


def dump_rows(rows, mapped, placed, n: int):
    """A full-length array in stored row order, `UNPLACED` where the mapping is undefined."""
    import numpy as np

    out = np.full(n, UNPLACED, dtype=np.int64)
    rows, mapped, placed = (np.asarray(x) for x in (rows, mapped, placed))
    out[rows[placed]] = mapped[placed]
    return out


def mapped_value(out, t_zero: int) -> dict:

    placed = out != UNPLACED
    return {
        "rows": int(out.size),
        "placed": int(placed.sum()),
        "sum_from_zero": int((out[placed] - t_zero).sum()),
    }


def arm_map_kernel(plan: dict):
    """The reader's kernel over the whole stored column: the reference every other arm meets."""
    import numpy as np
    import pyarrow as pa
    from escapewheel_reader import clocks

    packet = open_packet(plan)
    stored = packet.table("core.spike_events", columns=["unit_id", "t_tick"])
    with_clock = clocks.attach_clocks(packet, stored, "core.spike_events")
    batch = pa.record_batch(
        {
            "t_tick": with_clock.column("t_tick").combine_chunks(),
            "clock_id": with_clock.column("clock_id").combine_chunks(),
        }
    )
    ticks, keep = clocks.mapped(batch, plan["clock"], clocks.clock_graph(packet), plan["bound"])
    out = np.where(keep, ticks, UNPLACED)
    return mapped_value(out, plan["t_zero"]), out


def arm_map_diagnose(plan: dict):
    """Where the spikes fall against the anchors, and how many interpolations land on a half tick."""
    import numpy as np
    from escapewheel_reader import clocks

    packet = open_packet(plan)
    stored = clocks.attach_clocks(
        packet, packet.table("core.spike_events", columns=["unit_id", "t_tick"]), "core.spike_events"
    )
    ticks = stored.column("t_tick").to_numpy()
    clock = stored.column("clock_id").to_numpy()
    graph = clocks.clock_graph(packet)
    out = {"before_first": 0, "after_last": 0, "interior_ties": 0, "end_ties": 0, "unplaced_inside": 0, "unplaced": 0}
    for name, (t, p) in graph.anchors.items():
        mine = ticks[clock == name]
        slope, _ = clocks.rate(t, p)
        early, late = mine < t[0], mine > t[-1]
        inside = ~(early | late)
        out["before_first"] += int(early.sum())
        out["after_last"] += int(late.sum())
        raw = np.interp(mine[inside], t, p)
        out["interior_ties"] += int((raw - np.floor(raw) == 0.5).sum())
        ends = np.concatenate([slope * (mine[early] - t[0]), slope * (mine[late] - t[-1])])
        out["end_ties"] += int((ends - np.floor(ends) == 0.5).sum())
        _, placed = clocks.align(mine, t, p, bound=plan["bound"])
        out["unplaced"] += int((~placed).sum())
        out["unplaced_inside"] += int((~placed & inside).sum())
    return out, None


def arm_map_reader(plan: dict):
    """`spike_times` for every unit, the public eager path; placed rows only, in stored order.

    At a bound other than the packet's, the stored ticks through `on_clock`, which takes one.
    """
    import numpy as np
    from escapewheel_reader import STORED, on_clock, spike_times

    packet = open_packet(plan)
    units = packet.table("core.units", columns=["unit_id"])
    if plan["bound"] == plan["declared_bound"]:
        found = spike_times(packet, units=units)
    else:
        found = on_clock(packet, spike_times(packet, units=units, clock=STORED), plan["clock"], bound=plan["bound"])
    ticks = found.column("t_tick").to_numpy()
    value = {"rows": found.num_rows, "placed": found.num_rows, "sum_from_zero": int((ticks - plan["t_zero"]).sum())}
    return value, np.asarray(ticks, dtype=np.int64)


def arm_map_duckdb(plan: dict, sql_parameters: bool = False, aggregate: bool = False, rounding: str = "round_even"):
    packet = open_packet(plan)
    con = duck_setup(plan, packet, sql_parameters)
    query = duck_mapping(duck_spikes(packet), plan["clock"], rounding)
    if aggregate:
        row = con.sql(
            f"SELECT count(*), count(*) FILTER (placed), sum(t_tick - {plan['t_zero']}) FILTER (placed) FROM ({query})"
        ).fetchone()
        return {"rows": row[0], "placed": row[1], "sum_from_zero": int(row[2])}, None
    found = con.sql(query).to_arrow_table()
    out = dump_rows(found["row"], found["t_tick"].fill_null(0), found["placed"], plan["rows"])
    return mapped_value(out, plan["t_zero"]), out


def arm_map_polars(plan: dict, how: str, aggregate: bool = False):
    import polars as pl

    packet = open_packet(plan)
    frame = (polars_asof if how == "asof" else polars_search)(packet, plan)
    if aggregate:
        found = frame.select(
            rows=pl.len(),
            placed=pl.col("placed").sum(),
            total=(pl.col("mapped") - plan["t_zero"]).filter(pl.col("placed")).sum(),
        ).collect(engine="streaming")
        return {"rows": found["rows"][0], "placed": found["placed"][0], "sum_from_zero": int(found["total"][0])}, None
    found = frame.select("row", "mapped", "placed").collect(engine="streaming")
    out = dump_rows(
        found["row"].to_numpy(), found["mapped"].fill_null(0).to_numpy(), found["placed"].to_numpy(), plan["rows"]
    )
    return mapped_value(out, plan["t_zero"]), out


def arm_map_narwhals(plan: dict, backend: str):
    import narwhals as nw
    import polars as pl

    packet = open_packet(plan)
    anchors, params = edge_tables(packet, plan["clock"], plan["bound"])
    if backend == "duckdb":
        # Narwhals' DuckDB join runs on the default connection, which a relation from any other refuses.
        con = duck_setup(plan, packet, default=True)
        spikes = nw.from_native(con.sql(duck_spikes(packet)))
        a, m = nw.from_native(con.sql("SELECT * FROM anchors")), nw.from_native(con.sql("SELECT * FROM params"))
    else:
        # Polars' join_asof wants the left side sorted by its key.
        spikes = nw.from_native(polars_spikes(packet).sort("t_tick"))
        a, m = nw.from_native(pl.from_arrow(anchors).lazy().sort("t0")), nw.from_native(pl.from_arrow(params).lazy())
    frame = narwhals_mapping(spikes, a, m, plan["clock"]).to_native()
    found = frame.to_arrow_table() if backend == "duckdb" else frame.collect(engine="streaming").to_arrow()
    out = dump_rows(
        found["row"].to_numpy(),
        found["mapped"].fill_null(0).to_numpy(),
        found["placed"].to_numpy(zero_copy_only=False),
        plan["rows"],
    )
    return mapped_value(out, plan["t_zero"]), out


# go-cue analysis


def arm_cue_eager(plan: dict):
    """`spike_times` into a `pa.Table`, then the window analysis in Polars."""
    import polars as pl
    from escapewheel_reader import spike_times
    from trials import polars_windows

    packet = open_packet(plan)
    go = cues(packet, plan)
    table = spike_times(packet, units=packet.table("core.units", columns=["unit_id"]))
    spikes = pl.from_arrow(table.select(["unit_id", "t_tick"])).lazy().select(unit="unit_id", t="t_tick")
    found = polars_windows(spikes, pl.Series(go), BEFORE * plan["rate"], AFTER * plan["rate"])
    return summary(found["pairs"], found["offset"]), None


CUE_DUCK = """
SELECT s.unit_id, count(*) AS pairs, sum(s.t_tick - c.g) AS offset
FROM (SELECT unit_id, t_tick FROM ({mapping}) WHERE placed) s
ASOF JOIN cues c ON s.t_tick + {before} >= c.g
WHERE s.t_tick <= c.g + {after}
GROUP BY s.unit_id
"""


def arm_cue_duckdb(plan: dict):
    """The lazy SQL mapping with the cue window joined after it, cues far enough apart for ASOF."""
    import numpy as np
    import pyarrow as pa

    packet = open_packet(plan)
    go = cues(packet, plan)
    assert np.diff(go).min() > (BEFORE + AFTER) * plan["rate"]
    con = duck_setup(plan, packet)
    con.register("cues", pa.table({"g": go}))
    query = CUE_DUCK.format(
        mapping=duck_mapping(duck_spikes(packet), plan["clock"]),
        before=BEFORE * plan["rate"],
        after=AFTER * plan["rate"],
    )
    found = con.sql(query).to_arrow_table()
    explained = con.sql("EXPLAIN " + query).fetchall()[0][1]
    return {**summary(found["pairs"].to_numpy(), found["offset"].to_numpy()), "scan": scan_filters(explained)}, None


def arm_cue_polars(plan: dict):
    """The lazy Polars mapping (search form, no sort) with `trials.py`'s streaming window plan after it."""
    import polars as pl
    from trials import polars_windows

    packet = open_packet(plan)
    go = cues(packet, plan)
    mapping = polars_search(packet, plan, polars_spikes(packet, with_row=False))
    spikes = mapping.filter(pl.col("placed")).select(unit="unit_id", t="mapped")
    found = polars_windows(spikes, pl.Series(go), BEFORE * plan["rate"], AFTER * plan["rate"])
    return summary(found["pairs"], found["offset"]), None


def arm_cue_stream(plan: dict):
    """A `RecordBatchReader` from `Packet.scanner`, each batch through `clocks.mapped`, summed per unit."""
    import numpy as np
    import pyarrow as pa
    from escapewheel_reader import clocks
    from trials import window_sums

    packet = open_packet(plan)
    go = cues(packet, plan)
    units = unit_clocks(packet)
    unit_ids = units["unit_id"].to_numpy()
    clock_of = np.full(int(unit_ids.max()) + 1, -1, dtype=np.int64)
    clock_of[unit_ids] = units["clock_id"].to_numpy()
    graph, bound = clocks.clock_graph(packet), plan["bound"]
    pairs = np.zeros(clock_of.size, dtype=np.int64)
    offsets = np.zeros(clock_of.size, dtype=np.int64)
    before, after = BEFORE * plan["rate"], AFTER * plan["rate"]
    reader = packet.scanner("core.spike_events", columns=["unit_id", "t_tick"]).to_reader()
    for batch in reader:
        unit = batch.column("unit_id").to_numpy()
        ticks = batch.column("t_tick")
        batch = pa.record_batch({"t_tick": ticks, "clock_id": pa.array(clock_of[unit])})
        mapped, keep = clocks.mapped(batch, plan["clock"], graph, bound)
        counts, offset = window_sums(go, mapped[keep], before, after)
        pairs += np.bincount(unit[keep], weights=counts, minlength=pairs.size).astype(np.int64)
        offsets += np.bincount(unit[keep], weights=offset, minlength=offsets.size).astype(np.int64)
    return summary(pairs, offsets), None


# 60 s on the reference clock


def arm_slice_reader(plan: dict):
    from escapewheel_reader import spike_times

    packet = open_packet(plan)
    found = spike_times(packet, units=packet.table("core.units", columns=["unit_id"]), t_tick=tuple(plan["slice"]))
    ticks = found.column("t_tick").to_numpy()
    return {"rows": found.num_rows, "sum_from_lo": int((ticks - plan["slice"][0]).sum())}, None


def arm_slice_duckdb(plan: dict, widened: bool = False):
    packet = open_packet(plan)
    con = duck_setup(plan, packet)
    lo, hi = plan["slice"]
    spikes = duck_spikes(packet, tuple(plan["stored_slice"]) if widened else None)
    query = (
        f"SELECT count(*), sum(t_tick - {lo}) FROM ({duck_mapping(spikes, plan['clock'])}) "
        f"WHERE placed AND t_tick BETWEEN {lo} AND {hi}"
    )
    row = con.sql(query).fetchone()
    explained = con.sql("EXPLAIN " + query).fetchall()[0][1]
    return {"rows": row[0], "sum_from_lo": int(row[1] or 0), "scan": scan_filters(explained)}, None


def arm_slice_polars(plan: dict):
    import polars as pl

    packet = open_packet(plan)
    lo, hi = plan["slice"]
    frame = (
        polars_search(packet, plan, polars_spikes(packet, with_row=False))
        .filter(pl.col("placed") & pl.col("mapped").is_between(lo, hi))
        .select(rows=pl.len(), total=(pl.col("mapped") - lo).sum())
    )
    plan_text = frame.explain()
    found = frame.collect(engine="streaming")
    lines = [line.strip() for line in plan_text.splitlines()]
    at = next(i for i, line in enumerate(lines) if "SCAN" in line and "spike_events" in line)
    scan = lines[at : at + 4]
    return {"rows": found["rows"][0], "sum_from_lo": int(found["total"][0] or 0), "scan": scan}, None


def arm_slice_analysis(plan: dict):
    """`analysis.spike_events`, already on the reference clock, read by range."""
    packet = open_packet(plan)
    found = packet.table("analysis.spike_events", columns=["t_tick"], t_tick=tuple(plan["slice"]))
    ticks = found.column("t_tick").to_numpy()
    return {"rows": found.num_rows, "sum_from_lo": int((ticks - plan["slice"][0]).sum())}, None


#: Each arm: its runner and the modules imported before its clock starts.
ARMS = {
    "map kernel": (arm_map_kernel, ("escapewheel_reader", "numpy")),
    "map diagnose": (arm_map_diagnose, ("escapewheel_reader", "numpy")),
    "map reader": (arm_map_reader, ("escapewheel_reader", "numpy")),
    "map duckdb": (arm_map_duckdb, ("escapewheel_reader", "duckdb")),
    "map duckdb, sql parameters": (lambda p: arm_map_duckdb(p, sql_parameters=True), ("escapewheel_reader", "duckdb")),
    "map duckdb, round": (lambda p: arm_map_duckdb(p, rounding="round"), ("escapewheel_reader", "duckdb")),
    "map duckdb, aggregate": (lambda p: arm_map_duckdb(p, aggregate=True), ("escapewheel_reader", "duckdb")),
    "map polars asof": (lambda p: arm_map_polars(p, "asof"), ("escapewheel_reader", "polars")),
    "map polars search": (lambda p: arm_map_polars(p, "search"), ("escapewheel_reader", "polars")),
    "map polars search, aggregate": (
        lambda p: arm_map_polars(p, "search", aggregate=True),
        ("escapewheel_reader", "polars"),
    ),
    "map narwhals duckdb": (lambda p: arm_map_narwhals(p, "duckdb"), ("escapewheel_reader", "narwhals", "duckdb")),
    "map narwhals polars": (lambda p: arm_map_narwhals(p, "polars"), ("escapewheel_reader", "narwhals", "polars")),
    "cue eager": (arm_cue_eager, ("escapewheel_reader", "polars", "trials")),
    "cue duckdb": (arm_cue_duckdb, ("escapewheel_reader", "duckdb")),
    "cue polars": (arm_cue_polars, ("escapewheel_reader", "polars", "trials")),
    "cue stream": (arm_cue_stream, ("escapewheel_reader", "numpy", "trials")),
    "slice reader": (arm_slice_reader, ("escapewheel_reader",)),
    "slice duckdb": (arm_slice_duckdb, ("escapewheel_reader", "duckdb")),
    "slice duckdb, widened": (lambda p: arm_slice_duckdb(p, widened=True), ("escapewheel_reader", "duckdb")),
    "slice polars": (arm_slice_polars, ("escapewheel_reader", "polars")),
    "slice analysis": (arm_slice_analysis, ("escapewheel_reader",)),
}


def child(arm: str, plan: dict, warm: bool) -> None:
    """One cell: evict unless warm, time the arm, record peak RSS, then dump for the comparison."""
    import numpy as np

    warnings.filterwarnings("ignore")
    runner, modules = ARMS[arm]
    for module in modules:
        importlib.import_module(module)
    packet = plan["packet"]
    if not warm and not benchkit.is_remote(packet):
        root = Path(packet)
        benchkit.evict(root)
        if (left := benchkit.resident_fraction(root)) > benchkit.RESIDENT_LIMIT:
            sys.exit(f"{root} is still {left:.1%} resident after eviction")
    before = benchkit.received_bytes()
    clock = time.perf_counter()
    value, out = runner(plan)
    elapsed = time.perf_counter() - clock
    peak = benchkit.peak_mib()
    after = benchkit.received_bytes()
    dump = None
    if out is not None and plan.get("dump"):
        dump = str(Path(plan["scratch"], "dumps", arm.replace(" ", "_").replace(",", "") + ".npy"))
        Path(dump).parent.mkdir(parents=True, exist_ok=True)
        np.save(dump, out)
    received = after - before if before is not None and after is not None else None
    print(
        json.dumps(
            {"seconds": elapsed, "peak_mib": peak, "received_bytes": received, "value": value, "dump": dump},
            default=str,
        )
    )


def compare(reference: str, other: str, placed_only: bool) -> dict:
    """Rows on which a dump differs from the kernel's, by kind."""
    import numpy as np

    ref = np.load(reference, mmap_mode="r")
    got = np.load(other, mmap_mode="r")
    if placed_only:
        kept = ref[ref != UNPLACED]
        if kept.size != got.size:
            return {"rows": int(got.size), "reference_rows": int(kept.size), "mismatched": None}
        bad = int(np.count_nonzero(kept != got))
        return {"rows": int(got.size), "mismatched": bad}
    out = {"placement": 0, "value": 0, "max_abs": 0}
    step = 1 << 25
    for lo in range(0, ref.size, step):
        r, g = np.asarray(ref[lo : lo + step]), np.asarray(got[lo : lo + step])
        placement = (r == UNPLACED) != (g == UNPLACED)
        both = (r != UNPLACED) & (g != UNPLACED)
        value = both & (r != g)
        out["placement"] += int(placement.sum())
        out["value"] += int(value.sum())
        if value.any():
            out["max_abs"] = max(out["max_abs"], int(np.abs(r[value] - g[value]).max()))
    return out


def make_plan(packet_path: str, scratch: str, args) -> dict:
    """Every value a child would otherwise read before its clock starts."""
    import pyarrow.parquet as pq
    from escapewheel_reader import clocks
    from escapewheel_reader import open_packet as opened

    packet = opened(packet_path)
    target = clocks.reference_clock(packet)
    t_zero, num, den = clocks.origin(packet)
    if num % den:
        sys.exit("the reference clock's rate is not a whole number of ticks per second")
    rate = num // den
    trials = [r.resource_id for r in packet.manifest.resources if r.resource_id.endswith(".trials")]
    lo = t_zero + args.slice_start * rate
    span = (lo, lo + 60 * rate - 1)
    stored = clocks.stored_span(clocks.clock_graph(packet), target, span)
    plan = {
        "packet": packet_path,
        "scratch": scratch,
        "clock": target,
        "rate": rate,
        "t_zero": t_zero,
        "bound": clocks.declared_bound(packet) if args.bound is None else args.bound,
        "declared_bound": clocks.declared_bound(packet),
        "trials": trials[0],
        "slice": list(span),
        "stored_slice": list(stored),
        "region_aws": os.environ.get("AWS_REGION", "us-west-2"),
        "anonymous": anonymous(),
        "duckdb_memory": args.duckdb_memory,
        "dump": not args.no_dump,
    }
    resource = packet.table_resource("core.spike_events")
    if resource.is_local:
        metadata = pq.ParquetFile(resource.path).metadata
        plan["rows"] = metadata.num_rows
        stats = [metadata.row_group(i).column(2).statistics for i in range(metadata.num_row_groups)]
        plan["row_groups"] = metadata.num_row_groups
        plan["row_groups_overlapping_stored_slice"] = sum(s.min <= stored[1] and s.max >= stored[0] for s in stats)
    else:
        path, filesystem = resource.location.store()
        plan["rows"] = pq.ParquetFile(path, filesystem=filesystem).metadata.num_rows
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--packet", help="packet directory or s3:// URI (else BENCH_PACKET)")
    parser.add_argument("--scratch", type=Path, help="directory for dumps and DuckDB's spill (else BENCH_SCRATCH)")
    parser.add_argument("--arms", nargs="+", default=list(ARMS), choices=ARMS)
    parser.add_argument("--warm", action="store_true", help="also run each cell again without eviction")
    parser.add_argument("--memory-max", default="60G", help="kill a cell above this size, in systemd's form")
    parser.add_argument("--duckdb-memory", default="40GB", help="DuckDB's memory_limit, below --memory-max")
    parser.add_argument("--slice-start", type=int, default=1800, help="seconds after the origin the 60 s slice starts")
    parser.add_argument("--bound", type=float, help="map at this bound rather than the packet's declared one")
    parser.add_argument("--no-dump", action="store_true", help="skip the row-by-row comparison")
    parser.add_argument("--json-out", type=Path, help="write the result here as JSON")
    parser.add_argument("--child", help=argparse.SUPPRESS)
    parser.add_argument("--child-warm", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--plan", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child(args.child, json.loads(args.plan), args.child_warm)

    packet = benchkit.required_store(args.packet, "BENCH_PACKET", "the packet")
    scratch = str(
        benchkit.required_path(str(args.scratch) if args.scratch else None, "BENCH_SCRATCH", "the scratch directory")
    )
    plan = make_plan(packet, scratch, args)
    result = {
        "environment": benchkit.environment([packet]),
        "plan": plan,
        "core_version": benchkit.core_version(packet),
        "memory_max": args.memory_max,
        "cells": [],
    }
    print(f"packet {packet} (core {result['core_version']}), {plan['rows']:,} spikes\n")
    for arm in args.arms:
        for warm in (False, True) if args.warm else (False,):
            command = [__file__, "--child", arm, "--plan", json.dumps(plan)] + (["--child-warm"] if warm else [])
            cell = benchkit.run_child(command, args.memory_max)
            cell = {"arm": arm, "warm": warm, "load_average": [round(x, 2) for x in os.getloadavg()], **cell}
            result["cells"].append(cell)
            shown = (
                "failed: " + cell["error"] if "error" in cell else f"{cell['seconds']:8.2f}s {cell['peak_mib']:8.0f}MiB"
            )
            print(f"{arm:32s} {'warm' if warm else 'cold':5s} {shown}  {cell.get('value')}", flush=True)
    reference = next((c["dump"] for c in result["cells"] if c["arm"] == "map kernel" and c.get("dump")), None)
    if reference:
        print("\nagainst the kernel, row by row:")
        for cell in result["cells"]:
            if cell.get("dump") and cell["arm"] != "map kernel" and not cell["warm"]:
                cell["mismatch"] = compare(reference, cell["dump"], placed_only=cell["arm"] == "map reader")
                print(f"  {cell['arm']:32s} {cell['mismatch']}")
    benchkit.write_result(args.json_out, result)


if __name__ == "__main__":
    main()
