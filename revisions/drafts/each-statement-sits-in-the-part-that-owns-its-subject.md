# Each Statement Sits in the Part That Owns Its Subject

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `9bc97b61df20bfe74fb624170e841cc1688e4cf6` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§2.4, 3.2, 4.1, 4.2, 5.2, 7.3, 8, 9 and 10; Part 01 §§2.1, 2.2, 3.8, 3.9, 3.17, 3.23 and 3.24; Part 02 §§8.2, 8.3, 8.6, 10.3 and 12; Part 03 §9; Part 04 §5.3; Part 05 §§1, 2, 3.4, 3.7, 4.3, 4.4, 5.3, 10, 11, 13, 14.3 and 15; Part 06 §§3, 4, 6, 7 and 8; Part 07's title and §§1, 5, 6 and 7; Part 08's introduction and §§1 and 5; Part 09 §5.7; Part 10 §1; Part 12 §3 |
| **Depends on** | R32 §§2–6; R35 §§2 and 4–6; R39 §§2.1–2.4; R43 §2; R61 §§2.1, 2.2 and 3; R79 §2.1; R93 §3.5; R105 §3.3; R135 §3.1 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6 |

Section 3 is normative. Sections 1, 2, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 00 §9 assigns each numbered part a subject and forbids a part to state a second version of a
rule another part owns. Many statements agree with their owner, or have no other statement, but
sit in a part whose subject they are not, where an editor changing the owner has no reason to look:

- restatements of rules other parts own;
- a writer's procedure in Part 01, and a reader's and a validator's in Part 02;
- amendment, revalidation and cleanup rules that depend on no storage property, stated in Part 03,
  which binds only packets under the portable profile;
- dataset counts, benchmark timings and records of v0.1 withdrawals in normative text, several of
  them stale; and
- implementation planning in Parts 00, 07 and 08.

Part 05 also never says which actors it binds, and its writer-conformance definition asks a writer
to satisfy the whole part, validator and reader rules included. Two statements disagree with their
owners: Part 00 §4.1 says `core.intervals` holds one row per trial, and Part 01 §3.8 requires a
coordinate to carry a value on every axis of its frame, where R105 §3.3 lets it omit an axis its
source does not state. One rule has no
statement in prose: R39 accepted a session's time origin, and the reference validator enforces it,
but no part defines it.

This revision moves each statement to its owner and has every other part cite it. It states the
time origin and its check, has Part 05 name its actors, widens the amendment rules to every
profile, and moves the measurements behind Part 06's materialization rules to Part 10. No
registry document, schema or packet changes, and no verdict changes.

The change is structural. Appending would leave each misplaced statement standing beside its
relocation, which is the defect being repaired.

### 1.1 Structural crosswalk

The anchor bootstrap `9bc97b6` gave a canonical anchor to every section this revision moves,
retires, renumbers or revises that had none. Part 05 §1 is replaced under its number with a scope
section, `ew-validation-import-scope`. Four sections are added, each with a new canonical anchor,
and are cited by name in this revision since they do not yet have numbers:

- **the atlas-annotation subsection**, "A coordinate's atlas annotation", the last subsection of
  Part 02 §12 (`ew-coordinate-atlas-annotation`);
- **the discriminator-resolution subsection**, the last subsection of Part 05 §13
  (`ew-reader-discriminator-resolution`);
- **the amendment section**, "Amendment", a section of Part 05 before its normative references
  (`ew-packet-amendment`), with five subsections: "What an amendment is", "What an amendment may
  change", "Superseded manifests", "Scope of revalidation" and "Cleanup"; and
- **the materialization measurements**, the last section of Part 10
  (`ew-materialization-measurements`).

Part 05 §1's former anchor `ew-import-validation-principle` becomes an alias in Part 05 §2, and
Part 03 §9.6's `ew-packet-version-scope` an alias in the amendment section's first subsection. A
moved subsection keeps its canonical anchor, and a retired section's anchor is not reused.

