# Summaries in Parts 00 and 01 state their owners' rules, and Part 06 §4 binds

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-26 |
| **Based on** | `a7fb4c4ea26952a78b2d5d431b5957a6d791fa15` |
| **Decision domain** | specification |
| **Affects** | Part 00 §§3.2, 5.1 and 9; Part 01 §§2.1, 3.3 and 3.9; Part 02 §§2.2 and 12.6; Part 06's status line and §4; Part 09 §6.1 (cited, unchanged); the registry-document contract if §6's first question is answered as preferred; `revisions/applied.toml` destinations for the clauses Part 06 §4 carries |

## 1. Problem

Parts 00 and 01 summarize rules that other parts own, and accepted revisions have changed several
owning rules without changing the summary. Five now state a different rule from their owner, so an implementer reading
Part 00 or 01 and one reading Part 02, 06 or 09 owe different things:

| entry | summary | owner |
|---|---|---|
| PD-023 | Part 01 §3.3: a session declares its reference clock, unconditionally | R27 §2 and the registry: required only where a session declares more than one clock |
| PD-024 | Part 00 §3.2: a class references only one "beneath" it; neither core nor analysis references an extension | Part 09 §6.1: direction follows the declaring registry, and an extension registry's resources may reference that extension |
| PD-025 | Part 00 §5.1: an analysis resource becomes canonical only through a revision of this specification | Part 02 §2.2 and Part 06 §8: a specification or extension-registry change |
| PD-027 | Part 01 §2.1: an identifier is a signed 32-bit integer | Part 02 §5.3: `int32`, `int64` where values may exceed it, and a string catalog `resource_id` |
| PD-028 | Part 01 §3.9: a writer records the alignment measurement and the tolerance | Part 02 §12.6 (R99 §3.4): a writer should record them |

A sixth defect runs the other way. Four accepted clauses are placed in Part 06 §4, which Part 00
§9 and Part 06's own status line declare informative, so the obligations those revisions accepted
bind nobody (PD-026).

The placement-defect inventory records all six under the identifiers above. Its other entries are
placement only and are not part of this proposal.

## 2. Evidence

Observations are from the recorded baseline. Registry counts come from
`registry/logical_schemas.json` and the four `registry/extensions/*.json` documents. Quotations lowercase
their requirement keywords.

### 2.1 The reference clock (PD-023)

Part 01 §3.3 says a session "must declare the clock its times are reported on." R27 §2, the
accepted rule, says a session "should declare it. A session declaring more than one clock must
declare it", and the ledger gives R27 §2 a registry disposition: `core.sessions.reference_clock_id`
is `nullable`, and `core.sessions.reference_clock_declared` fires only for a session with more than
one clock. The conformance corpus expects `sessions_only`, a session with no clock and no
reference, to pass.

No corpus packet has one clock and no reference, and the AIND packets examined carry 11 to 13
clocks and declare a reference, so the narrower rule admits no packet the wider one refuses today. The reference reader does not
default to a sole clock: it raises `NotAligned` wherever `reference_clock_id` is null.

### 2.2 Reference direction (PD-024)

Part 00 §3.2 says "A content class may reference a class beneath it and must not reference one
above. Core does not reference analysis, and neither references an extension". Nothing defines
"beneath", and the two sentences disagree under either reading of the table's order. Read
downward, core may reference an extension; read upward, analysis may. The second sentence forbids
both.

Part 09 §6.1 keys direction on the declaring registry instead: an extension registry's reference
"must target either its selected core context or the same extension registry". Part 02 §2.2 lets
an extension registry declare `analysis` resources, so an extension's analysis table may reference
that extension's own tables under Part 09 and may not under Part 00.

