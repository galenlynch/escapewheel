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

## Arrow IPC is a family, so a delivery pins which member

The framing is fixed and three choices are not, and `ipc_floor.py` prices each.
`IpcWriteOptions` exposes `compression`, `metadata_version`, `emit_dictionary_deltas`,
`unify_dictionaries`, `allow_64bit` and `use_legacy_format`, so two adapters both writing "Arrow
IPC" can hand a build bytes it cannot read.

**Compression is a loss here.** 5,000,000 spike-shaped rows — an `int32` unit and an `int64` tick —
cross a real pipe in **32 ms** uncompressed at 60.0 MB, **109 ms** under LZ4 at 34.8 MB and **107
ms** under Zstd at 18.1 MB. Bytes that never leave memory pay 3.3x to be a third the size, and the
codec is a dependency an adapter author in another language may not have.

**The metadata version is already right.** `IpcWriteOptions().metadata_version` is `V5`, the default
since Arrow 1.0, so pinning it costs a conforming adapter nothing and stops `use_legacy_format=True`
emitting V4, which lays a union out differently.

**A dictionary column crosses, and the stream after it still opens.** A dictionary-encoded string
column puts a DictionaryBatch ahead of its record batch — 600 bytes for three values — and the next
resource's schema parses on the same handle. A *delta* dictionary is the least evenly implemented
part of the format, and an adapter gains nothing by sending one, since a delivery's types are the
build's to settle against the registry.

**Concatenation depends on both ends agreeing where a stream ended.** Two 376-byte streams leave the
handle at 376 and then at 752, which is what lets a second open find the second resource. Remove one
end-of-stream marker and the read fails loudly: `Header-type of flatbuffer-encoded Message is not
RecordBatch`.

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

## The interface, run end to end

`build_side.py` reads the NWB adapter's `NEEDS`, supplies exactly those, launches it out of process
and reads its rows over Flight. `serve_nwb.py` is the adapter side: it rebuilds `Clock` and
`ZoneInfo` from the values it was sent and receives no object of the writer's.

    a build supplies ['reference_clock', 'root', 'session_id', 'wanted', 'zone']
      as 389 bytes of JSON, naming 4 of the 18 resources this adapter produces
    Stage 1, before any rows move: {'core.sessions': 1, 'core.probes': 1,
                                    'core.electrodes': 2, 'core.clock_anchors': 0}
    fetched 4 resource(s), 4 rows, 194 ms including the adapter's process start
    rows identical to the same adapter in process: True
    ['core.clock_anchors'] is not in this session, and in process the adapter omits it;
    over the boundary it arrives at 0 rows

All three protocols now run the same adapter over all eighteen resources, and agree:

    a build supplies ['reference_clock', 'root', 'session_id', 'wanted', 'zone']
      as 721 bytes of JSON, naming all 18 resources this adapter produces

    flight-v0.1
      18 resources, 33 rows, 5 empty, complete=True, 243 ms
      identical to the adapter in process: True
    files-v0.1
      18 resources, 33 rows, 5 empty, complete=True, 351 ms
      identical to the adapter in process: True
    stream-v0.1
      18 resources, 33 rows, 5 empty, complete=True, 259 ms
      identical to the adapter in process: True

    all three protocols report the same Stage 1: True
    in process the adapter omits 5 of 18: ['core.array_assets', 'core.array_dimensions',
      'core.clock_anchors', 'core.unit_coordinate_values', 'core.unit_coordinates']
    over every protocol they arrive at 0 rows

**Running all eighteen is what found the defect.** At four resources every protocol agreed with the
in-process adapter; at eighteen all three lost the same two columns. `pa.Table.from_pylist` takes
its schema from the leading row, and `core.electrode_coordinates` carries R59's `region_id` and
`region_label` on one electrode of three, the first without them — so both columns left every
delivery and nothing raised. `arrow.py` gets it right in process, taking the union of the keys and
the registry's declared types; the three probe adapters each reached for the naive call instead,
which is the argument for shipping the conversion with the protocol rather than leaving it to each
adapter.

**Stage 1 costs each protocol something different.** Flight answers from `ListFlights`, files from
the Parquet footers, and the stream only by reading the delivery — the same ranking the draft gives,
now measured against a real adapter rather than argued.

The fourth resource in the earlier run is the one that makes absence mean something. `NWBSource` declares 18 resources
and `records()` returns 13 against this fixture, omitting the five it has nothing for and returning
none of them empty — so today a resource that never arrives is a crash and a source with nothing to
say, indistinguishably. Delivered empty it costs a name and no schema: zero columns, and 144 bytes
as a stream.

**Three things the draft does not say, found by needing them.**

**Rendezvous.** Nothing states how a build knows the adapter is listening. Here the server prints
`ready` on standard output and the build waits for that line — invented for this probe. Retrying the
connection until it succeeds would do as well, and the two are not interchangeable for a build that
must distinguish *not yet* from *never*.