| old location or statement | disposition | new location | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 00 §2.4, "the actor Part 05 binds throughout" | revise in place | same section, citing Part 05 §1 | none | §3.1 |
| Part 00 §3.2, the content-class table | replace with a citation | Part 02 §2.2 | none | — |
| Part 00 §4.1, the grain paragraph | replace with a citation | Part 02 §11 | none; Part 02 §11 declares each core resource's grain | — |
| Part 00 §4.2 | retire | Part 01 §3.14; the core registry's `core.units` columns and their rule | none; the v0.1 withdrawal is history | — |
| Part 00 §5.2 | retire | Part 06 §7; Part 00 §5.1 cites Part 06 | none | — |
| Part 00 §7.3, the `packet_version` paragraph | delete | the amendment section's "What an amendment is" | none | §3.2 |
| Part 00 §8 | retire | Part 07 §2 describes the distributions | none | — |
| Part 00 §§9 and 10 | renumber | one lower | none | — |
| Part 01 §2.1, "MUST carry a `*_name` column" | replace with a citation | Part 02 §8.2 | none | — |
| Part 01 §2.2 | revise in place | same section | states the origin, its absence and seconds | §3.3 |
| Part 01 §3.8, "MUST carry one value per axis" | revise in place | same section | a coordinate may omit an axis | §3.6 |
| Part 01 §3.8, "one row per axis" | replace with a citation | Part 02 §12.7 | none | — |
| Part 01 §3.8, the atlas-column prohibition | move | the atlas-annotation subsection | none; a table's columns are its declaration's | — |
| Part 01 §3.9, the acquisition-order rule | move | Part 05 §4.3 | none; an importer is a writer | — |
| Part 01 §3.17, "nullable" and the array count | revise in place | same section | none | — |
| Part 01 §3.23, the calibration ages and module count | delete | none | none | — |
| Part 01 §3.24, "one row per axis", the coordinate counts and the struck columns | revise in place | same section | none | — |
| Part 02 §8.2, the column counts and the script | revise in place | same section | none | — |
| Part 02 §8.3, the reader's resolution | move | the discriminator-resolution subsection | none | — |
| Part 02 §8.6, the band counts, measurements, key count and script | revise in place | same section | none | — |
| Part 02 §8.6, the unfilled-column report | move | Part 05 §5.3 | none | — |
| Part 02 §10.3, the second sentence | delete | Part 05 §5.3 states it | none | — |
| none | add | the atlas-annotation subsection | none | — |
| Part 03 §9 | retitle and replace the body | same section, "Amendment and retention" | the portable realization only | §3.2 |
| Part 03 §9.1 | move, split | the amendment section's "What an amendment is"; a new file per gaining resource stays in Part 03 §9 | binds every profile | §3.2 |
| Part 03 §9.2 | move | the amendment section's "What an amendment may change" | binds every profile | §3.2 |
| Part 03 §9.3 | move, split | the amendment section's "Superseded manifests"; the `manifests/` location stays in Part 03 §9 | binds every profile | §3.2 |
| Part 03 §9.4 | move | the amendment section's "Scope of revalidation" | binds every profile | §3.2 |
| Part 03 §9.5 | move, split | the amendment section's "Cleanup"; the stray's definition stays in Part 03 §9 | binds every profile | §3.2 |
| Part 03 §9.6 | merge | the amendment section's "What an amendment is" | binds every writer | §3.2 |
| Part 04 §5.3, the last paragraph | move | Part 05 §14.3 | none | — |
| Part 05 §1 | replace | same number, "Scope" | names the actors | §3.1 |
| Part 05 §1, its former content | merge | Part 05 §2's opening | none | — |
| Part 05 §3.4, the declared-fact list | replace with a citation | Part 12 §7 | none | — |
| Part 05 §3.7, writing to and closing standard input | replace with a citation | Part 12 §4 | none | — |
| Part 05 §4.3 | add a paragraph | same section | none | — |
| Part 05 §4.4, the empty arrival | replace with a citation | Part 12 §5 | none | — |
| Part 05 §4.4, the per-protocol failure channel | move | a column of Part 12 §3's table | none | — |
| Part 05 §5.3 | add two paragraphs | same section | the origin check; the unfilled-column report | §3.4 |
| Part 05 §10, the writer class | revise in place | same section | a writer's obligations only | §3.1 |
| Part 05 §11, the lead sentence | revise in place | same section | the criteria are necessary | §3.1 |
| none | add | the discriminator-resolution subsection | none | — |
| Part 05 §14.3 | add a paragraph | same section | none | — |
| none | add | the amendment section | every profile | §3.2 |
| Part 05 §15 | renumber | one higher, after the amendment section | none | — |
| Part 06 §3, the measurements | move | the materialization measurements | none | §3.5 |
| Part 06 §4, the population-window measurement | move | the materialization measurements | none | §3.5 |
| Part 06 §6 | retire | Part 09 §3 places task-shaped columns | none | — |
| Part 06 §§7 and 8 | renumber | one lower | none | — |
| Part 07's title, §1 "and the phase plan" | revise in place | same | none | — |
| Part 07 §5 | retire | none | none | — |
| Part 07 §6, the instruction | delete; renumber one lower | same content | none | — |
| Part 07 §7, the opening | revise in place; renumber one lower | same content | none | — |
| Part 08's introduction | revise in place | same, citing Part 05 §10 | none | — |
| Part 08 §1, the spike tables' columns | revise in place | same section | none | — |
| Part 08 §5 | retire | Part 05 §10 | none | — |
| Part 09 §5.7, "remains the route every implementation supports" | replace with a citation | Part 12 §3 | none | — |
| Part 10 §1 | revise in place | same section | none | §3.5 |
| none | add | the materialization measurements | none | §3.5 |

