# Summaries in Parts 00 and 01 state their owners' rules, and Part 06 §4 binds

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-26 |
| **Based on** | `a7fb4c4ea26952a78b2d5d431b5957a6d791fa15` |
| **Decision domain** | specification |
| **Affects** | Part 00 §§3.2, 5.1 and 9; Part 01 §§2.1, 3.3 and 3.9; Part 02 §§2.2 and 12.6; Part 05's validation reporting; Part 06's status line and §4; the registry meta-schema, registry-document contract descriptor and the description of `analysis.spike_events.clock_id`; `revisions/applied.toml` destinations for R37 §3.3, R40 §§2.1–2.2, R86 §2.4 and R95 §3.3; cited and unchanged: Part 02 §§2.6, 5.3 and 8.3, Part 03 §5.4, Part 04 §§2 and 4.1, Part 09 §6.1 |

## 1. Problem

Part 00 §9 forbids two things this specification does. A part may not state a second version of a
rule another part owns, and may summarize one only where the summary is explicitly informative.
An informative section may not be the sole statement of an obligation.

Parts 00 and 01 summarize rules that other parts own, normatively, and accepted revisions have
changed several owning rules without changing the summary. Five now state a different rule from
their owner, so an implementer reading Part 00 or 01 and one reading Part 02, 06 or 09 owe
different things:

| entry | summary | owner |
|---|---|---|
| PD-023 | Part 01 §3.3: a session declares its reference clock, unconditionally | R27 §2 and the registry: required only where a session declares more than one clock |
| PD-024 | Part 00 §3.2: a class references only one "beneath" it; neither core nor analysis references an extension | Part 09 §6.1: direction follows the declaring registry, and an extension registry's resources may reference that extension |
| PD-025 | Part 00 §5.1: an analysis resource becomes canonical only through a revision of this specification | Part 02 §2.2 and Part 06 §8: a specification or extension-registry change |
| PD-027 | Part 01 §2.1: an identifier is a signed 32-bit integer carrying no meaning | Part 02 §§2.6 and 5.3 and Part 04: `int32`, `int64` where values may exceed it, and a string catalog `resource_id` that names a resource within a namespace |
| PD-028 | Part 01 §3.9: a writer records the alignment measurement and the tolerance | Part 02 §12.6 (R99 §3.4): a writer should record them |

A sixth defect runs the other way. Four accepted clauses are placed in Part 06 §4, which Part 00
§9 and Part 06's own status line declare informative, so the obligations those revisions accepted
bind nobody (PD-026). A sweep of the ledger for other clauses placed only in informative sections
finds one more obligation in that position, R95 §3.3 in Part 07.

The placement-defect inventory records the six under the identifiers above. Its other entries are
placement only and are not part of this proposal.

## 2. Evidence

Observations are from the recorded baseline. Registry counts come from
`registry/logical_schemas.json` and the four `registry/extensions/*.json` documents. Quotations
lowercase their requirement keywords.

### 2.1 The reference clock (PD-023)

Part 01 §3.3 says a session "must declare the clock its times are reported on." R27 §2, the
accepted rule, says a session "should declare it. A session declaring more than one clock must
declare it", and the ledger gives R27 §2 a registry disposition: `core.sessions.reference_clock_id`
is nullable, and `core.sessions.reference_clock_declared` fires only for a session with more than
one clock. No part states R27 §2 in prose, so Part 01 §3.3's sentence is the only prose statement
and it is the wrong one.

The corpus has a negative case, `no_reference_clock`, two clocks and none named, which the rule
refuses. It has no case of exactly one clock and none named; `sessions_only` has no clock at all.
The AIND packets examined carry 11 to 13 clocks and declare a reference, so the narrower rule
admits no packet the wider one refuses today. The reference reader does not default to a sole
clock: it raises `NotAligned` wherever `reference_clock_id` is null.

### 2.2 Reference direction (PD-024)

