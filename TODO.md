# TODO

Live work first, then measurements worth reusing, then what was settled and when. Reasoning for a
settled item lives in the revision it produced and in git history, not here.

## State of the world

The generated state below is checked by `uv run --project escapewheel-writer python verify.py` —
which is the way to check it rather than by reading this block.

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R144 accepted. R42 and R73 withdrawn. No proposal or draft is open.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
43 tables, 348 columns, 111 references, 77 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
59 conformance packets
<!-- END facts: corpus -->

<!-- BEGIN facts: extensions -->
4 extension registries: aind_opto, aind_unit_qc, dynamic_foraging, vr_foraging
<!-- END facts: extensions -->

Each drawn from columns measured in a real
session rather than invented — see `registry/extensions/README.md`. The conformance corpus carries
one, because R54 §2.4a leaves a packet holding intervals no way not to.

**Phases 0–6 complete.** `escapewheel verify` closes R36 §2.4 and `escapewheel prune` closes R61 §3.
Phase 7 (Iceberg) untouched.

**This is one repository.** It was ten until 2026-09-04; each history was preserved through the
join, so `git log -- revisions/` and `git blame` reach back through it.

### What stands between here and a production trial

1. **Define the publication model.** The current core registry and its meta-schema now identify the
   complete registry-contract development shape as `0.6.0` (Part 02 §9.2). The dependent authority
   work still needs to define the released artifact set, publication state, and identifier
   discipline before a production trial.

---

# Live

## 1. Registry replay should give way to declarative authoring

`registry/build.py` derives the core registry by parsing Part 02's tables and then replaying the
accepted decisions that changed them. Replace it with one reviewed registry document or
deterministically assembled fragments, keep provenance in accepted history and Git rather than in
the registry document, and prove that the migration preserves the released registry bytes or a
defined canonical form. This is ordinary repository maintenance if the published contract is
unchanged; any change to the published form returns through the revision process.

## 2. No template scaffolds an extension project

**Not started.** Writing an extension is now well enough defined to scaffold, and nothing scaffolds
it: the four here were written by hand, and `registry/extensions/README.md` covers *what to model* —
what varies belongs on the row, a source's columns are evidence rather than a schema, deriving a
document from a pydantic model — while saying nothing about how to build and deliver one.

**The template.** Base it on `~/Documents/Code/aind-python-copier-template`, which already carries
the shape: `_templates_suffix: .jinja`, `_subdirectory: template`, copier ≥ 9.0.0, and conditional
`_exclude` blocks for docs, notebooks, a CLI and a `CLAUDE.md`.
`~/Documents/Code/aind-capsule-copier-template` is the other one to read before choosing which to
fork. What it should generate:

- `registry/<namespace>.json`, a skeleton declaring one table with every attribute a column owes,
  and a test running it against `registry/registry.schema.json`;
- an `extract.py` delivering by `files-v0.1`: it reads the build's JSON object of terms from
  standard input and writes `<resource_id>.parquet` into the `delivery_root` it names, beside an
  adapter declaration document (Part 12 §7) for the recipe's `delivery` table;
- an optional self-validation step against the extension's own document (R109 §3.5) and an
  optional run report (R109 §3.6);
- a `[source]` block, with its `delivery` table, and an `[encoding]` block to paste into a recipe.

**What the instructions must state**, because each is a rule an author will otherwise break:

- The document is a registry document in Part 02's format, namespaced (R17 §2, Part 09 §5.2), and the
  packet declares it in the manifest (Part 09 §5.3).
- Every column declares a type, a presence and a role (R2 §5, R48 §2.1); a string column declares
  its vocabulary (R101 §3.1); an identifier declares `carried` or `assigned` (R53 §2.3); a
  session-scoped table carries `session_id` and declares the reference (R88 §2.1).
- Rows arrive with identifiers as the **names** their source used, never numbers: the writer mints
  those packet-wide (R53 §2.5).
- The document **MUST NOT** be derived from the rows it delivers (R109 §3.2). Declare the **union**
  of what the pipeline may emit, as `nullable` — `aind_unit_qc.waveform_metrics` declares 14
  columns and its adapter delivers those its analyzer computed, so an analyzer run without
  `velocity_fits` delivers 12, and the two it lacks say that run did not compute them rather than
  that the extension lacks them.
- The command **MUST** be a function of its inputs (R109 §3.7). Where it cannot be, deliver a file
  produced beforehand instead.