## 2. Background

Section 2 is informative. Observations are from the recorded baseline, whose quick verifier passes
all 32 stages. Quotations lowercase their requirement keywords.

### 2.1 Restatements

| restating text | owner | observation |
|---|---|---|
| Part 00 §3.2's content-class table | Part 02 §2.2 | the same five rows and columns |
| Part 00 §4.1's grain paragraph | Part 02 §11 | "one row per trial in `core.intervals`", where Part 02 §11 declares bounded spans discriminated by kind |
| Part 00 §4.2 | Part 01 §3.14 and the core registry | the sole spike representation, and the `core.units` summary columns the registry declares and checks |
| Part 00 §5.2 | Part 06 §7 | a materialization is a realization, not a kind |
| Part 00 §7.3's last paragraph and Part 03 §9.6 | none | two versions of one rule: Part 00's binds every writer, Part 03's a writer "under a future lakehouse profile" |
| Part 01 §§3.8 and 3.24 | Part 02 §12.7 | a frame's values are one row per axis |
| Part 02 §10.3's second sentence | Part 05 §5.3 | why a storage check written as SQL fails silently, word for word |
| Part 04 §5.3's last paragraph | Part 05 §14.3 | a reader needs no validation receipt; Part 04 adds the per-resource inspection |
| Part 05 §§3.4, 3.7 and 4.4 | Part 12 §§4, 5 and 7 | an adapter's declared facts and their names; writing and closing standard input; an owned resource arriving empty |
| Part 09 §5.7 | Part 12 §3 | `files-v0.1` "remains the route every implementation supports", where Part 12 §3 has a build support every protocol of the group |

Part 05 §4.4 states which channel carries a failure under each protocol, which Part 12 does not.
The channel is a property of the protocol, so it moves into Part 12 §3's table.

### 2.2 Two summaries disagree with their owners

Part 01 §3.8 requires a coordinate to "carry one value per axis that frame declares". R105 §3.3
lets a coordinate carry values on fewer axes where its source states none on the rest, and Part 02
§12.7 states that permission. The ledger places R105 §3.3 in Part 01 §3.8, which states the
opposite. Both packaged sessions state every axis, so no packet's verdict depends on the choice,
and no check requires every axis: a value on an undeclared axis is an orphan, while a missing one is
not a finding.

Part 00 §4.1's `core.intervals` grain is a stale description rather than a rule: no check counts
rows per trial, and Part 02 §11's declaration governs.

### 2.3 Operational rules in Parts 01 and 02

Part 01 §3.9 obliges an importer to examine a source in acquisition order. That is a writer's
normalization procedure, which Part 05 §4.3 owns. The consumer rules of the same section state what
a converted value means and stay.

