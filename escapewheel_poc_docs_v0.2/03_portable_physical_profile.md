# Part 03 — Portable Physical Profile

Normative. Profile identifier: `escapewheel-portable-v0.1`.

## 1. Scope

This part defines how the logical resources of Part 02 are stored in the portable profile. A packet under this profile MUST be readable without a server.

This part is normative for a packet whose manifest declares `profile_id: escapewheel-portable-v0.1` and binds no other packet. It is the only part whose rules may depend on a storage technology (R93 §3.2). Where a number here supports a rule rather than stating one, the rule stays and the number is Part 10's (R93 §3.4).

## 2. Required technologies

| resource kind | format |
|---|---|
| catalog | JSON |
| tables | Apache Parquet |
| dense arrays | Zarr, v3 for packet-owned arrays (§6.1) |
| media | ordinary containers, such as MP4 |
| documents | Markdown, JSON, text, or PDF |

## 3. Directory layout

### 3.1 Recommended layout

```text
packet_root/
  packet.json

  tables/
    core/           <resource>.parquet
    analysis/       <resource>.parquet
    <namespace>/    <resource>.parquet      extension tables

  arrays/
    core/           <array_asset_id>.zarr/
    analysis/       <array_asset_id>.zarr/

  media/            <media_asset_id>.<ext>

  extensions/       <name>.json             extension registries

  schemas/
    logical_schemas.json                    the embedded registry

  manifests/        <packet_version>.json   superseded manifests

  docs/                                     human-readable sidecars

  validation/       validation_report.json
```

The catalog MUST record the actual layout. A reader MUST resolve resources through the catalog and MUST NOT infer them from paths.

### 3.2 Files that MUST NOT be written

`schemas/semantic_version.txt` is struck (R62 §2). It restated `semantic_standard_version`, which the catalog is required to carry, and so bought no otherwise-available access.

## 4. URI rules

A URI in the catalog or in a table MAY be relative to the packet root or absolute, or — where the entry names a `source` — relative to that source (Part 04 §5.5). A portable local packet SHOULD use relative URIs.

An absolute URI MAY name an external asset. A catalog entry for an external asset MUST declare it external (Part 04 §5).

A packet root MAY itself be an object-store prefix rather than a directory, in which case a relative URI resolves under that prefix (Part 00 §3).

## 5. Table storage

### 5.1 Encoding

A table MUST be a valid Parquet file. Compression SHOULD be Zstandard where available.

A large table SHOULD use row groups sized for analytical scans. Part 10 carries the sizes measured for one (R93 §3.4).

An identifier column is `int32`, or `int64` where its range requires it (Part 02 §5.3) and MUST NOT be dictionary-encoded in a way that requires unification across row groups before it can be compared.

### 5.2 Partitioning

A large multi-session table SHOULD be partitioned by `session_id`. A table MUST NOT be partitioned by `unit_id`, which produces many small files.

A partitioned table's row order across files is not defined by this profile. A single file is therefore preferred where the table's sort is load-bearing.

### 5.3 Ordering

A table MUST be stored in an order that settles its primary key by adjacency: every key column appears in the sort, and every sort column up to and including the last key column is either a key column itself or one the registry declares `determined_by` a subset of the key (Part 02 §8.5). Where the registry declares no sort for a table, the order required is its primary key's. A validator MUST report a departure as an **error** (R92 §2.2).

Two rows sharing a key are then neighbours, because nothing in the sort can order between them: a column that is a function of the key takes the same value in both. So the scan that establishes order settles uniqueness in the same pass, which is the means Part 02 §10.1 leaves to a profile to supply. A validator establishes order by scan rather than by query, because physical order is not visible to SQL (R12 §4, Part 02 §10.3).

