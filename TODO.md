# TODO

Live work only. Reasoning for a settled item lives in the revision it produced and in git
history, and measurements in `bench/` and Part 10.

## State of the world

The generated state below is checked by `uv run --project escapewheel-writer python verify.py` —
which is the way to check it rather than by reading this block.

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R170 accepted. R42 and R73 withdrawn. 1 change document, 0 Open and 1 Ready. None of them is binding, and none takes a number until it is accepted.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
47 tables, 367 columns, 117 references, 92 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
142 conformance packets
<!-- END facts: corpus -->

<!-- BEGIN facts: extensions -->
4 extension registries: aind_opto, aind_unit_qc, dynamic_foraging, vr_foraging
<!-- END facts: extensions -->

Each drawn from columns measured in a real
session rather than invented — see `extensions/README.md`. The conformance corpus carries
one, because R54 §2.4a leaves a packet holding intervals no way not to.

**Phases 0–5 complete, Phase 6 partial.** `escapewheel verify` closes R36 §2.4 and `escapewheel
prune` closes R61 §3; immutable publication is roadmap P11. Phase 7 (Iceberg) untouched.

**This is one repository.** It was ten until 2026-09-04; each history was preserved through the
join, so `git log -- revisions/` and `git blame` reach back through it.

### What stands between here and a v0.2 release

1. **Close the pre-release refactor.** [REFACTOR.md](REFACTOR.md) holds the audit's findings, the
   settled decisions and five stages of work, all landed, and every defect it lists is closed (§3).
2. **Field-test the release candidate** (roadmap P10.2). Packets are built and used from the
   current contract with every identifier still a development identifier (Part 02 §9.2). A defect
   in a part, registry or schema it finds is a revision; an implementation defect is maintenance.
   The user decides when it ends.
3. **Assign final identifiers** (P10.3), once the field test's revisions are incorporated.
4. **Publish immutably** (P11): the released artifact set, its manifest and the publication
   verifier.

**Order of work before the field test.** The refactor comes first, because each open change's
code lands in a module the refactor moves.

1. Refactor stages 1 to 5, each listed defect fixed in its stage.
2. Proposals are promoted, drafted and appraised alongside, since they are documents and the
   refactor changes no part.
3. An accepted revision is incorporated after the stage 4 splits, so its code lands once.
4. New adapters follow stage 2, where the adapter contract becomes a declared protocol: the one
   that delivers the files a recipe names (§3b) and a packet-owned option for video.
5. `bench/` (§3c) goes with stage 5 and the tooling work.

---

# Live

## 1. The extension and adapter template is unpublished

**A collaborator may start an extension soon.** `~/Documents/Code/escapewheel-copier-template`,
forked from `aind-python-copier-template` with `upstream` kept for `copier update`, generates an
extension, an adapter, or both. A generated project carries:

- the extension's TOML source with a per-session table and a trials table specialising
  `core.intervals`, its built document, and a test holding it to `check_directory`;
- a `files-v0.1` adapter delivering those tables with the rig's `core.clocks` row and observation
  window, times converted to ticks from the reference clock's rational rate, beside its
  declaration document;
- a `<kind>-recipe` command writing one session's recipe from its `metadata.json`;
- an end-to-end test building and reading a packet; and
- an `AGENTS.md` stating the rules an author would otherwise break, each by its owning section,
  and a `CLAUDE.md` importing it.

`extensions/AUTHORING.md` is the guide the generated `CONTRIBUTING.md` links to, and
`escapewheel registry --out core.json` writes the core registry a recipe binds.

What is left:

- **Publishing.** The template has no GitHub repository, and `galenlynch/escapewheel` is private,
  so a generated project's default git dependency installs only for someone with access. Nothing
  is released, so the escapewheel packages stay a dev group with `[tool.uv.sources]` until v0.2 is
  published, and identifiers are development values until P10.3.
- **Not scaffolded:** self-validation against the extension's own document (Part 12 §9) and a run
  report (Part 12 §9), events and their streams, and clock anchors for a rig with several clocks.

## 2. A delivered sync source cannot carry the terminal-anchor result

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

## 3. The pre-release refactor

**Done.** The audit asked for on 2026-09-06 ran on
2026-10-01 over the four packages, the repository scripts and the specification tooling.
[REFACTOR.md](REFACTOR.md) records what it found, the decisions taken and the work as five stages
of checklists, and its section 11 records each choice made on the way. Every stage and the
specification tooling work have landed. The last defect of its section 4, the ledger's two weak
checks, is closed: R158 has the check resolve a superseded entry's successor, and a one-time audit
read what each target states (§6).