Part 02 §8.3 says a reader should offer a discriminator's resolution, and Part 02 §8.6 says a
validator should report a `metadata` column that no row fills. Part 05 §13 owns reader operations,
and Part 05 §5.3 already states the comparable `columns_duplicated` report. The reference validator
implements the second as `<resource_id>.metadata_unfilled`.

Part 01 §3.8 forbids a table to carry an atlas structure's full name or ancestry path as columns,
which constrains a declaration. Part 01 §3.17 calls `semantic_type` "nullable", Part 02's presence
term, where the semantic statement is that a writer leaves it unfilled.

### 2.4 Amendment in the portable profile

Part 03 §1 makes Part 03 normative only for a packet declaring `escapewheel-portable-v0.1`, so a
packet under any other profile has no amendment rule. Most of Part 03 §9 depends on no storage
property: what an amendment may change and why, the ordering of `packet_version`, the refusal to bind
two digests under one registry ID and version, the scope of revalidation, cleanup's order, the
protection of strays and the retention floors. The portable profile's own part is how an amendment is
realized: a resource that gains rows becomes a new file, superseded manifests live under
`manifests/`, and a stray is a file under the packet root.

Part 00 §9 gives Part 05 the publication of a packet, and an amendment publishes one. Only one
profile exists, so widening the rules changes no packet, writer or validator. Leaving them in Part 03
would let a future profile's amendment rewrite core, which Part 03 §9.2 forbids for a reason that is
not about storage.

Outside accepted records, `revisions/impact.py` lists 55 live citations of Part 03 §9 and its
subsections: the writer's amendment, cleanup and verification code and its tests, the validator's
revalidation, Part 05 §§6 and 8, and Part 07 §3.

### 2.5 Part 05's actors

Part 05 §1 opens "Validation is importation", a build rule. The part first names an actor class in
Part 05 §10, which calls a writer conforming "when it satisfies this part", a definition R79 §2.1
wrote. The part also binds validators (Part 05 §§5, 9, 10 and 14.5) and readers (Part 05 §§13 and
14.3), so no writer can satisfy all of it, and Part 00 §2.4 calls the writer "the actor Part 05
binds throughout". The sections already group by actor, so one scope section states the boundary
without renumbering Part 05's fifteen sections and their citers.

Part 05 §11 opens "A writer conforms when it:", which reads as sufficient, where Part 05 §10 adds
every writer obligation of the part.

### 2.6 Evidence and history

| location | content | state |
|---|---|---|
| Part 01 §3.17 | `ElectricalSeries` on 22 of 25 arrays | recorded in R103 |
| Part 01 §3.23 | calibrations 133 and 302 days old; six modules citing one file | recorded in R89 |
| Part 01 §3.24 | 8,448 of 27,557 coordinate rows | recorded in R105 |
| Part 02 §8.2 | 16 name columns, 6 naming a kind; `registry/check.py` sorts them | `registry/check.py` now reports 16 and 10; the registry-document contract checks the name pairing as `registry.identity.name` |
| Part 02 §8.6 | 17 and 3 tables per band; 286,896,563 unfilled rows; 1.9 kB and 394.6 ms; 20 keys; `registry/check.py` enforces the bands | a recount under the section's definition gives 16 and 5; the contract checks the bands as `registry.metadata.eligibility` |
| Part 06 §§3 and 4 | alignment timings, a 100.6% size ratio, a 708-row view, a population window at 0.025 s against 7.7 s | measurements, which Part 10 owns |
| Part 06 §6 | four v0.1 resources withdrawn | history; its last sentence repeats Part 09 §3 |

Every count and measurement deleted from a part remains in the accepted revision that measured it.
R93 §3.5 kept R43's timings in Part 06 because "what they justify is a materialization rule rather
than a storage choice". Part 10 §1 already carries a number supporting a rule stated elsewhere, and
it records each measurement's date where Part 06 records none.

### 2.7 Implementation planning