- An encoding exception goes in the recipe's `[encoding]`, never in the schema, because it is a
  fact about one packet's values (R110 §3.4).

**Best practices worth stating beside the rules.** Isolate dependencies however you like — the
command is an argument list, so `uv run`, a pinned interpreter and a container are all just
commands, and that freedom is what R109 §3.1 exists to protect. Print for a person on stdout and
put anything a build should parse in the report file. Do not restate what the build already
derives: rows per table come from the Parquet footer at discovery (Part 05 §4.1).

## 3. A delivered sync source cannot carry the terminal-anchor result

R99 §3.2's terminal-anchor result is per probe clock. The sync source computes it, but the sorter
owns those clock rows, so it is a fact about another source's rows, which no resource carries and
no report key holds. A delivered sync leaves `withheld_first_anchor` and `withheld_last_anchor`
null where an in-process one fills them, and the build says so rather than leaving the packet
quietly poorer.

The build cannot recompute the result, because a withheld anchor never reaches the packet. The
recommended fix is a report key: sync's delivery report (Part 12 §9) carries the result per clock,
and the build stamps it on the clock rows as `_declare_withheld` does in process. It needs a
revision because it adds a report key. A table of sync's own would restate R99's columns, and a
general way for one source to contribute columns to another's rows is more mechanism than one fact
warrants. Nothing needs it while every recipe runs sync in process.

## 4. No code quality audit has run

Asked for on 2026-09-06 and not started. Correctness, interpretability, maintainability, and
above all **which problem domains this project owns**: where a dependency already solves something
well, the code should not be solving it again. The reader's `Location`, the writer's store
abstraction, the registry's generators and the clock arithmetic are the places to look first.

## 5. The repository directory is still `nwb-lake/`

R84 §2.1 renamed the repository and everything inside it moved. The checkout directory did not,
because renaming it mid-session breaks absolute paths in flight and `git mv` cannot rename the
working tree's own root. Both real recipes name absolute paths into it, so this and the
rebuild want doing in one order or the other, not at once.

## 6. Staging both packets to scratch needs a token

`aind-scratch-data` is not public, so `--no-sign-request` does not reach it. Roughly 1.2 GB and
700 MB excluding referenced LFP.

## 7. Parked: R42's write case survives its withdrawal

R42 is withdrawn on the read measurement (§ Settled below), and that stands. What did not fall
with it is the **write** cost: adding a sorting rewrites 650 MB (~48 s, growing with each sorting)
where partitioning writes one member (~4 s, flat).

A revision for that would be most of R42 §2 with a different §1 — the member array as a **MUST**
for a packet-owned prefix, rows as members concatenated in declared order, and R35's bound applied
per member. The ordering rule is *not* optional even without the performance argument: R12's
physical-order check and the 14 uniqueness checks riding on adjacency need a defined row order
across files.

**Not drafted, deliberately.** No session in the corpus has a second sorting, so the win is
hypothetical, and a revision drafted against an unpaid cost is how R42 came to sit proposed for a
week before being withdrawn. R42 §5 records what would reopen it: accumulated sortings, tables
outgrowing one file for other reasons, or multi-session packets making `session_id` partitioning
natural.

## 8. Smaller open items

- **Trial-in-block containment has no consumer.** The measurement below concluded that a trial
  needs no stored parent, and `dynamic_foraging` ships one anyway: `blocks` carries `start_tick`
  and `stop_tick` over 19 rows, and `trials.block_id` is populated in **450 of 450 and 708 of 708**
  rows with no nulls. That is not a contradiction — the measurement compared the *lookup* with the
  blocks given, while what the extension's producer does is derive the blocks, a contiguous-run
  grouping a consumer cannot get from a binary search. The general case, one `core.intervals` kind
  contained by another, arises in no packet: both hold exactly one `interval_kind`. So a reader
  operation waits for something to ask for it.
- **DuckDB's ASOF join is ten times worse than its range join, and nobody knows why.** It was
  expected to be the fix, being the formulation `alignment.aligned_spikes` already uses, and it
  measured 220 s against 21.7 s at a million trials. A follow-up probe timed out at ten minutes on
  100,000 rows, so the cause is unestablished. Nothing depends on it.
- **A second ergonomic surface** for people who avoid both SQL and raw PyArrow: DuckDB relations,
  a polars `LazyFrame` behind an extra, or both. Does not block anything.