One question from the 2026-09-06 request is not answered by it: which problems a dependency
already solves that this code solves again.

## 3a. No change document is open

`revisions/changes/` holds none. One question an accepted record left open is a change of its own:
`core.sessions.source_session_id` is declared `assigned` while its description names a source
system's identifier, which Part 01 §2.1 calls `carried`; no writer fills it, and `session_name`
already holds the identifier a source used. It wants retyping or removing.

**Accepted as R165, 2026-10-02:** Part 11 §4 states the ISO meaning of `BETWEEN` and `IN`, Part
11 §8 makes a valid rule that a validator cannot evaluate with Part 11's semantics incomplete, Part
11 §1 binds its meaning requirement to completed evaluations, and Part 05 §9.4 takes a rule's
causes from Part 11 §8. Its ISO basis is read in the 1992 draft and the 1999 edition, not in the
2023 edition Part 11 selects.

**Accepted as R166, 2026-10-02:** Part 02 §6.1 makes a table holding a column its declaration does
not declare non-conforming, and Part 05 §5.3 reports one at `error` under
`schema.column_undeclared`. An amending build refuses, before any source opens, a held column of a
table it does not derive again that the registry it binds does not declare, unless a `[drop]` entry
names it, and then writes the table without it. Recipe schema 0.5.0 admits `[drop]`.

**Accepted as R167, 2026-10-02:** one change document under `revisions/changes/` carries a change
from Open to Ready to acceptance, replacing the proposal and the draft. Only the stage fields,
citations, ledger and the reviewer's authorization bind acceptance; the pre-acceptance gates are
guidance. A ledger entry from R167 on carries no note, and the revision guide changes by ordinary
commits under the reviewer's approval.

**Accepted as R168, 2026-10-02:** Part 01 §3.18 makes a media asset's frames the frames it
presents, so a stored frame its edit list excludes has no row and one presented twice has two; a
frame's `pts` is its time on the container's presentation timeline; and `dropped` is true, false or
null as the writer knows of a loss. A frame's tick does not decrease in presentation order on one
clock, which `core.media_frames.t_tick_nondecreasing_with_frame_index` checks. Core is 0.19.0.

**Accepted as R169, 2026-10-02:** Part 02 §6.2 has a null in an `identifier` or `discriminator`
column state only that the row names nothing, neither that nothing exists to name nor that
something does, except where a numbered part gives another reading, as Part 03 §6.3 does for label
padding and the axis forms. A writer writes a null `label_id` only for padding. Three core
descriptions stop giving a null a reading of their own. Core is 0.20.0.

## 3b. Sidecars are declared, and video is not yet packet-owned

**Accepted as R160, 2026-10-02.** Core declares `core.sidecars`, `core.sidecar_scopes` and the
opaque catalog `core.sidecar_instances`, so a manifest lists a PDF, a README or a viewer's saved
state without an extension. The writer's `sidecars` adapter delivers the files a recipe names,
each as a packet-owned payload or as a referenced resource.

Implementation that follows it, none of it a specification change:

- **A packet-owned option for video.** The specification and the writer already admit a
  packet-owned media payload; the aind video adapter only references external files.

Left open and outside R160:

- Part 12 §5 binds a payload to a catalog row or a singleton and gives a family-mode payload no
  rule. No declaration uses family mode. Whether it gains a rule or is removed is undecided.
- An MRI volume that tables describe is a dense array or an extension's resource, not a sidecar,
  and nothing in core describes a volume's anatomy today. A scan that a result was computed from
  is a `core.source_files` row linked to the run, held wherever it is. A scan the packet only
  points at is a referenced sidecar.
- No shipped adapter delivers a `core.source_files` row for an input of an upstream run, such as
  the scan a registration read. Part 05 §7 requires rows only for a recipe's roots and forbids no
  other.

## 3c. `bench/` results are not yet in Part 10 or the writer's performance guide

`bench/` holds the cold-read, row-group and containment benchmarks against the current packet
shape, and `bench/results/history.md` dates every reading the repository quotes, the validator's
removed figures among them. Still to do: move the 2026-10-02 readings into Part 10 §§3 and 6 and
into `escapewheel-writer/docs/source/performance.md`, whose row-group figures are stale, and
port an S3 arm once a current packet is staged there. Nothing re-measures the validator's
figures; `build.py` times an import (§3d).

## 3d. A build's critical path is the sorter, then staging

A build opens up to `--source-workers` (4) sources at once, each as soon as every earlier source
it consumes or takes units or clocks from has been harvested, and handles them in recipe order, so
the packet and its log match a one-worker build. The waveforms source reads each slab's Zarr
chunks on `CHUNK_WORKERS` (8) threads without a separate existence check; it was 216 s of the
pre-change build and is now about 20 s. Every 776259 packet built this way matches `packet-r164`
resource for resource but `core.processing_runs`, which records the run's start time.