Part 00 §8 lists five components of "the first implementation", which Part 07 §2's three
distributions no longer match. Part 07 §5 is a phase-status table, Part 07 §6 instructs developers
when to run the corpus, and Part 07 §7 opens by stating where a number belongs. Part 08 §5 is a
six-item conformance checklist beside Part 05 §10's definition. Part 08 §1 says the spike tables
carry "four identifiers, a tick, and a clock per row"; the registry declares `session_id`,
`unit_id`, `t_tick` and `amplitude` on `core.spike_events`, and `session_id`, `unit_id`, `t_tick`,
`clock_id` and `time_bucket_tick` on `analysis.spike_events`.

### 2.8 The time origin

R39 §2.1 defines a session's origin as the earliest `start_tick` among its clocks' observation
intervals, expressed on the reference clock. R39 §2.2 adds that a packet declaring no observation
intervals declares no `t_zero_tick`, R39 §2.3 derives seconds through the reference clock's rational
rate and admits negative values, and R39 §2.4 forbids a writer that cannot map a start to declare an
origin. The ledger places R39 §§2.2–2.4 in Part 01 §2.2 and R39 §2.1 in the registry, whose
`t_zero_tick` description names the earliest observed tick. Part 01 §2.2 states only that seconds
derive from the origin, that a consumer lacking one refuses, and R39 §2.4.

The reference validator reports `time.origin_not_earliest` at `error` where a declared `t_zero_tick`
differs from the mapped minimum by more than one reference-clock tick, and `time.origin_unmappable`
where the session names no reference clock or a clock's start does not map. No part states either
check or the tolerance. A writer's estimator may fit anchors it does not record, so a validator's
mapping cannot reproduce the writer's exactly, and exact equality would fail a correct origin on
rounding. Part 01 §3.9's alignment tolerance is a percentile over an alignment, not a bound on one
value.

The reference validator maps a start through the clock's anchors onto its parent and treats the
parent as the reference; it maps through no linear transform and follows no parent chain. The two
AIND packets, of subjects 786867 and 776259, parent every clock directly to the reference through
anchors and declare origins of 450804406692 and 361746131863. No test or corpus variant exercises
either check.

## 3. Decision

Six clauses change what a part states; §1.1 places every other statement without changing its
meaning.

### 3.1 Part 05 names the actors it binds

Part 05 binds three actors of Part 00 §2.4. Part 05 §1 states which of its sections bind each:

| actor | sections |
|---|---|
| a writer, for each build it performs and each adapter it ships | Part 05 §§2–4, 6–8, 9.2, 9.3, 11, 12 and 14.4, and the amendment section |
| a validator | Part 05 §§5, 9, 10 and 14.5, and the amendment section's "Scope of revalidation" |
| a reader | Part 05 §§13 and 14.3 |

Part 05 §3 also constrains a recipe, Part 05 §6 what a reader observes of a commit, Part 05 §12 a
packet and a consumer, and Part 05 §§14.1, 14.2 and 14.6 every implementation. Part 05 §10 defines
the two conformance claims. Part 00 §2.4 cites Part 05 §1 for the actors Part 05 binds.

A writer conforms when it satisfies every obligation Part 05 places on a writer, on a build it
performs or on an adapter it ships, which includes recording provenance (Part 05 §7), and meets Part
05 §11's criteria. A packet is not judged by writer conformance. Part 05 §10 states this in place of
"satisfies this part", and Part 05 §11 opens "A conforming writer at least:".

### 3.2 Amendment rules bind every profile

The rules of Part 03 §§9.1–9.6 that depend on no storage property bind a writer and a validator under
every profile, and the amendment section states them:

- what an amendment is: a new version of an existing packet that MUST NOT modify the bytes of any
  resource a superseded manifest names, and whose `packet_version` MUST sort strictly after the
  superseded one as a semantic version;
- what an amendment may and MUST NOT change, with Part 03 §9.2's table, asymmetry and provenance
  exception, where adding rows to a provenance table is permitted without saying how they are stored;
- that every superseded manifest is retained with its own `created_at` and validation record, the
  superseded registry copy retained at the path its manifest records, and a writer MUST refuse an
  amendment binding two digests under one registry ID and version;
- Part 03 §9.4's scope of revalidation, unchanged; and
- cleanup's order, the protection of strays, the prohibition on an amendment deleting anything, and
  the retention floors.

`packet_version` versions the bundle. A writer MUST NOT increment it for a rewrite of a table's
rows. This one rule replaces Part 00 §7.3's paragraph and Part 03 §9.6.

