# Handoff — the v0.2 specification, and what is not in it

For someone picking up NWB-Lake. Two things this covers: where the implementation disagrees with the specification, and the packaging layer the specification deliberately does not describe.

## 1. What v0.2 is

`nwb_lake_poc_docs_v0.2/` is v0.1 with R1–R41 and R43–R70 applied. R42 was withdrawn.

`nwb_lake_poc_docs/` stays frozen and is the audit trail. `revisions/` stays the record of *why* each rule holds; v0.2 states only what holds, citing `(R<N> §x)` for provenance.

### 1.1 What changed in the compilation, beyond applying revisions

**Clauses are numbered.** The frozen documents have unnumbered headings, so revisions citing into them fell back to line numbers — `03:75`, `05:131`. Line numbers do not survive an edit. Every requirement in v0.2 has a stable clause number.

**Conformance is stated.** v0.1 never said who its requirements bind. v0.2 §2 of the README names four targets — writer, reader, validator, consumer — and says what a conforming packet and a conforming reader are.

**Part 02 delegates.** v0.1 spelled out 314 columns in prose, which is why it drew 87 amendment references. v0.2 states the rules a declaration obeys and points at the registry for the declarations themselves. It fell from 3,277 words to 1,858, and it can no longer drift from the artifact that generates the checks.

**Normative and informative are separated.** Parts 00–05 and 09 are normative; 06–08 are informative except where marked.

The whole set is 11,161 words against v0.1's 11,576, while carrying 61 revisions.

## 2. Divergence: where the implementation disagrees with v0.2

A binding revision beats the frozen spec, and v0.2 states the binding state. Four of the five entries below are closed; the fifth is a deliberate hold rather than a divergence. A systematic compliance pass against the implementation has not been run, so this is what is known rather than what there is.

### 2.1 R54 — **closed**

`core.trials` is now `core.intervals`, keyed `(session_id, interval_kind, interval_id)`, with
`core.trial_tags` withdrawn and four task columns struck. Each detail table carries the kind as
a constant column and references the whole key (R55 §2.3.1). 34 tables, 312 columns.

Implementing it exposed a validator bug worth knowing: `_declared_kinds` applied R55 §2.3.3's
single-column-key rule — which governs *paired values* — to every discriminator, so a shared-key
`interval_kind` naming a composite-key detail table read as naming nothing.

It also makes a practical requirement explicit: `interval_kind` resolves `required`, so **a
packet carrying intervals must carry an extension that declares their kind.** A bare interval is
not conforming, which is the point of R54 §1.

Four things kept pointing at the renamed table for longer than that entry suggested, and only
one of them failed loudly. `fixtures/build.py` raised `KeyError: 'core.trials'`, so **no fixture
packet was built or checked between R54 and R69** — the conformance corpus that exists to catch
this kind of drift was itself the drift, and it now carries the `dynamic_foraging` extension
because §2.4a leaves a core-only packet no way to hold an interval. Two extension registries
resolved `clock_from` through `core.trials`, `check.py`'s R9 §2 ledger still listed `core.trials`
and `core.trial_tags`, and `derived_from` omitted R54, R65 and R66 despite a `check.py` invariant
that should have caught it — it compared against a hand-maintained list, so the list was wrong in
the same way the thing it checked was. That list is now the union of what the build stamps and
what only the build file records.

### 2.2 R56's `unit` — **closed**

Derived in `col()` beside `role_of` and `identity_of`, so a future column carrying a unit in its
name cannot be added without one. `unit` on 12 columns, `unit_from` on 8, `clock_from` on 6.

### 2.3 R63 — **closed**

Every adapter declares a static `PRODUCES`; a source entry that declares no `owns` takes
everything in it that no other source owns. `PREFERRED` and `SHARED` moved from the scaffolder
into the recipe layer, so a draft and a build arbitrate the same way.

`Recipe.check` now reports an unclaimed producible resource **before any I/O** — the first of
the three ways a recipe loses a resource, moved from 90 s into a build to milliseconds.

### 2.4 `core.events.payload` — **closed**

The importer no longer writes `{"trial_id": N}`. R54 §3 settles what replaces it: an event
belongs to whatever intervals contain it, which may be none or several, and containment is a
query rather than a column.

### 2.5 `registry_version` is held, not broken

It reads `0.1.0` throughout, and that is deliberate: the field is for **compatibility**, follows
semantic versioning, and is pinned while the schema iterates fast. R48, R53, R56 and R59 would
each have forced a major increment had the hold not been in place.