One part of Part 00's rule has no other owner. No part except Part 00 §3.2 says that core does not
reference analysis, and Part 09 §6.1 permits it, since both are declared by the core registry. The
registries contain no such reference. A scan of every column reference and every `requires` entry
counts 100 from core to core, 14 from extension to core, 3 from extension to extension, 9 from
analysis to core and 2 from analysis to analysis, and none from a canonical resource into a
non-canonical one.

### 2.3 Promotion (PD-025)

Part 00 §5.1's preceding paragraph says Part 06 "owns its exact lineage, realization, and promotion
requirements"; its next says a resource "becomes canonical only through an explicit revision of
this specification." Part 02 §2.2 and Part 06 §8 both admit a change to the owning extension
registry as well, which R128 §3.2 chose. Part 00's sentence was not updated when R128 was incorporated.

### 2.4 Part 06 §4's obligations (PD-026)

Part 06 §4 states four obligations of a writer materializing `analysis.spike_events`: omit a spike
whose tick falls outside the mapped region, record the omitted count even when zero, refuse to
materialize where two spikes of one unit collide on one reference tick, and record the reason. The
ledger places R30 §2, R30 §4, R40 §2.3 and R92 §2.4 there. Part 00 §9 lists Part 06 as
"informative except §§2 and 5", and Part 06's status line says the same, so a writer that ignores
all four conforms.

The reference writer implements all four and cites Part 06 §4 for them.

### 2.5 Identifier representation (PD-027)

Part 01 §2.1 says "An identifier is a signed 32-bit integer." Part 02 §5.3 says identifier columns
are `int32` except where values may exceed it, where they are `int64`, "and except the catalog
`resource_id`", which the registry declares as a string identifier on `core.array_assets`,
`analysis.array_assets` and `core.media_assets`.

### 2.6 The alignment record (PD-028)

Three accepted revisions govern what a writer records when it extrapolates past the terminal
anchors:

- R40 §2.1: "a writer must record the value it used", meaning the tolerance;
- R40 §2.2: "a writer recording its measurement must record median, p95 and maximum"; and
- R99 §3.4, later: "A writer should record the measurement R40 §2.2 requires … with `distance`,
  `tolerance_seconds` and the per-clock statistics", because `parameters` keeps evidence for a
  decision and the decision itself is `core.sessions.alignment_bound`.

Part 01 §3.9 states R40 §2.1 and drops R40 §2.2's condition: a writer "must record the median, p95,
and maximum". Part 02 §12.6 states R99 §3.4 and drops R40 §2.2's completeness requirement. The two
accepted revisions also disagree with each other about the tolerance, R40 §2.1 requiring it and
R99 §3.4 listing it among what a writer should record.

The reference writer records the tolerance, the distance and all three statistics, so it meets
either reading.

## 3. Desired outcome and constraints

Each rule is stated once, by the part that owns it, and each summary either states the same rule
or cites it. The resolution should preserve:

- every packet's verdict: no corpus packet and no AIND packet examined changes validity;
- the registry bytes, except where §6's first question chooses a checked rule; and
- the reference implementation's behavior. Its comments and tests may cite different sections.

## 4. Options and tradeoffs

**PD-023.** The preferred direction states R27 §2 in Part 01 §3.3: a session declares its
reference clock where it declares more than one clock, and should otherwise. Requiring the
reference unconditionally is the alternative; it would add a registry rule and advance core's
development identifier for no packet that needs it. What a consumer does with one clock and no
reference stays unspecified; the reference reader refuses, and either answer leaves the rule
above unchanged.

**PD-024.** Three options:

1. Delete Part 00's direction rule and rely on Part 09 §6.1. No byte changes, and nothing forbids
   a core table from referencing a core-registry analysis table.
2. Replace it with a rule stated in Part 02 §2.2 beside canonicality, that a canonical resource
   does not reference or require a non-canonical one, and check it as a registry-document
   invariant. Part 00 §3.2 keeps the classes' meanings and cites Parts 02 and 09.
3. As option 2, with the rule stated but unchecked.