A stray is a file no manifest ever named, as the packet's profile defines it. Part 03 §9 keeps the
portable profile's realization and cites the amendment section for the rules:

- a resource that gains rows, a provenance table included, is written as a new file that the
  amended manifest names;
- superseded manifests are retained under `manifests/`, and a packet never amended carries no
  `manifests/` directory; and
- a stray is a file under the packet root that no manifest ever named, that lies outside the staging
  area (Part 03 §3.4), and that neither is listed by nor lies inside a directory listed by a
  promotion record whose `packet_version` is unpublished (Part 05 §6).

### 3.3 A session's time origin is its earliest observation on the reference clock

A session's time origin is a tick of its reference clock: the earliest observation-interval start
among the session's clocks, each mapped onto the reference clock (Part 01 §3.9). A writer declaring
an origin MUST declare that one. A writer MUST NOT declare an origin for a session with no
observation interval, and no checker verifies this. A writer unable to map one of the session's
observation starts onto the reference clock MUST NOT declare an origin.

A tick's seconds are its distance in ticks from the origin on the reference clock, divided by that
clock's rational rate, and are negative for a tick before the origin. Floating-point seconds MUST
NOT be the canonical representation. A consumer lacking an origin MUST refuse to derive seconds
rather than assume one.

Part 01 §2.2 states these rules and names no column.

### 3.4 A validator checks a declared origin

A validator MUST check each declared origin by mapping each of the session's observation starts onto
its reference clock, through the anchors or transform of every clock on the path from that start's
clock to the reference, within the alignment bound Part 02 §12.6 records. It MUST report, at `error`:

- under the check ID `time.origin_unmappable`, a session that declares an origin but no reference
  clock, or whose observation start does not map; and
- under the check ID `time.origin_not_earliest`, a declared origin more than one reference-clock
  tick from the earliest mapped start.

The tolerance is one tick because a writer's estimator may fit anchors the writer does not record.
Both findings belong to the core registry under Part 05 §9.5. Part 05 §5.3 states this rule.

### 3.5 Part 10 carries the measurements behind Part 06's materialization rules

Part 10's materialization measurements record what supports Part 06 §§2–4, each with its date:

- aligning all 6,781 units' spikes of subject 776259's session to one event and window costs 0.13 s
  to 1.72 s against trains already in memory, and a materialized copy of four alignments is
  288,550,992 rows, 100.6% of the spike table (by 2026-09-01; toolchain not kept);
- a wide trial table is 708 rows returned in 7.5 ms as a view (the same); and
- a ten-second window over all 4,505 units of subject 786867's session costs 0.025 s from
  `analysis.spike_events` against 7.719 s from the source NWB's per-unit spike times
  (2026-09-03; toolchain not kept).

Part 10 §1's scope includes a measurement supporting an analysis rule. Part 06 states no
measurement, and Part 06 §4 is normative throughout.

### 3.6 A coordinate carries values on the axes its source states

A coordinate MUST carry each of its values on an axis its frame declares, and MAY carry values on
fewer axes than the frame declares where its source states none on the rest. Part 01 §3.8 states
this in place of one value on every axis, and cites Part 02 §12.7 for the values' rows.

## 5. Consequence

No registry document, schema, descriptor or packet changes, so no identifier advances and no packet
is rebuilt. No verdict changes. §3.1 narrows what writer conformance asks without changing a
packet's claim. §3.2 changes nothing under the one profile that exists. §§3.3 and 3.4 state what R39
accepted and the reference validator enforces. §3.6 restores R105 §3.3's permission in Part 01, and
every shipped packet states every axis.