- **No conformance variant for R51 or the shape check.** The fixture packet has no array resources
  and no external ones, so exercising either there means introducing an external Zarr plus whatever
  table rows the registry's rules expect of one — a larger change to the shared fixture than the
  checks it would cover. The validator's own tests cover every path. Worth revisiting when the
  fixture next needs an array for another reason.
- **A second trials table from another paradigm** would settle whether an interval's task columns
  belong in core. R54 struck the four Part 02 defined and nothing wrote, so the question is now about
  what an extension carries rather than what core does.
- **Part 02 §5.2's exclusion of `list` has lost its Julia argument.** R3 §2.3 excluded `list`, which
  it calls core Parquet, because Parquet2.jl cannot read one. Every Julia read of a packet now goes
  through DuckDB.jl, which reads lists (R3 §7.3), so what still supports the exclusion is the lower
  implementation floor R3 §2.3 also argues. Worth re-deciding before a table next wants a repeated
  value inline.
- **A nullable identifier's null has no stated meaning.** Nothing obliges an adapter to report a
  value it could not fill, since Part 12 §9's report is a MAY. So a consumer cannot tell
  `core.array_channels.electrode_id` null meaning *this channel maps to no contact* from null
  meaning *I gave up*, and that is true of every nullable reference in the registry. `lfp` now
  refuses rather than writing such a null, and the column is null in **0 of 1,152 and 0 of 960**
  rows of the two packets, so there is no instance to write a rule against. Worth a revision when
  something produces one.
- **A source without `root` records no source file.** R135 §3.4 counts only the roots a recipe
  writes, so a source whose recipe entry omits `root` gets no `core.source_files` row. Undecided.

## 9. Implementation follow-ups

None open. `tables` sources deliver by `files-v0.1`, `aind_unit_qc` is an adapter in
`escapewheel-aind`, every name-minting adapter accepts `prefix`, and every store-reading adapter
accepts `source_cache` and keeps store objects as Part 12 §10 requires.

---

# Measured, for reuse

**Containment, four ways** (2026-09-02, five repeats), on blocks derived from a real session —
708 trials, 18 blocks, disjoint, minimum gap 5,750 ticks — and synthetic data at the same ratio.
Scripts in `/mnt/Data/escapewheel/bench/nesting/`, raw output in `results.txt`:

| trials | blocks | range join | ASOF join | searchsorted | stored column |
|---:|---:|---:|---:|---:|---:|
| **708** | **18** | 1.46 ms | 1.54 ms | **0.02 ms** | 0.60 ms |
| 10,000 | 250 | 5.58 ms | 32.70 ms | 0.07 ms | 1.00 ms |
| 100,000 | 2,500 | 267.68 ms | 2,202.66 ms | 1.02 ms | 3.05 ms |
| 1,000,000 | 25,000 | 21,708.92 ms | 219,594.04 ms | **15.95 ms** | 32.21 ms |

At real scale the lookup is free — 0.02 ms, cheaper than reading a stored `block_id`, because the
search returns indices where the column materialises a string per row. At a million trials it is
16 ms while DuckDB's range join is 21.7 s and its ASOF join 220 s, so the naive SQL is a trap that
springs only at a scale no packet has reached.

**The blocks are taken as given, which bounds what this settles.** `blocks.py` derives them from
the trials — a contiguous run sharing a reward-probability pair — because nothing recorded them
when this was measured. `dynamic_foraging` now does, and its `trials.block_id` is populated in
every row, so R43's "an alignment is a query" holds for the lookup and says nothing about the
grouping that produces the blocks.

Scripts in `/mnt/Data/escapewheel/bench/`: `s3_tires.py`, `s3_backends.py`, `clients.py`,
`duckdb_s3.py`, `s3_full_verify.py`, and `partition/` (`make_parts.py`, `bench2.py`,
`local_window.py`). Both staged prefixes under `s3://aind-scratch-data/galen.lynch/` are removed;
nothing of ours is left in the bucket. Restaging is `aws s3 cp --recursive` of a packet.

**DuckDB, R30 §6's query shapes against `analysis.spike_events`** (a throwaway query first, or
the first query is charged 3.4 s of setup and the comparison inverts):

