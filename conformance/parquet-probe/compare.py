import os

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

rng = np.random.default_rng(0)
NU, RATE, DUR = 500, 30000, 3600
units, ticks = [], []
for u in range(NU):
    n = rng.poisson(5 * DUR)
    units.append(f"unit_{u:04d}")
    ticks.append(np.sort(rng.integers(0, RATE * DUR, n)))
total = sum(len(t) for t in ticks)
print(f"{NU} units, {total:,} spikes, {DUR / 3600:.0f} h @ {RATE // 1000} kHz\n")


def const(v, n):
    return pa.array(np.full(n, v))


# --- flat: core.spike_events (all required columns per 02) ---
u_flat = np.concatenate([np.full(len(t), un) for un, t in zip(units, ticks)])
t_flat = np.concatenate(ticks)
flat = pa.table(
    {
        "session_id": const("s001", total),
        "unit_id": pa.array(u_flat),
        "sorting_run_id": const("sort_001", total),
        "curation_id": const("cur_001", total),
        "t_tick": pa.array(t_flat, type=pa.int64()),
        "clock_id": const("imec_s001", total),
    }
)
pq.write_table(
    flat,
    "cmp_flat.parquet",
    compression="zstd",
    use_dictionary=[
        "session_id",
        "unit_id",
        "sorting_run_id",
        "curation_id",
        "clock_id",
    ],
    column_encoding={"t_tick": "DELTA_BINARY_PACKED"},
)


# --- chunked: core.unit_spike_chunks, at two chunk sizes ---
def build_chunks(N):
    su, ci, tmin, tmax, ns, st = [], [], [], [], [], []
    for un, t in zip(units, ticks):
        for i in range(0, len(t), N):
            c = t[i : i + N]
            su.append(un)
            ci.append(i // N)
            tmin.append(int(c[0]))
            tmax.append(int(c[-1]))
            ns.append(len(c))
            st.append(c.tolist())
    n = len(su)
    return n, pa.table(
        {
            "session_id": const("s001", n),
            "unit_id": pa.array(su),
            "sorting_run_id": const("sort_001", n),
            "curation_id": const("cur_001", n),
            "chunk_index": pa.array(ci, type=pa.int64()),
            "t_min_tick": pa.array(tmin, type=pa.int64()),
            "t_max_tick": pa.array(tmax, type=pa.int64()),
            "clock_id": const("imec_s001", n),
            "n_spikes": pa.array(ns, type=pa.int64()),
            "spike_ticks": pa.array(st, type=pa.list_(pa.int64())),
        }
    )


sizes = {"flat (spike_events)": ("cmp_flat.parquet", total)}
for N in (1000, 10000):
    nrows, tbl = build_chunks(N)
    f = f"cmp_chunk{N}.parquet"
    pq.write_table(
        tbl,
        f,
        compression="zstd",
        use_dictionary=[
            "session_id",
            "unit_id",
            "sorting_run_id",
            "curation_id",
            "clock_id",
        ],
    )
    sizes[f"chunked, {N} spikes/chunk"] = (f, nrows)

print(f"{'representation':30s} {'rows':>10s} {'size':>9s}  {'bytes/spike':>11s}")
for k, (f, n) in sizes.items():
    b = os.path.getsize(f)
    print(f"{k:30s} {n:>10,} {b / 1e6:>7.2f}MB {b / total:>11.2f}")
