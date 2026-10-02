# TODO

Live work only. Reasoning for a settled item lives in the revision it produced and in git
history, and measurements in `bench/` and Part 10.

## State of the world

The generated state below is checked by `uv run --project escapewheel-writer python verify.py` —
which is the way to check it rather than by reading this block.

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R159 accepted. R42 and R73 withdrawn. 0 proposals and 5 drafts are open. Neither is binding; a draft takes no number until it is accepted.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
45 tables, 360 columns, 116 references, 91 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
120 conformance packets
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
   settled decisions and five stages of work, all landed. Two of its listed defects wait on a
   revision each (§3).
2. **Field-test the release candidate** (roadmap P10.2). Packets are built and used from the
   current contract with every identifier still a development identifier (Part 02 §9.2). A defect
   in a part, registry or schema it finds is a revision; an implementation defect is maintenance.
   The user decides when it ends.
3. **Assign final identifiers** (P10.3), once the field test's revisions are incorporated.
4. **Publish immutably** (P11): the released artifact set, its manifest and the publication
   verifier.

**Order of work before the field test.** The refactor comes first, because each open proposal's
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

## 1. No template scaffolds an extension project

**Not started.** Writing an extension is now well enough defined to scaffold, and nothing scaffolds
it: the four here were written by hand, and `extensions/README.md` covers *what to model* —
what varies belongs on the row, a source's columns are evidence rather than a schema, deriving a
document from a pydantic model — while saying nothing about how to build and deliver one.

**The template.** Base it on `~/Documents/Code/aind-python-copier-template`, which already carries
the shape: `_templates_suffix: .jinja`, `_subdirectory: template`, copier ≥ 9.0.0, and conditional
`_exclude` blocks for docs, notebooks, a CLI and a `CLAUDE.md`.
`~/Documents/Code/aind-capsule-copier-template` is the other one to read before choosing which to
fork. What it should generate:

- `<namespace>.json`, a skeleton declaring one table with every attribute a column owes,
  and a test running it against the specification's `registry.schema.json`;
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

## 3a. Five drafts await acceptance

The drafts are under `revisions/drafts/`, and `revisions/drafts/README.md` gives their order and
each one's appraisal. No proposal is open.

- **Core declares a catalog of sidecars.** §3b describes it. A sidecar is a file the packet
  asserts nothing through; `core.sidecars` is keyed on `resource_id`, a separate table states what
  a sidecar is about, and its media type is an open column naming the IANA registry.
- **A null producing run says the packet names none.** An array or event stream naming no
  producing run says only that the packet names none, and three descriptions are reworded.
- **A recipe accepts a discarded value by naming its column.** An `[overrides]` entry naming a
  column releases a null column of a corresponding row, and a build refuses an entry that can
  release nothing.
- **Core declares a clock's transform in typed columns alone.** `core.clocks` drops
  `transform_to_parent`, and Part 02 §5.2 stops counting core's `json_string` columns.
- **A unit is identified outside its packet by its name.** The name of every owned assigned
  identifier is `required` and a generated check reports one two rows share; Part 02 §12.1 and
  Part 02 §12.9 name `unit_name` and `interval_name`. The meta-schema `$id`, the descriptor and
  the core version advance, and every repository extension migrates.

## 3b. A file the packet only indexes has no declaration

**Drafted, 2026-10-01**, as `revisions/drafts/core-declares-a-catalog-of-sidecars.md`. A PDF, a
README, a viewer's saved state or an image in an unmodelled format has a class in Part 02 §2.2
(`documentation`) and a directory in Part 03 §3.1 (`docs/`), and no declaration, so a manifest
cannot list one. Listing one today takes an extension registry and an adapter. The draft has
core declare a catalog table and an opaque catalog of that class; Part 12 §5 already delivers an
opaque catalog, packet-owned or referenced.

Implementation that follows it, none of it a specification change:

- **An adapter that delivers the files a recipe names**, each as a packet-owned payload or as a
  referenced resource. No shipped adapter delivers a payload today.
- **A packet-owned option for video.** The specification and the writer already admit a
  packet-owned media payload; the aind video adapter only references external files.

Left open and outside the draft:

- Part 12 §5 binds a payload to a catalog row or a singleton and gives a family-mode payload no
  rule. No declaration uses family mode. Whether it gains a rule or is removed is undecided.
