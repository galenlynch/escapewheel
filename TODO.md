# TODO

Live work first, then measurements worth reusing, then what was settled and when. Reasoning for a
settled item lives in the revision it produced and in git history, not here.

## State of the world

Last checked 2026-09-09, by `python verify.py` — which is the way to check it, rather than by
reading this block. Everything below is what that command reports.

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R111 accepted. R42 and R73 withdrawn. No draft is open.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
43 tables, 351 columns, 111 references, 77 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
30 conformance packets
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

1. **Package a second session.** Every adapter has been developed and validated against exactly
   one, `ecephys_786867`. R59 already measured that `ecephys_776259` emits `ccf_id`/`ccf_acronym`
   where 786867 emits `brain_region_id`, so this is where the next defects are.
2. **Decide what `registry_version` is for.** Held at `0.1.0` while the schema moves; two packets
   claiming one version with incompatible schemas is what the field exists to prevent. Free to
   settle now, expensive once anyone outside holds a packet.
3. **Run the compliance scan against the implementation.** The equivalent against the spec found
   ten missing rules; nothing has run it against the registry, writer and validator.

---

# Live

## 1. Both packets are rebuilt, and not yet swapped in

Each sits in `packet-rebuilt/` beside the original, which is untouched. Committed with **0 errors
and 0 warnings**: `ecephys_776259` in 467 s with 286,896,563 spikes, `ecephys_786867` in 296 s with
7,570,450 media frames. Replacing the originals is a separate decision, governed by R32's amendment
discipline and `escapewheel prune`.

What the rebuild corrected, measured on the committed bytes rather than predicted:

| | before | after |
|---|---|---|
| `core.subjects.subject_name` | `786867` in **both** packets (R87 §1) | `776259` and `786867` |
| `species` | null | `Mus musculus`, from `subject.json` |
| `sex` | `Male`, outside R101 §3.9's closed set | `male` |
| clock windows | 1 of 13, and 1 of 11 (R98 §2.1) | 13 of 13, 11 of 11 |
| `animal_response` | `0`, `1`, `2` with the key elsewhere | left/right/no_response, R106 §5's counts exactly |
| coordinate frames | — | `ccf` and `probe`, five axes named as R105 §5 said |
| calibrations | — | 3 from `rig.json`, R89's first real rows |

**R68's prediction is confirmed against real data.** `core.media_frames` is **0.43 MB** against the
**0.40 MB** R68 §5 predicted, down from 11.73 MB, with `pts` at **0.04 bits/row** on
`DELTA_BINARY_PACKED`. The 0.03 MB over is R88's `session_id`, which R68 predates.

## 1a₀. Five writer bugs, all one shape

Every blocker the rebuild hit was an accepted revision implemented on **one code path and not the
other**, and no packet had been built since to notice:

| revision | what drifted |
|---|---|
| R95 §3.1 | `Clock.record` wrote a human label into `clock_name`, so no recipe spelling resolved |
| R96 §3.4 | the materializer read `spike_events.clock_id` after it was struck |
| R88 §2.3 | the central `session_id` fill read the session out of a table staged last |
| R98 §3.1 | the sorter never claimed the twelve clock windows only it knows |
| R88 §2.3 | `add_batches` never applied the fill at all, so a streamed table had nulls |

Two of the five are `add()` against `add_batches()`. The records path and the streaming path have
drifted apart and nothing compares them, which is a sharper statement of §1b than could be written
before: the pair is where a rule gets implemented once and forgotten once.

## 1₊₊₊. An extension copier template, and the instructions to go with it

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
- an `extract.py` matching the shape a recipe's `command` invokes — an argument list run in the
  source root, writing Parquet to declared paths;
- an optional self-validation step against the extension's own document (R109 §3.5) and an
  optional run report (R109 §3.6);
- a `[source]` block and an `[encoding]` block to paste into a recipe.

**What the instructions must state**, because each is a rule an author will otherwise break:

- The document is a registry document in `02`'s format, namespaced (R17 §2, `09` §5.2), and the
  packet declares it in the catalog (`09` §5.3).
- Every column declares a type, a presence and a role (R2 §5, R48 §2.1); a string column declares
  its vocabulary (R101 §3.1); an identifier declares `carried` or `assigned` (R53 §2.3); a
  session-scoped table carries `session_id` and declares the reference (R88 §2.1).
- Rows arrive with identifiers as the **names** their source used, never numbers: the writer mints
  those packet-wide (R53 §2.5).
- The document **MUST NOT** be derived from the rows it delivers (R109 §3.2). Declare the **union**
  of what the pipeline may emit, as `nullable` — `aind_unit_qc.waveform_metrics` declares 13
  columns where the extraction delivers 10, and that difference is what says a run did not compute
  `half_width` rather than that the extension lacks it.
