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

## Many resources cross one pipe, and Arrow frames them

An IPC stream carries **one schema** by construction, and the NWB adapter returns thirteen
resources. Streams concatenate: each ends with an end-of-stream marker, so a reader opens one,
reads to it, and opens the next on what is left — on a pipe as well as a buffer, since nothing
seeks. The resource identifier rides in the schema's own key-value metadata.

`probe.py` runs `emit.py` as a subprocess and reads **three resources with three different schemas
back off one non-seekable pipe**, in order and with the right row counts. Nothing is framed that
Arrow does not frame, and no length prefix or header is invented.

A pipe is also memory, so this route touches no disk. Where an adapter is not a child of the
build — another host, a scheduler — a port would be the shape, and Arrow Flight is its standard;
that is a protocol to add rather than a change to these two.

## Arrow Flight answers Stage 1 from its own vocabulary

Part 05 §4.1 has a build report, per source, what it offers per resource and how many rows, without
writing to the packet. `ListFlights` is that: a descriptor per resource with its schema and row
count, before any data moves, and `DoGet` then fetches one descriptor rather than everything.

A stream can be made to do both and the surface is ours: an invocation that reports rather than
emits, and a way to name which resources are wanted. Left unspecified, a stream adapter discovers
by extracting — which is what the NWB adapter's `offers()` costs in process today, computing every
record to count them — and emits everything it has for the build to discard.

**None of that saves the adapter the extraction, which is a separate question.** A footer answers
cheaply only after the file exists, and a `DoGet` per descriptor fetches selectively from an adapter
that may already have computed everything to list them. What saves the work is being told the wanted
set before starting, which a build knows from `owns` before any I/O (R63 §2.2) and can pass over any
protocol.

`flight.py` serves three resources over a **Unix socket** — `Location.for_grpc_unix`, so no port
and no network exposure — and a client lists them by descriptor and fetches each: **119 ms
including the server's process start**. Flight ships in the standard pyarrow wheel. What a build
supplies is the socket path, which it already passes in an argument list, so this protocol invents
nothing at all where `stream-v0.1` invents a metadata key.

The reason to keep the stream is the one R3 §2.1 has argued from the beginning: a raw IPC stream is
implementable wherever there is an Arrow binding, and Flight additionally needs gRPC bindings for
that language, which fewer Arrow implementations carry.