- An MRI volume that tables describe is a dense array or an extension's resource, not a sidecar,
  and nothing in core describes a volume's anatomy today. A scan that a result was computed from
  is a `core.source_files` row linked to the run, held wherever it is. A scan the packet only
  points at is a referenced sidecar.
- No shipped adapter delivers a `core.source_files` row for an input of an upstream run, such as
  the scan a registration read. Part 05 §7 requires rows only for a recipe's roots and forbids no
  other.

## 3c. `bench/` is untracked and holds no script yet

`bench/` has a `pyproject.toml` and a lock file and nothing else. Still to do: port the benchmark
scripts to the current packet shape, re-measure the cold-read figures on the NVMe, write its
README, fold in the older measurements, fix the probes' default paths, move the results into
Part 10, and add a `bench/` row to the root README's layout table. The figures in
`escapewheel-writer/docs/source/performance.md` are stale, and those removed from the validator's
design page have no home until this lands.

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
- **`core.media_frames.frame_index` order is unstated.** Presentation order is the near-certain
  intent, but nothing says so, and a convention read two ways misaligns media against neural data
  silently. `pts` and `dropped` need a real media import before they can be settled.
- **ADC-count amplitudes cannot be converted.** `core.units.amplitude_unit` may say ADC counts, and
  no gain is carried, so a packet alone cannot put them in physical units. Add a conversion when an
  importer needs one.
- **Zarr.jl over an object store, and Julia as a Zarr writer, are untested.**
- **The corpus expects four check IDs no part names.** `array.dimension_names`, `owned.digest`,
  `schema.column_absent` and `schema.column_type` are the reference validator's spellings, so those
  packets test this validator and not the specification. It matters only if the corpus is to judge
  a second validator.
- **An in-process source that omits an empty table escapes a refusal a delivered one draws.**
  `facts.refuse_a_discarded_fact` skips a resource fewer than two source kinds stated.
  REFACTOR.md §11.15 records it; changing it is behaviour the refactor does not list.
- **An amendment writes no `sources.json`**, so a source an amendment adds has no entry in the
  resolution document Part 04 §5.5 recommends. REFACTOR.md §11.17 records it.
- **The import command and `import_packet` bind different registries on an amendment.** The
  command binds a registry the amended packet binds and the recipe does not name; `build` and
  `import_packet` called directly do not. REFACTOR.md §11.17 records it.
- **No test amends a packet with a materializer.** The pipeline change of REFACTOR.md §11.17 was
  compared by bytes over eight such scenarios held outside the repository.
- **Four corpus packets expected to warn are not checked to pass**, and `tone_in_place_of_its_own`
  names no registry. REFACTOR.md §11.6 lists them.
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
  conversion rounds to nearest, ties to even. Four choices became proposals, in
  `revisions/proposals/`: the relation a consumer uses for a unit outside its packet, whether
  `[overrides]` resolves a discarded fact, removing `core.clocks.transform_to_parent`, and what a
  null `processing_run_id` on an array states.
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
domain through its text, which rounds to nearest, ties to even, as Part 11 §4 requires. Two
remain, with a third found while the sidecar draft was appraised and a fourth while the credential
draft was.

- **A sampled run's `code_uri` is not the recipe file's digest.** `Recipe.with_sample` recomputes
  the digest over a serialization of the decoded recipe with the cap added, so a sampled run and a
  full one differ in `processing_run_id`. Part 05 §3.2 has a writer record the recipe's digest and
  says nothing of a sampled run. Where the recorded recipe withholds a value, that digest also
  covers a form a reader can nearly rebuild from `parameters`. Whether a sampled run should digest
  the file is undecided.
- **`refuse_a_discarded_fact` never reads `[overrides]`,** and its message names that resolution.
  The rule itself waits on a revision.
- **`spec/tools/check.py` prints outcome lines for a non-valid core registry** and offers no
  output of the complete result.
- **The validator's forward check admits a core table the packet does not carry.** Part 02 §8.3
  has it return each row whose value names no resource the manifest declares; the check compares
  against every table the core registry declares. Whether an existing packet would draw a new
  finding is not measured. The sidecar draft's inventory names the alignment.

The same reading found four defects in the specification and the registry. Part 05 §1 and Part 11
§3 are repaired. Two wait on a proposal in `revisions/proposals/`.

- **The description of `processing_run_id` on both array-asset tables is false.** It says a null
  means the array was acquired, and a computed array whose run the packet does not record also
  carries null.
- **`core.clocks.transform_to_parent` is still declared.** R3 §3.4 replaced it with the two typed
  columns.