The scan MUST verify each `determined_by` declaration it relies on: of two adjacent rows sharing a primary key, every sort column declared `determined_by` a subset of that key MUST hold the same value in both, and a validator MUST report a difference as an **error** (R92 §2.3). A wrong declaration otherwise waives a check rather than failing one. The comparison reaches a declaration that is false between two adjacent rows, which the scan reports as a duplicate key as well, the second finding saying which to repair; a declaration false enough to sort two duplicates apart is beyond a scan of neighbours.

Where the scan finds a departure, uniqueness MUST be settled by aggregate rather than by adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of neighbours.

A reader MUST NOT depend on stored order for correctness. Establishing the order is the validator's work, and a reader that assumed it would be trusting a property of the profile rather than of the logical standard.

One table is stored in an order other than its primary key's, `analysis.spike_events`, under a `MUST` (R30 §3.2); Part 03 §5.4 gives it, and it satisfies this section because `clock_id` and `time_bucket_tick` are each declared `determined_by` a subset of the key. `core.events` needs no override: R91 §3.2 keys it on `(session_id, stream_id, t_tick)`, the order it is stored in. `core.spike_events` needs none either: R81 §2.4 makes its key `(session_id, unit_id, t_tick)`, and because units are numbered run-major the default order clusters a probe's spikes exactly as the old override did.

### 5.4 The overriding orders

| resource | order |
|---|---|
| `analysis.spike_events` | `session_id, clock_id, time_bucket_tick, unit_id, t_tick` |

A writer **MUST** emit `analysis.spike_events` in that order (R30 §3.2). It is the one resource whose layout is part of its reason for existing: bucketing by time and sorting by unit within each bucket leaves both columns with informative row-group statistics, so a unit filter and a time filter each prune.

A writer **SHOULD** start a new row group at each bucket boundary (R30 §3.3). A group cut at a fixed row count straddles boundaries and spans two buckets' worth of time. Row-group size and encoding are otherwise not normative: the right values follow from session length and unit count rather than from the schema.

### 5.5 The Parquet floor

A reader MUST support the compressions **uncompressed, Snappy, Gzip and Zstd**. A writer MUST use
one of those four and SHOULD use Zstd (R3 §2). Dictionary, RLE and delta encodings MAY be used and
MUST be supported by readers.

A writer SHOULD encode tick columns with `DELTA_BINARY_PACKED` and SHOULD NOT dictionary-encode
them. On a high-cardinality tick column a writer builds a dictionary nearly as large as the column,
abandons it at its size threshold, and emits a mix of partial-dictionary and plain pages larger
than either encoding alone.

A writer SHOULD encode with `DELTA_BINARY_PACKED`, and SHOULD NOT dictionary-encode, the first
column of a table's sort order whose role is `identifier` (R110 §3.1). Sorting a table by its key
(R10 §2) makes that column ascend across the whole table, which is what delta encoding exists for
and which no later key column has. `session_id` is not that column, being one value in a
single-session packet and already 0.03 bits a row under run-length encoding; a writer skips it and
takes the next.

A writer SHOULD NOT dictionary-encode a floating-point column, and SHOULD write one whose values
repeat as a declared exception (R110 §3.2). Repetition is what a dictionary indexes, and four
floats in five do not repeat enough to pay for one.

Neither rule is the property it stands in for, so a writer MUST be able to override each per
column, and every override MUST record what it measured and on what (R110 §3.3). An exception
recording nothing cannot be re-judged when the data changes. A writer SHOULD refuse an exception
naming a column no table declares, which is decidable with no packet in hand.

A writer SHOULD report, at `info`, a column whose encoding costs more than **1.5x** the smallest
available to it, measured over a sample of the rows it wrote (R110 §3.5). These rules are good
guesses, and the report is how the author of a table learns that theirs is one a guess misses. A
report and not a refusal: every encoding above is permitted, so a packet is conforming whichever
it uses.

Wall-clock timestamps MUST be Parquet `TIMESTAMP` with `isAdjustedToUTC=true` and `MICROS`
precision; A wall-clock column MUST NOT use `INT96`. Dates MUST be Parquet `DATE`, int32 days since the Unix epoch.

