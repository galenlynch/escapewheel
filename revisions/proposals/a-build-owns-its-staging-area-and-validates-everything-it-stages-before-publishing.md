# A build owns its staging area and validates everything it stages before publishing

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `82843394361c1c80e900cf6131e59583e91268c1` |
| **Decision domain** | specification |
| **Affects** | Part 00 §§2.4 and 8; Part 03 §§9.5, 11.2 and 11.3; Part 05 §§1, 2, 4.2, 6, 7, 8, 10 and 11; Part 07 §4; the reference writer's commit, amendment, import run, and array delivery; the writer's cleanup operation; code and test citations of Part 05 stage numbers |

## 1. Problem

A writer turns sources into a packet by a sequence of steps, and
[Part 05 §2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-pipeline) numbers
them. Four other places in Part 05 and Part 00 state their own sequence, and they disagree about
where provenance, materialization, and validation fall relative to publication. Read literally,
Part 05 §2 has a writer publish a packet and then add its provenance and its analysis resources,
which only an amendment can do.

Two further rules around the sequence do not hold of any build. Part 05 §7 obliges a writer to
record the files it read and to link them to the import run, and the reference writer records
neither. [Part 03 §9.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#95-cleanup)
forbids a writer to remove a file no manifest ever named, and every build the reference writer
completes removes its staging area, whose files no manifest names.

## 2. Evidence

All observations were read from the generated parts and the writer at the recorded baseline. The
repository verifier passes its 35 stages at that commit, and the writer's suite passes 632 tests.

### 2.1 Five statements of the order

| location | order stated |
|---|---|
| Part 05 §1 | discover, extract to staging, normalize, validate, commit, record in the manifest with provenance |
| Part 05 §2 | 1 discover, 2 extract to staging, 3 normalize, 4 validate, 5 commit, 6 record provenance, 7 materialize |
| Part 05 §6 | write the staged resources, validate them, move them to final paths, publish the manifest |
| Part 05 §8 | stage core, open the staged packet, derive from it, validate everything together, promote |
| Part 00 §2.4 | a writer stages, validates and commits |

Part 05 §2 and §8 contradict each other. Under §2, commit (step 5) precedes provenance (step 6) and
materialization (step 7). Part 05 §6 makes commit the publication of `packet.json`, and Part 05 §8
says deriving into a committed packet is an amendment under
[Part 03 §9.1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#91-what-an-amendment-is).
Following §2 therefore publishes each import without its provenance or analysis resources, and
adds them by at least one amendment. Validation also appears twice: as step 4 of §2, and as the
second step inside step 5 in §6.

The reference writer follows Part 05 §8. `session.build` adds the import's `core.processing_runs`
row before it calls `PacketWriter.commit`. `commit` stages every table and array under `staging/`,
runs each materializer on the staged packet, restages what changed, validates the staged packet
once, moves `tables/`, `arrays/` and the registries into place, and publishes `packet.json` last by
rename. The writer module's docstring states that five-step order.

Stage numbers are also cited outside Part 05. `scripts/cli.py` describes `import` as "Stages 2-6",
`session.py` and `recipe.py` cite "Stage 3", and four adapters and `delivery.py` cite "Stage 1": 15
citations in the writer's source. The AIND package's two adapters, a writer test, and the adapter
boundary probes under `conformance/` cite "Stage 1" too.

### 2.2 The writer records no inputs

Part 05 §7 has a writer record `core.source_files` for the inputs, one `core.processing_runs` row
for the import, and `core.processing_run_inputs` linking them.
[Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes)
makes that a writer-conformance obligation: a writer conforms only when it records provenance for
the import and the inputs it read. The same section makes provenance a recommendation for packet
conformance, and the core registry declares all three tables with `presence: optional`.

The reference writer writes the import run row and nothing else of the three. The only mention of
`core.source_files` or `core.processing_run_inputs` in its source is the `PROVENANCE` tuple of
tables an amendment may extend. Neither committed AIND session packet built by the reference
writer carries either table.

A build already holds a location for each input. Every source a recipe names reaches its adapter as
the `root` term of
[Part 03 §11.2](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-build-supplied-values),
a URI the build supplies. Nothing in
[Part 03 §11.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-referenced-resource-delivery)
lets an adapter reached by a protocol report the individual files it read beneath that root.

`core.source_files` requires only `source_file_id` and `uri`; `sha256`, `size_bytes`, `format` and
`modified_at` are nullable. `core.processing_run_inputs` requires `session_id`,
`processing_run_id` and `source_file_id`, and references the other two tables.

### 2.3 Every build removes files no manifest named

Part 03 §9.5 defines a stray as a file no manifest ever named, forbids a writer to remove one, and
forbids an amendment to delete anything as part of amending. Part 05 §6 has a commit that finds an
error leave its staging in place for inspection. Part 05 §2 has a build supply every delivery
location empty.

The reference writer places its staging area at `staging/` under the packet root, and removes files
there on every route:

- `commit` removes `staging/` after it publishes, including the staged `packet.json`;
- `commit` and `stage_at` empty an existing `staging/` before they begin, which is what a refused
  build left;
- `amend` empties an existing `staging/` inside a committed packet before it begins, and removes
  it after it publishes; and
- `session.build` empties a leftover `staging/deliveries/<kind>` before supplying it as
  `array_location`.

None of those files was named by a manifest, so each removal is of a stray under Part 03 §9.5.
Each is also what the rules around it require: the staged manifest cannot remain beside the
published one, and a leftover delivery location cannot be supplied empty without being cleared.
The writer's cleanup operation, `prune`, never removes a stray and reports every file under
`staging/` as one.

A related case is outside `staging/`. A build interrupted between moving `tables/` into place and
publishing leaves promoted files and no manifest. The writer refuses to commit into such a root
rather than remove them, citing Part 03 §9.5.

### 2.4 Extraction does not all land under the packet root

Part 05 §4.2 has extraction copy or stream candidate resources into a staging area under the packet
root. The reference writer supplies a `files-v0.1` adapter its `delivery_root` inside
`<out>.deliveries`, a sibling of the packet root, and holds in-process rows in memory. Only
packet-owned arrays are delivered under `staging/`, as Part 03 §11.3 requires. Part 05 §2 already
lets a build choose any location it owns for a delivery, so §4.2 is the narrower statement.

## 3. Desired outcome and constraints

- One section owns the order of a build, and every other statement of it refers there.
- The order is one a writer can follow without amending its own packet: provenance and analysis
  resources are staged, validated and published with core.
- The writer-conformance obligation to record inputs stays, and the reference writer meets it.
- Removing a build's own staging area is permitted, so the rules around it can be followed, while
  a file a person or another tool left in a packet stays protected.
- Packet conformance does not change, and no existing packet has to be rebuilt.

## 4. Options and tradeoffs

### 4.1 Owner of the order

**Part 05 §2 owns it** (preferred direction). Its numbered list becomes:

1. discover what each source offers, writing nothing;
2. deliver, through the locations and routes a build supplies;
3. normalize and write the result to the staging area;
4. record the import's provenance;
5. materialize analysis resources from the staged packet;
6. validate the whole staged packet;
7. promote the staged resources to their final locations; and
8. publish the manifest.

Part 05 §1 keeps its principle and refers to §2 for the order. Part 05 §6 keeps the atomicity and
publication rules for steps 7 and 8. Part 05 §§7 and 8 keep what they require of steps 4 and 5.
Part 00 §§2.4 and 8 already summarize without an order and need only a citation.

The direction named the steps from delivery onward. Discovery is kept as step 1 because Part 05
§4.1 and the `inspect` command depend on it, and it writes nothing, so its position constrains no
other step.

Rejected: **Part 05 §6 owns the order.** Commit would then span delivery through publication, and
"commit" would stop naming the atomic publication that Part 05 §6 and Part 04 use it for.

### 4.2 Headings and stage numbers

**Drop the stage numbers from the headings of Part 05 §§4 to 8** (preferred direction). "Stages 1 to
3", "Stage 4: Validate" and the rest would name their subject, and the number of a step lives only
in §2's list. The sections stay where they are, so the change is ordinary rather than structural.
Code citing "Part 05 Stage N" is re-pointed to the section that states the rule.

Alternative: **renumber the headings to the new order.** Validation would become step 6 in §5, and
the section order would no longer follow the step order unless §§7 and 8 moved before §5, which is a
structural change for no gain in meaning.

### 4.3 Recording inputs

**Keep Part 05 §7's obligation and implement it** (preferred direction). What the obligation covers
depends on its granularity:

- **One row per source root** (preferred direction). A build records one `core.source_files` row per
  distinct `root` it supplied, with `uri` the root, and one `core.processing_run_inputs` row linking
  each to the import run. It needs no adapter change and no new delivery field. `size_bytes` and
  `sha256` stay null unless a build knows them without reading the source.
- **One row per file an adapter read.** This records what a reader of provenance most wants, but an
  adapter reached by a protocol has no way to report its files, so Part 03 §11.3 would gain a
  delivery field and every out-of-process adapter would have to fill it.

Neither option computes a digest of an input. Hashing a raw recording costs a full read of it,
which the nullable `sha256` column already avoids requiring.

Rejected: **weaken Part 05 §7 to a recommendation.** It would make the reference writer conform by
changing the rule rather than the writer, and it would leave a packet unable to say where its core
came from.

### 4.4 Staging and the stray rule

**A build owns its staging area** (preferred direction). Part 05 defines the staging area as a
location a build owns for the duration of that build, whose contents are part of no packet until
promoted. Part 03 names its location in this profile as `staging/` directly under the packet root,
and excludes it from §9.5's definition of a stray. A writer may then empty or remove it:

- after it publishes;
- before a build at the same root starts; and
- before an amendment starts, since an amendment's staging area is equally the build's.

A refused build still leaves it for inspection under Part 05 §6.

Fixing the name is what lets a cleanup tell a staging area from an ungoverned directory; a build
that recorded its staging location elsewhere would need that record to survive the failure it
describes. The cost is a reserved name at the packet root, beside `tables/`, `arrays/`,
`registries/`, `manifests/` and `packet.json`.

Rejected: **move staging outside the packet root.** It would remove the conflict with Part 03 §9.5,
but promotion would no longer be a rename within one filesystem, and Part 03 §11.3 would lose the
guarantee that a delivered array reaches its final path by that rename.

### 4.5 Interrupted promotion

**A promotion record makes an interrupted promotion the build's own** (preferred direction).
Promotion is the one step that writes at packet paths before a manifest names them: a commit moves
`tables/`, `arrays/` and the registries into place and writes `sources.json` and the candidate
manifest, and an amendment moves each written file into place and retains the superseded manifest
under `manifests/`. A build interrupted there leaves files §9.5 calls strays, at paths a
retry needs. A writer cannot tell them from files placed there another way, which is why the
reference writer refuses to build over them.

The rule:

- Before its first write outside `staging/`, a build writes a **promotion record** into
  `staging/`: every path outside `staging/` the promotion will create, relative to the packet root,
  and the `packet_version` it will publish. The record is durable before promotion begins, and it
  lists no path that already exists.
- A path the record lists is the build's own until that `packet_version` is published. A retry
  that finds a record, and a published manifest at an earlier version or none, may remove every
  listed path that exists and then proceed as a new build.
- A retry that finds a record whose `packet_version` is published treats it as stale and removes
  only `staging/`, since promotion completed and only the cleanup was lost.
- A path at the packet root that no record lists and no manifest names stays a stray, which no
  writer removes.

Part 03 §9.5 then defines a stray as a file no manifest ever named, outside `staging/`, and not
listed by a promotion record whose version is unpublished. Because the record lives in `staging/`,
it adds no reserved name beyond §4.4's. Because a listed path cannot have existed before the record
was written, removing it cannot remove anything a build did not create.

Rejected: **complete the interrupted promotion instead of undoing it.** The moved bytes would need
checking against the staged manifest's digests before publication, which costs a read of them and
saves only the rebuild that removal forces.

Rejected: **keep promoted files as strays**, as the reference writer does now. It is safe, but a
crash during a promotion that takes seconds leaves a root that no writer may repair, and a person
must remove files by hand at the paths the specification protects.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged; no concept's meaning changes. |
| logical prose, registry declarations, rules | Unchanged; the three provenance tables keep their declarations and optional presence. |
| physical profiles | Affected: Part 03 §9.5 excludes `staging/` and paths an unpublished promotion record lists, and §11.2 and §11.3 cite Part 05 for the staging area instead of Part 05 §1. |
| packet manifest and schemas | Unchanged. |
| validation and import | Affected: Part 05 §§1, 2, 4.2, 6, 7 and 8 as in §4. Part 05 §§10 and 11 cite no step number and are unchanged. |
| extension registries | Unchanged. |
| writer | Affected: record source roots and inputs for the import run; write a promotion record before `commit` and `amend` promote, and undo a recorded interrupted promotion on retry instead of refusing it; module docstring; the Part 05 stage citations listed in §2.1, including the AIND package and the adapter boundary probes. |
| writer cleanup | Affected: `prune` reports `staging/` apart from strays. |
| reader and validator | Unchanged; the validator checks no writer obligation (Part 05 §10). |
| adapters | Unchanged under one row per root; affected under one row per file. |
| existing packets | Unchanged and still conforming; an amendment may add input rows (Part 03 §9.2). |
| conformance fixtures and tests | Affected: writer tests for the input rows, for removing a leftover staging area, for undoing an interrupted promotion and refusing an unrecorded one, and for `prune` leaving `staging/` out of its strays. No packet fixture changes. |
| revision tooling | Unchanged. |
| documentation | Affected: Part 07 §4's `PacketWriter` summary and the writer README's commit sequence, if they state an order. |

## 6. Open questions

1. **Input granularity.** Preferred: one `core.source_files` row per source root, since one per file
   needs a new delivery field that every out-of-process adapter would have to fill.
2. **Interrupted promotion.** Preferred: a promotion record in `staging/` makes the
   paths a promotion creates the build's own until its version is published (§4.5).
3. **Keeping the decisions together.** The order, the input obligation, and the staging area can
   each be accepted alone. They are kept in one proposal because each settles part of the same
   build sequence, and Part 05 §§2, 6 and 7 would otherwise be amended three times in succession.
   Splitting them is possible without changing any of the three.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [ ] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