| query | local | S3 cold | S3 warm | rows |
|---|---|---|---|---|
| `count(*)` whole | 0.03 s | **0.24 s** | 0.09 s | 286,896,563 |
| units + window | 0.04 s | 0.56 s | 0.11 s | 884 |
| 10 s window | 0.04 s | 0.56 s | 0.11 s | 348,913 |
| 24 adjacent units | 0.15 s | 3.38 s | 0.21 s | 572,551 |
| 24 scattered units | 0.15 s | 3.37 s | 0.21 s | 757,259 |

Counting 287 M rows costs 0.24 s — the footer only. Pruning becomes round trips: selective
queries 0.56 s against broad ones 3.4 s. Object cache worth 16x. Cold 6–22x local, warm 1.4–3x.
**The SQL is byte-identical local and remote** — no query rewriting was needed for any of it.

*Harness flaw:* the "scattered units" set strides an unordered `DISTINCT`, so its row count
differs between runs. Timings are unaffected.

**S3 clients**, all agreeing key-for-key on the listing:

| client | list | 1 worker | 8 workers | new dependencies |
|---|---|---|---|---|
| boto3 | 0.102 s | 14.8 MB/s | 79.4 MB/s | botocore |
| s3fs | 0.130 s | 26.8 MB/s | 95.8 MB/s | aiobotocore + botocore + aiohttp |
| pyarrow.fs | 0.099 s | 13.6 MB/s | 79.4 MB/s | none, already required |
| obstore | 0.117 s | **35.4 MB/s** | **100.2 MB/s** | one Rust wheel |

Within 26% once concurrent, so the choice is dependency weight and scheme coverage. `stores.py`
now lives in the validator, with two users and both on the verification side — this package
checks what a manifest claims and the writer establishes it through `verify`. **obstore on merit,
pyarrow.fs on conservatism** if the client is ever revisited.

**R36 verification:** the digest is identical computed from S3 and from local disk
(`3660170e5c3f2205…`), so the canonical member listing is store-independent as intended.
Whole packet, 2,496 objects and 6.83 GB across twelve arrays:

| | list | digest |
|---|---|---|
| S3 | 1.31 s | 88 s |
| local disk | 0.33 s | 75 s (91 MB/s, cold) |

Against a whole-packet build of 1 min 51 s, which is what §2 turns on.

---

# Settled 2026-09-12 to 2026-09-17: the adapter boundary

- **Where a protocol is needed it is `flight-v0.1`** (2026-09-12). A Flight descriptor is the
  format's, so the protocol invents no metadata key, and `ListFlights` and `DoGet` answer discovery
  and the per-resource fetch from Arrow's own vocabulary. An adapter needs a protocol once it is
  released apart from the build.
- **Core ships adapters for standards, not institutions.** Seven adapters stay in the writer:
  `sorter`, `sync`, `openephys`, `harp`, `nwb`, `lfp` and `waveforms`. `escapewheel-aind` holds
  `session`, `video` and `aind_nwb`, moved with `git mv` so `git log --follow` reaches through. It
  registers them through the `escapewheel.sources` and `escapewheel.compensations` entry-point
  groups, and `escapewheel-aind/tests/test_boundary.py` asserts, by parsing imports, that the
  writer imports none of it. A kind is matched by name, so AIND's `session` consumes `aind_nwb` and
  cannot be ordered against the base `nwb`.
- **The NWB reader splits by subclass, not by source.** R108 §3.2 forbids composing a row from two
  sources, and the dialect's columns share rows with the standard ones. So `NWBSource` reads only
  what NWB core 2.9.0 declares, through hook points, and `escapewheel_aind.nwb.AindNWBSource`
  supplies the rest in about 120 lines. `inventory/nwb-adapter-base-and-dialect.md` classifies
  every read: **36** names are base NWB, **17** are one pipeline's, and three conventions show at
  no call site. Two base-reader gaps were repaired: a contact falls back to `(group_name, id)`
  where a file has no `channel_name`, which no NWB version defines, and `core.devices` reads
  `serial_number`, which **0 of 10** real devices set. A per-column dialect mapping was rejected,
  since what differs includes columns becoming rows, and a source needing conversion delivers
  Parquet by `files-v0.1`.
- **`lfp` derives its probe from the series' electrodes**, which belong to one `ElectrodeGroup`,
  rather than parsing a series name NWB does not constrain. The two agree on **10 of 10** real
  series, so no `array_asset_id` moved.