### 5.6 One null

Under `escapewheel-portable-v0.1` a column value is present or null and there is no second marker. Parquet's definition level carries one bit and Arrow's validity bitmap carries one, so a value that is inapplicable, one that was never recorded, and one a source recorded as unknown all arrive as the same null (R101 §3.10).

NaN is not the exception it looks like. It is a value of a float column rather than an absent one, so it reaches 30 of the registry's 330 columns and none of the rest, and Parquet's statistics exclude it from a page's bounds — a page holding only NaN publishes no minimum and no maximum.

A writer MUST NOT adopt a sentinel value meaning absent; an absent value is null. Where the reason for the absence matters, core records the fact that distinguishes it rather than encoding the reason in the value: R44 §2.3 gave a run a `scope` so an undeterminable one is distinguishable from an unambiguous one, and R22 §3 nulls `normalized_label` where a source's label has no honest projection.

## 6. Array storage

### 6.1 Version

A packet-owned array MUST be Zarr v3 (R21 §3.1). A referenced array MAY be Zarr v2, because a packet does not control how an external producer wrote it.

An array MUST use a **regular chunk grid** (R3 §7.1): every chunk the same shape, the last along each axis permitted to be partial. An irregular grid is expressible in Zarr and is not readable by every binding.

Stated as the prohibition a validator can check: `physical_profile: "zarr_v2"` MUST NOT appear on a resource that is not `external: true` (R21 §3.2).

Each array resource declares its own Zarr version in the catalog. A reader MUST check a resource's `physical_profile` together with its `codecs` before opening it, and MUST fail **for that resource**, naming whichever it lacks — the per-resource degradation R15 §2 requires applies to the version as much as to the codec, because a reader may support a codec in one Zarr version and not the other.

### 6.2 Axis order

Array axes are stored order, slowest-varying first (R3 §5). An array's codec chain MUST NOT include `transpose`.

A column-major binding enumerates axes in reverse. The client adapts; the format does not.

### 6.3 Axis coordinates

Every axis MUST declare its coordinates in `core.array_dimensions`, in one of the forms of R20 §2. A regularly sampled axis declares an origin tick, a step, and a length rather than storing per-sample values.

A step MAY be rational, declared as a numerator and denominator (R33 §2): a 30 ms bin at 31,250 Hz is 937.5 ticks.


An axis MUST declare no more than one coordinate form: two descriptions of the same positions can disagree and nothing would say which governs (R20 §3).

A rational step is a numerator and a denominator. `step_tick_den`, where present, MUST be positive, the numerator MUST be present wherever an origin is, and the pair SHOULD be in lowest terms so two packets describing the same axis describe it identically (R33 §2).

Where an array declares both a sampling rate and a regular tick axis, the two describe the same thing and MUST agree (R20 §4). The rate is retained as a validated denormalization, not as a second source of truth.

### 6.4 Codecs

A writer MAY use any Zarr codec. The catalog MUST name every codec a resource uses. A reader MUST check a resource's declared codecs before opening it, and MUST fail naming what it lacks rather than returning partial data (R14 §2.2, R15 §2).

The floor a reader is required to support is stated per Zarr version, because implementations differ between them (R21 §3):

| `physical_profile` | a reader MUST support | a writer MAY also use |
|---|---|---|
| `zarr_v3` | `none`, `gzip`, `zstd` | `blosc` (cname=zstd, shuffle=shuffle), `sharding_indexed` |
| `zarr_v2` | `none`, `zstd`, `blosc` (cname=zstd) | — |

The asymmetry between the versions is measured, not chosen: `gzip` is in the v3 floor and not the v2 one because a v2 array compressed with gzip raises `KeyError: "gzip"` in a reader that reads every other combination. Codecs are declared per resource, not per packet: a reader MUST NOT refuse a packet over a codec used only by resources it does not open. The catalog's packet-level codec list is their union, for a whole-packet capability answer.

