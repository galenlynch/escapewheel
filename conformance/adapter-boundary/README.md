# What crosses between a build and an adapter

Two drafts propose that an adapter declare what a build supplies it, and that it deliver its rows
out of process. Both were written against the shape of the writer's code rather than against a run
of it, so `probe.py` constructs two adapters from values that survive a JSON round trip and reports
what comes back.

Run it with `uv run --project ../../escapewheel-writer python probe.py`.

## The NWB adapter's inputs cross, and its rows are unchanged

Everything a build passes it goes over in **271 bytes of JSON** — a root, the reference clock's
`core.clocks` row, an IANA zone string, and one recipe option — and the adapter returns **33 rows
across 13 resources, identical** to the ones it returns when constructed the way `session.py`
constructs it today, with a `Clock` object and a `ZoneInfo`.

That is the draft's closed list tested on the adapter that receives the most, and it holds. It
needs no store: `store=None` is already the default, and the adapter opens its own root.

## Two mappings do not survive

| passed | `json.dumps` |
|---|---|
| `units`, keyed by `(device_name, source_unit_id)` | refused — keys must be str, int, float, bool or None |
| `electrodes`, keyed by an electrode row index | accepted, and the keys **return as strings** |

The second is worse than the first. A refusal is a failure someone fixes; an integer key that
returns as `"0"` is a mapping the adapter looks up with the wrong type, and only where it crosses a
boundary. Both want a record form — a list of rows carrying the key as columns — rather than a
mapping, which is R3 §3.0's rule for a packet turned on what a build hands an adapter.

## A dense array has no route at all

`WaveformSource.staged_arrays()` returns `StagedArray`, whose fields are
`values, array_asset_id, chunks, shard, codecs, fill_value`. **Five of the six cross**; the sixth is
the measurement. Neither draft says how one gets across, and both say "records" throughout.

The three adapters handed an open store today — `nwb`, `waveforms`, `lfp` — are the three that read
big binary, and two of them stage arrays. The third does not: `LFPSource.external_arrays()` returns
**references rather than bytes**, which is R14's external-resource model and crosses a boundary
unchanged. That is the shape of an answer and it is already in the tree.
