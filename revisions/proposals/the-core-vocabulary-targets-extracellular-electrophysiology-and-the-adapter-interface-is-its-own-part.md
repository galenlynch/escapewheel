# The core vocabulary targets extracellular electrophysiology, and the adapter interface is its own part

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `752844b29641668a55d148d2f28b244b2cd0a95b` |
| **Decision domain** | specification |
| **Affects** | Part 00 §§1, 3.1.3, 3.2, 9 and 10; Part 02 §2.2; Part 03 §§1, 11 and 12; the Part 05, 07 and 09 sections citing Part 03 §11, and Part 09 §5.8; a new Part 12; the specification README; `framework.py`, `headings.toml` and the specification-framework conformance probe; `revisions/applied.toml`; the descriptions in `registry/adapter.schema.json` and `registry/recipe.schema.json`; source comments and developer documents citing Part 03 §11 |

## 1. Problem

Part 00 §1 states what the specification is for: "a portable representation of extracellular
electrophysiology data". The packet mechanism does not confine a packet to that modality. The
manifest (Part 04), the registry model (Part 02 §§2–10), the portable profile (Part 03), validation
(Part 05), extensions (Part 09) and the rule language (Part 11) contain no rule that needs a spike,
a unit or an electrode. Every table of those kinds is optional, and a packet holding only behavior
conforms today. The core vocabulary is what targets extracellular electrophysiology: its sorting,
unit and electrode tables, and the Part 01 concepts behind them. The text states neither fact
precisely. Part 00 §3.2 and Part 02 §2.2 then define the `core` content class as "domain-general
normalized facts", which contradicts Part 00 §1 on the most natural reading of either.

The same part holds a second defect. Part 03 §11, "Reaching a source", specifies what passes
between a build and its adapters: the protocols rows cross by, the values a build supplies, what a
delivery states, and the declaration document. Part 00 §9 gives Part 03 a different subject, the
"portable physical mapping of logical resources to stored bytes". §11 is 41% of Part 03's words, and
an adapter author has to read it alongside Part 05 §§3.4, 3.7 and 4.4 and Part 09 §5.8, which hold
further rules of the same interface.

The two defects share a roadmap entry and nothing else, and §6 asks whether to split them.

## 2. Evidence

Every count was measured at the recorded baseline. Registry counts come from
`registry/logical_schemas.json` and `registry/extensions/*.json`. Citation counts come from a
regular-expression scan of every file tracked at the baseline except the generated single-file
rendering. The scan matched `Part 03 §11`, `Part 03 §11.n` and `§§` lists including 11, the five
§11 anchors, and `revisions/applied.toml` entries whose Part 03 destination lies in §11.

### 2.1 The specification states three scopes

| location | what it says | scope it implies |
|---|---|---|
| Part 00 §1 | "a portable representation of extracellular electrophysiology data" | extracellular electrophysiology |
| Part 00 §1, design objectives | a packet is "straightforward to produce from existing acquisition and sorting outputs" | extracellular electrophysiology |
| Part 00 §3.2 and Part 02 §2.2 | `core` holds "domain-general normalized facts" | every domain |
| Part 09 §3 | the fields core carries are those needed to interpret "units, clocks, channels, arrays, or spike times"; a sidecar takes what is not "required to interpret the recording" | a recording, with spikes |
| specification README §1 | "extracellular electrophysiology data", then "whether neurophysiology data can be represented" | two scopes in consecutive paragraphs |
| root README | "An extracellular-electrophysiology data-lake format" | the format itself, not its vocabulary |
| Part 08 §1 | "One ecephys session with behaviour" | an example; consistent with any scope |