The consequence is real while it lasts — two packets both declaring `0.1.0` can have incompatible
schemas, so the **embedded registry is the authority** and `registry_version` alone cannot decide
compatibility. v0.2 §5.2 says so.

What to do about it is a judgement about stability rather than a repair: when the schema settles,
lift the hold and increment on the next breaking change. Nothing is wrong with the mechanism.

### 2.6 Compliance scan against the implementation — first pass, 2026-09-04

240 normative sentences across the 69 accepted revisions: 133 constrain a packet or schema, 42 a
validator, 33 a reader, 32 a writer.

**The mechanically checkable surface is clean.** Every table, column and rule the revisions name
resolves against the registry, or is a struck or renamed artifact a revision names to say what it
changed. Four names needed chasing and all four were correct: `core.intervals.parent_interval_id`
was considered and rejected by R54 itself; `scope_resolves` was regenerated under R55's names and
does reach extension kinds; `index_contiguous` went with the `interval_index` R47 struck; and
`nwb_lake_writer.arrow.number` exists.

**One writer obligation was not met, and is now fixed.** R40 §2.3 requires a withheld-anchor count
per clock *including zero* — "a packet that drops nothing says so" — and both the per-clock entry
and the parameters block were gated on the count being non-zero. A reader could not distinguish a
clock that was checked and passed from one never checked. The packet now reports ten clocks where
it reported four.

**Two more writer obligations were not met, and are now fixed.**

`prune` read a `retention` object from the manifest, the writer never wrote one, and the manifest
schema did not declare the property — so the operation consumed a field nothing could legitimately
produce, and R61 §2.2's *"a writer SHOULD emit one"* was unmet at all three layers. Every manifest
now declares R61's defaults: one kept version, no age limit.

`core.intervals.metadata` was filled on **450 of 450** rows with 10 keys and 138 KB of JSON, and
all ten — `bait_left`, `reward_probabilityL`, `lickspout_position_x` and the rest — are already
typed columns of `dynamic_foraging.trials`. R54 §2.5 forbids exactly this: filling that column
routinely puts an extension's typed columns back into a string no rule can see and every row must
parse. The column is now absent from the packet and carriage is an opt-in for a task with no
extension.

**Every writer and validator obligation has now been walked.** The 32 writer obligations: three
were unmet (R40 §2.3, R61 §2.2, R54 §2.5) and are fixed; the rest hold, including R52's digest on
34 of 34 owned resources, R57's `$schema` first, R64's `nominal` on 3,840 probe-frame contacts,
R59's absent `ccf_name`, R44's scope on 22 of 22 runs, R70's paired rate, and R67's one device per
instrument. The 42 validator obligations hold, several vacuously and correctly — R57's two MUST
NOTs are satisfied by `$schema` appearing nowhere in the validator or reader, which is what "MUST
NOT require, MUST NOT dereference" asks for.

**What this pass did not do:** the 33 reader/consumer obligations. Most are prohibitions on a
consumer rather than on this codebase — R58 §2.2's "MUST NOT treat an unrecognised basis as
measured" binds whoever reads the packet — but the reference reader is a consumer too, and nothing
has checked it against them.

### 2.7 Reviewed and declined, 2026-09-04

Two external reviews recommended changing interval closure and identifier width. Both were
declined. Recorded here with the reasons, because the arguments for them are good ones and will
be made again.

**Intervals stay closed (R45 §2.1).** Half-open composes and matches array slicing, and the
review's case for it is sound in general. It does not hold here. Measured across the built
packet, nothing tiles as an interval pair — trials are separated by an inter-trial gap of
6,250–7,031 ticks, there is one clock observation window, and the stream windows overlap; the one
thing that does tile, `analysis.spike_events`'s 15 time buckets, is a single `time_bucket_tick`
column with no closure to choose. What closed buys is that both columns hold the same kind of
value, an observed tick: half-open would make `stop_tick` a bound, and for a sample clock where
tick 0 *is* sample 0 the stop of an N-sample recording is sample N, which was never acquired —
so `core.clock_observation_intervals` would say a clock was observing at a tick it was not. It is
also the safer end: a closed interval reaching `INT64_MAX` has no half-open form. Half-open's real
advantage is that `stop - start` is what a reader expects to work; that hazard is symmetric, and
the format states and validates its convention.

