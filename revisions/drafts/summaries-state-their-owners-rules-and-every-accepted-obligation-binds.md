# Summaries State Their Owners' Rules, and Every Accepted Obligation Binds

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `a0f7d8b14928afe19b1079fb2b98455d5ee86d25` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§3.2, 5.1 and 9; Part 01 §§2.1, 3.3 and 3.9; Part 02 §§2.2, 9.2, 9.4 and 12.6; Part 05 §5.3; Part 06's status line and §4; `registry/registry.schema.json`; the registry-contract descriptor; the core registry's `registry_version` and its description of `analysis.spike_events.clock_id`; the four repository extension registries' `$schema` and `registry_version` |
| **Depends on** | R20 §5.1; R27 §2; R30 §§2 and 4; R37 §3.3; R40 §§2.1–2.3; R92 §2.4; R95 §3.3; R99 §3.4; R126 §3.2; R128 §3.2; R130 §3.7; R139 §3.3 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8; §3.9 |

Section 3 is normative. Sections 1, 2, 5, 6 and 7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 00 §9 forbids a part to state a second version of a rule another part owns, and forbids an
informative section to be the sole statement of an obligation. The specification breaks both rules.

Parts 00 and 01 summarize rules that other parts own, normatively, and accepted revisions have
changed five of those rules without changing the summary. A reader of Part 00 or 01 and a reader of
the owner then owe different things: whether a one-clock session names its reference clock, which
content classes may reference which, how an analysis resource becomes canonical, what an identifier
is, and what a writer records about its alignment error.

The other failure runs the opposite way. Part 06 §4 carries four accepted obligations of a writer
materializing `analysis.spike_events`, in a section Part 00 §9 declares informative, so they bind
nobody. R95 §3.3's obligation of a validator is placed only in informative Part 07 and stated in no
normative part.

This revision states each rule once, at its owner, and has each summary state the same rule or cite
it. It binds Part 06 §4 and states R95 §3.3 in Part 05. It adds one registry-document invariant,
that a canonical resource depends only on canonical resources, which advances the registry
meta-schema's development identifier. It also restores two parts of accepted clauses that the
current text dropped: R40 §2.3's per-clock omitted count and R40 §2.2's completeness condition.

The change is structural because it replaces text inside existing sections. Appended sections would
leave each wrong summary standing beside its correction.

### 1.1 Structural crosswalk

The anchor bootstrap `a0f7d8b` added `ew-stable-identity`, `ew-session-concept` and
`ew-clock-concept` to Part 01 §§2.1, 3.3 and 3.9, and `ew-clock-alignment-record` to Part 02 §12.6.
Every other affected section already carries a canonical anchor. No section moves, splits, merges
or retires, and no section is added.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 01 §3.3, "MUST declare the clock its times are reported on" | replace in place | same section | required only for a session with more than one clock | §3.1 |
| Part 01 §2.1, "An identifier is a signed 32-bit integer" and the ban on semantic meaning | replace in place | same section, citing Part 02 §5.3 and Part 04 §4.1 | representation moves to its owner; the ban reaches integer identifiers | §3.2 |
| Part 01 §2.1, the `carried` row, "the source's own number" | revise in place | same section | "value" | §3.2 |
| Part 01 §3.9, "a writer MUST record the value it used" | delete the clause | Part 02 §12.6 | the tolerance record is recommended | §3.3 |
| Part 01 §3.9, "MUST measure its error and MUST record the median, p95, and maximum" | replace in place | same section, citing Part 02 §12.6 | measurement stays; the record moves | §3.3 |
| Part 02 §12.6, the paragraph on `core.processing_runs.parameters` | replace in place | same section | the record is recommended, and complete where made | §3.3 |
| Part 00 §3.2, "A content class MAY reference a class beneath it …" | replace with a citation | Part 02 §2.2 and Part 09 §§6.1–6.2 | canonical targets only; an extension's own analysis may reference it | §3.4 |
| none | add a paragraph at the end of the section | Part 02 §2.2 | a canonical resource depends only on canonical resources | §3.4 |
| Part 02 §9.2, the meta-schema `$id` and the core registry's version | revise in place | same section | both advance to 0.8.0 | §3.5 |
| Part 02 §9.4, the descriptor ID, invariant table and resource-invariant list | revise in place | same section | `escapewheel-registry-contract-v0.5` adds one invariant | §3.5 |
| Part 00 §5.1, the second paragraph | delete | Part 06 §§2 and 8 | promotion also by an extension-registry change; disposability unchanged | §3.6 |
| Part 00 §9, the Part 06 row | revise in place | same section | §4 is normative | §3.7 |
| Part 06, the status line | revise in place | same line | §4 is normative except its measurement | §3.7 |
| Part 06 §4, "A row group lies inside one time bucket" | replace with a citation | Part 03 §5.4 | none; the section states no layout rule | §3.7 |
| Part 06 §4, the ten-second window measurement | mark informative | same section | none | §3.7 |
| core registry, the description of `analysis.spike_events.clock_id` | revise | same declaration | the session's reference clock | §3.7 |
| Part 06 §4, "MUST record the count omitted among its parameters" | replace in place | same section | a count for each clock | §3.8 |
| none; the ledger places R95 §3.3 in Part 07, which does not state it | add a paragraph at the end of the section | Part 05 §5.3 | binds a validator | §3.9 |