The word "domain" carries two senses. R71 §2.2 introduced "domain-general" to put identity, time,
instruments, arrays, units, spikes, intervals and provenance in core, with a task's own facts in an
extension. There, "domain" means the task or lab an extension serves, as in Part 00 §4.1 ("a fact
a single domain owns belongs in that domain's extension") and Part 09 §2 ("domain-rich,
lab-specific facts"). A reader of Part 00 meets the other sense first, the recording modality of
§1. Under that sense, "domain-general" claims what 15 declared tables contradict (§2.2).

The review that raised the finding, the project sanity check of 2026-09-17, recommended
distinguishing the packet architecture from "the current ecephys/core profile". Part 00 §3.1.3
already defines a physical profile, and `profile_id` names one, so a vocabulary called a profile
would give that word a second meaning.

### 2.2 Fifteen of 43 declared tables are extracellular

The core registry declares 46 resources. Its 42 `core` declarations are 40 tables, the dense-array
family `core.array_asset_instances` and the opaque family `core.media_asset_instances`. Its 4
`analysis` declarations are 3 tables and one dense-array family.

Fifteen of the 43 tables are specific to extracellular electrophysiology. Fourteen are core:
`core.probes`, `core.electrodes`, `core.electrode_coordinates`, `core.electrode_coordinate_values`,
`core.sorting_runs`, `core.sorting_run_channels`, `core.curation_versions`, `core.units`,
`core.spike_events`, `core.unit_quality_labels`, `core.unit_electrodes`, `core.unit_coordinates`,
`core.unit_coordinate_values` and `core.unit_observation_intervals`. The fifteenth is
`analysis.spike_events`. Together they hold 112 of the 348 table columns and 17 of the 77 Tier 2
rules.

None of them is required. `core.sessions` is the one required singleton (Part 02 §2.5). Its
required `subject_id` references `core.subjects`, so every packet carries those two tables, and
neither is extracellular. No declaration names an extracellular table in `requires`. The general
tables reach into the extracellular ones at one point only:

- none of the 60 rules on the other 28 tables reads an extracellular table;
- one general column references one, the nullable `core.array_channels.electrode_id`; and
- the general tables close two vocabularies, `core.processing_runs.status` and
  `core.subjects.sex`, and neither is extracellular.

The prose has the same shape. Eight of the 24 concepts in Part 01 §3 are extracellular: Probe,
Electrode, Unit, Spike event, Quality label, ElectricalSeries, Sorting run and Curation version.
Part 00 §4.2, Part 02 §12.1, Part 02 §12.2, Part 05 §13.2 and Part 06 §4 state rules for
extracellular tables, and each binds only where its tables are present.

### 2.3 A packet without extracellular data conforms

The four extension registries show what a non-extracellular domain needs from core:

| extension | core declarations it references |
|---|---|
| `dynamic_foraging` | `core.sessions`, `core.clocks`, `core.intervals` (also read by a rule) |
| `vr_foraging` | `core.sessions`, `core.intervals` |
| `aind_opto` | `core.sessions`, `core.devices` |
| `aind_unit_qc` | `core.sessions`, `core.units` |

`aind_unit_qc` is the one extension that depends on the extracellular vocabulary. None of the four
declares a required singleton.

The conformance corpus has no packet without extracellular tables, so a probe built two. A script
took the corpus's valid packet from `fixtures/build.py`'s `content()`, deleted tables, wrote the
result with its `write_packet()`, and validated it with `escapewheel_validator.validate`:

- with the 14 extracellular core tables deleted, leaving 15 core tables and
  `dynamic_foraging.trials`, the packet passed with no error or warning;
- with only `core.sessions` and `core.subjects` kept, it passed as well.

The only findings either drew were `info` findings, about unfilled `metadata` columns, extension
tables the packet did not carry, and data-page types left unassessed. A behavior packet does meet
one constraint, which applies to every packet: `core.intervals` requires each `interval_kind` to name
an extension resource, so a packet carrying intervals carries an extension.

### 2.4 Part 03 §11 is an interface between writer components

| section | subject | canonical anchor | words | keywords |
|---|---|---|---:|---:|
| §11 | the four delivery routes and why the section is in Part 03 | `ew-reaching-a-source` | 234 | 0 |
| §11.1 | protocol groups | `ew-protocol-groups` | 485 | 8 |
| §11.2 | what a build supplies | `ew-build-supplied-values` | 953 | 26 |
| §11.3 | what a delivery states | `ew-referenced-resource-delivery` | 687 | 19 |
| §11.4 | the Arrow IPC floor | none | 409 | 8 |
| §11.5 | the declaration document | `ew-adapter-declaration-document` | 513 | 11 |
| §11.6 | reaching an adapter that has to be running | none | 173 | 3 |

The section runs 151 lines and 3,454 words, against Part 03's 651 lines and 8,342 words. It holds
75 of Part 03's 190 BCP 14 keywords. Its clauses bind builds and adapters, the two terms Part 00
§2.4 resolves to a writer, and none binds a reader or a validator. The profile descriptor
`registry/physical_profiles/escapewheel-portable-v0.1.json` owns the profile's identifiers,
interfaces, floors and anchors, and it names no protocol and no §11 anchor.

§11 argues for its own placement: it is "the profile's rather than the pipeline's because every
rule in it would change if the profile changed". Most of its rules would not change. The input
object on standard input, `needs` and `accepts`, the declaration document, identifiers as source
names, and an empty resource arriving empty depend on no storage technology. Three things do:

- the protocol group, whose members carry rows as Parquet files, Arrow IPC streams and Arrow Flight;
- the Arrow IPC floor of §11.4; and
- a packet-owned array, which an adapter writes as Zarr v3 (Part 03 §6.1) into `array_location`.

The first two are formats for exchange between processes rather than for storing a packet. The third
writes the packet's own bytes. Part 00 §3.1.3 makes a physical profile the only abstraction level
whose rules may depend on a storage technology, and Part 03 §1 makes Part 03 the only such part. A
new part holding §11 therefore needs a place under those two sentences.

§11 carries two further attachments:

- **Incorporations.** Part 03 §1 incorporates `registry/resources.schema.json` as the shape of
  §11.3's resource document, and §11.5 incorporates `registry/adapter.schema.json`.
- **References.** §11 is the only direct invoker of the Arrow entry in Part 03 §12; Part 03 §5.6
  mentions Arrow informatively. Parquet is invoked by Part 03 §5 and again by §11.1's `files-v0.1`
  row.

Other parts hold more of the interface, several times as a restatement:

- Part 05 §3.4 lists the six facts an adapter declares, whose document form is §11.5's.
- Part 05 §3.7 restates §11.2's obligation to write the supplied object to standard input and close
  it, and adds that a build reads while it writes.
- Part 05 §4.4 restates §11.3's rule that a resource with nothing to deliver arrives empty, and says
  which channel carries a failure under each protocol.
- Part 09 §5.7 restates the protocol group for an extension's rows.
- Part 09 §5.8 specifies a run's report: its JSON form, and which channel carries it under each
  protocol. Its subject is "an extension". §11, however, lists a report among every adapter's
  routes, §11.2 supplies `report_path` to any adapter, and §11.5 sends every adapter's `stated`
  values through the report.

### 2.5 Citations into Part 03 §11

| population | citations | after a move |
|---|---:|---|
| Part 03 §1, citing §11.3 | 1 | becomes a citation of the new part |
| §11, citing other Part 03 sections (§§1, 3.4, 5.5, 6.1, 8.1, 8.2) | 6 | each becomes a Part 03 citation |
| §11, citing its own subsections | 13 | local, renumbered with the section |
| Parts 05 (12), 07 (6) and 09 (4) | 22 | rewritten |
| `revisions/applied.toml` destinations | 29 | rewritten; below |
| `headings.toml` anchor records | 5 | regenerated |
| accepted records, 12 of them | 133 | unchanged |
| committed evidence manifests, 6 of them | 13 | unchanged |
| Python source and tests, 35 files | 160 | rewritten |
| incorporated schema descriptions, `adapter.schema.json` (5) and `recipe.schema.json` (1) | 6 | rewritten; vendored copies regenerate |
| developer documents, 5 files | 9 | rewritten |

The 29 ledger destinations belong to 24 Decision clauses of R115, R116, R117, R119, R129, R130,
R133, R134 and R135. Twenty-two are anchored and change only their part. Seven are numeric (§11.2
four times, §11.4 twice, §11.6 once) and migrate to anchors, as a structurally affected destination
does. §11.4 and §11.6 have no canonical anchor, so a structural draft needs the metadata-only anchor
bootstrap commit that `revisions/CONTRIBUTING.md` requires before its final appraisal.

Accepted records are read at their own baselines. `revisions/evidence.py` resolves an evidence
manifest against the working tree only before its record is committed. Neither population
therefore needs an edit.

Four source comments cite `Part 03 §11` with no subsection. `revisions/check_citations.py` would
flag a stale `Part 03 §11.2`, since no such heading would remain. If Part 03 §12 became §11, the
bare form would instead resolve to the normative references. `headings.py --check` still reports
it, because the heading of Part 03 §11 changes, and it lists every citer.

### 2.6 Renumbering cost by position

| new part's position | parts renumbered | live citations of renumbered parts | accepted-record citations then naming another part |
|---|---|---:|---:|
| 12, after Part 11 | none | 0 | 0 |
| 06, after Part 05 | 06–11 | 188 in 48 files | 234 |
| 04, after Part 03 | 04–11 | 1,112 in 120 files | 697 |

Both counts cover `Part NN §` citations, and the live count also covers ledger `part` values. The
accepted-record count spans all 141 records. A renumbered part also renames its file, which breaks
every relative link to it.

Whatever the position, Part 03 loses its §11. Renumbering Part 03 §12 to §11 rewrites three live
citations, in Part 00 §10, Part 03 §1 and the specification README; its anchor
`ew-portable-profile-normative-references` survives.

Most of the tooling finds parts by globbing `[0-9][0-9]_*.md`: `combine.py`, `headings.py`,
`columns.py`, `revisions/check_citations.py`, `revisions/impact.py` and `registry/check.py`. A new
file needs no change in any of them. `framework.py` hard-codes three things:

- the part set, `EXPECTED_PARTS`, as 00 to 11;
- the reference allocation (`REFERENCE_OWNERS`, `REFERENCE_ROWS`, `REFERENCE_ANCHORS` and
  `REFERENCE_INVOCATIONS`); and
- the README projection message.

`conformance/specification-framework/probe.py` uses a row for Part 12 as its unknown-part negative
case, so a real Part 12 needs another number there.

## 3. Desired outcome and constraints

A reader of Part 00 learns two facts: that the packet mechanism confines no packet to a modality,
and that the core vocabulary targets extracellular electrophysiology. The adapter interface lives in
a part of its own in v0.2. The outcome also has to preserve:

- every declaration, packet and verdict, since neither decision changes what conforms;
- "profile" as the word for a physical profile alone;
- one owner for each rule, with the rules a relocation moves changing meaning only by an enumerated
  Decision clause;
- a declared home for the interface's dependence on Parquet, Arrow and Zarr, under Part 00 §3.1.3's
  rule on storage technology;
- every live citation, ledger destination and anchor record repointed in one incorporation, with
  accepted records and committed evidence left untouched; and
- the two open proposals that amend Part 03 §11.2 and Part 03 §11.3, for opaque delivery and a
  source cache, whose texts a relocation would carry.

## 4. Options and tradeoffs

### 4.1 Scope wording

**Two statements in Part 00 §1** (preferred direction). The packet mechanism would be described as
applying to any data a registry can declare. The core vocabulary, meaning Part 01's concepts and the
core registry's declarations, would be described as targeting extracellular electrophysiology and
the session it was recorded in. Another modality declares its vocabulary in an extension registry
under Part 09, and its facts enter core only by a revision under Part 09 §7. Neither statement
creates an obligation. The `core` row of Part 00 §3.2 and Part 02 §2.2 would stop claiming
generality across modalities; §6 asks for its wording. The specification README's §1 would follow
Part 00, and the root README's opening line would follow as developer documentation.

Rejected: **keep the current text.** A behavior packet conforms and yet falls outside the stated
scope, and `core` stays "domain-general" beside a scope confined to one modality.

Rejected: **call the whole specification domain-general.** Fifteen tables and eight concepts are
extracellular, so a reader looking for another modality's vocabulary in core would find none. The
2026-09-17 review warned against exactly that overclaim.

Rejected for v0.2: **move the extracellular declarations out of core** into a registry of their own.
That renames 15 declarations in every packet carrying them. `core.array_channels.electrode_id`
would then reference an extension, which Part 00 §3.2's direction of reference forbids, and
`aind_unit_qc` would retarget. It is the route to take once a second modality's vocabulary reaches
core.

### 4.2 Where the interface goes

**A new numbered part** (preferred direction). Rejected: **keeping it in Part 03**, for the evidence
of §2.4.

Rejected: **folding it into Part 05.** Part 05 already runs 8,185 words, and its subject is the
build's procedure. The interface also depends on technologies that Part 00 confines to the physical
level, so a part mixing both would reproduce the mixture that now afflicts Part 03 in a second
place. The placement-defect inventory already records that mixture against Part 03.

### 4.3 Number

**Part 12** (preferred direction). It renumbers no part and needs only the `framework.py` and
probe changes of §2.6. The rendering puts it after Part 11. Numbered order is not dependency order
anyway, since Part 00 §9 lists Part 11 third. Rejected: **slotting it after Part 03 or Part 05**,
for the renumbering costs in §2.6.

Part 03 §12 would become §11 (preferred direction). Rejected: **leaving a gap at §11.** A gap would
keep a stale bare `Part 03 §11` unresolvable, but every reader would meet the missing number, and
`headings.py` already reports the changed heading together with its citers.

### 4.4 Name

**"Adapter Interface"** (preferred direction), with the file `12_adapter_interface.md`. It names
what an adapter author implements, in the term Part 00 §2.4 defines. The alternatives:

- **"Build and Adapter Interface"** names both sides but is longer, and every clause already names
  its actor.
- **"Source Delivery"** names one of the four subjects.
- **"Reaching a Source"**, the current heading, names an activity rather than a subject.

### 4.5 Classification

**A second part at the physical level, bound to the portable profile** (preferred direction). The
part would specify the adapter interface of `escapewheel-portable-v0.1`, for the builds that write
a packet declaring it. Part 00 §3.1.3 would say that the physical level comprises Part 03 and this
part, and Part 03 §1's "only part" sentence would say the same. The protocol group stays the
portable profile's, so no rule changes meaning.

Rejected: **give the interface an identity and version of its own**, which a later profile could
share. A new identifier belongs with the work on final identifiers, and no second profile exists to
share it.

Rejected: **split by dependence**, keeping the group table and the array-bytes rule in Part 03 and
moving the rest. §11.1 and §11.3 would each straddle two parts, and an adapter author would read
both for one interface.

### 4.6 What moves with §11

| material | disposition | reason |
|---|---|---|
| Part 03 §11 whole, the incorporations of the delivery and adapter schemas, and the Arrow reference entry | moves (preferred) | one subject, and §2.4 shows its attachments |
| Part 09 §5.8, the run's report | joins (preferred) | §11 already routes every adapter's report and `stated` values through it, and its channel paragraph is protocol knowledge; its subject would widen from an extension to an adapter, which is a meaning change |
| Part 09 §5.7 | stays | its subject is an extension's registry document and determinism; its protocol sentence becomes a citation |
| Part 05 §3, the session recipe | stays | the recipe is the build's input from its author; it owns arbitration and provenance, and Part 05 §2's order depends on it; the `delivery` table is a recipe member |
| Part 05 §3.7 and Part 05 §4.4 | stay | they are the build's procedure; where they restate a rule the new part owns, the restatement becomes a citation |
| Part 03 §9, amendment and retention | stays | packet lifecycle, not the adapter boundary |

### 4.7 Reference entries

The Arrow entry moves to the new part, whose prose would be its only direct invoker. Parquet would
then be invoked directly by two parts, so Part 00 §10 sends its entry to Part 00 as a shared
reference (preferred direction), with Parquet's logical types beside it.

Rejected: **have the `files-v0.1` row cite Part 03 §5 in place of Parquet.** That would bind a
delivery to Part 03 §5.5's writer floor, which binds no delivery today, and so change meaning.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01's concepts keep their meanings, and Part 00 §1 describes which of them the core vocabulary targets. |
| framework prose | Affected: Part 00 §1 gains the two scope statements; §3.1.3 names the new part at the physical level; §3.2's `core` row changes wording; §9 gains a Part 12 row and a dependency-direction item; §10 gains the shared Parquet entry. |
| logical prose | Affected: Part 02 §2.2's `core` row, matching Part 00 §3.2. |
| registry meta-schema and declarations | Unchanged; no declaration moves, and the meta-schema does not restate content-class meanings. |
| declarative rules | Unchanged. |
| physical profiles | Affected: Part 03 loses §11, its §1 incorporation of the delivery schema and its Arrow and Parquet rows; §1's "only part" sentence changes; §12 becomes §11. The profile descriptor is unchanged. |
| new Part 12 | Affected: holds §11's text, the two incorporations, the Arrow entry, and Part 09 §5.8 if it joins. |
| packet manifest and schemas | Unchanged in shape. The descriptions in `adapter.schema.json` and `recipe.schema.json` cite the new part, which changes their bytes but not their `$id`; the final-identifier work decides whether it should. |
| validation and import | Affected in citation only: Part 05 §§2, 3.4, 3.5, 3.7, 3.9 and 4.4 repoint; restatements become citations. |
| extension registries | Unchanged. |
| reader, writer, validator, adapters | Unchanged in behavior; 160 source citations in 35 files repoint. |
| existing packets | Unchanged and still conforming; nothing to regenerate. |
| conformance fixtures and tests | Affected: the framework probe's unknown-part case moves off 12, and its Parquet-placement case follows §4.7. No packet fixture changes. |
| revision tooling | Affected: `framework.py`'s part set and reference allocation; 29 ledger destinations; a regenerated `headings.toml`; an anchor bootstrap for Part 03 §11.4 and §11.6, and for Part 09 §5.8 if it joins. |
| generated publications | Affected: the combined rendering gains Part 12, and the specification README's part table gains a row. |
| developer documentation | Affected: the root README's opening line, the specification style guide's placement table, and 9 citations in 5 files. |

## 6. Open questions

1. **Split.** Resolved 2026-09-24: the scope wording of §4.1 and question 2 is promoted to the
   draft accepted as R141, and this proposal
   continues for the relocation alone, which question 7 orders after the opaque-delivery and
   source-cache items. The scope draft is structural in form, because it replaces text inside
   existing sections. The two share no clause.
2. **The `core` row.** Preferred: replace "domain-general normalized facts" with a phrase that
   claims no generality across modalities, such as "normalized facts of the core vocabulary",
   stated identically in Part 00 §3.2 and Part 02 §2.2. Keeping "domain-general" and defining
   "domain" as an extension's task or lab is the alternative. It preserves R71's sense but keeps a
   word that most readers take as a modality.
3. **Number and name.** Preferred: Part 12, "Adapter Interface", with Part 03 §12 renumbered to §11
   (§4.3 and §4.4).
4. **Classification.** Preferred: a second part at the physical level, bound to the portable profile
   (§4.5). An independent interface identity waits for the final-identifier work.
5. **Part 09 §5.8.** Preferred: it joins the new part, with its subject stated as an adapter. The
   draft would carry that widening as an enumerated Decision clause, since §11 already presumes it.
6. **Parquet's reference entry.** Preferred: a shared Part 00 entry (§4.7).
7. **Order against the opaque-delivery and source-cache proposals.** Preferred: incorporate the
   relocation after both. Each content decision is then reviewed at its current owner, the
   relocation's crosswalk and counts cover the final text of §11, and no draft has to rebase onto
   a part that does not yet exist.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