- The command **MUST** be a function of its inputs (R109 §3.7). Where it cannot be, deliver a file
  produced beforehand instead.
- An encoding exception goes in the recipe's `[encoding]`, never in the schema, because it is a
  fact about one packet's values (R110 §3.4).

**Best practices worth stating beside the rules.** Isolate dependencies however you like — the
command is an argument list, so `uv run`, a pinned interpreter and a container are all just
commands, and that freedom is what R109 §3.1 exists to protect. Print for a person on stdout and
put anything a build should parse in the report file. Do not restate what the build already
derives: rows per table come from the Parquet footer at `05` Stage 1.

## 1₊₄. Audit the clauses that already name an actor

**Queued, with a method and a trigger.** R111 defines writer, reader, validator and consumer and
fixes the 45 clauses that named neither an actor nor the part they constrain. It audits none of the
**146 normative sentences that already name one**, and its §6 records that as open — but an `Open`
section is a record rather than a queue: **72 of 110 accepted revisions carry one, and 13 later
revisions have ever reached back into one**, always where evidence forced the question (R64 into
R58 §4 once both packets carried a probe frame; R70 into R68 §5 once its premise failed for
referenced media). An item with no trigger does not acquire one, which is why this sits here too.

**The method.** Read each clause and ask whether the obligation is about what a reader **returns**
or what a consumer **concludes**; repoint it where the answer disagrees with the noun. Same for the
writing side, where a build is one run of a writer (R111 §3.2), so the question is whether the
obligation belongs to the run or to whatever performs it.

**The measured starting point.** §2.2's finding is that the split already follows the part — `01`
binds 19 clauses to a consumer and 2 to a reader, `03` binds 6 to a reader and none to a consumer —
so an actor out of place for its part is the cheap test. It returns **10 suspects**, of which seven
are correct on reading and **three are arguable in both directions**:

- `01` §7 — "a **reader** MUST NOT assume any base beyond what the origin declares" reads as
  interpretation until R3 §6 and R48 make base conversion the reader's job at the boundary.
- `00` §5 and `06` §1 — "A **consumer** MAY delete and recompute any of them" sits oddly, no
  consumer mutating a packet, though each sentence before it already states the artifact fact.

**The trigger.** The next revision that moves an obligation across `05` §10's two conformance
classes, since a misattributed actor is exactly what corrupts that boundary, and R111 §3.2 is what
made it decidable in the first place.

## 1a. The packets' physical layout and encoding

**Not started.** Several tables have changed shape substantially — R105's four coordinate tables at
74,223 value rows, R81's collapse of unit identity, R88's `session_id` on every session-scoped
table, R83's `core.sorting_run_channels`, R99's phase steps — and a rebuild is the moment to check
what Parquet actually does with them rather than what it was assumed to do.

R68 §1.3 is the precedent and the method: `core.media_frames.pts` was **96.9%** of its table because
a column declaring nothing else gets dictionary encoding, and a monotonic ramp of 7.5 M values is
its worst case. That closed without a revision, the writer's choice being the defect. Worth checking
per table: which encoding each column got, whether a sort makes a column compress away as R88 §4
measured for `session_id` at 1.0005x, and whether any row group is small enough that its footer
costs more than its rows.

## 1a₁. The corpus proves the format and not the writer

**Found by the rebuild.** Two accepted revisions had left the writer unable to build any packet at
all, and neither 448 tests nor 28 conformance packets saw it:

- `Clock.record` wrote a human label into `core.clocks.clock_name`, which R95 §3.1 defines as what
  `clock_id` stands for. Nothing could resolve a recipe's `harp` back to a clock, so materializing
  `analysis.spike_events` raised `NotAligned`. R53 is what exposed it — making `clock_id` an integer
  retired the path where the identifier *was* the string.
- `materialize.spike_events` read `core.spike_events.clock_id`, which R96 §3.4 struck in favour of
  §3.3's hop through `core.units.clock_id`, and died on a `KeyError`.

Both are on paths `fixtures/build.py` does not take: it writes rows directly rather than through
`Clock.record`, and the corpus has no packet whose `analysis.spike_events` the materializer derived.
So the corpus proves that an implementation agrees about the **format** and proves nothing about the
**writer**, which is where twenty-one revisions of drift accumulated unseen.

**Queued to work on**, and two more instances landed on 2026-09-10, both of the same shape.

- Three test fixtures carried columns the registry does not declare — `core.array_assets` rows with
  `name` and `kind`, where the table declares `array_asset_name` and no `kind` at all, and a
  `core.clocks` row with `name` for `clock_name`. `PacketWriter.add` documented such keys as ignored
  and dropped them, so an array asset went nameless through three tests for as long as they have
  existed. It refuses them now, and that refusal protects nothing in `fixtures/`.