The preferred direction is option 2. The rule follows from disposability: Part 06 §2 lets a writer
delete any analysis resource, and a canonical row referencing one would then fail its foreign key.
A declaration decides it, so a check is cheap; option 3 would add a rule a tool could check and
does not. Option 2 changes the registry-document contract, which §6 asks about.

**PD-025.** The preferred direction deletes Part 00 §5.1's promotion sentence, leaving Part 06 §8,
which Part 00 already names as the owner. Narrowing Parts 02 and 06 to revisions of this
specification would reverse R128 §3.2 and deny an extension author the ability to promote their own
resource.

**PD-026.** Three options:

1. Declare §4 normative in Part 00 §9's status row and Part 06's status line, keeping its
   measurement as a marked informative paragraph until placement cleanup moves it to Part 10.
2. Move the four obligations into §2 or a new normative section, leaving §4 descriptive.
3. Mark them informative, which would leave R30 §2, R30 §4, R40 §2.3 and R92 §2.4 with no binding
   destination and so is not credible.

The preferred direction is option 1. It keeps each obligation beside the table it governs and
changes two status lines instead of moving text.

**PD-027.** The preferred direction leaves identifier meaning in Part 01 §2.1, where it says an
identifier is stable and encodes no meaning, and cites Part 02 §5.3 for representation. Restating
Part 02's exceptions in Part 01 would keep two copies of a logical fact.

**PD-028.** The preferred direction states the recording rule once, in Part 02 §12.6, where
`parameters` is described. A writer should record the measurement, the distance and the tolerance.
One that records the measurement records the median, p95 and maximum together. Part 01 §3.9 keeps
the obligation to measure and cites Part 02 §12.6 for the record. This follows R99 §3.4, the later
decision, on the tolerance. §6 asks whether the tolerance should instead stay required.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | affected: Part 01 §§2.1, 3.3 and 3.9 |
| logical prose | affected: Part 02 §§2.2 and 12.6 |
| registry meta-schema, declarations and rules | unchanged, except the registry-document contract under PD-024 option 2 |
| physical profiles | unchanged: no rule here depends on storage |
| packet manifest and other schemas | unchanged |
| validation and import | unchanged for packets; a registry-document check is added under PD-024 option 2 |
| extension registries | unchanged: none references a non-canonical resource |
| reader, writer, validator, adapters | unchanged behavior; citations in comments move from Part 01 §3.9 to Part 02 §12.6 where they concern the record |
| existing packets | unchanged verdicts; under PD-024 option 2, registries carried by new packets gain a new development identifier |
| conformance fixtures and tests | a negative registry fixture for PD-024 option 2; none for the rest, which change no verdict |
| architecture and analysis prose | affected: Part 00 §§3.2, 5.1 and 9, and Part 06's status line and §4 |
| revision tooling and ledger | affected: the Part 06 §4 destinations stay and become binding; the R40 §2.1 and §2.2 destinations move with the record |
| generated publications and documentation | the single-file rendering; the placement-defect inventory closes PD-023 to PD-028 |

## 6. Open questions

1. **Should PD-024's rule be checked now?** Preferred: yes, as option 2. A new invariant needs a
   new contract descriptor, which a checker selects through the meta-schema identifier, so every
   registry document's `$schema` advances to a new development value while the field test runs,
   and packets built before and after are told apart by it. Deferring only the check to final identifiers would avoid that and leave
   an unchecked rule for the rest of the field test.
2. **Is the tolerance record required or recommended?** Preferred: recommended, following R99 §3.4,
   because `core.sessions.alignment_bound` carries the decision a consumer uses and the tolerance
   is evidence for it. Keeping R40 §2.1's requirement would make Part 02 §12.6 require one
   `parameters` key and recommend the rest.
3. **One draft or several?** Preferred: one. Each item is small, each resolves toward an owner, and
   none depends on another, so splitting would cost six acceptance rounds for no separate decision.

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
