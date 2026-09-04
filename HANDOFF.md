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

1. **Run the compliance scan against the implementation.** The equivalent scan against the spec
   found ten missing rules; nothing has run it against the registry, writer and validator, so
   §2 is what is known rather than what there is.
2. **Decide what `registry_version` is for**, and write the revision. It is the last open
   divergence and the only one that needs a decision rather than work.
3. **R65** is drafted and unaccepted: one nullable `device_id` on `core.array_assets`, so an
   array can name the instrument that made it.
