# TODO

Live work first, then measurements worth reusing, then what was settled and when. Reasoning for a
settled item lives in the revision it produced and in git history, not here.

## State of the world

Last checked 2026-09-04, by `python verify.py` — which is the way to check it, rather than by
reading this block. Everything below is what that command reports.

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R86 accepted. R42 and R73 withdrawn. R87 proposed and not binding.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
35 tables, 308 columns, 76 references, 68 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
27 conformance packets
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

## 1. R87 is drafted and not accepted

Only the user moves a revision from Proposed to Accepted. R85 and R86 were accepted on
2026-09-06 and are applied.

- **R87 — A Recipe May Not Contradict a Source It Reads.** Its check is already implemented and
  tested (3 tests in `test_session_extent.py`), because it caught a live bug: the 776259 recipe
  declared `subject_id = "786867"`.

Neither packet has been rebuilt against R85, so `core.devices.parent_port` is null in both. The
column is nullable and both remain conforming; the values arrive with §2's rebuild.

## 1a. A code quality audit of the whole project

Asked for on 2026-09-06 and not started. Correctness, interpretability, maintainability, and
above all **which problem domains this project owns**: where a dependency already solves something
well, the code should not be solving it again. The reader's `Location`, the writer's store
abstraction, the registry's generators and the clock arithmetic are the places to look first.

## 2. `ecephys_776259` needs rebuilding, and R86's evidence depends on it

Its recipe is corrected in `[subject]` and **not in `[session]`**, where `subject_id` still reads
`786867`; both need the true value before the rebuild. The packet still names subject `786867` in
`core.subjects.subject_name`, and nothing else about it is stale — its session times are the true
April ones, because the session source supplies them, and it reads its sorted asset from S3.

R86 §2.2 was corrected before acceptance and no longer depends on this: it states **6 of 13**
name columns colliding and excludes `subject_name` explicitly, naming the recipe defect as the
only reason the two packets agree on a value. The rebuild removes the collision and changes
nothing in the revision.

## 2a. `registry_version` — still `0.1.0`

Unchanged through R48, R53's string-to-int32 change, R56, R81 and R83. Two packets claiming one
version with incompatible schemas is what the field exists to prevent, and it is preventing
nothing. Free to settle while nobody outside holds a packet, and free to batch into any rebuild.

## 2b. The repository directory is still `nwb-lake/`

R84 §2.1 renamed the repository and everything inside it moved. The checkout directory did not,
because renaming it mid-session breaks absolute paths in flight and `git mv` cannot rename the
working tree's own root.

## 2c. Staging both packets to scratch needs a token

`aind-scratch-data` is not public, so `--no-sign-request` does not reach it. Both packets are
current apart from 776259's subject; roughly 1.2 GB and 700 MB excluding referenced LFP.

## 3. `vr_foraging.json` — draftable now, not drafted

**In progress when this stopped.** I had said the inventory's prose was not enough to draft from
without inventing types. That was wrong: `Aind.Behavior.VrForaging.Packaging`'s `models.py` carries
the `Site` and `SessionMetadata` pydantic models with types, optionality **and units**, read via
`gh api repos/AllenNeuralDynamics/Aind.Behavior.VrForaging.Packaging/contents/src/aind_behavior_vr_foraging_packaging/models.py`.

What the source settles:

- **`odor_concentration` is per olfactometer channel** — *"the concentration levels of each odor
  channels (unit: percentage)"*. So the child table R3 §2.1 forces is
  `(session_id, site_id, odor_channel, concentration)`, `odor_channel` a **`structural_index`**
  (0-based, converted at a 1-based boundary per R3 §6) and `concentration` a `float64`
  with `unit: "%"`.
- **Every unit lives in a prose description** — centimeter, second, percentage, milliliter, cm/s.
  Independent evidence for R56: a real pipeline hand-writing units into English because there was
  nowhere else to put them. This would be the first extension carrying `unit` on live data.
- **The eleven index columns are `sequence_position`, not `structural_index`** — `site_index`,
  `site_index_in_patch`, `site_index_by_type`, `patch_index_in_block`, and so on. They are
  ordinals within a scope, which R48 distinguishes.
- **Five columns are derived** — `reward_delay_duration` is literally
  `reward_onset_time - choice_cue_time`, `last_stop_duration` likewise. R3 §3.0 says a table does
  not restate what the data declares, so they are candidates to strike.
- **`has_forced_rewards` references the events table in prose** —
  *"See events table (event_name='ManualWaterDelivery')"*.
- **`last_stop_time` is renamed to dodge NWB** — the source comment says *"While this variable
  should ideally be called stop_time, NWB reserves the names start_time and stop_time."* The cost
  R50 weighed for `offset`, paid by someone else.

## 4. `core.events.payload` carries a column R11 struck

Measured on the real session: payload correlates **perfectly** with type — `delay_start`, `go_cue`
and `reward_outcome` carry one on all 708 rows each, the four lick and reward-delivery types carry
none — and its only key is `trial_id`.

That is not a typed payload. It is `core.events.trial_id`, which **R11 §5 struck**, smuggled back
through JSON by the importer. R54 makes striking it more right rather than less: an event can fall
inside a trial *and* an opto epoch *and* a block at once, so one `trial_id` names one kind and
silently ignores the rest, where containment answers correctly.

Fix: the NWB source stops writing it. Payload is then null on every row of this session, which is
what `optional` is supposed to mean (R3 §2.1).

**Not** an argument for an event discriminator. If a genuinely typed event appears, the mechanism
is R55's — but as a nullable `event_kind` beside `event_type`, never by repurposing it:
`event_type` is an open vocabulary a validator MUST NOT reject values from (R11 §4), and several
types may share one payload schema (`left_lick` and `right_lick`). No packet has such a case, so
this is a note rather than a proposal.

## 5. Nesting: containment is cheap, but not in SQL

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

## 6. Parked: R42's write case

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

## 7. Smaller, still open

- **`core.trials` is task-shaped.** `choice`, `rewarded`, `stimulus_id` and `condition_id` are one
  paradigm's vocabulary in the core schema — a foraging, navigation or passive-viewing trial has
  none of them — and R43 already ruled that a task's shape belongs in an R17 extension when it
  moved `trials_wide`'s columns there. But the evidence cuts the other way than the old note said:
  measured on a real packet, only `stimulus_id` is empty. `condition_id`, `choice`, `rewarded` and
  `metadata` are populated in all 708 rows, so they are carrying real data and withdrawing them
  costs something. Needs a second trials table from a different paradigm to settle.
- **A second ergonomic surface** for people who avoid both SQL and raw PyArrow: DuckDB relations,
  a polars `LazyFrame` behind an extra, or both. Does not block anything.
- **`registry/tables.html`** remains untracked, deliberately.
- **No conformance variant for R51 or the shape check.** The fixture packet has no array resources
  and no external ones, so exercising either there means introducing an external Zarr plus whatever
  table rows the registry's rules expect of one — a larger change to the shared fixture than the
  checks it would cover. The validator's own tests cover every path. Worth revisiting when the
  fixture next needs an array for another reason.

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