R79 §2.1 is superseded in part by §3.1: writer conformance no longer includes validator and reader
obligations. R93 §3.5 is superseded in part by §3.5: R43's timings move to Part 10, and R93 §3.5's
rule for Part 07's own numbers stands. R43 §2 becomes `rationale`: no part declares the withdrawn
table, so nothing is left to bind.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Part 01 §2.2 takes §3.3 and Part 01 §3.8 takes §3.6; §1.1's relocations and deletions apply to Part 01 §§2.1, 3.8, 3.9, 3.17, 3.23 and 3.24. | The evidence record names `ew-time-basis` and `ew-coordinate-concept`. |
| logical prose and registry | Part 02 §§8.2, 8.3, 8.6 and 10.3 follow §1.1, and the atlas-annotation subsection is added. No declaration changes; the `t_zero_tick` description already names the earliest tick. | `registry/check.py` passes unchanged. |
| physical profiles | Part 03 §9 keeps the portable realization and cites the amendment section; §§9.1–9.6 are removed and §§10–12 keep their numbers. The descriptor is unchanged. | The evidence record names `ew-portable-amendment`. |
| packet manifest and JSON Schemas | Unchanged. Part 04 §5.3 loses a reader paragraph and its citers of Part 03 §9 cite the amendment section. | None required. |
| validation and import | Part 05 §1 becomes its scope (§3.1), Part 05 gains the discriminator-resolution subsection, the amendment section (§3.2) and two Part 05 §5.3 paragraphs (§3.4 and the moved report), Part 05 §§10 and 11 follow §3.1, and Part 05 §15 is renumbered. | The evidence record names each new anchor. |
| extensions | Unchanged. Part 09 §5.7 cites Part 12 §3; no extension registry or adapter changes. | None required. |
| reader, writer, validator, adapters | The validator maps an origin through a transform and a parent chain, and evaluates each session against its own reference clock, where it now maps through anchors onto the parent and takes the packet's first reference clock. Code comments and messages citing Part 03 §9, Part 01 §2.2 for the check, and "Part 01 §3.9's tolerance of one parent tick" cite the amendment section and Part 05 §5.3. The writer and reader change only citations. | The validator suite with the cases of §6. |
| conformance fixtures and tests | Validator tests for both origin checks, and a corpus variant for each, as §6 names. | `fixtures/corpus.py` and the validator suite. |
| revision process and tooling | Ledger destinations follow their text: clauses placed in Part 03 §§9.1–9.6, Part 01 §§3.8 and 3.9, Part 02 §§8.3 and 8.6, Part 04 §5.3, Part 05 §§1 and 10, Part 06 §6 and Part 07 §7 move to their new anchors. R39 §2.1 becomes `applied` at `ew-time-basis`, and R39 §2.4 gains `ew-validation-shim`. R79 §2.1 and R93 §3.5 gain notes; R43 §2 becomes `rationale`. The placement-defect inventory closes PD-007, PD-009 to PD-019 and PD-029 to PD-032. | `ledger.py`, `evidence.py`, `repoint.py` and `revisions/PLACEMENT-DEFECTS.md`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. Citers of Part 00 §§9 and 10 follow the renumbering: Parts 02, 03, 04 and 12, the specification README and the roadmap. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor:

- §3.1 at `ew-validation-import-scope`, `ew-conformance-classes` and `ew-writer-acceptance-criteria`;
- §3.2 at `ew-packet-amendment` and `ew-portable-amendment`;
- §3.3 at `ew-time-basis`;
- §3.4 at `ew-validation-shim`;
- §3.5 at `ew-materialization-measurements`; and
- §3.6 at `ew-coordinate-concept`.

These cases distinguish §3.4 from the current specification, which states no check:

- a session whose declared origin is two reference-clock ticks after its earliest mapped start fails
  `time.origin_not_earliest`, and one a single tick away passes;
- a session declaring an origin whose probe clock declares an observation interval and no anchors
  fails `time.origin_unmappable`;
- a session declaring an origin whose clock is mapped by a linear transform passes where the origin
  is the transformed minimum, which the reference validator now reports as unmappable; and
- a clock parented to another non-reference clock maps through both, where the reference validator
  now reads the parent's ticks as the reference's.

Both AIND packets pass unchanged. §3.6's evidence is a corpus packet whose coordinate omits one axis
of its frame, which passes, as it does today.

§§3.1, 3.2 and 3.5 change no verdict, so their evidence is review of Parts 03, 05 and 10 against
each clause and the rerun of the writer's amendment and cleanup suites after their citations move.
§3.3's rule for a session with no observation interval is unchecked, and no corpus packet declares
an origin.
