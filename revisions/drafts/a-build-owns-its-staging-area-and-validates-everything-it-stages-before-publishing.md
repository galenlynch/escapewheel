# A Build Owns Its Staging Area and Validates Everything It Stages Before Publishing

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `f5f33647eb9c3e29ff8c850afa480468fea0c582` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§2.4 and 8; Part 03 §§3, 9.5, 11.2, and 11.3; Part 05 §§1, 2, 4, 4.2, 5, 6, 7, and 8 |
| **Depends on** | [R134 §3.4](../accepted/R134-an-adapter-declares-its-whole-contract-and-delivers-only-where-a-build-points-it.md#3-decision) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A writer turns sources into a packet by a sequence of steps.
[Part 05 §2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-import-pipeline) numbers
them, and Part 05 §§1, 6, and 8 and
[Part 00 §2.4](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-specification-actors) each state
their own sequence. They disagree about where provenance, materialization, and validation fall
relative to publication. Read literally, Part 05 §2 has a writer publish a packet and then add its
provenance and its analysis resources, which only an amendment can do.

Two rules around that sequence hold of no build the reference writer performs.
[Part 05 §7](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#7-stage-6-provenance)
obliges a writer to record the sources it read and link them to the import run, and the writer
records neither. [Part 03 §9.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#95-cleanup)
forbids a writer to remove a file no manifest ever named, and every build removes its staging area,
whose files no manifest names.

This revision gives the order of a build to Part 05 §2 and has every other statement of it refer
there. Provenance and analysis resources are staged, validated, and published with core, and
nothing is promoted before the whole staged packet passes. It keeps the obligation to record inputs
and sets its granularity at one row per source root. It defines the staging area as the build's
own, names it `staging/` in the portable profile, and adds a promotion record that makes the paths
an interrupted promotion created the build's own until its version is published. A stray becomes a
file outside both.

The change is structural because it replaces rules inside existing sections: Part 05 §2's
seven-stage table, Part 05 §4.2's placement of extraction, Part 05 §6's four-step commit, Part 05
§7's unqualified input record, and Part 05 §8's description of materialization; Part 03 §9.5's
definition of a stray and its ban on deletion during an amendment; and the staging citations in
Part 03 §§11.2 and 11.3. It also changes the headings of Part 05 §§4–8, which drop their stage
numbers so that no section moves. Appending a new section would leave each of those rules standing
beside its replacement. One subsection is added, at the end of Part 03 §3.

### 1.1 Structural crosswalk

Part 05 §§1 and 2, Part 03 §§11.2 and 11.3, and Part 00 §2.4 already carry canonical anchors. Part
05 §§4, 4.2, 5, 6, 7, and 8, Part 03 §9.5, and Part 00 §8 carry none, so a metadata-only anchor
bootstrap commit must give them the IDs in the table below and become this draft's `Based on`
before its final appraisal. The subsection this revision adds to Part 03 §3 receives
`ew-staging-area` when it is created. No section moves, splits, merges, or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 05 §1 (`ew-import-validation-principle`), a resource is imported when discovered, extracted, normalized, validated, committed, and recorded with provenance | replace in place | same section | a resource is imported when staged, validated with the whole staged packet, promoted, and published, in Part 05 §2's order | §3.1 |
| Part 05 §2 (`ew-import-pipeline`), a seven-stage table with commit before provenance and materialization | replace in place | same section | eight steps, with provenance and materialization before validation and publication last; which steps may interleave and which must wait; the staging area defined as the build's own | §§3.1, 3.2 |
| Part 05 §4 (`ew-import-sources`), headed "Stages 1 to 3" | retitle | same section, "Discover, deliver, and normalize" | none | §3.1 |
| Part 05 §4.2 (`ew-import-delivery`), headed "Extract"; extraction copies into a staging area under the packet root | replace in place and retitle | same section, "Deliver" | a build reads a delivery where it supplied it, which need not be the staging area, and writes what it normalizes into the staging area | §3.1 |
| Part 05 §5 (`ew-import-validation`), headed "Stage 4: Validate" | retitle | same section, "Validate" | none | §3.1 |
| Part 05 §6 (`ew-import-commit`), headed "Stage 5: Commit"; a four-step commit that writes, validates, moves, and publishes; a commit finding an error leaves staging | replace in place and retitle | same section, "Commit" | commit is promotion and publication of a packet that already passed; a packet verdict other than `passed` refuses it; a promotion record precedes every write outside the staging area and decides which paths a retry may remove | §3.3 |
| Part 05 §7 (`ew-import-provenance`), headed "Stage 6: Provenance"; record source files, the import run, and their links | replace in place and retitle | same section, "Provenance" | the rows are staged before validation; one `core.source_files` row per distinct recipe `root`, whose `uri` is that root as the recipe states it | §3.4 |
| Part 05 §8 (`ew-import-materialization`), headed "Stage 7: Materialize" | replace in place and retitle | same section, "Materialize" | materialization is step 5, and its output is staged and validated with core | §3.1 |
| none | add | a subsection at the end of Part 03 §3, "The staging area" (`ew-staging-area`) | the portable profile's staging area is `staging/` under the packet root | §3.2 |
| Part 03 §9.5 (`ew-packet-cleanup`), a stray is a file no manifest ever named; an amendment deletes nothing | replace in place | same section | a stray also lies outside `staging/` and outside every path an unpublished promotion record lists; an amendment may remove a staging area and the paths a promotion record makes its own | §3.5 |
| Part 03 §11.2 (`ew-build-supplied-values`), `array_location` lies under the staging area | replace one table row | same section | cites Part 05 §2 for the staging area | §3.2 |
| Part 03 §11.3 (`ew-referenced-resource-delivery`), the staging area cited as Part 05 §1; commit moves an array by the rename Part 05 §6 performs | replace one sentence | same section | cites Part 05 §2 for the staging area and the new subsection for the rename within one filesystem | §3.2 |
| Part 00 §2.4 (`ew-specification-actors`), a writer stages, validates and commits | extend in place | same section | cites Part 05 §2 for the order | §3.1 |
| Part 00 §8 (`ew-implementation-thesis`), an import succeeds only when validation succeeds | replace one sentence | same section | the validation is of the whole staged packet, citing Part 05 §§1 and 2 | §3.1 |

## 2. Background

Observations were read from the parts and the writer at the recorded baseline.

### 2.1 Five statements of the order

| location | order stated |
|---|---|
| Part 05 §1 | discover, extract to staging, normalize, validate, commit, record in the manifest with provenance |
| Part 05 §2 | 1 discover, 2 extract to staging, 3 normalize, 4 validate, 5 commit, 6 record provenance, 7 materialize |
| Part 05 §6 | write the staged resources, validate them, move them to final paths, publish the manifest |
| Part 05 §8 | stage core, open the staged packet, derive from it, validate everything together, promote |
| Part 00 §2.4 | a writer stages, validates and commits |

Part 05 §2 and Part 05 §8 contradict each other. Under Part 05 §2, commit (stage 5) precedes provenance (stage 6)
and materialization (stage 7). Part 05 §6 makes commit the publication of `packet.json`, and Part 05
§8 says deriving into a committed packet is an amendment under
[Part 03 §9.1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#91-what-an-amendment-is).
Following Part 05 §2 therefore publishes each import without its provenance or analysis resources
and adds them by at least one amendment. Validation also appears twice: as stage 4 of Part 05 §2,
and as the second step inside stage 5 in Part 05 §6.

The reference writer follows Part 05 §8. `session.build` adds the import's `core.processing_runs`
row before it calls `PacketWriter.commit`. `commit` stages every table and array under `staging/`,
runs each materializer on the staged packet, restages what changed, validates the staged packet
once, writes the source resolution document at the packet root, moves `tables/`, `arrays/`, and the
registries into place, and publishes `packet.json` last by renaming a candidate file.

The stage numbers are cited outside Part 05. Fifteen citations in the writer's source name one:
`scripts/cli.py` describes `inspect` as Stage 1 and `import` as Stages 2-6, `session.py` and
`recipe.py` cite Stage 3, and four source adapters and `delivery.py` cite Stage 1. The writer's
`pyproject.toml` cites Stage 5, and one writer test, the AIND package's two adapters, the adapter
boundary probes under `conformance/`, the source inventories, and the repository and writer READMEs
cite Stage 1 or Stages 2-6.

### 2.2 The writer records no inputs

Part 05 §7 has a writer record `core.source_files` for the inputs, one `core.processing_runs` row
for the import, and `core.processing_run_inputs` linking them.
[Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes)
makes that a writer-conformance obligation and a recommendation for packet conformance, and the core
registry declares all three tables `presence: optional`.

The reference writer writes the import run row and nothing else of the three. Its only mention of
`core.source_files` or `core.processing_run_inputs` is the `PROVENANCE` tuple of tables an amendment
may extend, and neither committed AIND session packet carries either table. No declared rule or
validator check reads either table beyond its generated key and reference checks.

A build already holds a location for every source it reads: a recipe gives a source its `root`
([Part 05 §3.1](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-recipe-purpose)), and
the build supplies it to the adapter as a URI
([Part 03 §11.2, what a build supplies](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-build-supplied-values)).
Nothing in [Part 03 §11.3, what a delivery states](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-referenced-resource-delivery)
lets an adapter reached by a protocol report the files it read beneath that root.

`core.source_files` requires only `source_file_id` and `uri`; `sha256`, `size_bytes`, `format`, and
`modified_at` are nullable. `core.processing_run_inputs` requires `session_id`,
`processing_run_id`, and `source_file_id`, keyed on the last two.

### 2.3 Every build removes files no manifest named

Part 03 §9.5 defines a stray as a file no manifest ever named, forbids a writer to remove one, and
forbids an amendment to delete anything as part of amending. Part 05 §6 has a commit that finds an
error leave staging in place for inspection, and Part 05 §2 has a build supply every delivery
location empty.

The reference writer places its staging area at `staging/` under the packet root and removes files
there on every route:

- `commit` removes `staging/` after it publishes, including the staged `packet.json`;
- `commit` and `stage_at` empty an existing `staging/` before they begin, which is what a refused
  build left;
- `amend` empties an existing `staging/` inside a committed packet before it begins, and removes it
  after it publishes; and
- `session.build` empties a leftover `staging/deliveries/<kind>` before supplying it as
  `array_location`.

None of those files was named by a manifest, so each removal is of a stray under Part 03 §9.5, and
each is what the rules around it require: the staged manifest cannot remain beside the published
one, and a leftover delivery location cannot be supplied empty without being cleared. The writer's
cleanup operation, `prune`, never removes a stray and reports every file under `staging/` as one.

Promotion is the one step that writes at packet paths before a manifest names them. A build
interrupted between moving `tables/` into place and publishing leaves promoted files and no
manifest, which Part 03 §9.5 calls strays at paths a retry needs. The writer cannot tell them from
files placed there another way, so it refuses to commit into such a root. `amend` also writes each
newly bound registry document at its final path before it validates, and removes it again if
validation refuses, so a refused amendment removes files no manifest named.

### 2.4 Delivery does not all land under the packet root

Part 05 §4.2 has extraction copy or stream candidate resources into a staging area under the packet
root. The reference writer supplies a `files-v0.1` adapter its `delivery_root` inside
`<out>.deliveries`, a sibling of the packet root, and holds in-process rows in memory. Only
packet-owned arrays are delivered under `staging/`, as Part 03 §11.3 requires. Part 05 §2 already
lets a build choose any location it owns for a delivery (R134 §3.4), so Part 05 §4.2 is the
narrower statement.

### 2.5 Alternatives

**Part 05 §6 owns the order.** Commit would then span delivery through publication, and "commit"
would stop naming the atomic publication that Part 05 §6 and Part 04 use it for. Rejected.

**Renumber the headings of Part 05 §§4–8 to the new order.** Validation would become step 6 in Part 05
§5, and the sections would no longer follow the steps unless Part 05 §7 and Part 05 §8 moved before
it, which moves material for no gain in meaning. Dropping the numbers leaves each section where it
is, and the number of a step lives only in the list of Part 05 §2. Discovery keeps position 1 in the list because Part 05
§4.1 and `escapewheel inspect` depend on it, and it writes nothing, so its position constrains no
other step.

**One `core.source_files` row per file an adapter read.** It records what a reader of provenance
most wants, but an adapter reached by a protocol has no way to report its files, so Part 03 §11.3
would gain a delivery field that every out-of-process adapter would have to fill. One row per root
needs neither. Rejected.

**Record the root as the build resolved it** rather than as the recipe states it. A relative root
resolves against the recipe's directory, so the recorded row would depend on where the recipe was
when the build ran, and two builds of one recipe over the same bytes would record different rows,
contrary to the logical determinism of
[Part 05 §11](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#11-minimum-acceptance-criteria).
A store URI is the same either way. Rejected.

**Weaken Part 05 §7 to a recommendation.** The reference writer would conform by changing the rule
rather than the writer, and a packet could not say where its core came from. Rejected.

**Move staging outside the packet root.** It would remove the conflict with Part 03 §9.5, but
promotion would no longer be a rename within one filesystem, and Part 03 §11.3 would lose the
guarantee that a delivered array reaches its final path by that rename. Fixing the name `staging/`
costs one reserved name at the packet root and lets a cleanup tell a staging area from an
ungoverned directory; a build that recorded its staging location elsewhere would need that record to
survive the failure it describes. Rejected.

**Complete an interrupted promotion instead of undoing it.** The moved bytes would need checking
against the staged manifest's digests before publication, which costs a read of them and saves only
the rebuild that removal forces. Rejected.

**Keep promoted files as strays.** It is safe, but a crash during a promotion that takes seconds
leaves a root that no writer may repair, and a person must remove files by hand at the paths the
specification protects. Rejected.

### 2.6 Feasibility and overlap

Every obligation here uses information the writer already holds: the recipe's roots, the staged
packet, and the `packet_version` it is about to publish. Writing the promotion record needs one
small file made durable before the first write outside `staging/`, and undoing an interrupted
promotion needs only the listed paths. The manifest schema's registry `path` pattern admits a path
under `staging/`, so `amend` can stage a registry document and bind it there while it validates, as
it already binds staged resources. No library, storage property, or performance claim beyond those
Part 05 §6 already relies on is introduced.

No other proposal or draft is open at the baseline. A separate change is expected to move Part 03
§11 into a part of its own. This revision replaces one table row of Part 03 §11.2 and one sentence
of Part 03 §11.3, and this draft cites both by their anchors, `ew-build-supplied-values` and
`ew-referenced-resource-delivery`, which move with them. Whichever change is incorporated second
carries the other's citations across: a moved §11.3 keeps its citation of Part 05 §2 and rewrites
its short citation of the staging-area subsection as a Part 03 citation.

## 3. Decision

Five subsections set the order of a build, make the staging area the build's own, make commit a
promotion under a promotion record, set what a writer records about its inputs, and redefine a
stray. Each quotation is the text its labelled owner carries, headed by the owner's heading.
Inside a quotation, a citation naming its own part is written in full so it can be checked against
the current parts, and incorporation shortens it to `§x.y`; the citation of the subsection this
revision adds to Part 03 §3 is already in that short form, `§3.4`. Unquoted paragraphs of an owner
are unchanged.

### 3.1 A build follows one order

*Part 05 §1, "Core principle", replaces its second paragraph:*

> A resource is imported when a build has staged it, validated it as part of the whole staged
> packet, promoted it to its final location, and published a manifest naming it, in the order
> Part 05 §2 states.

*Part 05 §2, "Pipeline", replaces its table:*

> A build performs these steps in this order:
>
> 1. discover what each source offers, writing nothing (Part 05 §4.1);
> 2. deliver each source's resources through the locations and routes the build supplies
>    (Part 05 §4.2);
> 3. normalize them to the logical schemas and write the result to the staging area (Part 05 §4.3);
> 4. record the import's provenance in the staging area (Part 05 §7);
> 5. materialize analysis resources from the staged packet (Part 05 §8);
> 6. validate the whole staged packet (Part 05 §5);
> 7. promote the staged resources to their final locations (Part 05 §6); and
> 8. publish the packet manifest (Part 05 §6).
>
> A build MAY interleave steps 1 to 3 across sources, within the constraints Part 05 §4.3 places on
> normalization, and a packet-owned array delivered into the staging area is staged by its delivery.
> A build MUST finish steps 4 and 5 before it begins step 6, MUST NOT begin step 7 until step 6 has
> returned a packet verdict of `passed` (Part 05 §9.5), and MUST NOT begin step 8 until step 7 has
> finished.

The paragraph that follows the table in Part 05 §2, forbidding a writer to combine parsing,
normalization, validation, and writing into one opaque step, is unchanged.

*Part 05 §4 is headed "Discover, deliver, and normalize". Part 05 §4.2, headed "Deliver", reads:*

> A build reads each source's delivery from the locations and routes it supplied (Part 05 §2), which
> need not lie in the staging area, and writes what it normalizes from them into the staging area
> (Part 05 §4.3). A writer MUST stream a table whose row count is large rather than materializing it
> as host objects.

*Part 05 §5 is headed "Validate".*

*Part 05 §8, headed "Materialize", reads:*

> Materialization is step 5 of Part 05 §2: a build opens the staged packet, computes each derived
> resource from it, and writes the result to the staging area, so step 6 validates it with core
> before anything is promoted.
>
> Deriving into an already-committed packet is an amendment (Part 03 §9.1), not part of an import.

*Part 00 §2.4, "Conformance targets and actors", replaces the second sentence of its writer
paragraph:*

> It stages, validates and commits, in the order Part 05 §2 states, and it is the actor Part 05 binds
> throughout.

*Part 00 §8, "Implementation thesis", replaces its last sentence:*

> An import succeeds only when validation of the whole staged packet succeeds (Part 05 §§1 and 2).

### 3.2 A build owns its staging area

*Part 05 §2, "Pipeline", adds after the order of §3.1 and before its delivery paragraph:*

> The **staging area** is a location a build owns for the duration of one build, where it writes
> what it will publish. What the staging area holds is part of no packet until promotion moves it to
> its final location. A physical profile names where its staging area lies.
>
> A writer MAY empty or remove a staging area:
>
> - after it publishes the manifest of the build that owns it;
> - when it begins a build at the same packet root; and
> - when it begins an amendment of the packet at that root.
>
> A writer MUST NOT empty or remove a staging area that holds a promotion record until it has acted
> on the record as Part 05 §6 requires.

*Part 03 §3 gains a last subsection, numbered 3.4 and headed "The staging area":*

> In this profile a build's staging area (Part 05 §2) is the directory `staging/` directly under the
> packet root. A writer MUST stage an import or an amendment there and nowhere else under the packet
> root, and keeps its promotion record there (Part 05 §6).
>
> Fixing the name lets a writer and a cleanup tell a build's staging area from a directory this
> specification does not govern (Part 03 §9.5), and placing it under the packet root lets promotion
> move a staged resource to its final path by a rename within one filesystem.

*Part 03 §11.2, "What a build supplies", replaces the `array_location` row of its term table:*

> | `array_location` | a location under the build's staging area (Part 05 §2) to write an array to (Part 03 §11.3) |

*Part 03 §11.3, "What a delivery states", replaces the third sentence of its paragraph on an
adapter's arrays:*

> Where the packet will own the array, a build MUST supply a location under the staging area
> (Part 05 §2), and an adapter reached by a protocol MUST write the array there, so promotion
> (Part 05 §6) moves it to its final path by a rename within one filesystem (§3.4).

### 3.3 A commit promotes under a promotion record

*Part 05 §6, headed "Commit", reads, keeping its two paragraphs on the publication mechanism and on
a conditional write between the first paragraph and the fourth:*

> A **commit** is steps 7 and 8 of Part 05 §2: **promotion**, which moves a validated staged packet's
> resources to their final locations, and **publication** of its manifest at `packet.json`, last and
> atomically. Commit MUST be atomic with respect to a concurrent reader. A reader MUST observe either
> the previously committed manifest or the newly published one, and MUST NOT observe a manifest
> naming a resource that is not yet in place. A writer MUST NOT publish a manifest until every
> packet-owned resource it names is at its final location and has passed validation.
>
> A writer whose validation returns a packet verdict other than `passed` MUST NOT promote anything
> or write a manifest at the packet root, and SHOULD leave its staging area in place for inspection.
>
> Before a build or an amendment writes anything outside its staging area, the writer MUST write a
> **promotion record** into the staging area and make it durable. The record states the
> `packet_version` the writer will publish and lists, relative to the packet root, every file and
> directory the writer will create outside the staging area before it publishes, other than the
> manifest itself. For an import these include the promoted resource directories, the bound
> registries, the source resolution document, and any file publication writes before it installs
> the manifest; for an amendment, every file it writes and the superseded manifest it retains
> (Part 03 §9.3). A writer MUST refuse to promote where a path its record lists already exists,
> naming the path, and MUST NOT create outside the staging area a path its record does not list,
> other than one inside a directory the record lists. This specification does not fix the record's
> format.
>
> A path a promotion record lists, with everything inside it, belongs to the build or amendment
> that wrote the record until a manifest carrying the record's `packet_version` is published. A
> writer beginning a build or an amendment at a packet root whose staging area holds a promotion
> record MUST read the record before it empties the staging area or writes anything else, and then:
>
> - where no manifest is published at the packet root, or the published manifest's
>   `packet_version` sorts before the record's, compared as a semantic version, the writer MAY
>   remove every listed path that exists, and then proceeds as a new build or amendment; and
> - where the published manifest's `packet_version` equals the record's or sorts after it, the
>   record is stale, and the writer MUST NOT remove a listed path.
>
> A writer that cannot read a promotion record MUST NOT remove any path outside the staging area on
> the record's account, and MUST refuse to build or amend at that packet root, naming the record.

### 3.4 A writer records the source roots it read

*Part 05 §7, headed "Provenance", reads:*

> A build records the import's provenance as step 4 of Part 05 §2, so the rows are staged and
> validated with the resources they describe. A writer MUST record:
>
> - one `core.processing_runs` row for the import, declaring its `scope` and `scope_kind`;
> - one `core.source_files` row for each distinct `root` among the recipe's sources (Part 05 §3.1),
>   whose `uri` is that root as the recipe states it; and
> - one `core.processing_run_inputs` row linking each of those `core.source_files` rows to the
>   import run.
>
> A writer is not required to read a source to fill `sha256`, `size_bytes`, `format`, or
> `modified_at`, each of which may be null.

### 3.5 A stray lies outside every build's own paths

*Part 03 §9.5, "Cleanup", replaces its second and third paragraphs:*

> A **stray** is a file under the packet root that no manifest ever named, that does not lie under
> `staging/` (§3.4), and that is not listed, or inside a directory listed, by a promotion record
> whose `packet_version` is unpublished (Part 05 §6). A writer MUST NOT remove a stray. A packet may
> carry files this specification does not govern, and cleanup that deletes the ungoverned is a
> data-loss bug wearing an operation's name. The operation reports by default and acts only when
> asked.
>
> An amendment **MUST NOT** delete anything as part of amending, other than a staging area as
> Part 05 §2 permits and the paths Part 05 §6 lets it remove when it acts on a promotion record. A
> file that no manifest version names any longer MAY be deleted, but by cleanup, as a separate
> operation — which is what keeps an amendment's failure from having removed something.

## 4. What this does not change

A packet carrying no `core.source_files` or `core.processing_run_inputs` rows still conforms, and a
validator still reports no writer obligation as a packet finding (Part 05 §10). The three provenance
tables keep their declarations and optional presence.

## 5. Consequence

Packet bytes and packet conformance are unchanged, and no packet is rebuilt. The reference writer
now fails writer conformance on its input rows and on removing its own staging area; after
incorporation it records one `core.source_files` row per recipe root and links each to the import
run, which adds two small tables to every packet it builds. An existing packet may gain those rows
by an amendment, which Part 03 §9.2 already permits. A root holding promoted files from an
interrupted promotion and a promotion record becomes repairable by retrying the build; a root
holding promoted files and no record stays refused, as today. `prune` reports `staging/` and any
path an unpublished promotion record lists apart from its strays. The writer's `amend` stages a
newly bound registry document under `staging/` instead of writing it at its final path before
validation, so a refused amendment writes nothing outside `staging/`.

No accepted clause is superseded whole. R134 §3.4's rule that a build owns each delivery location
stands and is the case of the staging area this revision generalizes.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. No concept's meaning changes. | None required. |
| logical prose and registry | Unchanged. The three provenance tables keep their declarations and optional presence, and no rule is added. | None required. |
| physical profiles | Part 03 §3 gains the staging-area subsection naming `staging/`. Part 03 §9.5 redefines a stray and lets an amendment remove a staging area and the paths a promotion record makes its own. Part 03 §§11.2 and 11.3 cite Part 05 §2 for the staging area and the new subsection for the rename. | `evidence/R<N>.json` names each anchor. |
| packet manifest and JSON Schemas | Unchanged. The promotion record is not a packet artifact and has no schema, and the manifest schema's registry `path` pattern already admits a path under `staging/`. | None required. |
| validation and import | Part 05 §§1, 2, 4.2, 6, 7, and 8 as quoted, and the headings of Part 05 §§4–8. Part 05 §§10 and 11 cite no stage number and are unchanged. | The writer tests below. |
| extensions | Registry content unchanged. The AIND package's two adapters re-point their Stage 1 citations to Part 05 §4.1. | The AIND suite passes. |
| reader, writer, validator, adapters | The writer records one `core.source_files` row per distinct recipe `root` and one `core.processing_run_inputs` row for each in `session.build`; writes a promotion record in `commit` and `amend` before the first write outside `staging/`; on a retry acts on a record as Part 05 §6 says, replacing `_refuse_occupied`'s refusal where a record makes the paths its own; stages `amend`'s newly bound registries under `staging/`; restates its module docstring's order; and re-points the fifteen stage citations in its source and the one in `pyproject.toml` to the section that states each rule. `prune` reports `staging/` and paths an unpublished record lists apart from its strays. The reader's two docstrings citing Part 05 §7 for the time origin re-point to Part 01 §2.2. The validator is unchanged, since it checks no writer obligation (Part 05 §10). | Writer tests below. |
| conformance fixtures and tests | Packet fixtures are unchanged, because every changed obligation binds a writer. Writer tests cover a build recording one input row per distinct root, including two sources sharing one root; a root recorded as the recipe states it; a leftover `staging/` emptied before a build; an interrupted commit and an interrupted amendment undone on retry from their promotion records; a stale record whose version is published, after which only `staging/` is removed; promoted directories with no record still refused; an unreadable record refused; a refused amendment leaving nothing outside `staging/`; and `prune` reporting `staging/` apart from strays. The adapter boundary probes re-point their Stage 1 citations. | `escapewheel-writer` and `escapewheel-aind` suites. |
| revision process and tooling | Ordinary ledger and evidence records, each clause targeting its owners by anchor. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. Part 07 §4's `PacketWriter` summary already reads "stage, validate, commit" and is unchanged. The repository and writer READMEs re-point their Stage 1 and Stages 2-6 citations, and the source inventories' Stage 1 citations re-point to Part 05 §4.1. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor: §3.1 at Part 05 §§1, 2, 4, 4.2, 5, and 8 and Part 00
§§2.4 and 8; §3.2 at Part 05 §2, the new Part 03 staging-area subsection, and Part 03 §§11.2 and
11.3; §3.3 at Part 05 §6; §3.4 at Part 05 §7; and §3.5 at Part 03 §9.5.

The negative cases distinguish the new rules from the current ones:

- a build from a recipe naming two distinct roots publishes two `core.source_files` rows and two
  `core.processing_run_inputs` rows, where the current writer publishes neither table;
- a build interrupted after moving `tables/` into place and before publishing, retried, removes the
  paths its promotion record lists and publishes, where the current writer refuses the root;
- a root holding `tables/` with no promotion record and no manifest is refused, naming the
  directory, and nothing is removed, as now;
- a root whose promotion record cannot be read is refused, naming the record, and nothing outside
  `staging/` is removed;
- an amendment whose validation fails leaves no new registry document outside `staging/`, where the
  current writer writes one at its final path and removes it; and
- `prune` over a root holding a leftover `staging/` reports no stray under it, where it now reports
  every file there.

The positive cases are a build recording one `core.source_files` row for two sources that share a
root and one `core.processing_run_inputs` row linking it to the import run; a root recorded exactly
as the recipe writes it, relative or not; a stale promotion record whose `packet_version` the
published manifest carries, after which the retry removes only `staging/`; and an interrupted
amendment whose record lists the retained superseded manifest and its written files, which the retry
removes before amending again. The order of §3.1 holds of the current writer's `commit`, so a test
that materialization's output and the import run row are validated with core before promotion holds
the corrected text rather than distinguishes it.

## 7. Open

Two builds at one packet root at once are outside this decision. §3.2 lets a writer beginning a
build empty a staging area, which assumes one build per root at a time, as the current writer does;
a later revision could add a lock to the staging area without changing any clause here.

A promotion record's format is the writer's, so one writer may meet a record another wrote and be
unable to read it; §3.3 then has it refuse rather than guess. A later revision could fix the format
if two writer implementations come to share packet roots.