Part 00 §3.2 says "A content class may reference a class beneath it and must not reference one
above. Core does not reference analysis, and neither references an extension". Nothing defines
"beneath", and the two sentences disagree under either reading of the table's order. Read
downward, core may reference an extension; read upward, analysis may. The second sentence forbids
both.

Part 09 §6.1 keys direction on the declaring registry instead: an extension registry's reference
"must target either its selected core context or the same extension registry", and the same holds
for a declaration dependency or catalog binding. Part 02 §8.3 separately forbids core to reference
an extension's resource and lets it name one through a discriminator. Part 02 §2.2 lets an
extension registry declare `analysis` resources, so an extension's analysis table may reference
that extension's own tables under Part 09 and may not under Part 00.

One part of Part 00's rule has no other owner. No other part says that core does not reference
analysis, and Part 09 §6.1 permits it, since the core registry declares both. The registries
contain no such dependency. A scan counts 100 references and declaration dependencies from core to
core, 14 from extension to core, 3 from extension to extension, 9 from analysis to core and 2 from
analysis to analysis; two catalog bindings from core to core and one from analysis to analysis;
and none, of any kind, from a canonical resource into a non-canonical one.

A checked rule needs a new registry-document contract. Part 02 selects a descriptor by a tuple
that includes the meta-schema identifier, and forbids reinterpreting a descriptor that selected a
contract. Adding an invariant therefore means a new descriptor and a new development meta-schema
identifier, which every registry document names in `$schema`.

### 2.3 Promotion (PD-025)

Part 00 §5.1's first paragraph says Part 06 "owns its exact lineage, realization, and promotion
requirements"; its second says a resource "becomes canonical only through an explicit revision of
this specification." Part 02 §2.2 and Part 06 §8 both admit a change to the owning extension
registry as well, which R128 §3.2 chose. The same paragraph's first two sentences repeat Part 06
§2's disposability rule nearly word for word.

### 2.4 Part 06 §4's obligations (PD-026)

Part 06 §4 states four obligations of a writer materializing `analysis.spike_events`: omit a spike
whose tick falls outside the mapped region, record the omitted count even when zero, refuse to
materialize where two spikes of one unit collide on one reference tick, and record the reason. The
ledger places R30 §2, R30 §4, R40 §2.3 and R92 §2.4 there, and R130 §3.7 made the run record
conditional on a writer recording the run at all. Part 00 §9 lists Part 06 as "informative except
§§2 and 5", and Part 06's status line says the same. The reference writer implements all four and
cites Part 06 §4 for them.

Section 4 also holds text that binding it would turn into rules it does not own or does not state
faithfully:

- "A row group lies inside one time bucket" states, without qualification, the physical layout
  that Part 03 §5.4 only recommends;
- the ten-second window measurement is evidence, which Part 10 owns;
- the generated column table describes `clock_id` as "normally the session's reference", where
  R30 §2 makes it the reference; and
- R40 §2.3 requires a writer to record how many rows it omitted "and on which clock", where §4
  asks only for the count. The reference writer records one total.

Elsewhere, the ledger places three clauses only in informative sections:

| clause | placed in | state |
|---|---|---|
| R43 §2 | Part 06 §6 | a withdrawn table may be absent; no part requires it, so the clause has nothing left to bind |
| R86 §2.4 | Part 07 | Part 05 already states it, so only the ledger is incomplete |
| R95 §3.3 | Part 07 | a validator should report two equal columns at `info` and must not fail them; no normative part states it, and the reference validator implements it |

### 2.5 Identifiers (PD-027)

Part 01 §2.1 says "An identifier is a signed 32-bit integer", that implementations "must not
encode semantic meaning in identifier values", and that a carried identifier is "the source's own
number". Part 02 §5.3 excepts the catalog `resource_id` from the integer types, and Part 02 §2.6
declares it a string identifier with carried identity on `core.array_assets`,
`analysis.array_assets` and `core.media_assets`. Part 04 §2 says a resource ID is a name rather than
an assigned number, and Part 04 §4.1 requires it to open with a namespace and a dot, so its value
carries meaning by design.

