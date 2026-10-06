# Design

The writer builds a packet from a recipe. Source adapters read a session's files and return
records, `PacketWriter` stages those records, the validator checks the staged packet, and a commit
publishes it. The [README](https://github.com/galenlynch/escapewheel/tree/main/escapewheel-writer)
says how to run a build. This page explains why the code is shaped as it is.

The measurements on this page come from `ecephys_776259_2025-04-09`, a session of twelve probes,
6,781 sorted units and 286,896,563 spikes, unless a paragraph names another source.
[Performance](performance.md) holds the throughput measurements.

## A build validates before it publishes

Part 05 treats validation as the act of importing: copying or converting bytes only stages them,
and a resource is imported once it passes the checks for its schema. `PacketWriter` therefore
works in this order (Part 05 §2):

1. it writes the normalized resources and the import's provenance under `staging/` (Part 03 §3.3);
2. it derives the analysis resources the caller asked for from the staged packet (Part 05 §8);
3. it validates the whole staged packet in place;
4. it records every path that promotion will create, then promotes the files to those paths
   (Part 05 §6);
5. it renames the manifest to `packet.json` last.

Until the last step the packet root holds no manifest, so a reader finds nothing where it could
have found a partial import. The promotion record lets the next build remove whatever an
interrupted promotion left behind.

`PacketWriter` knows nothing about NWB, SpikeInterface or any other source. Adapters hand it
records, and it turns them into a packet or refuses.

## A recipe holds every parameter of a build

Part 05 §4.3 requires normalization to be deterministic in declared parameters, and
`core.processing_runs` records the run that used them. A build script meets neither requirement:
its parameters sit wherever its statements put them, and nothing can hash it. A recipe is the
parameter set as one file, so the run's row carries the parameters themselves
(`core.processing_runs.parameters`) and a reader can see what produced the packet.

`recipe` opens no source and writes nothing. Checking is separate from building so that a wrong
recipe is refused before a build that takes minutes. The most useful checks come from the registry.
A source declares the resources it owns, and the registry declares which resources reference
which. An owned table whose required foreign key points at a table no source produces can never
validate, and those two documents show it with no data in hand.

### A replaced packet shows what a recipe dropped

A recipe can lose a resource in three ways that `Recipe.check` cannot see, because each is an
omission and the recipe holds nothing that contradicts it:

- `owns` is exclusive, and a resource it does not name is discarded;
- a source the recipe never lists produces nothing;
- an absent `[[materialize]]` block derives nothing.

`compare` catches all three by comparing the finished packet with the packet it replaces. It warns
and never fails, because narrowing a packet is legitimate and only the recipe's author knows
whether it was meant.

## Adapters order a build

A foreign key constrains validity and not write order. Parquet files are independent, so
`core.spike_events` can be written before `core.units`. Data flowing between adapters is what
sequences a build: `NWBSource` needs the sorter's units before it can attach a unit to an
electrode, and no reference in the registry says so. Each adapter therefore declares what it
`CONSUMES` (Part 05 §3.4), and `session` orders the adapters by those declarations.

## The recipe assigns each resource to one source

Four adapters can each produce `core.probes`. Without a rule the last adapter to run wins in
silence. `session` filters every source's records to the resources the recipe says that source
owns, so the choice is declared in one place a reader can see.

## The build numbers every assigned identifier

An identifier is an `int32`, and `keys` chooses the number for every identifier the registry
declares `assigned` (Part 02 §8.2). All adapters share one `keys` instance. Two adapters that numbered the same probe
differently would produce a defect no foreign key can see, because both numbers resolve, to
different rows.

A carried identifier does not pass through `keys`. `region_id` is the atlas's own structure number,
and the writer copies it. A source's number for a unit or an interval is a label and not a carried
identifier: a sorter numbers from zero within each run, and a source numbers each kind of interval
separately, so only the packet can say which row a number names.

`keys` assigns numbers from 0 in first-seen order. Part 05 §4.3 requires only that a committed key
does not move. A deterministic order also makes two builds of the same sources produce the same
packet, so a rebuild can be compared with the packet it replaces. Where Part 02 orders a kind's
numbers, as §12.1 does for units and §12.9 for intervals, the caller asks for them in that order.

An amending build first holds every number the amended packet assigned. A held name keeps its
number, and every new name is numbered from one past the largest held number (Part 05 §4.3).

## Seconds become ticks by quantization only

Time in a packet is an integer count of ticks on a declared clock, and seconds are derived from it
(Part 01 §2.2). An importer has two ways to turn a source's seconds into ticks.

- **Quantization.** The source's values already lie on the clock's grid, so `round(t * rate)`
  loses nothing. `Clock.ticks` quantizes and checks, and raises `OffGrid` for a value off the grid.
- **Fitting.** The source's values lie on no grid, so recovering ticks means estimating a rate and
  an offset. `clock` does not offer this, because the result is a guess.

One NWB holds both cases. Every behaviour and trial timestamp lies exactly on HARP's 31,250 Hz
grid. The spike times have a per-probe alignment applied in float seconds and lie on no grid, so
the build takes spikes from the sorter, which still has sample indices
(`inventory/nwb-zarr-776259-2025-04-09.md` §3.3).

An epoch is localized with an IANA zone and not a fixed offset. A HARP epoch 134 days before an
April session in Pacific time falls in November, across the daylight-saving transition, where a
fixed offset is wrong by an hour.

## Column types come from the registry

A writer does not invent a schema. `arrow` takes every column's type and presence from
`logical_schemas.json`, so a packet cannot disagree with the registry it embeds.

## Encoding rules cover every table; exceptions are measured

`encoding.choose` implements Part 10 §2.13's rules. The rules apply to any table the writer stages,
an extension's as much as core's, because Part 09 §5.6 lets a writer require no code of an
extension. The exception tables name `core.*` and `analysis.*` columns only. An extension that has
its own exceptions passes them to `PacketWriter`.

The exceptions are not in the registry, because encoding and row-group size are not normative: the
right values follow from session length and unit count. Two cases show why a rule alone is not
enough.

- A dictionary over near-unique `int64` ticks is the worst option at every row-group size. The
  Parquet writer builds a dictionary nearly as large as the column, overflows the page limit,
  abandons the dictionary mid-column and emits both (`conformance/parquet-probe/real.py`).
- `anchor_index` ascends over thousands of anchors per clock, and `n_spikes` is a large count with
  no repeats. Both store better as deltas, and neither name says so.

`inefficient` reports a column whose chosen encoding is more than `TOLERANCE` = 1.5 times its best
one, so a wrong guess is seen.

## A packet-owned array is chunked for the read and sharded for the store

`conformance/zarr-probe/waveforms.py` compared layouts on 6,781 unit waveforms. Four results set
what `arrays` does.

**A chunk matches the read.** One unit's template reads in 0.6 ms from a one-unit chunk and in
3.9 ms from a 512-unit chunk.

**A shard keeps small chunks from becoming small files.** Sharding turned 6,782 files into 15 for
0.4% more bytes and no loss of speed. On an object store, 6,782 files are 6,782 requests.

**A shard's size comes from the store's latency and bandwidth.** Amazon's S3 guidance recommends
byte-range fetches of 8-16 MB for parallel reads, bills objects under 128 KB as 128 KB in three
storage classes, and suggests multipart upload above 100 MB. `target_object_bytes` derives a size
from latency and bandwidth and does not hardcode that band, because the answer is several times
smaller from inside the region. Measured against `aind-open-data` from outside AWS, fixed latency
is 86% of a 128 KB fetch, 73% of a 1 MB fetch, 18% of 4 MB and 15% of 8 MB. That puts a round trip
at about 34 ms and the stream at about 40 MB/s.

**The compressor goes inside the shard.** zarr-python applies a default compressor when none is
named, and a codec wrapped around a shard forces a reader to inflate the whole shard to reach one
chunk. The partial read then takes 188 ms against 0.6 ms, and only a warning announces it.
`write_zarr` always passes `compressors=None` and puts the codec in the shard's own pipeline.

## The analysis spike table exists for its sort order

Part 06 offers a view where a transformation is cheap and a materialized table where it is
expensive or often reused. Aligning clocks is cheap: 29 M spikes a second, so a query over a few
units pays milliseconds. `analysis.spike_events` is materialized for its layout. Core's spike ticks
are on one clock per probe, so core cannot order spikes by time across probes, and a common clock
makes that order possible.

The analysis table drops the exact probe tick, which `core.spike_events` keeps. A spike that the
clock mapping cannot place is dropped and not guessed, so the analysis table is not row-aligned
with core. Every analysis resource declares its lineage to core in the manifest's `derived_from`
(Part 06), and a packet without the analysis layer is complete.

Three choices in `materialize` rest on measurements.

- `BUCKET_SECONDS` is 300 s, the best of 10, 60 and 300 on a 5,364 s session with 7,291 units.
- Buckets are coalesced before they are written. Writing each bucket's rows as they arrived
  produced 140,315 row groups against 2,197, and a table half again as large.
- The spill is Parquet with the tick column delta-encoded. An uncompressed Arrow IPC spill took
  321.8 s against 76.6 s. Under pyarrow's default encoding the tick column cost 1,195 MB and 77.4 s
  against 500 MB and 60.9 s.

## An amendment is settled before anything is staged

An amendment adds groups of rows that a packet lacks and changes no row the packet holds
(Part 05 §15.2). `amending` therefore reads the packet first. The packet's identifiers seed the
build's, and each table's delivered rows are compared with the held rows before the table is
written. The group test is the validator's own (`escapewheel_validator.amendment`), so the writer
never builds an amendment that the validator would then report.

An entry of `[packet].replaces` names a packet root or a manifest file, such as one that a packet
retains under `manifests/`. `replacing` resolves a relative entry against the recipe and refuses a
bad entry before any source opens.

## Pruning removes orphans before manifests, and never strays

`prune` removes two things in a fixed order. Orphans go first. A manifest identifies the orphans
of its own version, so expiring the manifest first would leave an orphan that nothing can tell
from a stray. Superseded manifests go second, as far as the retention policy allows.

A stray is a file that no manifest has named, outside the staging area and outside every path an
unpublished promotion record claims. `prune` reports strays and never removes them, because a
packet may carry files the specification does not govern. It reports the files of a build or
amendment in progress separately and leaves them alone.

`prune` removes nothing unless the caller asks, and reporting is the default (Part 05 §15.5).

## `verify` records external bytes once they are reachable

A commit records only what the build could reach. A packet built away from where its data will
live records nothing about that data, because Part 04 §5.2 requires a writer that cannot reach a
URI to record nothing. `verify` runs once the bytes have landed: it reaches them and records what
it found. No file is written and no resource is added. The new version changes only what the
manifest says about resources the packet does not own. A `sha256` over one session's LFP took 88 s
against S3.

## An adapter can run outside the build's process

A build reads an adapter's `protocols`, `produces`, `contributes`, `states`, `needs`, `accepts` and
`consumes` before it opens any source. Reading them from a class means importing the adapter, and
Part 12 §7 forbids requiring that. An adapter that a build cannot import publishes the same facts
as a JSON document. `declaration` generates the document from the class, since every field is read
off the class with no judgement. The document says nothing about the machine: the command, the
root and the options stay in the recipe.

`serving` and `reading` implement the three protocols Part 12 §3 names: `serving` encodes each wire
format in the adapter's process, and `reading` decodes it in the build's. The protocols differ under
load.
`files-v0.1` delivers Parquet on disk, which a build streams one batch at a time, so it suits a
large source. `stream-v0.1` and `flight-v0.1` hold each resource as it arrives, because a build
consumes resources in its own order and cannot rewind a pipe.

A build passes its terms to an adapter on standard input, because an argument list has a size
limit and one term with a record per unit exceeded it (Part 12 §4).

Arrays and opaque payloads do not cross as rows. Each crosses as bytes in a location the build
supplies (Part 12 §5). An adapter places each opaque payload alone in a directory named by its
resource ID, and `opaque` reads that location and refuses what a packet cannot own. The writer
binds a payload to its catalog row at commit, when it has every source's rows.

## A build finds an extension's registry by path or entry point

Part 09 §5.1 makes an extension a registry document, and Part 09 §5.3 has the packet carry it.
`extensions` finds the document in one of two places. A document being drafted is a file beside
the recipe, named by its path. A document that someone else maintains arrives in an installed
distribution, which has no path a recipe could name, so the distribution registers it under an
entry-point group.

A distribution carries the registry document and, where the raw source needs parsing, a source
adapter. Both matter only while a packet is built. The built packet embeds the document, and
reading it needs nothing installed.

`scaffold` drafts a registry document from a Parquet file. It reads what the file states: column
names, Arrow types mapped to the registry's vocabulary, and whether a column is ever null. A
column's `role` and `identity` cannot be derived from its name, its type or its key membership, so
the draft marks each guess and leaves the classification to the author. A default would make a
forgotten classification look deliberate.

## Source adapters return records

No single source carries a whole session. The NWB is the only source for trials and behaviour and
the only one with CCF registration, and the integer tick that `core.spike_events` needs survives
only in the sorter's output (`inventory/nwb-zarr-776259-2025-04-09.md` §6). A packet therefore
merges sources, and an adapter that wrote packets could not be merged.

The built-in adapters read standards that many institutions write: SpikeInterface, Open Ephys,
Harp and NWB. An adapter for one institution's format is registered under `SOURCE_GROUP` from its
own distribution, as `escapewheel-aind` registers its four.

### NWB

`NWBSource` emits what the NWB is the authority for: identity, devices and probes, electrodes and
their coordinate frames, behaviour event streams, and trials. It does not emit `core.units` or
`core.spike_events`, because the NWB's spike times lie on no tick grid.

The clock is a parameter. Nothing in an NWB declares a time base, and NWB's contract makes
`timestamps` seconds relative to `session_start_time`. In the measured file they count from the
HARP epoch, 134 days earlier. The caller passes the clock the times are on, and `Clock` checks
every conversion against its grid, so a wrong clock raises `OffGrid`.

The zone is a parameter for the same reason. The file does not name `America/Los_Angeles`, and its
stored offsets are unreliable: the subject's date of birth carries `-07:53`, the offset of Pacific
Local Mean Time. The adapter checks each stored offset against the declared zone and reports the
ones that disagree.

A signal is staged as an array and not as rows. One 400 Hz thermistor is 5,881,692 samples, and
delta encoding takes it from 11.8 MB to 3.47 MB.

### Sorter

`spikes.npy` carries `sample_index`, a count of samples since the recording began, so
`core.spike_events.t_tick` needs no conversion.

Several numberings of a unit meet in a sorted asset, and no two agree.

- `unit_index` in `spikes.npy` is an offset into `unit_ids` and not an identifier. On one stream
  `unit_ids` spans 0 to 841 for 836 units, because Kilosort leaves gaps where clusters merged. The
  adapter resolves every unit through `unit_ids[unit_index]` and never stores the offset.
- The Kilosort cluster ID is unique within a stream and not across streams: the session has 810
  distinct labels across 6,781 units.
- The NWB's `units` table numbers rows densely across every probe. Joining it to the sorter's
  units needs `(device_name, original_cluster_id)`.
- The packet's `unit_id` is the number the build assigns. The adapter names a unit by its run, its
  curation and its zero-padded label, and the writer numbers those names in order (Part 02 §12.1).

The adapter emits no `core.clock_anchors`. A curated sorting holds nothing that relates one
stream's samples to another's, so a packet with several probes needs the sync adapter.

`STREAM_WORKERS` is 4. Over twelve probe streams, one worker took 20.5 s at 1.5 GiB, four took
7.0 s at 4.7 GiB, and twelve took 5.3 s at 11.5 GiB.

### Sync

The sync adapter supplies `core.clock_anchors`: the shared sync pulse that each stream records,
paired with the HARP time that `aind-ephys-rig-qc` wrote onto it.

**Only an owned stream has anchors.** A record node's directory lists every stream the node saw,
and only the streams it owns were aligned. An unowned entry holds acquisition-local seconds and
nothing marks it unaligned. The adapter detects ownership by `original_timestamps.npy`, the archive
that rig-qc writes when it replaces a timestamp array. It skips a stream without the archive and
reports the skip. Read as aligned, such a stream would put a probe's sync pulses 17.7 million
seconds from their place.

**`sample_numbers` is the sorter's counter.** A TTL directory holds four arrays that count time:

```text
sample_numbers.npy        raw hardware counter, absolute across the acquisition
local_timestamps.npy      recording-relative seconds, already drift-corrected
original_timestamps.npy   acquisition-relative seconds, before HARP alignment
timestamps.npy            HARP seconds, after it
```

`sample_index` in `spikes.npy` indexes the preprocessed recording, which is built from raw samples
with no correction. It corresponds to `sample_numbers` and to none of the seconds arrays:
`sample_numbers - local_timestamps * rate` takes 895 distinct values across one stream's pulses.
The recording's first raw sample is element 0 of `continuous/<stream>/sample_numbers.npy`, which
the adapter memory-maps so that it never reads the 1.3 GB file.

`DISCONTINUITY` is 400 µs. An anchor interval's parent advance departs from the clock's median
ratio by at most 160 µs across 76,622 intervals, and two known upstream discontinuities cost 672
to 832 µs each.

### Waveforms

The waveform adapter reads a template from the `SortingAnalyzer` beside the curated sorting, and
not from the NWB exported afterwards. Both hold the same array, `(4559, 210, 384)` float64 on one
session. The export loses three things the analyzer states.

- **The contacts a unit sits on.** SpikeInterface computes a template on the contacts near the unit
  and records them in `sparsity_mask`. The export pads every unit to all 384 channels with zeros.
  The mask keeps 6.7% of that rectangle, 14 to 26 contacts a unit.
- **The unit each row describes.** The analyzer's `sorting/unit_ids` match the curated sorting's
  IDs on 10 of 10 streams. The export renumbers rows by table position.
- **The unit of the values.** The analyzer declares `settings.return_in_uV`. The export writes
  `unit: "volts"` on values that reach ±1654.

The packet stores a template sparse, as int16, and as `(unit, channel, sample)`. The int16 step is
peak/32767, well under the 0.052 µV standard error of the best-resolved tenth of the means.

### LFP

Five facts about LFP data set the shape of `LFPSource`.

- **The packet references the arrays.** Twelve probes hold 5.8 GB of compressed int16. Part 04 §5.1
  expects a resource of that size to be referenced, and transcoding it would discard the
  acquisition's own compression.
- **The arrays are Zarr v2**, which only an external resource may be (Part 03 §6.1).
- **The stored timestamps are not used.** Every series stores 7,983,750 float64 timestamps on a
  regenerated nominal grid, with the sign of `t0` flipped. LFP sample 0 lands within 0.2 ms of its
  probe's own sample 0, and each sample advances exactly 24 AP ticks, so a regular-tick axis states
  the timing in three integers on the clock the spikes are on.
- **The channel axis is labelled.** LFP keeps every fourth contact, 96 of 384, so a range cannot
  describe the axis. Its labels name rows of `core.electrodes`.
- **`inter_sample_shift` varies per channel**, with eight distinct values in a series, because a
  Neuropixels ADC samples its channels in turn. `conversion` has one value per series and stays on
  `core.array_assets` (Part 02 §5.2).

`verify` defaults to `size`. Listing a session's twelve LFP prefixes takes 0.33 s, and digesting
the 6.83 GB behind them takes 75 s from local disk and 88 s from S3. `members` costs no requests
and adds 2,496 entries to the manifest.

### Open Ephys

`settings.xml` describes every probe as a chain: a PXI basestation in a slot, a connect board on
the basestation, a headstage on a port, and the probe. Three of the four report their own firmware
or hardware version, and the versions differ within one session. Part 01 §3.5 makes each element
that reports its own versions a device. The adapter emits those three and leaves the probe's row
to the NWB, which knows the probe's part number and serial.

Identity comes from physical position, because every basestation, connect-board and headstage
serial number in the measured session is `0`. A slot identifies a basestation and its connect
board, and a slot and port identify a headstage.

### Harp

A Harp acquisition directory carries `device.yml`, the device schema that the Harp protocol
defines: the device's name, its `whoAmI` type code, its firmware version and its registers. On
`ecephys_786867` no rig, session or processing JSON mentions the sniff sensor, and `device.yml`
names and versions it. The adapter reads `device.yml` alone. The signal reaches the packet through
the NWB, already aligned, so decoding Harp's binary register streams would add a dependency for
nothing.

### Adapters share one store per root

`NWBSource` and `LFPSource` open the same `.nwb` directory and both read the electrodes table.
`SourceStore` caches each pure read, so two adapters cannot disagree about the same bytes.
`SourceStore.head` decodes only the chunks it needs: an LFP series stores 7,983,750 timestamps and
the adapter wants two of them.

The root is a `UPath`, because a session's assets may be prefixes on an object store. A build
reads about 12% of a sorted asset, and the adapters alone know which 12%, so the build reads in
place and does not fetch the asset first. The source cache keeps an object that is read twice from
being fetched twice, which matters for a stream's 344 MB `spikes.npy`.

### NWB-Zarr is decoded without `zarr`

Everything an importer needs from an NWB-Zarr file is a one-dimensional array: table columns,
timestamps and scalar metadata. `zarr_compat` decodes those from their chunk bytes with the codecs
they declare, which needs `numcodecs` alone. The writer therefore depends on neither `zarr`,
`hdmf-zarr` nor `pynwb`. Decoding from chunks also avoids two faults that make zarr-python 3.3
refuse these files (`inventory/nwb-zarr-776259-2025-04-09.md` §1).

- Four arrays, among them `session_start_time`, are `|O` with `fill_value: 0` and a `vlen-bytes`
  filter, and zarr-python's v2 parser rejects the fill value. Decoding from chunk bytes never
  consults it.
- `electrodes/group` is pickled `hdmf-zarr` object references. `zarr_compat` raises
  `UnsupportedEncoding` for it, and the plain `group_name` column beside it holds the same
  information.

`DenseV2` reads a template array the same way, because a packet owns `core.waveform_mean` and has
to read those bytes.

### A compensation is declared

Every adapter works around something known to be wrong in its source. A correction leaves no trace:
a packet built from a corrected source looks like one built from a source that was never broken.
When the fault is fixed upstream, an importer that keeps correcting produces a packet that is wrong
in the opposite direction. Negating an LFP `t0` that upstream has already negated is the case that
prompted the mechanism.

An adapter therefore declares each compensation it applies, and the build records them in
`core.processing_runs.parameters`. A packet then states what its importer assumed, and the packets
that assumed a since-fixed fault can be found. A deliberate pass-through is declared too, because
choosing not to correct is also an assumption.

An adapter served out of process cannot hand the build a list, and one written in another language
cannot add to the build's registry. Its delivery therefore carries a `compensations` table stating
each one in full: `id`, `defect`, `action` and optionally `evidence` (Part 12 §5). The table goes
last, because an adapter may apply a compensation while an earlier table streams. The build takes
it out before it counts or stages what arrived, and records two rows that agree in every text once.