**Which recipe options an adapter accepts.** The closed list has "a recipe option" as a row, and an
adapter's `NEEDS` names terms rather than options, so `interval_kind` had to be passed beside the
declaration rather than through it. Either an adapter names the options it accepts in the same
declaration, or a build cannot refuse a recipe that sets one the adapter will ignore.

**Whether the wanted set is honoured.** `serve_nwb.py` computes every resource and filters, so
naming three of eighteen saved nothing. The saving is available to an adapter and not required of
one, and nothing a build can check tells the two apart.

## What a failure carries, run end to end

`failures.py` starts six adapters over `flight-v0.1`, each failing a different way, and reports what
the build is left holding. The table is synthetic and tiny: what is measured is what crosses a
process boundary, not what an adapter extracts.

    **The adapter never binds.** A build retrying the socket sees the exit rather than
    waiting on it: detected in 114 ms, and standard error carries
      'NWBSource: /mnt/Data/no-such-session holds no NWB file'

    **A plain exception in `do_get`.** What crosses is a string:
      ArrowInvalid, message 1108 chars, extra_info 0 bytes
      standard error: 0 bytes

    **A structured failure.** The same call, with the finding attached to it:
      FlightServerError, message 317 chars, extra_info 125 bytes of JSON
      parsed: level='error' resource='core.electrodes'
      standard error: 0 bytes

    **A failure partway through a stream.** Two batches had already crossed:
      FlightServerError, rows delivered to the build: 0

    **A run that succeeded and has something to say.** Two places carry it in band:
      Stage 1 `app_metadata`, per resource: 127 bytes, level='warning'
      `DoAction('report')`, per run, after the rows: 1 problem(s), read [...]

    **An adapter with nothing to say.** Asking costs a build one refused call:
      ListActions: [], DoAction: ArrowNotImplementedError

**Standard error is empty for both failing modes.** The draft had a build capture standard error and
report it with a failure, which is right for a command and reports nothing here — a Flight adapter's
diagnosis travels on the connection. What a build reports has to be named per protocol, which §3.10
now does.

**A plain exception crosses, badly.** 1,108 characters, the adapter's Python traceback and gRPC's
debug context pasted inside the message. The same failure raised as a Flight error carrying one
Part 09 §5.8 `problems` entry is 125 bytes a build parses.

**No rows survive a failed transfer.** Two of four rows had crossed as batches and `read_all`
returned none, so a build never holds part of a resource and needs no count to know it.

**A report needs a channel the protocol already has.** `DoAction("report")` is one action name and
no file; a build asks after the rows and before the adapter exits. `app_metadata` on the Stage 1
`FlightInfo` carries bytes too and is the wrong place — Stage 1 runs before the extraction a finding
would be about.

## What a failure carries over the stream, where nothing discards

`stream_failures.py` is the same experiment against `stream-v0.1`: rows on standard output as
concatenated IPC streams, one per resource, and a command that stops at four different points.

    **A run that finishes.** 7 of 7 rows, exit 0, parse error
      Tried reading schema message, was null or length 0

    **The command dies between two resources.** The first is complete and valid:
      the build holds {'core.sessions': 1}, exit 1, parse error
      Tried reading schema message, was null or length 0

    **The command dies after the rows and before the end-of-stream marker.**
      the build holds {'core.sessions': 1, 'core.units': 4}, exit 1
      parse error: Tried reading schema message, was null or length 0

    **The command is killed inside a batch.** What had already been decoded stays decoded:
      the build holds {'core.sessions': 1, 'core.units': 0}, exit 1
      parse error: Expected to read 200 metadata bytes, but only read 120

**A reader treats end of file as end of stream.** The end-of-stream marker was withheld and all four
rows arrived anyway, reported with the same parse error a clean finish reports. Flight discards a
partial transfer; the stream does not. Nothing in the bytes separated a finished run from a run that
died between two resources or one that died before its last marker — all three ended `Tried reading
schema message, was null or length 0` — so a build reading the bytes to decide whether a run
succeeded got the wrong answer twice in three.

**One empty stream fixes it, and the probe now ends with one.** A delivery terminated by an empty
stream whose `resource_id` is the reserved value `end` costs **128 bytes**, and its absence says the
delivery was truncated. It also names the suspect, which the completeness set cannot: the last
resource read is the one the adapter died inside, where the set reports the first that never
arrived.

    a complete delivery is 7 rows over 3 resources, ended by an empty stream named
    'end' costing 128 bytes

    the command finishes:
      holds {'core.sessions': 1, 'core.units': 4, 'core.intervals': 2}, exit 0
      delivery complete
    it dies between two resources:
      holds {'core.sessions': 1}, exit 1
      delivery truncated, last read 'core.sessions'
    it dies after the rows, before the end-of-stream marker:
      holds {'core.sessions': 1, 'core.units': 4}, exit 1
      delivery truncated, last read 'core.units'
    it is killed inside a batch:
      holds {'core.sessions': 1, 'core.units': 0}, exit 1
      delivery truncated, last read 'core.units'

A resource ID is dotted, so no undotted token can be one and the reserved value collides with
nothing.