### 6.5 What the array declares, and what the tables declare

`core.array_assets` MUST NOT carry dtype or shape. The Zarr array declares them, and restating them buys no otherwise-unavailable access (R3 §3.0).

`core.array_dimensions` carries axis names, because a Zarr binding in another language cannot see them.

Zarr attributes MAY duplicate helpful metadata. Metadata required for validation MUST also be represented in tables or the catalog, so that it is not reachable only through an array store.

## 7. Metadata placement

| kind | location |
|---|---|
| packet-level facts | the catalog |
| queryable scientific facts | tables |
| semi-structured, lab-specific values | a `json_string` column, or a sidecar |
| human-readable context | `docs/` |

A value used for filtering, grouping, joining, or validation MUST be a first-class typed column.

## 8. Immutability

### 8.1 Packet-owned bytes

A writer MUST NOT modify a resource the packet owns once it is committed (R14 §2.3). A correction is a new packet version, not an edit.

This promise is what allows an amendment to skip revalidating untouched files (R35 §2), so it is verified rather than assumed: a writer records a checksum for every packet-owned resource (§10).

### 8.2 External bytes

This specification promises nothing about bytes the packet does not own. What a packet records about an external resource is what was true when it was checked, not a claim about now (R14 §2.3.1).

## 9. Amendment, versioning, and retention

### 9.1 What an amendment is

An **amendment** produces a new version of an existing packet and MUST NOT modify any file the superseded manifest names (R32 §2). A table that gains rows is written as a **new file**, and the amended manifest names the new file; no byte of the old one changes. Immutability is thereby a property of files, and a resource's *content* may be superseded by naming different bytes.

An amendment MUST set a `packet_version` that sorts strictly after the superseded one, compared as a semantic version.

### 9.2 What an amendment may and may not do

| | |
|---|---|
| Add an analysis resource | MAY |
| Add rows to a provenance table (`core.processing_runs`, `core.source_files`, `core.processing_run_inputs`), as a new file | MAY |
| Remove an analysis resource | MAY — Part 06 makes them disposable |
| Add a core resource | MAY |
| Change the content of a core resource other than the provenance tables | MUST NOT |
| Remove a core resource | MUST NOT |
| Change `packet_id`, `profile_id`, or the standard versions | MUST NOT |

The asymmetry is the design: an amendment **extends** what a packet says and does not revise it. A packet whose core data was wrong is a new packet, not a new version of an old one, because anything already derived from the old core is silently invalidated and nothing in the format can detect that.

Provenance tables are the exception because they are append-only by nature — a row records that something ran, and a later run does not change what an earlier one did.

### 9.3 The manifest

Every superseded manifest is retained under `manifests/` (R32 §4), so a later cleanup can distinguish a file an old version named from a file nothing ever named. A retained manifest keeps its own `created_at` and its own validation record; an amendment MUST NOT rewrite either.

Where an amendment installs a different registry, the packet retains the superseded copy alongside it (R32 §4.1). Installing different content under a `registry_version` the packet has already retained makes that version ambiguous **within one packet**, and a writer MUST refuse it.

### 9.4 Scope of revalidation

An amendment MUST validate the whole packet, not only what it added (R32 §5). What R35 bounds is
the *work*, not the verdict: the resources an amendment did not write are immutable, so their
verdict is determined rather than assumed, and re-establishing it costs nothing.

A writer performing an amendment MUST establish the physical order of the resources it writes, and a validator MUST NOT
require it to re-establish that order for any other packet-owned resource (R35 §4).

A validator MUST re-run a check when it is **attached to** a resource the amendment writes, **or when its
query names one**; a check meeting neither condition MAY be skipped (R35 §2). The second test is
syntactic — a generated check refers to a resource by its flattened name — so a rule that names a
resource added later is caught without the registry having to declare that it might.