- `fixtures/build.py` calls `pq.write_table` directly and never constructs a `PacketWriter`, so no
  corpus packet passes through the encoding rules at all. Measured: `core.spike_events.t_tick` is
  `RLE_DICTIONARY` in every corpus packet, which is the encoding R68 §3 wrote its SHOULD against and
  `03` §5.5 now tells a writer not to use.

The second is the sharper statement of the whole item. Every rule this repository has added about
how a packet is *written* — encodings, assigned identifiers, session fill, physical order — is
enforced on a path the corpus does not take, so the corpus can pass forever while the writer drifts.

**The corpus is not where this gets fixed, and that is settled rather than open.** 29 of its 30
packets are `valid` deliberately corrupted — `null_required` sets a required column to `None`,
`orphan_fk` points a row at a clock that does not exist, `unsorted_spikes` swaps two rows out of
order — and refusing exactly those corruptions is what `PacketWriter` is for: `unsorted_spikes`
raises `OrderViolation` while staging, and the other two fail Tier 1 at commit. `fixtures/build.py`
writes Parquet directly because that is the only way to produce a packet the writer would never
emit. Only `valid` could be built through the writer, and one packet is a test rather than a corpus.

The coverage says where to put that test. `clock.py` is at **95%** and `materialize.py` at **85%**,
so both modules that broke were covered and broke anyway; `session.py`, which drives a build — the
source loop, the harvest, the two staging paths — is the least covered module in the package at
**68%**, and its uncovered lines are that loop. Both bugs were interface mismatches between modules
that each pass their own tests, which is what an end-to-end test catches and a unit test cannot.

So the work is one test in `escapewheel-writer/tests/`: a small recipe with synthetic sources, run
through `session.py`, asserting the packet it produces — including that its encodings are the ones
`03` §5.5 asks for, which is the assertion no corpus packet can make. Sized at an afternoon, not a
restructuring, and best done after the two open drafts are accepted, since it would assert what they
define and a test may not cite a draft any more than a revision may.

## 1a₃. What is left on encodings, after the rule landed

The rule and its exceptions catch every large case; **59 columns remain more than 15% off the best
choice, worth roughly 400 kB across both packets**, and I stopped rather than chase them:

- **High-cardinality floats prefer plain to a dictionary** by 1.3-1.8x — `axis_value` in both
  coordinate child tables, `unit_quality_labels.confidence`, and most of `aind_unit_qc.metrics`.
  A blanket rule is measured wrong in the other direction: `metrics.presence_ratio` and
  `sliding_rp_violation` prefer the dictionary by 1.77x, so this wants either per-column exceptions
  or a cardinality test, and neither is worth 400 kB yet.
- **`core.unit_electrodes.electrode_id`** prefers plain to the dictionary by 1.7x, being a trailing
  key component.
- **`aind_unit_qc.metrics.num_spikes_used`** wants delta, 1.7x, and no rule reaches an extension's
  columns.

The reason to record rather than fix: the packet is 1.76 GB and the residual is 0.02% of it. What
made the first pass worth doing was 37 columns at 5x to 79x, not the tail.

## 1a₂. The source cache defaults onto tmpfs

**Found by the rebuild, twice.** `sources/store.py`'s `cache_directory()` returns
`$TMPDIR/escapewheel-source-cache`, defaulting to `/tmp` — which on this machine is tmpfs, so every
object fetched from an S3 asset is held in **RAM that a cgroup cap does not bound**. Two builds of
`ecephys_786867` were killed for system memory pressure while capped at 24 GB and then 8 GB, because
the cap never applied to the pages that mattered.

The cache itself is right: `store.py` measures that an adapter reads `spikes.npy` twice and that the
second read costs another 344 MB over the network. What is wrong is where it lands by default, and
the honouring of `TMPDIR` is what makes the workaround one variable — `TMPDIR=/mnt/Data/tmp`.

Worth deciding whether a default that is RAM on any machine with a tmpfs `/tmp` is the right one, or
whether the cache should sit beside the packet as the materializer's scratch already does
(`dir=packet.root.parent`). The two temp locations in one build already disagree.

## 1b. A code quality audit of the whole project

Asked for on 2026-09-06 and not started. Correctness, interpretability, maintainability, and
above all **which problem domains this project owns**: where a dependency already solves something
well, the code should not be solving it again. The reader's `Location`, the writer's store
abstraction, the registry's generators and the clock arithmetic are the places to look first.