**Identifiers stay `int32` with R53 §2.4's escape.** The review read the compiled spec, which had
dropped that escape and said flatly `int32`. Restoring it is compiler repair and is done; widening
every identifier is a different change, and R53 §2.4 already covers the case the width argument is
about — an identifier whose distinct values may exceed `int32` MUST be `int64`, which no core
table approaches. What the review got right and is kept is the separable half: R76 makes an
out-of-range conversion fail rather than wrap, which is the actual hazard, since a wrapped `int32`
is a valid `int32` that passes every rule in the registry.

**What would reopen either.** For intervals, a table whose rows must partition a session, where
closed makes adjacency `next.start == prev.stop + 1` and someone will get it wrong. For widths, an
extension that genuinely exceeds `int32` — at which point R53 §2.4 applies and nothing needs
reopening at all.

### 2.8 A second session, packaged 2026-09-04

`ecephys_776259_2025-04-09_17-25-12` commits clean: **0 core errors, 0 warnings**, 4m52s, 41
resources of which 12 are external. It is the larger of the two — 287 M spikes against 131 M,
6,781 units against 4,505, 708 intervals against 450 — and its numbers are the ones the revisions
have been citing all along, which they took from inventory rather than from a built packet.

Its inputs came from `aind-open-data` over S3. **31.7 MB out of a 213 GB raw prefix** served
`sync` and `openephys`, because those adapters open `settings.xml`, `structure.oebin`,
`sync_messages.txt` and `events/*/TTL/*.npy` and nothing else; the continuous data nothing reads is
the other 213 GB. The sorted asset cost **7.5 GB in 71 seconds** with `s5cmd`, selecting
`spikes.npy` and `spike_amplitudes` rather than the prefixes that hold them — `curated/` and
`postprocessed/` together are 61 GB, and the `provenance.pkl` beside every `spikes.npy` is 12 GB
that nothing opens.

**Five differences from the first session, all of which the tooling surfaced rather than
swallowed.**

1. **No sniff detector.** Its acquisition streams are 786867's minus that one, and a recipe
   declaring the signal failed. The message was misleading — `UnsupportedEncoding: … is not a
   Zarr v2 array` for a path that does not exist.
2. **Two record nodes over two experiments.** Both carry the same probes, so two clocks end in
   `.45883-1.samples` and the LFP source refused: *"2 clocks end in … so the time axis has no
   clock"*. `SorterSource(experiment=…)` disambiguates, and `sync` already defaulted to
   `experiment1`.
3. **Several TTL streams carry no `original_timestamps.npy`** — on S3, not just locally — so their
   timestamps are acquisition-local rather than HARP. `SyncSource` skipped each with a note and
   still found 28 streams and 76,646 anchors.
4. **`aind_unit_qc` is a second pass.** `extract_qc.py` reads the *staged* packet to map unit ids,
   so it cannot run before a first build exists. The packet carries `dynamic_foraging` only.
5. **A selective fetch has to take the metadata too.** Omitting the analyzers' own `.zattrs` left
   `settings.return_in_uV` unreadable, so no sorting run declared an `amplitude_unit` and
   validation refused the commit. Caught by a rule, not by a crash.

**Two usability gaps found.** `nwb-lake inspect nwb` cannot run: it needs `interval_kind` and
`inspect` has no way to pass an option, so `05` Stage 1 is unavailable for the central adapter.
And the Zarr message in (1) should distinguish an absent path from an unsupported encoding.

**No adapter needed changing.** Every difference was absorbed by a recipe option or reported as a
note, which is what the recipe layer is for.

## 3. The packaging layer

The specification describes packets. It does not describe how packets get made, which is most of the code. That layer is deliberately outside the spec: a conforming packet can be produced by any means.

### 3.1 The recipe

A packet is built from several sources at once — a sorter for exact sample indices, an exported file for task structure and registration, acquisition metadata for identity. There is therefore no `import <file>`. The unit of work is a **recipe**: one TOML file naming every source, what each supplies, the clocks, and what to materialize.

The recipe is also the provenance record. Its digest becomes the import run's `code_uri` and the whole document lands in the run's parameters, so a committed packet says what produced it.

**Its failure mode was silence.** `owns` is exclusive: records a source emits for a resource it does not own are discarded with no trace, and `Recipe.check` caught only contradictions — owned twice, undefined, dangling required key — where an omission contradicts nothing. R63 closed that: `owns` is now optional and its absence means the whole of the adapter's `PRODUCES`, so **a recipe states what it narrows**. A resource nothing claims is reported before any I/O.