A validator **MUST make that test over-inclusive where it is uncertain** (R35 §5). Matching a resource name inside
a string literal or a comment re-runs a check that did not need it, which costs time; failing to
match one costs correctness. A validator that cannot show an input is immutable MUST run the
check (R35 §6): skipping a check whose inputs *could* have changed stays forbidden, which is what
R32 §5 was protecting.

### 9.5 Cleanup

Cleanup is a separate operation and MUST proceed orphans first, superseded manifests second (R61 §2.1). Expiring a manifest first would make an orphan indistinguishable from a stray, permanently.

A writer MUST NOT remove a **stray** — a file no manifest ever named (R61 §2.1). A packet may carry
files this specification does not govern, and cleanup that deletes the ungoverned is a data-loss
bug wearing an operation's name. The operation reports by default and acts only when asked.

An amendment **MUST NOT** delete anything as part of amending (R32 §6). A file that no manifest
version names any longer MAY be deleted, but by cleanup, as a separate operation — which is what
keeps an amendment's failure from having removed something.

A packet MAY declare its own retention, and a writer SHOULD emit one (R61 §2.2): how many superseded manifests to keep, and an optional age beyond which one may be dropped. Both are **floors** — a manifest is expired only when both permit it — and both default to one kept version and no age limit, because a packet is archival where a table is operational. A packet never amended retains nothing and carries no `manifests/` directory at all, so the common case costs nothing.

### 9.6 What a version is not

`packet_version` versions the bundle. A writer MUST NOT increment it for a rewrite of a table's rows under a future lakehouse profile (R61 §4).

## 10. Checksums

A writer records a `sha256` over each packet-owned resource by default (R52 §2). This is the one case where a digest verifies what the packet itself claims, and it is cheap: whole-file, one file per resource.

A digest is whole-file, not per-row-group. Parquet cannot be appended to, so "which pages moved" is not a question the format can be asked, and Parquet's own page CRC32 is a corruption detector that a rewritten file passes.

A packet-owned resource recording no digest is not checked, and a verification report MUST state how many it skipped for that reason (R52 §2.3). A pass that does not say what it skipped reports clean on resources it never looked at.

Verification of external resources is optional and layered (Part 04 §5.3).

## 11. Reaching a source

An adapter reads one source and returns records, and a build assembles a packet from several (Part 05 §3.1). This section is what passes between them: the protocols rows may cross by, what a build supplies an adapter, what a delivery states, and how an adapter declares itself. It is the profile's rather than the pipeline's because every rule in it would change if the profile changed, and because an adapter is the first thing an implementation in another language writes (R115 §3.6).

An **adapter** here is code that reads one source, whether the reference implementation ships it or a third party does. A clause binding an adapter binds one it does not ship identically (R115 §1).

### 11.1 Protocol groups

A profile names a **group** for each way rows cross a process boundary, and the protocols in it. `escapewheel-portable-v0.1` names one group, out of process, holding three:

| protocol | rows cross as |
|---|---|
| `files-v0.1` | Parquet the recipe names, one file per resource |
| `stream-v0.1` | a sequence of Arrow IPC streams on standard output, each schema naming its resource |
| `flight-v0.1` | Arrow Flight over a Unix socket the build names, one descriptor per resource |

An adapter **released independently of a build** MUST declare and support at least one protocol in a group, and a build MUST support every protocol in every group this profile names (R115 §3.3). The asymmetry is deliberate: there is one build and there will be many adapters, so no negotiation can fail. A build meeting such an adapter that declares no protocol of the group MUST refuse it, naming the group, before any source is opened.

An adapter a build ships with need not declare one, and a build reaches it directly. The test is the release boundary rather than who wrote the code: an adapter inside a build's distribution is upgraded in the commit that changes a dependency, where one released apart is on the far side of a version boundary the build moves without asking, and the protocol is what keeps that move from being an outage. A build MAY serve an adapter it ships over any protocol of the group, which is how one becomes reachable out of process without declaring anything.