## 2. Background

Section 2 is informative. Registry counts were taken at the recorded baseline from
`registry/logical_schemas.json` and the four `registry/extensions/*.json` documents by a script
reading every declaration's `requires`, catalog binding and table references. Quotations lowercase
their requirement keywords.

### 2.1 The reference clock

Part 01 §3.3 says a session "must declare the clock its times are reported on". R27 §2 says a
session "should declare it. A session declaring more than one clock must declare it", and the
ledger gives R27 §2 a registry disposition: `core.sessions.reference_clock_id` is nullable, and the
Tier 2 rule `core.sessions.reference_clock_declared` fires only for a session with more than one
clock. No part states R27 §2 in prose.

The corpus refuses `no_reference_clock`, two clocks and none named, and passes `sessions_only`,
which has no clock. No corpus packet has one clock and none named. Two AIND electrophysiology
packets, of subjects 776259 and 786867, carry 13 and 11 clocks and each names its reference, so
neither changes verdict under the narrower rule. Requiring the reference unconditionally would add a registry rule for no
packet that needs it.

### 2.2 Reference direction

Part 00 §3.2 says "a content class may reference a class beneath it and must not reference one
above. Core does not reference analysis, and neither references an extension". The ledger places
R20 §5.1 there, which defined the order the text omits: extension above analysis above core, so an
extension may reference analysis and analysis may not reference an extension. Two later revisions
moved away from that order without repairing the sentence:

- R71 made extension resources canonical and analysis disposable, so R20's permission lets a
  canonical resource depend on one a writer may delete, which R20's own rationale forbids for core
  ("core stays interpretable when analysis resources are deleted, which is what makes them
  disposable").
- R126 §3.2, stated in Part 09 §6.1, keys direction on the declaring registry: an extension
  registry's references, dependencies and catalog bindings target its core context or itself. An
  extension registry may declare `analysis` resources (Part 02 §2.2), so its analysis table may
  reference its own extension tables under Part 09 and may not under Part 00.

The prohibition that core not reference analysis has no statement other than Part 00's, and Part
09 §6.1 permits it, since the core registry declares both.

The registries hold 128 table references: 100 from core to core, 14 from extension to core, 3 from
extension to extension, 9 from analysis to core and 2 from analysis to analysis. They hold three
catalog bindings, two from core to core and one from analysis to analysis, and no declaration names
anything in `requires`. None targets a non-canonical resource from a canonical one, so a rule
forbidding that admits every shipped registry.

Part 02 §9.4 selects a contract descriptor by a tuple that includes the meta-schema identifier and
forbids reinterpreting a descriptor after publication. A checked invariant therefore needs a new
descriptor selected by a new meta-schema identifier. Stating the rule unchecked would avoid the new
identifiers, but it would leave a rule that a tool could decide from the declarations and does not.

### 2.3 Promotion

Part 00 §5.1 says Part 06 "owns its exact lineage, realization, and promotion requirements", then
that an analysis resource "becomes canonical only through an explicit revision of this
specification". Part 02 §2.2 and Part 06 §8 also admit a change to the owning extension registry,
which R128 §3.2 chose. The same paragraph's first two sentences restate Part 06 §2's disposability
rule nearly word for word.

### 2.4 Part 06 §4 and R95 §3.3

Part 06 §4 states the obligations of a writer materializing `analysis.spike_events`. It omits a
spike whose tick falls outside the mapped region, records the omitted count even when it is zero,
refuses to materialize where two spikes of one unit collide on one reference tick, and records the
reason. The ledger places R30 §2, R30 §4, R40 §2.3 and R92 §2.4 there. R130 §3.7 made both records
conditional on the writer recording the run. The reference writer implements all four and cites
Part 06 §4.

Binding the section as written would also bind text that states no rule of its own, or states an
accepted rule unfaithfully:

- "A row group lies inside one time bucket" states outright the layout Part 03 §5.4 recommends;
- the ten-second window measurement is evidence;
- the column table, generated from the registry, calls `clock_id` "normally the session's
  reference", where R30 §2 makes it the reference. The reference writer maps onto the reference
  by default and accepts a recipe option naming another clock; and
- R40 §2.3 requires the omitted count "and on which clock", where §4 asks for one count. The
  reference writer records one total, so a count of 2 does not say which probe's mapping fell short.

The ledger places three other clauses only in informative sections:

| clause | placed in | state |
|---|---|---|
| R43 §2 | Part 06 §6 | a withdrawn table may be absent; no part requires it, so nothing is left to bind |
| R86 §2.4 | Part 07 | Part 05 §13.1 states it, so only the ledger is incomplete |
| R95 §3.3 | Part 07 | a validator should report two equal columns at `info` and must not fail them; no normative part states it |

The reference validator implements R95 §3.3 under the check ID `<resource_id>.columns_duplicated`,
and no validator test exercises it.

### 2.5 Identifiers

Part 01 §2.1 says "an identifier is a signed 32-bit integer", that implementations "must not encode
semantic meaning in identifier values", and that a carried identifier is "the source's own number".
Part 02 §5.3 excepts the catalog `resource_id` from the integer types. Part 02 §2.6 declares it a
string identifier with carried identity on `core.array_assets`, `analysis.array_assets` and
`core.media_assets`. Part 04 §2 makes a resource ID a name rather than an assigned number, and Part
04 §4.1 requires it to open with a namespace and a dot. A resource ID's value therefore carries
meaning by design, and it is not a number.

### 2.6 The alignment record

Four accepted clauses govern a writer mapping past the terminal anchors:

- R37 §3.3: a writer establishing a bound wider than one median anchor interval "must measure it";
- R40 §2.1: "a writer must record the value it used", meaning the tolerance;
- R40 §2.2: "a writer recording its measurement must record median, p95 and maximum"; and
- R99 §3.4, later: "a writer should record the measurement R40 §2.2 requires … with `distance`,
  `tolerance_seconds` and the per-clock statistics", because `parameters` holds evidence for a
  decision and the decision is `core.sessions.alignment_bound`.

Part 01 §3.9 states R37 §3.3's measurement and R40 §2.1, and states R40 §2.2 without its condition:
a writer "must record the median, p95, and maximum". Part 02 §12.6 states R99 §3.4 without R40
§2.2's completeness. The ledger marks R37 §3.3 superseded by R40, although its note says R40
replaced only the tolerance and the statistic, and the measurement survives in Part 01 §3.9. The
reference writer records the tolerance, the distance and all three statistics.

### 2.7 Overlap

No other proposal or draft is open. The placement-defect inventory's remaining entries are
placement only, and a separate structural revision is to resolve them. That revision is to move
Part 06 §4's measurement to Part 10.

## 3. Decision

Five subsections settle a rule a summary misstates and state it at its owner, §3.5 advances the
registry identifiers for the invariant §3.4 adds, and three bind accepted obligations. The crosswalk in §1.1 places each.

### 3.1 A session with more than one clock declares its reference clock

A session declaring more than one clock MUST declare the clock its times are reported on, and a
session declaring one clock SHOULD declare it. Part 01 §3.3 states this rule in place of an
unconditional one.

### 3.2 An identifier is stable, and Part 02 fixes its representation

Any object referenced by another object MUST have a stable identifier. Implementations MUST NOT
derive an identifier from a value's position in a file, and MUST NOT encode semantic meaning in an
integer identifier's value. Part 02 §5.3 fixes each identifier column's type, and Part 04 §4.1 fixes
the form of a resource ID, which names its namespace. A `carried` identifier is the source's own
value, reproduced unchanged.

### 3.3 A writer measures its alignment error, and Part 02 §12.6 owns the record

A writer reaching past one median anchor interval MUST measure its error. A profile or a recipe
MAY state a tolerance other than the default of 3 ms at p95. Part 01 §3.9 states both and cites
Part 02 §12.6 for the record.

A writer SHOULD record in `core.processing_runs.parameters` the tolerance it judged its alignment
against and, where it measured its error, the distance and the measurement. A writer recording the
measurement MUST record its median, p95 and maximum together, so a consumer can judge the packet by
a stricter rule than the writer applied. Part 02 §12.6 states this rule, and no other part states a
second version of it.

### 3.4 A canonical resource depends only on canonical resources

A registry document MUST NOT declare a `core` or `extension` resource that has a table reference,
a `requires` entry or a catalog binding targeting an `analysis` declaration. A writer may delete
any analysis resource under Part 06 §2, which would leave a canonical resource depending on one
without its target. Part 02 §2.2 states this rule. A discriminator names a resource without depending on it
(Part 09 §6.2), so the rule does not reach one.

Which registry a declaration may target remains Part 09 §6.1's rule. Part 00 §3.2 states no
direction of reference and cites Part 02 §2.2 and Part 09 §§6.1–6.2.

### 3.5 The registry identifiers advance

The registry-contract descriptor MUST assign the invariant `registry.resource.canonical_targets`,
at phase `semantic`, for classes `core` and `extension`, with the anchors `ew-resource-content-class`
and `ew-registry-conformance`, after `registry.resource.dependency`. It is one of the resource
invariants of Part 02 §9.4. Each outcome's instance pointer names the offending reference, `requires`
entry or catalog binding. Where the target
lies in the core context, the invariant is core-dependent under Part 02 §9.4.

These incorporated identifiers MUST advance:

| artifact | from | to |
|---|---|---|
| registry meta-schema `$id` | `https://escapewheel.org/schemas/registry/0.7.0` | `https://escapewheel.org/schemas/registry/0.8.0` |
| registry-contract descriptor ID | `escapewheel-registry-contract-v0.4` | `escapewheel-registry-contract-v0.5`, selecting meta-schema 0.8.0 |
| core registry `registry_version` | `0.7.0` | `0.8.0` |

The meta-schema changes only its `$id`. An extension registry migrated to meta-schema 0.8.0 MUST
carry a `registry_version` different from the one it carried under 0.7.0; the core specification
does not assign it.

### 3.6 An analysis resource is promoted by its owning registry's change

An analysis resource becomes canonical only by a change to its declaration's content class, made
through a revision of this specification or of the extension registry declaring it. Part 06 §8
owns this rule and Part 06 §2 owns disposability. Part 00 §5.1 states what the analysis content
class may contain and cites Part 06 for the rest.

### 3.7 Part 06 §4 is normative

Part 06 §4 is normative except its measurement of a population window, which is marked
informative. Part 00 §9's row for Part 06 and Part 06's status line name §§2, 4 and 5 as its
normative sections.

The section states no physical layout of its own: it cites Part 03 §5.4 for the table's stored
order and its row groups. `analysis.spike_events.clock_id` is the session's reference clock, as the
table's purpose under R30 §2 requires, and the core registry's description of that column says so.
The table therefore holds no rows for a session declaring no reference clock.

### 3.8 A writer records omitted spikes per clock

A writer materializing `analysis.spike_events` that records the materialization's run MUST record
among its parameters, for each clock from which it mapped spikes, how many of that clock's spikes it
omitted, including a count of zero. Part 06 §4 states this rule in place of a single count.

### 3.9 A validator reports two equal columns at `info`

A validator SHOULD report each pair of columns of one table resource that hold equal values in
every row, where those values are not all the same, at `info` under the check ID
`<resource_id>.columns_duplicated`, naming both columns. It MUST NOT report such a pair at `error`.
The finding concerns one resource, so Part 05 §9.5 attributes it to the registry whose declaration
the resource's entry names. Part 05 §5.3 states this rule.

## 5. Consequence

Every packet is rebuilt to bind core registry 0.8.0, as after any meta-schema change. A packet
binding 0.7.0 names a meta-schema that a checker knowing only 0.8.0 does not select. No table's
values change. No packet's verdict changes: every shipped registry passes §3.4, the corpus has no
one-clock session without a reference, and the reference writer already omits and refuses as Part
06 §4 says. It maps onto the reference unless a recipe names another clock, which no shipped recipe
or test fixture outside the writer's own suite does. Packets built for the release-candidate
field test bind 0.8.0 if they are built after incorporation.

The meta-schema change is incompatible, so the core registry and each of the four repository
extension registries name meta-schema 0.8.0. Core's `registry_version` becomes 0.8.0. `aind_opto`
and `vr_foraging` advance from 0.7.0 and `aind_unit_qc` and `dynamic_foraging` from 0.8.0, each to
a version of its own.

R20 §5.1 is superseded by §3.4 together with R126 §3.2. Its permission for an extension to reference
analysis is withdrawn. Its prohibition on analysis referencing an extension now binds only across
registries, so an extension registry's own analysis resources may reference it. R40 §2.1's
recording sentence is narrowed to §3.3's recommendation, which R99 §3.4 already made, and its
ledger entry gains a note. R37 §3.3's note records that its measurement is stated by §3.3.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Part 01 §3.3 takes §3.1, Part 01 §2.1 takes §3.2, and Part 01 §3.9 takes §3.3's first paragraph. | `evidence/R<N>.json` names `ew-session-concept`, `ew-stable-identity` and `ew-clock-concept`. |
| logical prose and registry | Part 02 §12.6 takes §3.3's second paragraph, Part 02 §2.2 takes §3.4, and Part 02 §§9.2 and 9.4 take §3.5. The meta-schema and descriptor take §3.5. The core registry source takes §3.7's `clock_id` description and §3.5's version, and `registry/build.py` and `registry/check.py` follow the identifiers. `registry/check.py` gains the invariant. | `evidence/R<N>.json` names each anchor, the meta-schema and descriptor, and the column's description; `registry/check.py` passes every shipped registry. |
| physical profiles | Unchanged. Part 03 §5.4 is cited, not changed. | None required. |
| packet manifest and JSON Schemas | Unchanged. The manifest names no content class, and the registry meta-schema changes under the row above. | None required. |
| validation and import | Part 05 §5.3 takes §3.9, which the reference validator already implements. The registry-document checker in the validator gains §3.5's invariant and selects the v0.5 descriptor. | The validator suite and the registry-document tests below. |
| extensions | Each of the four repository extension registries names meta-schema 0.8.0 and advances its own `registry_version`. None references a non-canonical resource. `escapewheel-aind` pins no registry identifier. | `registry/check.py` over every extension registry. |
| reader, writer, validator, adapters | The writer records §3.8's per-clock counts in place of one total and withdraws its option to map `analysis.spike_events` onto a clock other than the session's reference. The validator adds §3.5's invariant. Tests pinning meta-schema 0.7.0, the v0.4 descriptor or core 0.7.0 follow the new identifiers. Comments citing Part 01 §3.9 for the record cite Part 02 §12.6, and the validator's citation of Part 07 for §3.9 cites Part 05 §5.3. The reader is unchanged: it refuses a session with no reference clock and reads no parameter. | The writer and validator suites. |
| conformance fixtures and tests | A corpus clean variant with one clock and no reference. Registry-document cases for §3.4. A validator test for §3.9 and a writer test for §3.8. | `fixtures/corpus.py` and the package suites. |
| revision process and tooling | Ordinary ledger and evidence records. R20 §5.1 becomes `superseded`. R37 §3.3 and R40 §2.1 gain notes. R40 §2.2 moves to `ew-clock-alignment-record`. R95 §3.3 gains `ew-validation-shim` and R86 §2.4 gains `ew-reader-session-presentation`. `facts.py`, the interval-kinds probe and the registry-codegen prototype's registry document follow the new identifiers. The placement-defect inventory closes PD-023 to PD-028 and PD-008's remaining item, and removes the row-group statement from PD-016's remainder. | `ledger.py`, `evidence.py` and `revisions/PLACEMENT-DEFECTS.md`. |
| generated publications and developer documentation | The combined specification and the heading index regenerate. Part 06 §4's column table shows the new description. The specification README's identifier table, `framework.py`'s expected values, `registry/README.md`, and Part 08 §§2 and 3 follow the new identifiers. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied` by canonical anchor:

- §3.1 at `ew-session-concept`;
- §3.2 at `ew-stable-identity`;
- §3.3 at `ew-clock-concept` and `ew-clock-alignment-record`;
- §3.4 at `ew-resource-content-class` and `ew-packet-content-classes`;
- §3.5 at `ew-registry-self-description` and `ew-registry-conformance`;
- §3.6 at `ew-analysis-promotion` and `ew-analysis-content-requirements`;
- §3.7 at `ew-numbered-part-ownership` and `ew-analysis-spike-events`;
- §3.8 at `ew-analysis-spike-events`; and
- §3.9 at `ew-validation-shim`.

These registry-document cases distinguish §3.4 from the current rule, each invalid under the v0.5
descriptor with `registry.resource.canonical_targets` and valid under v0.4 apart from its selector:

- a core table with a reference to `analysis.array_assets`;
- a core declaration naming an analysis declaration in `requires`;
- an extension's `extension` table with a reference to its own `analysis` table; and
- an extension's `extension` table with a reference to a core-registry analysis table, which is
  core-dependent.

Two positive cases pin what the rule admits. An extension's `analysis` table may reference its own
`extension` table, which R20 §5.1 forbade, and every shipped registry passes.

For the packet rules:

- a session with one clock and no reference passes, and two clocks with none fail
  `core.sessions.reference_clock_declared`, as today;
- a materialization omitting spikes on one of two clocks records a nonzero count for that clock and
  zero for the other, where the reference writer now records one total;
- a materialization cannot be directed onto a clock other than the session's reference, where the
  reference writer's suite now asserts that it can; and
- a table with two equal columns whose values vary draws one `info` finding under
  `<resource_id>.columns_duplicated`. Two equal constant columns draw none, and no case draws an
  error.

§§3.1, 3.2, 3.6 and 3.7 change no verdict, so their evidence is review of each part against its
clause. §3.3's recommendation is not machine-checked: `parameters` is free JSON, and Part 02 §12.6
keeps the facts a consumer needs in columns.

## 7. Open

Whether a Tier 2 rule checks that `analysis.spike_events.clock_id` equals the session's
`reference_clock_id` is deferred. §3.7 states the fact either way, and the reference writer
satisfies it.