Two mitigations exist now: a note when a source produces a resource nothing claims, and `import --compare`, which reports resources a prior packet had and this build does not. The second catches cases the first cannot, including a source the recipe never lists.

`--compare` matches on resource identifier, so it cannot tell a **rename** from a loss: R54's rename reported `lost core.trials` correctly and unhelpfully. It also produces false positives across *different sessions*, for anything whose identifier embeds a probe. Compare a rebuild against the packet it replaces, which is the default, and read a warning as "this identifier is gone" rather than "this data is gone".

### 3.2 Source adapters

One per source kind: sorter, sync, NWB, waveforms, LFP, tables.

The contract that makes them testable: **an adapter returns records, never a path.** It touches no filesystem. That keeps normalization decisions out of I/O code.

Two properties worth knowing before writing one:

- **A compensation is declared.** Every adapter works around something known to be wrong upstream. A correction is invisible by construction, which is fine until the upstream fault is fixed and the importer starts producing data wrong in the other direction. So each is registered with its evidence, and every one applied is recorded in the run's parameters. Declining to correct a known defect is equally a compensation and is declared as a pass-through.
- **`tables` needs no code at all.** An extension supplies Parquet files and a registry document, and imports nothing of ours. That is the intended path for a new extension: nothing to install, so nothing to rot.

### 3.3 The registry build

`registry/build.py` generates `logical_schemas.json` and `tables.md`. Rules are authored in `registry/rules.json`, as SQL or as a template the build expands. **Never edit the generated file.**

`registry/check.py` holds the invariants no SQL can see, because they are properties of the registry rather than of any packet: naming conventions, role and identity consistency across references, that a discriminator declares what it resolves to, that every document names its meta-schema. It runs for core and for each extension.

### 3.4 The CLI

One command, `nwb-lake`, provided by three distributions through an entry-point group. `inspect` reports what a source offers; `init` drafts a recipe; `import --check` reports every knowable problem in milliseconds; `import` builds; `verify` records what is true of external resources; `prune` removes what a packet no longer names.

### 3.5 Extensions in practice

Four exist, each built from real data rather than from a model: `dynamic_foraging`, `aind_unit_qc`, `aind_opto`, `vr_foraging`. Two are exercised by a real packet.

One rule was struck after data refuted it: `aind_unit_qc.a_peak_is_counted` failed on 61 of 4,322 units with zero peaks of either sign and a normal peak-to-valley. Extensions are designed against measurements, and a rule that a real dataset contradicts is withdrawn rather than excused.

## 4. Things a newcomer will otherwise rediscover

- **The NWB and the local sorting can be different sortings.** For `ecephys_786867`, the NWB was written 2025-12-24 and the sorted asset re-run 2026-07-29. They pair 4,322 units by `(device_name, ks_unit_id)` and **0 of 4,322 agree on spike count**. Any comparison between them must verify the pairing rather than assume it.
- **The LFP lives under `processing/ecephys/LFP`**, not under `acquisition/`. Looking in the obvious place and concluding a session has no LFP is a mistake already made.
- **A packet is small because it references.** The example packet owns 482 MB and points at 4.25 GB. Owned size is not a measure of content.
- **Reserved NWB names are not honoured.** A future NWB projection is a mapping exercise, and this is a deliberate choice rather than an oversight.

## 5. Suggested order of work

Before a production trial, in this order:

1. **Package a second session.** Every adapter has been developed and validated against exactly
   one, `ecephys_786867`. That is the largest unknown here, and there is already measured evidence
   it will bite: R59 found `ecephys_776259` emits `ccf_id`, `ccf_acronym` and `ccf_name` where
   786867 emits `brain_region_id` — two exporters of one pipeline disagreeing about core's own
   column. Until a second session commits clean, "it works" means "it works on one file layout".
2. **Finish the compliance scan.** A first pass ran 2026-09-04 and is recorded in §2.6. It cleared
   the mechanically checkable surface and sampled the behavioural one; the rest of the 240
   normative sentences have not been walked.

`registry_version` is **not** on this list. §2.5 settles it: semantic versioning, held at `0.1.0`
while the schema iterates. That is a decision already made, not an open question.

Done since this document was written: R65 through R70 are accepted and implemented, the ten
repositories became one with their histories preserved, and `python verify.py` runs every
generator and every check in 25 s — including the stage nothing had: regenerate, then demand a
clean tree.