- **`waveforms` reads the sorter's analyzer, not the NWB copy.** The NWB's `waveform_mean` is a
  densified copy of `extensions/templates/average`, keyed by a row `id` that differs from
  `ks_unit_id` in **6,775 of 6,781** and **4,138 of 4,505** rows. The analyzer states the unit ids,
  a sparsity mask keeping **6.7%** of the rectangle, and `return_in_uV`. So the join is the
  build-supplied `units` term, and the sample axis starts at `-ms_before`. `zarr_compat.DenseV2`
  decodes from chunk bytes, which reads a cached `s3://` path and keeps a `#` in a path segment:
  **534 units cut in 15.2 s, 0 missed and 0 blank**. The first evidence measured a SpikeInterface
  0.103.0 sorting no packet uses; the authoritative sortings match their packets at **4,505** and
  **6,781** units.
- **One rule names a contact for all three readers of an electrodes table.** `nwb.contact_ids`
  serves `nwb`, `lfp` and `waveforms`, which had disagreed on the fallback and so could mint one
  contact under two spellings.
- **The three real recipes deliver every AIND kind out of process**, over `stream-v0.1`, each with
  a declaration in the packet's `declarations/`. `session` and `aind_nwb` name
  `reports/<kind>.json`, because a delivered source without a `report_path` states nothing and the
  recipe's declared values stand unchecked, which moved `session_end_time` by 17 minutes in the
  trial run. All three check with **0 errors**. `df-packet` gained the four coordinate resources
  its two coordinate tables referenced.

---

# Settled 2026-09-15

- **R118 is accepted and applied.** Part 03 §5.5's encoding rules are four, over declared order and
  counted repetition, with 12 exceptions for core tables in the writer and 5 entries in the two
  recipes under `/mnt/Data`. Both packets were rebuilt under it the same day and
  promoted. Every table holds the same rows and values, except `core.processing_runs`, whose import
  run records the changed recipe; 213 and 222 columns changed encoding, none sits 1.15x or more off
  its best, and the tables shrank by 686 kB and 272 kB. Both validate at their paths with 0 errors
  and the one `core.clocks.tick_zero_plausible` warning. The packets they replaced, and the
  recipes' R110-era `[encoding]` blocks, were deleted the same day.
- **Julia reads a packet through DuckDB.jl, and the delta encodings stay.** Parquet2.jl, the
  pure-Julia reader, decodes none of `DELTA_BINARY_PACKED`, `DELTA_LENGTH_BYTE_ARRAY`,
  `DELTA_BYTE_ARRAY` or `BYTE_STREAM_SPLIT`, in 0.2.34, the latest registered version, or on its
  `master` branch at the commit of 2026-09-01, so all six tables of `ecephys_786867` tried fail on
  their first delta column. DuckDB.jl 1.5.2 reads every one, in process. R3 §2.3 had weighed DuckDB.jl
  and chosen Parquet2.jl, but R3 §7.3 tested list columns and never an encoding. Of three ways out —
  name DuckDB.jl, drop delta at 1.24x on `core.spike_events.t_tick` and a rebuild of every packet, or
  add delta decoding to a package this project does not own — the first was chosen, since no packet
  changes. `conformance/parquet-probe/readers.py` and `readers.jl` record and reproduce the
  DuckDB.jl result; Part 02 §5.2 and Part 07 §2.2 name no reader and stay true. What the
  choice leaves open about `list` is a smaller item under §8.

---

# Settled 2026-09-14

- **An extension can be checked.** `escapewheel extension check <document> --registry <core>` runs
  the invariants any registry document is held to, which were a script in this repository and are
  now `escapewheel_validator.registry_document`: **31 to 35 per document**, depending on what its
  tables declare. `registry/check.py` imports the same `structural` and `declarations`, so core is
  held to exactly what an extension is and the two cannot drift; its own report is unchanged at 206
  lines. `--packet` reads the core registry a packet embeds (R2 §8) instead of a path, since that is
  what an author has to hand, and `--all` lists the invariants that held as well as those that did
  not. Checking the four shipped extensions is now a test rather than a side effect of their sitting
  beside the script. `escapewheel extension` gains a verb: `draft` is what it did, `check` is new.
