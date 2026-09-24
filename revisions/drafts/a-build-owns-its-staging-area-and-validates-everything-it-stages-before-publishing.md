# A Build Owns Its Staging Area and Validates Everything It Stages Before Publishing

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `3ac0410c3476570785e1e6239044456ae63289c6` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §§3, 9.5, 11.2, and 11.3; Part 05 §§1, 2, 4, 4.2, 5, 6, 7, and 8 |
| **Depends on** | [R134 §3.4](../accepted/R134-an-adapter-declares-its-whole-contract-and-delivers-only-where-a-build-points-it.md#3-decision) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A build, one execution of a writer against one recipe
([Part 00 §2.4](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-specification-actors)), turns
sources into a packet in a sequence of steps. Part 05 states that sequence in four places, and the
four disagree about where provenance, materialization, and validation fall relative to publication.
Read literally, [Part 05 §2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-pipeline)
has a writer publish a packet before it records the packet's provenance or derives its analysis
resources, which only an amendment could then add.

Two rules beside that sequence are broken by every build of the reference writer,
`escapewheel-writer`. [Part 05 §7](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-provenance)
obliges a writer to record the sources it read, and the writer records none.
[Part 03 §9.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-packet-cleanup)
forbids a writer to remove a stray, a file no manifest ever named, and every build removes its
staging area, whose files no manifest names.

This revision makes Part 05 §2 the one statement of the order: provenance and analysis resources
are staged and validated with core, and nothing is promoted until the whole staged packet passes.
It keeps the obligation to record inputs, at one row per source root. It makes the staging area the
build's own and names it `staging/` in the portable profile, and a promotion record makes the paths
an interrupted promotion created the build's own until its version is published. A stray becomes a
file outside both.

The change is structural because it replaces rules inside Part 05 §§1, 2, 4.2, 6, 7, and 8 and Part
03 §§9.5, 11.2, and 11.3; appended sections would leave each rule standing beside its replacement.
The headings of Part 05 §§4–8 drop their stage numbers so that no section moves, and one subsection
is added at the end of Part 03 §3.

### 1.1 Structural crosswalk

Commit `3ac0410` added the canonical anchors `ew-import-sources`, `ew-import-delivery`,
`ew-import-validation`, `ew-import-commit`, `ew-import-provenance`, and `ew-import-materialization`
to Part 05 §§4, 4.2, 5, 6, 7, and 8, `ew-packet-cleanup` to Part 03 §9.5, and
`ew-implementation-thesis` to Part 00 §8, and changed nothing else. The subsection added to Part 03
§3 takes `ew-staging-area` when it is created. No section moves, splits, merges, or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 05 §1](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-validation-principle), a resource is imported when discovered, extracted, normalized, validated, committed, and recorded with provenance | replace in place | same section | a resource is imported when staged, validated with the whole staged packet, promoted, and published | §3.1 |
| [Part 05 §2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-pipeline), a seven-stage table with commit before provenance and materialization | replace in place | same section | eight steps, publication last; which steps may interleave and which wait; the staging area and when a writer may empty it | §§3.1, 3.2 |
| [Part 05 §4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-sources), "Stages 1 to 3" | retitle | same section, "Discover, deliver, and normalize" | none | none |
| [Part 05 §4.2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-delivery), "Extract"; extraction copies into a staging area under the packet root | replace in place and retitle | same section, "Deliver" | a build reads a delivery where it supplied it, which need not be the staging area | §3.1 |
| [Part 05 §5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-validation), "Stage 4: Validate" | retitle | same section, "Validate" | none | none |
| [Part 05 §6](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-commit), "Stage 5: Commit"; a four-step commit that writes, validates, moves, and publishes | replace in place and retitle | same section, "Commit" | commit promotes and publishes a packet that already passed, under a promotion record | §3.3 |
| [Part 05 §7](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-provenance), "Stage 6: Provenance"; record the inputs, the import run, and their links | replace in place and retitle | same section, "Provenance" | rows staged before validation; one `core.source_files` row per distinct recipe `root` | §3.4 |
| [Part 05 §8](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-materialization), "Stage 7: Materialize" | replace in place and retitle | same section, "Materialize" | materialization is step 5, validated with core | §3.1 |
| none | add | last subsection of Part 03 §3, "The staging area" (`ew-staging-area`) | the portable profile's staging area is `staging/` | §3.2 |
| [Part 03 §9.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-packet-cleanup), a stray is a file no manifest ever named; an amendment deletes nothing | replace in place | same section | a stray also lies outside `staging/` and every path an unpublished promotion record lists; an amendment may remove both | §3.5 |
| [Part 03 §11.2](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-build-supplied-values), `array_location` under the staging area | replace one table row | same section | cites Part 05 §2 for the staging area | §3.2 |
| [Part 03 §11.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-referenced-resource-delivery), the staging area cited as Part 05 §1 | replace one sentence | same section | cites Part 05 §2 and the new subsection for the rename | §3.2 |