`bench/build.py` times one recipe at several worker counts (`bench/results/2026-10-02-build-*`).
On 776259, one worker against four: 426 and 506 s against 449 and 479 s with scratch on the
rotational disk, 795 against 377 s with it on the NVMe, peak RSS 3.5 to 3.9 GiB either way.
The sources take 239 to 258 s at one worker and 232 to 237 s at four (397 against 190 s on
the NVMe pair, where the one-worker cell's S3-bound waveforms and unit QC ran two to three times
slower than in any other cell). Four workers cut the work after
the sorter from about 72 s to 48 s, but nothing else of substance runs alongside the sorter's 144
to 188 s, because every source that does work consumes it. Staging varied from 131 to 349 s
between cells, which hides the difference in the totals. Still to do:

- find why staging varies so much, and log what each resource takes to stage, before deciding
  whether to stage resources in parallel;
- profile the sorter, the critical path, splitting its 287 M-spike read between store round trips,
  the rotational disk and compute, as the waveforms profile did;
- repeat each cell enough times to report a spread, with the source cache on the NVMe too;
- dispatch ready sources in recipe order rather than in the order they became ready, which
  matters only when more are ready than there are workers.

## 4. The repository directory is still `nwb-lake/`

R84 §2.1 renamed the repository and everything inside it moved. The checkout directory did not,
because renaming it mid-session breaks absolute paths in flight and `git mv` cannot rename the
working tree's own root. Both real recipes name absolute paths into it, so this and the
rebuild want doing in one order or the other, not at once.

## 5. Parked: R42's write case survives its withdrawal

R42 is withdrawn on the read measurement, and that stands. What did not fall
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

## 6. Smaller open items

- **The dev library answers nothing about provenance or open changes.** Once the change-document
  revision lands, `escapewheel-dev` gains two read-only queries: the accepted clauses whose ledger
  entry points at a section, and the open change documents that cite one. Nothing else about
  revision records, the ledger or registry history goes in.
- **Trial-in-block containment has no consumer.** The containment measurement in `bench/` concluded
  that a trial needs no stored parent, and `dynamic_foraging` ships one anyway: `blocks` carries
  `start_tick` and `stop_tick` over 19 rows, and `trials.block_id` is populated in **450 of 450 and 708 of 708**
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
- **A nullable identifier's null has no stated meaning.** Nothing obliges an adapter to report a
  value it could not fill, since Part 12 §9's report is a MAY. So a consumer cannot tell
  `core.array_channels.electrode_id` null meaning *this channel maps to no contact* from null
  meaning *I gave up*, and that is true of every nullable reference in the registry. `lfp` now
  refuses rather than writing such a null, and the column is null in **0 of 1,152 and 0 of 960**
  rows of the two packets, so there is no instance to write a rule against. Worth a revision when
  something produces one.
- **`core.media_frames.dropped` has no stated meaning, and `pts` depends on an edit list.** Part 01
  §3.18 makes `frame_index` presentation order, but no part says what `dropped` marks, and an MP4
  whose edit list offsets its timeline gives a different `pts` to a reader that ignores the list.
- **ADC-count amplitudes cannot be converted.** `core.units.amplitude_unit` may say ADC counts, and
  no gain is carried, so a packet alone cannot put them in physical units. Add a conversion when an
  importer needs one.
- **Zarr.jl over an object store, and Julia as a Zarr writer, are untested.**
- **The corpus expects two check IDs no part names.** `array.dimension_names` and `owned.digest`
  are the reference validator's spellings, so those
  packets test this validator and not the specification. It matters only if the corpus is to judge
  a second validator.
- **An in-process source that omits an empty table escapes a refusal a delivered one draws.**
  `facts.refuse_a_discarded_fact` skips a resource fewer than two source kinds stated.
  REFACTOR.md §11.15 records it; changing it is behaviour the refactor does not list.
- **An amendment leaves a `sources.json` the root holds as it is**, so a source it adds has no
  entry there. Part 05 §6 refuses a promotion onto a path that exists, and Part 04 §5.5 asks a
  writer to name every source; whether an amendment may rewrite the document is a specification
  question.
- **`tone_in_place_of_its_own` names no registry.** It draws a core error beside the `cue` one,
  and the corpus's per-registry check requires core to pass. REFACTOR.md §11.6 records it.