- **A build is driven end to end by a test.** `escapewheel-writer/tests/test_build_end_to_end.py`
  writes synthetic sources to disk, names them in a recipe, and runs `session.build` and
  `PacketWriter.commit`, which nothing did: `fixtures/build.py` calls `pq.write_table` directly, so
  every rule about how a packet is *written* was enforced on a path the corpus does not take. Five
  assertions, in **1.1 s** on ten spikes and two probes — the packet commits with 0 errors, a
  clock's name is what its identifier stands for (R95 §3.1), every session-scoped table's
  `session_id` is non-null including the streamed one (R88 §2.3), the encodings are the ones
  `encoding.encodings` chose (Part 03 §5.5), and the records path and the streaming path produce
  identical Parquet for one table. Each was checked by mutation rather than by assertion alone:
  writing the human label into `clock_name`, skipping the streamed session fill, and dropping delta
  encoding each fail exactly one test and the other four pass.
- **Both packets are rebuilt and promoted.** `packet-rebuilt-2` of 2026-09-14 replaced the
  committed original in `/mnt/Data/776259-packet/` and `/mnt/Data/786867-packet/`, and the original
  and the 2026-09-12 intermediate were deleted; each session now holds one packet, at the path its
  recipe's `out` names. Both validate at that path with **0 errors and 1 warning**, the warning
  being `core.clocks.tick_zero_plausible` on a harp counter running from device power-on 167 and 498
  days before its session. What the originals lacked, measured against them before they went:
  **32 and 34 tables against 40**, with calibrations, coordinate frames and their axes, electrode
  and unit coordinate values and clock phase steps absent entirely, and
  `core.clock_observation_intervals` holding **1 row where the rebuild holds 13 and 11** (R98 §2.1).
  That last defect made a derived table wrong rather than thin: `core.spike_events` is identical in
  both, so the originals' `analysis.spike_events` had silently dropped **19,704 and 9,398 spikes**
  falling outside a window that had one row.
- **A channel index resolves through the run's kept list.** `escapewheel_reader.channels` offers
  what Part 02 §12.2 requires of a consumer: `kept_channels` reads `core.sorting_run_channels`,
  `electrode_at` performs the lookup over one index or an array of them, and
  `runs_without_channels` names the runs no index can be resolved for. A run declaring no channels
  raises `UnresolvableChannelIndex` rather than falling back to `core.electrodes`, and the
  exception's `channels_declared` separates that from an index outside a list the run did declare.
  Measured on the two rebuilt packets: **3,375 of 4,510** indices in `ecephys_776259` and **1,651
  of 3,813** in `ecephys_786867` name a different contact than the contact list would, eleven of
  twelve runs and seven of ten having dropped channels, one diverging at index 2. One run dropped
  three contacts from the tail and shifts nothing, which is how the convention stayed invisible.
- **The source cache lands where the build names it.** `source_root` passed `cache_storage` nested
  under `simplecache={...}`, the chained-URL form fsspec documents and which UPath parses and then
  drops: the filesystem came back with `storage` at a `tempfile.mkdtemp()` while the directory
  `source_root` had just created stayed empty, so every fetched object went to tmpfs — RAM a cgroup
  cap does not bound, which is what killed two builds capped at 24 GB and 8 GB. The option goes at
  the top level with the target's options under the protocol name. `escapewheel import` places the
  location in the packet's parent directory by default and supplies it as `source_cache` (R142).

---

# Settled 2026-09-10

- **The actor audit is complete.** All **176 normative sentences that name an actor** were read
  against R111 §3.1's line — a reader is bound by what it returns, a consumer by what it concludes.
  **Seven were repointed**: Part 01 §3.9's reader became a consumer, Part 00 §5 and Part 06 §1's
  consumer became a writer, Part 03 §6 and Part 05 §11 left `implementation` for a validator and a
  writer, and Part 09 §8's five anti-patterns split across three actors. Every `build` clause was
  already correct and 36 of 37 consumer clauses were, which is the result worth keeping. The
  distribution now runs writer 75, consumer 37, validator 26, build 24, reader 20, and
  **implementation 2**.
- **The encoding residual is closed.** The item recorded **59 columns more than 15% off the best
  choice, worth about 400 kB**; R110 delivered all three predicted fixes and left **five columns and
  12.6 kB**, every one in `aind_unit_qc.metrics` — an extension's table, which is what R110 §3.4
  exists for. Three recipe declarations close it: `firing_range` and `amplitude_median` take the
  dictionary (1.30x and 1.32x over plain), `isi_violations_count` plain (1.15x). Both recipes carry
  them and `Recipe.encoding_problems` returns clean, leaving **zero columns over 15%** in either
  packet.

---

# Settled 2026-09-09

