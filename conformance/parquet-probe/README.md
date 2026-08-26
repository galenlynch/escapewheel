# Parquet spike-table probe

Produces the Parquet evidence cited in
[R3 §7.3](../../revisions/R3-cross-language-physical-floor.md).

| script | question |
|---|---|
| `ticks.py` | `int32` vs `int64` tick column size |
| `delta.py` | which encodings pyarrow chooses, and what delta buys |
| `compare.py` | flat `spike_events` vs chunked `unit_spike_chunks`, size |
| `compare2.py` | delta on a nested child path; query timings |
| `access.py` | retrieval patterns across three layouts |
| `lists.jl` | whether Parquet2.jl reads list columns (primitives control) |
| `lists-duckdb.jl` | same file via DuckDB.jl |

```bash
uv run --with pyarrow --with numpy --with duckdb python access.py
```

One synthetic session: 500 units, ~9M spikes, 1 h at 30 kHz, uniform firing, DuckDB only.
Bursty real data and direct pyarrow access are untested. Last run: pyarrow 25.0.1.
