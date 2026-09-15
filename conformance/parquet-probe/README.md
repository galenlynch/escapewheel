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
| `layout.py` | which encoding each column of a committed packet got, and three shapes worth a look |
| `alternatives.py` | what every encoding Part 03 §5.5 permits would have cost each column of a committed packet |

```bash
uv run --with pyarrow --with numpy --with duckdb python access.py
uv run --with pyarrow python alternatives.py /mnt/Data/786867-packet/packet
```

One synthetic session: 500 units, ~9M spikes, 1 h at 30 kHz, uniform firing, DuckDB only.
Bursty real data and direct pyarrow access are untested. Last run: pyarrow 25.0.1.

`layout.py` and `alternatives.py` read a committed packet rather than a synthetic session, and run
after a rebuild.