A protocol carries its version in its name, semantically versioned from `v0.1`. A profile MUST NOT change what a named protocol means; a protocol that changes how rows cross is a new member of the group, and a build MUST NOT read support for one version as support for another (R115 §3.3). Retiring a protocol is a change to this profile and not a decision a build makes.

An adapter a recipe opts into the writer's process (Part 05 §3.9) is bound by this section too: the opt-in decides where a build runs an adapter, not what the adapter supports.

### 11.2 What a build supplies

An adapter MUST declare every value a build supplies it, and a build MUST supply exactly what the adapter declares and MUST NOT decide it from the source's kind (R115 §3.1). Everything supplied is data: a build MUST NOT require an adapter to accept a live handle — an open store, a connection, an object of the implementation's own — because what crosses a process boundary is text, and an adapter with two ways in has one that depends on where it is running.

The vocabulary is closed. Each term names one value and the form it takes, so an adapter and a build written by different people pass the same thing:

| term | what a build passes |
|---|---|
| `root` | the source's location as a URI, which the adapter opens for itself |
| `session_id` | the session's own name, never the integer a build assigns (§11.3) |
| `reference_clock` | the reference clock's row: identifier, rational tick rate, origin |
| `clocks` | one such row per clock declared before this source runs |
| `first_samples` | one record per stream: its name, and the integer its samples start at |
| `units` | one record per unit: the source's label for it, and the identifier assigned |
| `wanted` | the resource IDs the recipe leaves this source owning, so it produces no more |
| `array_location` | a location under the staging area to write an array to (§11.3) |
| an option, by its name | the value the recipe carries under it — a `zone`, an `interval_kind` |

A build MUST resolve each declared name against that list first and the recipe's options second, and MUST refuse a recipe where a name resolves to neither (R115 §3.1). A profile adding a term amends this section.

A build MUST refuse a recipe where a term the list carries cannot be filled, naming the term and the source, and MUST NOT pass such a term absent or empty: `first_samples` needs a source that states them and `units` one that produced them, and an adapter cannot tell a term nobody filled from one whose value is legitimately empty (R115 §3.1).

A build MUST pass a collection as records carrying its key as columns. A mapping's keys are a type the crossing does not keep: an integer key returns as a string, and a compound key does not cross at all.

Some terms belong to a protocol rather than to an adapter. `flight-v0.1` requires `socket`, the address to serve on; `files-v0.1` requires `delivery_root`, the directory to write the delivery into; both `files-v0.1` and `stream-v0.1` require `report_path` where a report is expected (Part 09 §5.8). A build MUST supply whichever terms its adapter's protocol requires, and an adapter MUST NOT declare one — declaring the protocol is what asks for it.

What crosses is one JSON object keyed by the term. A build MUST write it to the command's standard input and MUST close that stream when it has, MUST NOT pass it as an argument, and MUST NOT add any argument to the command the recipe carries (R116 §3.1). An adapter MUST read its standard input to end of file and parse it as that object before it writes any rows, and a build supplies nothing else on that stream. An option appears under `options`, keyed by its name, so no option collides with a term.

An argument list is not the channel because it has a size no profile can raise — 131,072 bytes for one argument on Linux, 32,767 characters for a whole command line on Windows — and a term carrying one record per unit reached 322,799 bytes on a real session, where an adapter's whole object measured 721 against a fixture that had none (R116 §2.1). Standard input carries nothing under any protocol of the group and has no such limit.

The wanted set is a term a build supplies and an adapter MAY act on. A build settles ownership before any source is opened (Part 05 §3.4), so an adapter told what is wanted may extract no more; acting on it is permitted rather than required, because for some sources producing three resources costs what producing all of them costs, and a build cannot tell an adapter that extracted three from one that extracted everything and discarded the rest.