The writer's arbitration layer is the newest candidate. `STATES`, `PREFERRED`, `SHARED` and
`RECIPE_SUPPLIES` are four tables consulted in different orders by `_resolve_ownership` and
`_note_unclaimed`, which is how they came to disagree about what a preference means — R108 §2.2
measures three entries where one reads the table and the other does not. One relation, derived from
each adapter's `PRODUCES`, would make every arbitration rule a query over it and make a stale entry
a failure rather than a silence; `core.unit_electrodes` sat in `PREFERRED` uncontested until R108
§3.4 struck it. Not a query engine: the relation is dozens of rows, and what SQL buys in
`rules.json` is that the queries are authored outside the code, which is not true here.

## 2. `registry_version` — still `0.1.0`

Unchanged through R48, R53's string-to-int32 change, R56, R81, R83 and every revision since. Two
packets claiming one version with incompatible schemas is what the field exists to prevent, and it
is preventing nothing. Free to settle while nobody outside holds a packet, and free to batch into
the rebuild. The four extension registries do bump: `dynamic_foraging` is at 0.3.0 and the other
three at 0.2.0.

## 2b. The repository directory is still `nwb-lake/`

R84 §2.1 renamed the repository and everything inside it moved. The checkout directory did not,
because renaming it mid-session breaks absolute paths in flight and `git mv` cannot rename the
working tree's own root. Both recipes name absolute paths into it, so this and the rebuild want
doing in one order or the other, not at once.

## 2c. Staging both packets to scratch needs a token

`aind-scratch-data` is not public, so `--no-sign-request` does not reach it. Roughly 1.2 GB and
700 MB excluding referenced LFP.

## 3. Nesting: containment is cheap, but not in SQL

**Measured 2026-09-02**, five repeats, on blocks derived from a real session (708 trials, 18
blocks, disjoint, minimum gap 5,750 ticks) and synthetic data at the same ratio:

| trials | blocks | range join | ASOF join | searchsorted | stored column |
|---:|---:|---:|---:|---:|---:|
| **708** | **18** | 1.46 ms | 1.54 ms | **0.02 ms** | 0.60 ms |
| 10,000 | 250 | 5.58 ms | 32.70 ms | 0.07 ms | 1.00 ms |
| 100,000 | 2,500 | 267.68 ms | 2,202.66 ms | 1.02 ms | 3.05 ms |
| 1,000,000 | 25,000 | 21,708.92 ms | 219,594.04 ms | **15.95 ms** | 32.21 ms |

**At real scale containment is free** — 0.02 ms, cheaper than reading a stored `block_id`
column, because the join returns indices where the column materialises a string per row. R43's
"an alignment is a query" holds, and no parent column is needed.

**At scale, neither SQL formulation is usable.** The operation is 16 ms at a million trials;
DuckDB's range join takes 21.7 s and its ASOF join 220 s. **The ASOF result contradicts the
prediction** — it was expected to fix the range join, being the formulation the reader already
uses to assign a spike to its preceding event, and it is ten times worse. A follow-up probe to
find out why timed out at ten minutes on 100k rows, so **the cause is not established.** Worth a
separate look; the conclusion does not depend on it.

**What follows:** the reader should own containment as an operation, the way it already owns
`aligned_spikes` rather than telling callers to write the join. The naive SQL is a trap that only
springs at a scale no packet has reached yet.

`dynamic_foraging.blocks` now declares that blocks may not overlap, which is what makes the
binary search sound: a trial inside two blocks has no containing block. Scripts in
`/mnt/Data/escapewheel/bench/nesting/` with the raw output in `results.txt`.

## 4. Parked: R42's write case

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

## 5. Smaller, still open

- **A second ergonomic surface** for people who avoid both SQL and raw PyArrow: DuckDB relations,
  a polars `LazyFrame` behind an extra, or both. Does not block anything.
- **No conformance variant for R51 or the shape check.** The fixture packet has no array resources
  and no external ones, so exercising either there means introducing an external Zarr plus whatever
  table rows the registry's rules expect of one — a larger change to the shared fixture than the
  checks it would cover. The validator's own tests cover every path. Worth revisiting when the
  fixture next needs an array for another reason.
- **A second trials table from another paradigm** would settle whether an interval's task columns
  belong in core. R54 struck the four `02` defined and nothing wrote, so the question is now about
  what an extension carries rather than what core does.

---

# Measured, for reuse

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
- **An interval's task columns are gone from core.** R54 struck the four `02` defined and nothing
  wrote, so `choice`, `rewarded`, `stimulus_id` and `condition_id` appear nowhere in the registry.
- **`registry/tables.html` is tracked.** The note saying it was deliberately untracked is stale.
- **The recipes no longer say `owns` where two sources each hold part.** See §1.

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