- **R89 through R108 are accepted and applied.** The item that stood here said R89 to R93 were
  drafted and none accepted; twenty of them landed since. `revisions/drafts/` is empty.
- **`vr_foraging.json` is drafted and shipped.** The extension carries `sites`, `site_odors` and
  `sessions`, with the `(session_id, site_id, odor_channel_index, concentration)` child table R3
  §2.1 forces, `odor_channel_index` as a `structural_index`, and the eleven ordinals within a scope
  declared `sequence_position` as R48 distinguishes. Units are on the columns rather than in prose,
  which is what R56 was drafted against.
- **`core.events.payload` no longer smuggles `trial_id`.** The NWB source stops writing it, and the
  comment where it did records that R11 §5 struck the column. Payload now travels only where the
  stream's data varies.
- **An interval's task columns are gone from core.** R54 struck the four Part 02 defined and nothing
  wrote, so `choice`, `rewarded`, `stimulus_id` and `condition_id` appear nowhere in the registry.
- **`registry/tables.html` is tracked.** The note saying it was deliberately untracked is stale.
- **The recipes no longer say `owns` where two sources each hold part.**

---

# Settled 2026-09-03

- **The extension mechanism, end to end.** A recipe names extensions by id (installed, via the
  `escapewheel.extensions` entry point) or by path; `PacketWriter` resolves a resource against core
  then extensions; a packet carries `extensions/<id>.json` and `layer: "extension"` entries;
  the validator generates checks with no per-extension code and reports them apart from core.
  Three at once is three times one — tested.
- **A source may be files.** `kind = "tables"` reads Parquet that already exists, optionally after
  running a `command` — an argument list, not a shell, with no opinion about environments, so
  nothing requires uv. Rows arrive as **names** and the writer numbers them, which is what lets an
  adapter run outside this process at all. An extension can now be *entirely data*: a JSON
  document and some Parquet, nothing installed and so nothing to rot.
- **`escapewheel.sources` entry point**, for the case that genuinely needs `Context`. Built-ins are
  consulted first so a plugin cannot shadow `sorter`; a broken one is skipped with its reason.
- **`escapewheel extension`** drafts a registry from Parquet. It writes no role, so the draft does
  **not** validate until a human finishes it — the first version guessed and the draft validated,
  which a test asserting it should not is what caught.
- **The invariant, written down:** an extension declares; it never ships code on the read path.
  The only code it may require is a source adapter, only to write, at the import boundary.

# Settled

- **R53 — identifiers are `int32`.** Measured: 10.2x on a join, 13.8x on selecting 24 units, 5.3x
  on `ORDER BY`, parquet 1.1% smaller. 96 assigned, 14 carried, 14 `*_name` columns. The reader
  needed no change at all, being type-agnostic. Migration is regeneration.
- **R52 — packet-owned resources record a digest**, and `--checksums` recomputes them. 0.60 s for
  1,209 MB, 0.5% of a build. Whole-file, not per-row-group: Parquet cannot be appended to, so
  "which pages moved" is not a question the format can be asked.
- **R56 — a column declares its unit and its clock.** `core.clock_anchors` carried two coordinate
  columns on different clocks, distinguished only by a description, with `parent_clock_id` not
  even a column of that table. Seven columns now declare their context; `check.py` verifies it
  resolves.
- **R17 exercised, then plumbed.** `registry/extensions/dynamic_foraging.json`, 17 checks with no
  per-extension code, validated and reported apart from core. A recipe and the writer now carry
  one end to end.
- **`escapewheel verify` — Phase 6.** Records what is true once the bytes land, as a new packet
  version with both manifests retained. 208 members with 208 store digests in 1.2 s against S3.
- **`pkt.table()` reads a remote table**, through `pyarrow.fs`. Schema 0.80 s, 6,781 rows 0.52 s.
- **Five defects the work surfaced.** `core.media_frames.media_asset_id` referenced nothing (the
  class R46 fixed sixteen of, missed by its own sweep). A foreign key was numbered in its own map,
  so `parent_clock_id` and `clock_id` diverged and the parent chain named a clock that does not
  exist — caught by the conformance corpus. Numbering depended on staging order. A damaged Parquet
  file crashed the ordering scan instead of producing a finding. And a vendored meta-schema went
  stale for the third time, now fixed by making it a build artifact `check.py` compares.

## Earlier, 2026-09-02

