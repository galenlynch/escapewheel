import numpy as np, pyarrow as pa, pyarrow.parquet as pq, os
print("pyarrow", pa.__version__)
rng = np.random.default_rng(0)
unit, tick = [], []
for u in range(500):
    n = rng.poisson(5*3600)
    unit.append(np.full(n, f"unit_{u:04d}")); tick.append(np.sort(rng.integers(0, 30000*3600, n)))
tbl = pa.table({"unit_id": pa.array(np.concatenate(unit)),
                "t_tick":  pa.array(np.concatenate(tick), type=pa.int64())})
print(f"{tbl.num_rows:,} rows\n")

cfgs = {
  "default (dict on)":      dict(),
  "dict off":               dict(use_dictionary=False),
  "DELTA_BINARY_PACKED":    dict(use_dictionary=False, column_encoding={"t_tick":"DELTA_BINARY_PACKED"}),
  "DELTA + BYTE_STREAM_SPLIT unit": dict(use_dictionary=["unit_id"], column_encoding={"t_tick":"DELTA_BINARY_PACKED"}),
}
for name, kw in cfgs.items():
    f = f"d_{abs(hash(name))}.parquet"
    try:
        pq.write_table(tbl, f, compression="zstd", **kw)
        enc = pq.ParquetFile(f).metadata.row_group(0).column(1).encodings
        tickmb = pq.ParquetFile(f).metadata.row_group(0).column(1).total_compressed_size/1e6
        print(f"{name:34s} total {os.path.getsize(f)/1e6:6.2f} MB   t_tick {tickmb:5.2f} MB   enc={enc}")
    except Exception as e:
        print(f"{name:34s} FAILED {type(e).__name__}: {e}")
