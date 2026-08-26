import numpy as np, pyarrow as pa, pyarrow.parquet as pq, os
rng = np.random.default_rng(0)
# 500 units, ~5 Hz, 1 h at 30 kHz -> sorted ticks per unit, then sorted as the spec recommends
rows = []
for u in range(500):
    n = rng.poisson(5 * 3600)
    t = np.sort(rng.integers(0, 30000 * 3600, size=n))
    rows.append((np.full(n, f"unit_{u:04d}"), t))
unit = np.concatenate([r[0] for r in rows])
tick = np.concatenate([r[1] for r in rows])
print(f"{len(tick):,} spikes; max tick {tick.max():,} (int32 max {2**31-1:,})")

for name, typ in (("int32", pa.int32()), ("int64", pa.int64())):
    tbl = pa.table({"unit_id": pa.array(unit), "t_tick": pa.array(tick, type=typ)})
    f = f"ticks_{name}.parquet"
    pq.write_table(tbl, f, compression="zstd", use_dictionary=["unit_id"])
    print(f"  t_tick as {name}: {os.path.getsize(f)/1e6:6.2f} MB")