### 11.3 What a delivery states

A delivery carries one table per resource asked for. Which columns that table holds is a statement: an adapter MUST deliver a column wherever any row of that resource carries a value, and an absent column says the source produced no value for it in any row, which is Part 02 §5's presence and nothing else (R115 §3.6). A build MUST NOT read an absent column as saying anything more.

An adapter MUST hand over identifiers as the names its source used and never as numbers, because a writer mints every assigned identifier packet-wide and the numbers do not exist until it has (Part 05 §8). Types, column order, numbering and the declared sort are the build's: it holds the registry and settles all four on arrival.

A resource an adapter owns and has no rows for MUST arrive empty rather than not arriving (R115 §3.10). An empty delivery states that the source had nothing to say; a resource that does not arrive states that the run failed, and a build that cannot tell them apart cannot report either.

An adapter's arrays MUST NOT cross as rows. A dense array crosses as a reference: its `array_asset_id`, the layout the adapter chose — chunking, sharding, codecs, fill value — and a location. Where the packet will own the array, a build MUST supply a location under the staging area (Part 05 §1) and the adapter MUST write the array there and return the reference, so commit moves it by the rename Part 05 §6 already performs. Where the array is external (§8.2), a build supplies no location and the producer returns the URI its source already has.

**A packet-owned array crosses as the bytes themselves.** A build MUST supply `array_location`, one directory per source, since two sources may each deliver an asset of one name and a shared directory would make them one array; the adapter MUST write each array into it as Zarr v3 (§6.1), in a directory named by the array's `array_asset_id` with the suffix `.zarr` (R117 §3.1). A build MUST take that name as the asset's identifier and MUST refuse a delivery where an array arrives that the source's `core.array_assets` rows do not declare, or where a row declares a packet-owned array that did not: an asset whose bytes and whose row disagree about which asset they are is one a build cannot describe.

Nothing else crosses for such an array, and a build MUST NOT require an adapter to state any of it. Every field of its manifest entry is in the array or in the build: `physical_profile` is the array's `zarr_format`, `codecs` its codec chain outermost first and descending through a shard, `size_bytes` and `sha256` the bytes a build digests for anything the packet owns (Part 03 §8.1), and the rest the build's own (R117 §2.2). An adapter delivering an array therefore writes bytes where one delivering rows performs no I/O at all, which is the cost of an array not being records (R115 §3.6).

**A referenced resource crosses as a resource document.** An adapter that delivers one MUST deliver that document with it, under the reserved resource identifier `resources` (§11.4): a JSON object carrying `resources`, an array with one entry per such resource, each a manifest resource entry as Part 04 §5 declares one (R117 §3.2). A build MUST merge each entry into the manifest it writes and MUST NOT require any field but `resource_id` and `uri`, since a writer that cannot reach a URI records nothing (Part 04 §5.2) and `external` is a field a build fills rather than reads. Its shape is published as `registry/resources.schema.json`, and a build MUST refuse a document that does not satisfy it, naming what is wrong, before it writes a manifest: this is the catalog's own content arriving from elsewhere, and a malformed entry merged into a manifest is a packet that misdescribes its own resources (R117 §3.3).

The document is part of the delivery and not a report. A build MUST NOT require a report and MUST NOT fail on one's contents (Part 09 §5.8), so a fact a catalog cannot be written without does not travel in one; a resource that does not arrive is already a failed run (Part 05 §4.4), which is the rule this needs and does not restate. A build MUST NOT count the document among the resources the recipe left the source owning.

### 11.4 The Arrow IPC floor

An Arrow IPC stream carries one schema and an adapter returns many resources, so under `stream-v0.1` the streams concatenate: each ends with the format's own end-of-stream marker, and the resource identifier rides in the schema's key-value metadata under the key `resource_id` (R115 §3.3). That key and two reserved values of it — `end`, and `resources` for the document §11.3 requires of an adapter delivering a referenced resource — are the whole of what this protocol adds to Arrow. A resource identifier is dotted, so no undotted token collides with either (R117 §3.2). A document carried this way travels as text in a single-row table rather than as a column per field, so the manifest's schema stays the one description of an entry.