## 2. Background

Observations were read from the parts and from `escapewheel-writer` at the recorded baseline.

### 2.1 Part 05 states the order four ways

| location | order stated |
|---|---|
| Part 05 §1 | discover, extract to staging, normalize, validate, commit, record in the manifest with provenance |
| Part 05 §2 | 1 discover, 2 extract to staging, 3 normalize, 4 validate, 5 commit, 6 record provenance, 7 materialize |
| Part 05 §6 | write the staged resources, validate them, move them to final paths, publish the manifest |
| Part 05 §8 | stage core, open the staged packet, derive from it, validate everything together, promote |

Part 05 §§2 and 8 contradict each other. Part 05 §2 puts commit, stage 5, before provenance and
materialization; Part 05 §6 makes commit the publication of `packet.json`; and Part 05 §8 makes
deriving into a committed packet an amendment
([Part 03 §9.1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#91-what-an-amendment-is)).
Validation appears twice, as stage 4 and as the second step inside stage 5. Part 00 §2.4's "stages,
validates and commits" agrees with every reading and is unchanged.

The reference writer follows Part 05 §8. `session.build` adds the import's `core.processing_runs`
row before it calls `PacketWriter.commit`, and `commit` stages every table and array under
`staging/`, runs each materializer on the staged packet, validates the staged packet once, moves
`tables/`, `arrays/`, and the registries into place, and publishes `packet.json` last by renaming a
candidate file.

Stage numbers are cited outside Part 05: fifteen times in the writer's source, once in its
`pyproject.toml`, and in one writer test, the AIND package's two adapters, the adapter-boundary
probes under `conformance/`, the source inventories, and the repository and writer READMEs.

### 2.2 The writer records no inputs

Part 05 §7 has a writer record `core.source_files` for its inputs, one `core.processing_runs` row
for the import, and `core.processing_run_inputs` linking them.
[Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes)
makes that a writer-conformance obligation and a recommendation for packet conformance, and the core
registry declares all three tables `presence: optional`.

The reference writer writes the run row and neither of the other two tables, and neither committed
AIND session packet carries either. No declared rule or validator check reads either table beyond
its generated key and reference checks. `core.source_files` requires only `source_file_id` and
`uri`; `core.processing_run_inputs` requires `session_id`, `processing_run_id`, and
`source_file_id`, keyed on the last two.

A build already holds a location for every source it reads: a recipe gives each source a `root`
([Part 05 §3.1](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-purpose)).
An adapter reached by a protocol has no way to report the files it read beneath that root, because
[Part 03 §11.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-referenced-resource-delivery)
gives a delivery no field for them.

### 2.3 Every build removes files no manifest named

Part 03 §9.5 forbids a writer to remove a stray and an amendment to delete anything as part of
amending. The reference writer places its staging area at `staging/` under the packet root and
removes files there on every route:

- `commit` removes `staging/`, including the staged `packet.json`, after it publishes;
- `commit` and `stage_at` empty a `staging/` a refused build left before they begin;
- `amend` empties an existing `staging/` before it begins and removes it after it publishes; and
- `session.build` empties a leftover `staging/deliveries/<kind>` before supplying it as
  `array_location`.

Each removal is of a stray under Part 03 §9.5, and each is what a neighbouring rule requires: the
staged manifest cannot remain beside the published one, and Part 05 §2 has a build supply every
delivery location empty. The writer's cleanup operation, `prune`, never removes a stray and reports
every file under `staging/` as one.

Promotion writes at packet paths before a manifest names them. A build interrupted between moving
`tables/` into place and publishing leaves promoted files and no manifest, which Part 03 §9.5 calls
strays at the paths a retry needs, so the writer refuses to commit into such a root. `amend` writes
each newly bound registry document at its final path before it validates and removes it again if
validation refuses.

### 2.4 Row deliveries land outside the staging area

Part 05 §4.2 has extraction copy candidate resources into a staging area under the packet root. The
reference writer supplies a `files-v0.1` adapter a `delivery_root` in `<out>.deliveries`, a sibling
of the packet root, and holds in-process rows in memory; only packet-owned arrays are delivered
under `staging/`. Part 05 §2 already lets a build choose any location it owns for a delivery (R134
§3.4), and Part 05 §4.2 contradicts it.

### 2.5 Alternatives

Giving Part 05 §6 the order would stretch commit from delivery to publication, and "commit" would
stop naming the atomic publication Part 05 §6 and Part 04 use it for. Renumbering the headings of
Part 05 §§4–8 to the new order would require moving §§7 and 8 before §5 to keep sections in step
order, which moves material for no change in meaning. One `core.source_files` row per file read
would need a new delivery field that every out-of-process adapter fills. Recording a root as the
build resolved it would make two builds of one recipe over the same bytes record different rows
when the recipe moves, contrary to Part 05 §11's determinism. Weakening Part 05 §7 to a
recommendation would leave a packet unable to say where its core came from. Moving staging outside
the packet root would make promotion a copy rather than a rename within one filesystem. Completing
an interrupted promotion instead of undoing it would need the moved bytes checked against the staged
digests and saves only a rebuild. Keeping promoted files as strays would leave a root no writer may
repair after a crash during a promotion that takes seconds.

### 2.6 Feasibility and overlap

Every obligation uses information the writer already holds: the recipe's roots, the staged packet,
and the `packet_version` it is about to publish. The promotion record is one small file made
durable before the first write outside `staging/`. The manifest schema's registry `path` pattern
admits a path under `staging/`, so `amend` can bind a staged registry document while it validates.

Two proposals opened after the baseline amend other sentences of sections this draft changes: the
digest proposal amends Part 03 §11.3's paragraph on an array's digest, and the Zarr reader-floor
proposal amends Part 05 §5.3, whose parent this draft retitles. Neither changes a rule this draft
relies on. A later change is expected to move Part 03 §11 into a part of its own; this draft cites
Part 03 §§11.2 and 11.3 by anchors that move with them.

## 3. Decision

Five subsections set the order of a build, make the staging area the build's own, make commit a
promotion under a promotion record, set what a writer records about its inputs, and redefine a
stray. The crosswalk in §1.1 places each at its owner.

### 3.1 A build follows one order

Part 05 §2 states the order of a build, and every other statement of it cites Part 05 §2. A build
MUST perform these steps in this order:

1. discover what each source offers, writing nothing;
2. deliver each source's resources through the locations and routes the build supplies;
3. normalize them to the logical schemas and write the result to the staging area;
4. record the import's provenance in the staging area (§3.4);
5. materialize analysis resources from the staged packet into the staging area;
6. validate the whole staged packet;
7. promote the staged resources to their final locations; and
8. publish the packet manifest.

A build MAY interleave steps 1 to 3 across sources, within the constraints Part 05 §4.3 places on
normalization, and a packet-owned array delivered into the staging area is staged by its delivery.
A build MUST finish steps 4 and 5 before it begins step 6, MUST NOT begin step 7 until step 6 has
returned a packet verdict of `passed` (Part 05 §9.5), and MUST NOT begin step 8 until step 7 has
finished.

A resource is imported when a build has staged it, validated it with the whole staged packet,
promoted it, and published a manifest naming it. A build reads each delivery where it supplied it,
which need not be the staging area. Deriving into an already-committed packet is an amendment
(Part 03 §9.1), not part of an import.

### 3.2 A build owns its staging area

The **staging area** is the location a build or an amendment owns while it runs and into which it
writes what it will publish. What it holds belongs to no packet until promotion moves it to its
final location. A physical profile names where its staging area lies.

In the portable profile the staging area is the directory `staging/` directly under the packet
root, and a writer MUST stage an import or an amendment there and nowhere else under the packet
root. Under the packet root, promotion moves a staged resource to its final path by a rename within
one filesystem; a fixed name lets a writer and a cleanup tell a staging area from a directory the
specification does not govern. Where the packet will own an array, the `array_location` a build
supplies lies under the staging area.

A writer MAY empty or remove a staging area:

- after it publishes the manifest of the build or amendment that owns it;
- when it begins a build at the same packet root; and
- when it begins an amendment of the packet at that root.

A writer MUST NOT empty or remove a staging area that holds a promotion record until it has acted
on the record as §3.3 requires.

### 3.3 A commit promotes under a promotion record

A **commit** is steps 7 and 8 of §3.1: **promotion**, which moves a validated staged packet's
resources to their final locations, and **publication** of its manifest at `packet.json`, last and
atomically. A writer MUST NOT publish a manifest until every packet-owned resource it names is at
its final location and has passed validation. A writer whose validation returns a packet verdict
other than `passed` promotes nothing, MUST NOT write a manifest at the packet root, and SHOULD leave
its staging area in place for inspection. Part 05 §6's guarantee to a concurrent reader, its
publication mechanism, and its conditional write stand.

Before a build or an amendment writes anything outside its staging area, the writer MUST write a
**promotion record** into the staging area and make it durable. The record states the
`packet_version` the writer will publish and lists, relative to the packet root, every file and
directory the writer will create outside the staging area before it publishes, other than the
manifest. For an import these are the promoted resource directories, the bound registries, the
source resolution document, and any file publication writes before it installs the manifest; for
an amendment, every file it writes and the superseded manifest it retains (Part 03 §9.3). A writer
MUST refuse to promote where a path its record lists already exists, naming the path, and MUST NOT
create outside the staging area a path its record neither lists nor places inside a listed
directory. This specification does not fix the record's format.

A listed path, with everything inside it, belongs to the build or amendment that wrote the record
until a manifest carrying the record's `packet_version` is published. A writer beginning a build or
an amendment at a packet root whose staging area holds a promotion record MUST read the record
before it empties the staging area or writes anything else, and then:

- where no manifest is published at the packet root, or the published manifest's `packet_version`
  sorts before the record's as a semantic version, the writer MAY remove every listed path that
  exists, and then proceeds as a new build or amendment; and
- where the published manifest's `packet_version` equals the record's or sorts after it, the record
  is stale, and the writer MUST NOT remove a listed path.

A writer that cannot read a promotion record MUST NOT remove any path outside the staging area on
the record's account, and MUST refuse to build or amend at that packet root, naming the record.

### 3.4 A writer records the source roots it read

A writer MUST record, in the staging area at step 4 of §3.1:

- one `core.processing_runs` row for the import, declaring its `scope` and `scope_kind`;
- one `core.source_files` row for each distinct `root` among the recipe's sources (Part 05 §3.1),
  whose `uri` is that root as the recipe states it; and
- one `core.processing_run_inputs` row linking each of those `core.source_files` rows to the import
  run.

A writer need not read a source to fill `sha256`, `size_bytes`, `format`, or `modified_at`, each of
which may be null.

### 3.5 A stray lies outside every build's own paths

A **stray** is a file under the packet root that no manifest ever named, that lies outside the
staging area (§3.2), and that neither is listed by nor lies inside a directory listed by a promotion
record whose `packet_version` is unpublished (§3.3). A writer MUST NOT remove a stray. An amendment
MUST NOT delete anything as part of amending, other than a staging area as §3.2 permits and the
paths §3.3 lets it remove when it acts on a promotion record.

## 4. What this does not change

A packet carrying no `core.source_files` or `core.processing_run_inputs` rows still conforms, since
§3.4 binds a writer and a validator reports no writer obligation as a packet finding (Part 05 §10).

## 5. Consequence

Packet bytes and packet conformance are unchanged, and no packet is rebuilt. The reference writer
fails writer conformance until it records one `core.source_files` row per recipe root and links
each to the import run, which adds two small tables to every packet it builds; an existing packet
may gain those rows by an amendment, as Part 03 §9.2 permits. A root holding promoted files and a
promotion record becomes repairable by retrying the build, and a root holding promoted files and no
record stays refused. `amend` stages a newly bound registry document under `staging/`, so a refused
amendment writes nothing outside `staging/`.

No accepted clause is superseded whole. §3.5 narrows R61 §2.1's stray and R32 §6's ban on deleting
during an amendment. R74 §§2.1–2.3 stand in Part 05 §6, and R134 §3.4's rule that a build owns each
delivery location stands as the case this revision generalizes.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged; no concept's meaning changes. | None required. |
| logical prose and registry | Unchanged; the three provenance tables keep their declarations and optional presence, and no rule is added. | None required. |
| physical profiles | Part 03 §3 gains the staging-area subsection; Part 03 §9.5 redefines a stray and lets an amendment remove a staging area and the paths a promotion record makes its own; Part 03 §§11.2 and 11.3 cite Part 05 §2 for the staging area. | `evidence/R<N>.json` names each anchor. |
| packet manifest and JSON Schemas | Unchanged; the promotion record is not a packet artifact, and the registry `path` pattern already admits a path under `staging/`. | None required. |
| validation and import | Part 05 §§1, 2, 4.2, 6, 7, and 8 state §§3.1–3.4, and the headings of Part 05 §§4–8 drop their stage numbers. | The writer tests below. |
| extensions | Registry content unchanged. The AIND package's two adapters cite Part 05 §4.1 instead of Stage 1. | The AIND suite passes. |
| reader, writer, validator, adapters | The writer records the input rows in `session.build`; writes a promotion record in `commit` and `amend` before the first write outside `staging/`; acts on a record on retry in place of `_refuse_occupied`'s refusal; stages `amend`'s newly bound registries; and cites sections instead of stage numbers in its source and `pyproject.toml`. `prune` reports `staging/` and the paths an unpublished record lists apart from strays. The reader and validator are unchanged, since neither checks a writer obligation. | Writer tests below. |
| conformance fixtures and tests | Packet fixtures are unchanged, because every changed obligation binds a writer. The adapter-boundary probes cite sections instead of stage numbers. | `escapewheel-writer` and `escapewheel-aind` suites. |
| revision process and tooling | Ordinary ledger and evidence records. The ledger entries of R74 §§2.1–2.3, R32 §6, R61 §2.1, and R111 §3.5 that target Part 05 §§4.2 and 6 and Part 03 §9.5 by number move to those sections' anchors, and the notes of R32 §6 and R61 §2.1 record the narrowing. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. The repository and writer READMEs and the source inventories cite sections instead of stage numbers. Part 07 §4's "stage, validate, commit" is unchanged. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor: §3.1 at Part 05 §§1, 2, 4.2, and 8; §3.2 at Part 05
§2, the new Part 03 staging-area subsection, and Part 03 §§11.2 and 11.3; §3.3 at Part 05 §6; §3.4
at Part 05 §7; and §3.5 at Part 03 §9.5.

Writer tests distinguish the new rules from the current ones:

- a build from a recipe naming two distinct roots publishes two `core.source_files` rows and two
  `core.processing_run_inputs` rows, where the current writer publishes neither table;
- a build interrupted after moving `tables/` into place, retried, removes the paths its promotion
  record lists and publishes, where the current writer refuses the root;
- a root holding `tables/` with no promotion record and no manifest is refused, naming the
  directory, and nothing is removed;
- a root whose promotion record cannot be read is refused, naming the record, and nothing outside
  `staging/` is removed;
- an amendment whose validation fails leaves no new registry document outside `staging/`, where the
  current writer writes one at its final path; and
- `prune` over a leftover `staging/` reports no stray under it, where it now reports every file
  there.

Further tests cover two sources sharing one root, recorded once; a relative root recorded as the
recipe writes it; a stale promotion record, after which a retry removes only `staging/`; and an
interrupted amendment whose record lists the retained superseded manifest, removed on retry. The
current writer's `commit` already validates materialized output and the import run row before
promotion, so a test of §3.1's order confirms the corrected text rather than distinguishing it.

## 7. Open

Two builds at one packet root at once are outside this decision. §3.2 lets a writer beginning a
build empty a staging area, which assumes one build per root at a time; a later revision could add
a lock without changing any clause here. A promotion record's format is the writer's, so a writer
may meet a record another writer wrote and be unable to read it, and §3.3 then has it refuse; a
later revision could fix the format if two writer implementations come to share packet roots.
