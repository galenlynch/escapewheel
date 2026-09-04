import numpy as np, pyarrow as pa, pyarrow.parquet as pq, os, time, duckdb
rng = np.random.default_rng(0)
NU, RATE, DUR = 500, 30000, 3600
units = [f"unit_{u:04d}" for u in range(NU)]
ticks = [np.sort(rng.integers(0, RATE*DUR, rng.poisson(5*DUR))) for _ in range(NU)]
tot = sum(len(t) for t in ticks)

u_flat = np.concatenate([np.full(len(t), un) for un, t in zip(units, ticks)])
t_flat = np.concatenate(ticks)
enc = {"t_tick": "DELTA_BINARY_PACKED"}; dic = ["unit_id"]

# flat sorted by (unit, t)  -- as 03 recommends
pq.write_table(pa.table({"unit_id": pa.array(u_flat), "t_tick": pa.array(t_flat, type=pa.int64())}),
               "a_by_unit.parquet", compression="zstd", use_dictionary=dic, column_encoding=enc)
# flat sorted by t
o = np.argsort(t_flat, kind="stable")
pq.write_table(pa.table({"unit_id": pa.array(u_flat[o]), "t_tick": pa.array(t_flat[o], type=pa.int64())}),
               "a_by_time.parquet", compression="zstd", use_dictionary=dic, column_encoding=enc)
# chunked
su,ci,tmn,tmx,ns,st = [],[],[],[],[],[]
for un,t in zip(units,ticks):
    for i in range(0,len(t),1000):
        c=t[i:i+1000]; su.append(un); ci.append(i//1000); tmn.append(int(c[0])); tmx.append(int(c[-1])); ns.append(len(c)); st.append(c.tolist())
pq.write_table(pa.table({"unit_id":pa.array(su),"chunk_index":pa.array(ci,type=pa.int64()),
    "t_min_tick":pa.array(tmn,type=pa.int64()),"t_max_tick":pa.array(tmx,type=pa.int64()),
    "n_spikes":pa.array(ns,type=pa.int64()),"spike_ticks":pa.array(st,type=pa.list_(pa.int64()))}),
    "a_chunk.parquet", compression="zstd", use_dictionary=dic,
    column_encoding={"spike_ticks.list.element":"DELTA_BINARY_PACKED"})
for f in ("a_by_unit","a_by_time","a_chunk"): print(f"{f:12s} {os.path.getsize(f+'.parquet')/1e6:5.2f} MB")
print()

con=duckdb.connect(); U1="'unit_0042'"; U10="','".join(units[40:50])
W="t_tick BETWEEN 30000000 AND 33000000"; WC="t_max_tick >= 30000000 AND t_min_tick <= 33000000"
Q={
 "retrieve 1 unit's train":   (f"SELECT t_tick FROM 'a_by_unit.parquet' WHERE unit_id={U1}",
                               f"SELECT t_tick FROM 'a_by_time.parquet' WHERE unit_id={U1}",
                               f"SELECT UNNEST(spike_ticks) FROM 'a_chunk.parquet' WHERE unit_id={U1}"),
 "retrieve 10 units' trains": (f"SELECT t_tick FROM 'a_by_unit.parquet' WHERE unit_id IN ('{U10}')",
                               f"SELECT t_tick FROM 'a_by_time.parquet' WHERE unit_id IN ('{U10}')",
                               f"SELECT UNNEST(spike_ticks) FROM 'a_chunk.parquet' WHERE unit_id IN ('{U10}')"),
 "100 s window, all units":   (f"SELECT t_tick FROM 'a_by_unit.parquet' WHERE {W}",
                               f"SELECT t_tick FROM 'a_by_time.parquet' WHERE {W}",
                               f"SELECT t FROM (SELECT UNNEST(spike_ticks) t FROM 'a_chunk.parquet' WHERE {WC}) WHERE t BETWEEN 30000000 AND 33000000"),
}
print(f"{'access pattern':28s} {'flat/unit':>10s} {'flat/time':>10s} {'chunked':>10s}")
for name,qs in Q.items():
    ts=[]
    for q in qs:
        con.sql(q).fetchall(); t0=time.perf_counter(); con.sql(q).fetchall(); ts.append((time.perf_counter()-t0)*1000)
    print(f"{name:28s} {ts[0]:>8.1f}ms {ts[1]:>8.1f}ms {ts[2]:>8.1f}ms")