### 2.6 The alignment record (PD-028)

Four accepted clauses govern what a writer does when it maps past the terminal anchors:

- R37 §3.3: a writer establishing a bound wider than one median anchor interval "must measure it";
- R40 §2.1: "a writer must record the value it used", meaning the tolerance;
- R40 §2.2: "a writer recording its measurement must record median, p95 and maximum"; and
- R99 §3.4, later: "A writer should record the measurement R40 §2.2 requires … with `distance`,
  `tolerance_seconds` and the per-clock statistics", because `parameters` keeps evidence for a
  decision and the decision itself is `core.sessions.alignment_bound`.

Part 01 §3.9 states R37 §3.3's measurement, R40 §2.1, and R40 §2.2 without its condition: a writer
"must record the median, p95, and maximum". Part 02 §12.6 states R99 §3.4 and drops R40 §2.2's
completeness requirement. R40 §2.1 and R99 §3.4 also disagree about the tolerance. The ledger marks
R37 §3.3 superseded by R40 as a whole, although its note says R40 replaced only the tolerance and
the statistic; the obligation to measure survives in Part 01 §3.9 with no placed clause.

The reference writer records the tolerance, the distance and all three statistics, so it meets
either reading.

## 3. Desired outcome and constraints

Each rule is stated once, by the part that owns it, and each summary either states the same rule
or cites it. Every accepted obligation is stated in a normative section. The resolution should
preserve:

- every packet's verdict: no corpus packet and no AIND packet examined changes validity;
- every current registry document's validity, although each names a new meta-schema identifier;
  and
- the reference implementation's behavior, except that the writer records the omitted count per
  clock (§6). Its comments and tests may cite different sections.

## 4. Options and tradeoffs

**PD-023.** The preferred direction states R27 §2 in Part 01 §3.3: a session declares its reference
clock where it declares more than one clock, and should otherwise. Requiring the reference
unconditionally is the alternative; it would add a registry rule for no packet that needs it. What
a consumer does with one clock and no reference stays unspecified; the reference reader refuses.

**PD-024.** Three options:

1. Delete Part 00's direction rule and rely on Part 09 §6.1 and Part 02 §8.3. No byte changes, and
   nothing forbids a core table from referencing a core-registry analysis table.
2. Replace it with a rule stated in Part 02 §2.2 beside canonicality, that a canonical resource's
   references, declaration dependencies and catalog bindings target only canonical resources, and
   check it as a registry-document invariant. Part 00 §3.2 keeps the classes' meanings and cites
   Parts 02 and 09.
3. As option 2, with the rule stated but unchecked.

The preferred direction is option 2. The rule follows from disposability: Part 06 §2 lets a writer
delete any analysis resource, and a canonical row referencing one would then fail its foreign key.
A declaration decides it, so a check is cheap; option 3 would add a rule a tool could check and
does not. The check costs a new development meta-schema identifier (§2.2).

**PD-025.** The preferred direction deletes Part 00 §5.1's promotion sentence and its restatement
of disposability, leaving Part 06, which Part 00 already names as the owner of both. Narrowing
Parts 02 and 06 to revisions of this specification would reverse R128 §3.2 and deny an extension
author the ability to promote their own resource.

**PD-026.** Three options:

1. Declare §4 normative in Part 00 §9's status row and Part 06's status line.
2. Move the four obligations into §2 or a new normative section, leaving §4 descriptive.
3. Mark them informative, which would leave R30 §2, R30 §4, R40 §2.3 and R92 §2.4 with no binding
   destination and break Part 00 §9's own rule.

