import pyarrow.parquet as pq, pyarrow as pa, os, time, duckdb

# can the list child get DELTA_BINARY_PACKED?
tbl = pq.read_table("cmp_chunk1000.parquet")
for path in ("spike_ticks.list.element", "spike_ticks"):
    try:
        pq.write_table(tbl, "t.parquet", compression="zstd",
                       use_dictionary=["session_id","unit_id","sorting_run_id","curation_id","clock_id"],
                       column_encoding={path: "DELTA_BINARY_PACKED"})
        print(f"delta on '{path}': OK  -> {os.path.getsize('t.parquet')/1e6:.2f} MB")
    except Exception as e:
        print(f"delta on '{path}': {type(e).__name__}: {str(e)[:90]}")

print()
con = duckdb.connect()
Q = {
 "spikes per unit": {
   "flat":  "SELECT unit_id, COUNT(*) FROM 'cmp_flat.parquet' GROUP BY unit_id",
   "chunk": "SELECT unit_id, SUM(n_spikes) FROM 'cmp_chunk1000.parquet' GROUP BY unit_id"},
 "spikes in 100 s window": {
   "flat":  "SELECT COUNT(*) FROM 'cmp_flat.parquet' WHERE t_tick BETWEEN 30000000 AND 33000000",
   "chunk": """SELECT COUNT(*) FROM (SELECT UNNEST(spike_ticks) t FROM 'cmp_chunk1000.parquet'
               WHERE t_max_tick >= 30000000 AND t_min_tick <= 33000000) WHERE t BETWEEN 30000000 AND 33000000"""},
 "total spikes": {
   "flat":  "SELECT COUNT(*) FROM 'cmp_flat.parquet'",
   "chunk": "SELECT SUM(n_spikes) FROM 'cmp_chunk1000.parquet'"},
}
print(f"{'query':26s} {'flat':>10s} {'chunked':>10s}   result match")
for name, qs in Q.items():
    out = {}
    for k, q in qs.items():
        con.sql(q).fetchall()                       # warm
        t0 = time.perf_counter(); r = con.sql(q).fetchall(); out[k] = (time.perf_counter()-t0, r)
    same = sorted(str(x) for x in out['flat'][1]) == sorted(str(x) for x in out['chunk'][1])
    print(f"{name:26s} {out['flat'][0]*1000:>8.1f}ms {out['chunk'][0]*1000:>8.1f}ms   {same}")