"Arrow IPC" names a family, so this profile pins one member of it, as §5.5 pins Parquet's compressions. An adapter MUST write uncompressed record-batch bodies at metadata version V5, and MUST send each dictionary whole rather than as a delta against one already sent (R115 §3.3). Compressing buys nothing on a pipe and costs an adapter author a codec in a language whose Arrow binding may not carry one; V5 has been the default since Arrow 1.0, and a delta dictionary is the least evenly implemented part of the format.

An adapter MUST terminate every resource's stream with the end-of-stream marker and a build MUST consume exactly to it, so the next resource's schema begins at the next byte. An adapter that omits one delivers bytes no reader can frame; a build that consumes past one loses every resource after it and reports a truncation on a delivery that finished.

A reader treats end of file as end of stream, so a delivery cut at a message boundary parses clean and cannot be told from a short one. `stream-v0.1` therefore ends a delivery with an empty stream whose `resource_id` is `end`. A build MUST refuse a delivery that did not end with it, and MUST name the last resource it read as the one the adapter died inside rather than the first that never arrived (R115 §3.10). A resource identifier is dotted, so no undotted token can collide with the reserved value.

Where rows travel on standard output they are bytes. An adapter MUST write the stream to a binary handle and a build MUST read one, because a platform translating a line ending corrupts the stream, which then fails as malformed data rather than as an encoding error.

### 11.5 The declaration document

A build reads what an adapter declares before it opens any source, and for a class it reads that by importing the adapter — which this section forbids requiring. An adapter a build cannot import MUST publish its declarations as a JSON document the recipe names, and a build MUST read that document before it launches anything (R115 §3.12).

The document carries what belongs to the adapter and nothing that belongs to the machine: `kind`, `protocol`, `produces`, `states`, `needs` and `consumes`. The command, the root and the options stay in the recipe, because which interpreter is installed where is the recipe author's fact and the resources an adapter can supply is not. Its shape is published as `registry/adapter.schema.json`.

A build MUST treat a document and an importable declaration of the same facts as one declaration, and MUST NOT prefer either where both are present. An implementation shipping both MUST generate the document rather than maintain it.

A build MUST refuse a declaration whose `protocol` names no protocol of a group this profile names, whose `produces` names a resource no loaded registry declares, whose `states` names a field no recipe block carries, or whose `needs` names what §11.2 resolves to neither a term nor an option (R115 §3.12). None of those need the adapter opened or imported.

`states` names the recipe fields a source can state and the values need the source read, so no static document carries them: they travel under `stated` in the run's report (Part 09 §5.8), keyed by the same `block.field` name. An adapter declaring a non-empty `states` MUST return them. A build MUST read a declared field absent from the report as unstated rather than as disagreeing, since a source stating nothing is a fact and not a mismatch (Part 05 §3.6).

### 11.6 Reaching an adapter that must be running

Where a protocol needs the adapter running — `flight-v0.1` does, `files-v0.1` and `stream-v0.1` do not — the protocol MUST say how a build establishes that. `flight-v0.1` says it by connection: a build retries the address it supplied until the socket answers or the adapter's process exits, and reports the exit (R115 §3.9). A readiness line on standard output is weaker, because a build waiting for a line that never comes cannot tell *not yet* from *never* unless it watches the process as well, which is the whole of what retrying already does.

The retry puts one obligation on the adapter: it MUST NOT bind before it can answer `ListFlights`. A build's first call arrives as soon as the socket answers, so an adapter that binds and then extracts serves discovery from a half-built server.

A build that started a process owns it and terminates it once it holds the rows and the report, so an adapter MUST NOT rely on running code after its last response.