- **R53 accepted and implemented** — identifiers are `int32`. Measured: 10.2x on a join, 13.8x on
  selecting 24 units, 5.3x on `ORDER BY`, parquet 1.1% smaller. 96 assigned, 14 carried, 14
  `*_name` columns. Registry 292 → 306 columns, 70 → 71 references. Writer, fixtures and the
  corpus regenerated; the reader needed no change at all, being type-agnostic about identifiers.
- **R17 exercised** — `registry/extensions/dynamic_foraging.json`, 17 checks with no
  per-extension code, `trials` keyed to `blocks` by column rather than containment join.
- **Three defects the work surfaced.** `core.media_frames.media_asset_id` referenced nothing, so a
  frame naming an asset that does not exist validated clean — the class R46 fixed sixteen of,
  missed by its own sweep. A foreign key was numbered in its own map, so `parent_clock_id` and
  `clock_id` diverged and the parent chain named a clock that does not exist. And numbering
  depended on the order tables were staged in.

- **R52 accepted and implemented.** Every packet-owned resource records a `sha256` at commit,
  and `--checksums` recomputes them: a mismatch is an error, and a resource recording none is
  reported rather than passed over. 0.60 s for 1,209 MB, 0.5% of a build. Settled whole-file over
  per-row-group — Parquet has no append, so "which pages moved" is not a question the format can
  be asked, and its page CRC32 is a corruption detector a rewritten file passes (0.06% of bytes,
  measured, shelved).
- **`escapewheel verify` — Phase 6.** Reaches a store once the bytes have landed and records what is
  there, as a new packet version with both manifests retained. Three levels (`size`, `members`,
  `sha256`); validation narrowed to level 3 with `scan` and `recheck` empty, for the reason an
  amendment narrows them to what it wrote — here that is nothing. It also fills in a packet-owned
  digest missing from anything committed before R52. Verified against `s3://aind-open-data`: 208
  members with 208 store digests in 1.2 s.
- **`pkt.table()` reads a remote table**, through `pyarrow.fs`, which pyarrow ships — no new
  dependency. Credentials stay the caller's (R14 §2.3). Schema 0.80 s, 6,781 rows 0.52 s against
  S3. R14 §2.3's warning is unaddressed and still stands: an external table's rules cannot run at
  all when it is unreachable.
- **The two array shape paths are unified.** The external check compared rank and axis lengths
  where the packet-owned one compared only rank, though an owned array's shape is already in hand.
- **Column names are checked, standing** — R50 §5's last open item. Nine conventions over 292
  columns; R48's `role` makes seven of them exact rather than heuristic, and they flag nothing.
  Five exceptions are declared with reasons (`offset` ×3, `n_spikes`, `size_bytes`), and a stale
  exception fails as loudly as a new violation.
- **A damaged file is a finding, not a traceback.** Found while testing R52: flipping one byte in
  a Parquet file crashed the ordering scan with a ZSTD error. It now steps its iterator, so a
  decompression failure becomes `resource.unreadable` — and stays streaming, because materialising
  287 M rows of key columns is the 26 GB that scan exists to avoid.

- **R51 accepted and implemented.** `members` on an external prefix, `store_digest` per member,
  `validate --store-digests` as the level between listing and reading, and `verify = "members"` in
  the writer. Its evidence was corrected first: 2,394 of 2,496 members are single-part, not 208 of
  208, because the largest array has 102 chunks uploaded multipart — which turned §2.3's skipped
  count from a nicety into what stops a clean pass on an array half unchecked.
- **The writer's `verify` default stays `size`**, on measurement: 75 s local and 88 s from S3 to
  digest, against a 1 min 51 s build. A digest is a publication cost (§2), not a per-build one. The
  hollow `external.verified` that made that unsafe is fixed — it now names what it compared, and
  reports what it had nothing to compare against.
- **External arrays get a shape check.** Rank against `core.array_dimensions` and axis length
  against a coordinate table keyed by `(array_asset_id, axis_index)`. Free — the metadata document
  was already read for codecs. This is what catches a change that actually invalidates the packet;
  a content digest catches one that does not, since the packet claims nothing about an array's
  values.
- **R42 withdrawn.** Read case measured negative in both engines; pyarrow's apparent win is scan
  parallelism, reproducing at the same ratio on local disk with no round trips. Write case parked
  above.
- **`escapewheel init` can draft an `lfp` source**, and `LFPSource.offers` reports
  `core.array_channels`. Between them, why no recipe had ever set `verify`.