- **The ledger cannot see whether a section states an applied clause.** Two clauses were recorded
  at sections that never stated them and were found by hand, and a pilot reading of 40 of the 770
  applied targets found 9 that do not fully state their clause. The proposal to record a quoted
  passage for each target was withdrawn on 2026-10-01 as too heavy to maintain. Every target was
  read once instead. Of the 2,634 rules in the 501 applied clauses, two readings confirm 111 that
  no part states with the revision's force, and dispute 21 more; 140 clauses are recorded at
  targets that differ from the sections stating them. `revisions/audit/applied-targets.md` lists
  the findings by repair class. A third reading of the 72 plain restorations passed 56, most with
  new wording, referred 14 for a choice and rejected 2. The 56 were restored on 2026-10-01, one
  commit per part, and the 2 are noted in the ledger. The other classes had the same critical
  reading, recorded per entry under `revisions/audit/repairs/`: of the 22 class C, 17 class D and
  21 disputed rules, 25 can be entered as that reading words them, 18 need a decision and 17 are
  not owed. On 2026-10-02 twelve of the 25 were entered, with the confirmed ledger targets,
  dispositions and notes. The other thirteen, twelve of them in Part 05 §14, waited on the choices
  in `revisions/audit/repairs/decisions.md`, which records each answer and the commit that entered
  it. Every choice took its preferred option on 2026-10-02 and the thirteen are entered.
  Decision 8, answered last, restored to Part 11 §4 the rule that every exact-to-approximate
  conversion rounds to nearest, ties to even. Four choices became revisions: R161 (what a null
  `processing_run_id` states), R162 (`[overrides]` resolves a discarded fact), R163 (removing
  `core.clocks.transform_to_parent`) and R164 (the relation a consumer uses for a unit outside its
  packet).
- **A source without `root` records no source file.** R135 §3.4 counts only the roots a recipe
  writes, so a source whose recipe entry omits `root` gets no `core.source_files` row. Undecided.

## 7. Implementation follow-ups

`tables` sources deliver by `files-v0.1`, `aind_unit_qc` is an adapter in `escapewheel-aind`,
every name-minting adapter accepts `prefix`, and every store-reading adapter accepts `source_cache`
and keeps store objects as Part 12 §10 requires.

The audit's critical reading found six implementation defects, and
`revisions/audit/applied-targets.md` lists them with the text findings beside them. Four are
fixed: the writer checks an extension registry registered as a file path from its bytes,
`escapewheel import` writes the result of the registry it rejects, the validator interpolates
`PERCENTILE_CONT` in binary64, and it converts a `DECIMAL` value or literal to an approximate
domain through its text, which rounds to nearest, ties to even, as Part 11 §4 requires. One
remains, with a second found while the credential draft was appraised.

- **A sampled run's `code_uri` is not the recipe file's digest.** `Recipe.with_sample` recomputes
  the digest over a serialization of the decoded recipe with the cap added, so a sampled run and a
  full one differ in `processing_run_id`. Part 05 §3.2 has a writer record the recipe's digest and
  says nothing of a sampled run. Where the recorded recipe withholds a value, that digest also
  covers a form a reader can nearly rebuild from `parameters`. Whether a sampled run should digest
  the file is undecided.
- **`spec/tools/check.py` prints outcome lines for a non-valid core registry** and offers no
  output of the complete result.

The same reading found four defects in the specification and the registry. Part 05 §1 and Part 11
§3 are repaired, R161 rewords the false `processing_run_id` description of both array-asset
tables, and R163 removes `core.clocks.transform_to_parent`, which R3 §3.4 replaced. Two more were
found while the drafts were appraised: one in Part 04 §7 with the draft R161 became, and one in
Part 05 §15.6 with the draft R163 became, which wants a proposal of its own.

- **A held file's undeclared column is invisible to an amendment.** Part 05 §15.6 compares rows
  over the columns the amended manifest's registry declares, and no validator check reports a file
  column the bound registry does not declare. An amendment binding a registry that stopped declaring
  a column therefore drops the column's values from a table it rewrites, and keeps them unreported
  in one it does not. R166 refuses unless the recipe names the column, and has a validator
  report a column a table's declaration does not declare.
- **An amendment re-checks only the resources it wrote.** The reference build passes the validator
  the written resources alone as the set to re-check
  (`escapewheel-writer/src/escapewheel_writer/publication.py`, line 233), so a rule a newer registry
  adds to a table the amendment leaves alone does not run, against the over-inclusive test of
  Part 05 §15.4.
- **Part 04 §7 says the manifest records outputs at resource granularity.** The sentence before it
  says an entry names no producing run, and the manifest schema has no member recording a
  resource's outputs. Which of the provenance tables the clause meant is not stated.