The preferred direction is option 1. It keeps each obligation beside the table it governs and
changes two status lines instead of moving text. Binding §4 also requires that its row-group
sentence cite Part 03 §5.4 rather than restate it, that the measurement move to a marked
informative note until placement cleanup moves it to Part 10, and that the `clock_id` description
name the session's reference clock as R30 §2 does. The description is registry text, and the
PD-024 check already advances the registry's development identifier.

R95 §3.3 has the same defect. The preferred direction states it in Part 05's validation reporting,
where Part 05 already states R86 §2.4's reader rule. R43 §2 and R86 §2.4 need only ledger
maintenance.

**PD-027.** The preferred direction keeps identity meaning in Part 01 §2.1: an identifier is
stable, is not derived from a position in a file, and an integer identifier encodes no meaning. A
carried identifier becomes "the source's own value". Representation, and the resource ID's
namespaced form, are cited to Part 02 §§2.6 and 5.3 and Part 04 §4.1. Restating those exceptions
in Part 01 would keep two copies of a logical fact.

**PD-028.** The preferred direction states the recording rule once, in Part 02 §12.6, where
`parameters` is described. A writer should record the measurement, the distance and the tolerance.
A writer that records the measurement records the median, p95 and maximum together. Part 01 §3.9
keeps R37 §3.3's obligation to measure and cites Part 02 §12.6 for the record. This follows R99
§3.4, the later decision, on the tolerance.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | affected: Part 01 §§2.1, 3.3 and 3.9 |
| logical prose | affected: Part 02 §§2.2 and 12.6 |
| registry meta-schema, declarations and rules | affected: a new development meta-schema identifier and contract descriptor with one semantic invariant; the `analysis.spike_events.clock_id` description; no declaration or rule changes meaning |
| physical profiles | unchanged: Part 03 §5.4 is cited, not changed |
| packet manifest and other schemas | unchanged |
| validation and import | affected: Part 05 states R95 §3.3, which the reference validator already implements; registry checking gains one invariant |
| extension registries | affected: each names the new meta-schema identifier; none references a non-canonical resource |
| reader, writer, validator, adapters | registry checking gains the invariant; the writer records the omitted count per clock; otherwise citations only, from Part 01 §3.9 to Part 02 §12.6 where they concern the record |
| existing packets | unchanged verdicts; packets built after the change carry registries naming the new identifier |
| conformance fixtures and tests | a positive packet with one clock and no reference; negative registry documents in which a core column references, a core declaration requires, and a core catalog binds an analysis resource |
| architecture and analysis prose | affected: Part 00 §§3.2, 5.1 and 9, and Part 06's status line and §4 |
| revision tooling and ledger | affected: Part 06 §4's destinations become binding; R37 §3.3's measurement gains a destination; R40 §§2.1–2.2 move with the record; R86 §2.4 gains its Part 05 destination and R95 §3.3 a normative one |
| generated publications and documentation | the single-file rendering; the placement-defect inventory closes PD-023 to PD-028 |

## 6. Open questions

1. **Should PD-024's rule be checked now?** Resolved 2026-09-26: yes, as option 2, accepting a new
   development meta-schema identifier while the field test runs.
2. **Is the tolerance record required or recommended?** Resolved 2026-09-26: recommended, following
   R99 §3.4, since `core.sessions.alignment_bound` carries the decision a consumer uses.
3. **How does Part 06 §4 bind?** Resolved 2026-09-26: option 1, by its status. One draft carries
   every item, since none depends on another.
4. **Is the omitted count recorded per clock?** Resolved 2026-09-26: yes, as R40 §2.3 requires. A
   spike's omission depends on its own clock's anchors, so a total cannot say which mapping fell
   short. The reference writer then records a count for each clock.
5. **Does R95 §3.3 join this proposal?** Resolved 2026-09-26: yes, stated in Part 05's validation
   reporting. It fails Part 00 §9's rule the same way Part 06 §4 does, and placement cleanup would
   bind it only after the field test.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
