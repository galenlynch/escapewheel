# A Unit Is Identified by Its Packet-Assigned Unit ID

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `8ac911aab964c0da54ec22b5b73ce5cc199be864` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§3.3, 4.3, and 9; Part 01 §3.13; Part 02 §§7.1 and 12.1; Part 05 (new §13); Part 07 §7; Part 08 §4 |
| **Depends on** | R81 §§2.1–2.6; R86 §§2.1–2.4; R120 §§3.3–3.8; R122 §§3.3–3.6 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6 |

Section 3 is normative. Sections 1, 2, and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision reconciles the specification with the logical unit identity already incorporated by
Part 02: a packet-assigned `unit_id` identifies a unit within one packet, and a reference to that
unit uses `unit_id` alone. It removes the incompatible composite identity from the architectural
and semantic parts, preserves the condition that a packet carrying units carries the sorting and
curation resources they name, and corrects informative queries and reader behavior that still use
the obsolete key.

It also completes the directly coupled placement repair in Part 00 §3.3. Part 02 remains the owner
of logical session scope, Part 05 becomes the explicit owner of reader composition and exact-unit
selection behavior, and Part 07 retains only informative implementation rationale. Part 00 keeps
the packet concept and architectural map rather than exact registry counts, reader algorithms,
join keys, or measurements.

This is a structural revision because append-only text would leave the contradictory identity and
misplaced reader rules in their present owners. The existing source material must be retired,
split, or reduced while its surviving rules move to the sections that own their subjects.

### 1.1 Structural crosswalk

The canonical anchors in this table are the stable identities used during incorporation. Six
existing headings do not yet have them; §6.1 records the required metadata-only bootstrap.

| old location | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 00 §3.3 `ew-packet` — packet definition, contents, and single- or multi-session allowance | retain | Part 00 §3.3 `ew-packet` | none | §3.6 |
| Part 00 §3.3 — session-scope definition and copied table counts | remove the duplicate definition and stale counts | Part 02 §7.1 `ew-session-scope` | none; the existing logical rule remains authoritative | §§3.3, 3.6 |
| Part 00 §3.3 — reader discriminator, label, and cross-packet presentation rules | move | new Part 05 reader-session-presentation subsection, planned anchor `ew-reader-session-presentation` | none | §§3.3, 3.6 |
| Part 00 §3.3 — unit join-key rule | replace the misplaced duplicate | Part 02 §12.1 `ew-unit-identity`; new Part 05 reader-unit-selection subsection, planned anchor `ew-reader-unit-selection`, for operational selection | correct the composite-key conflict while preserving packet versus cross-packet scope | §§3.1, 3.3, 3.4 |
| Part 00 §3.3 — join-cost measurement | retire from current normative prose | accepted R86 retains provenance; Part 07 §7 retains only current qualitative implementation rationale | no contract change | §3.6 |
| Part 00 §4.3 `ew-unit-identity-architecture` — composite identity | retire and give its anchor as an alias to the logical successor | Part 02 §12.1 `ew-unit-identity` | change: `unit_id` alone is the unit identity | §§3.1, 3.6 |
| Part 00 §4.3 `ew-unit-identity-architecture` — sorting and curation resource condition | move | Part 02 §12.1 `ew-unit-identity` | none | §§3.2, 3.6 |
| Part 00 §9 `ew-numbered-part-ownership` — Part 05 subject row | amend | Part 00 §9 `ew-numbered-part-ownership` | clarify that Part 05 owns reader operations, as its dependency-direction clause already states | §3.6 |
| Part 01 §3.13 `ew-unit-concept` — composite logical key | remove from the semantic concept | Part 02 §12.1 `ew-unit-identity` | change: Part 01 defines what a Unit means without selecting its logical key | §§3.1, 3.6 |
| Part 01 §3.13 `ew-unit-concept` — one sorting and curation per Unit | retain | Part 01 §3.13 `ew-unit-concept` | none | §3.1 |
| Part 02 §7.1 `ew-session-scope` | retain as the logical owner | Part 02 §7.1 `ew-session-scope` | none; direct-versus-transitive extension conformance remains deferred | §§3.3, 3.6 |
| Part 02 §12.1 `ew-unit-identity` | retain and add the relocated resource condition | Part 02 §12.1 `ew-unit-identity` | identity unchanged from the incorporated registry; conditional requiredness becomes single-owned prose | §§3.1, 3.2, 3.6 |
| Part 05, after §12 | add three reader-operation subsections under the planned anchor `ew-reader-operations` | planned anchors `ew-reader-session-presentation`, `ew-reader-unit-selection`, and `ew-reader-declared-types` | state reader presentation, exact-selection, and declared-type behavior in the normative operational part | §§3.3–3.6 |
| Part 07 §7 `ew-reference-performance-notes` | demote its uppercase reader recommendation to informative rationale and repoint it | the new Part 05 reader-session-presentation subsection owns the rule; Part 07 §7 remains informative | none; exact historical ratios not re-established at this baseline are not presented as current measurements | §§3.3, 3.6 |
| Part 08 §4 `ew-example-queries` | correct the query projection | Part 02 §12.1 and the incorporated registry own the key; Part 08 remains informative | none; the example begins agreeing with the current contract | §§3.1, 3.6 |

The specification README, root README, registry README, reader README, API documentation, and
generated combined specification are projections or developer documentation rather than new
normative destinations. They change during incorporation but do not acquire an entry in the
normative crosswalk.

## 2. Background

### 2.1 The authoritative logical declarations already use one unit identifier

Part 02 §12.1 says that the packet assigns `unit_id`, that it identifies a unit on its own, and
that a unit-keyed table carries `unit_id` rather than the producing run or curation. The expressly
incorporated core registry agrees. `core.units` has primary key `unit_id`; core and analysis spike
events reference it on `unit_id`; the four other core unit relations reference it on `unit_id`;
and all three unit-keyed `aind_unit_qc` tables do the same.

Part 00 §4.3 and Part 01 §3.13 instead require
`(session_id, unit_id, sorting_run_id, curation_id)`. The Part 08 query joins on that obsolete
tuple even though its extension and quality tables do not carry the run or curation columns. This
is an ownership conflict, not a choice between two equally current encodings: R81 produced the
one-column declarations, and R122 assigns exact logical identities and references to Part 02 and
the registry it incorporates.

The second sentence of Part 00 §4.3 is independent of the bad key. A packet with `core.units`
needs the `core.sorting_runs` and `core.curation_versions` rows its required columns name. The
current validator skips a foreign-key check when the target resource is wholly absent, so the
condition must remain in prose until later requiredness work can declare it as data.

### 2.2 The current reader implements both identities

The generated conforming packet's `core.spike_events` table carries `session_id`, `unit_id`,
`t_tick`, and `amplitude`. At the appraisal baseline, a stored-clock read for `unit_id = 0`
returns 30 rows. Passing `sorting_run_id = 0` to the same public method raises an Arrow field error
because that column is absent. The accessor, its support helper, alignment queries, standalone
reader registry, and validator fixture nevertheless retain the four-column model.

The reader also invokes its unresolved-run guard before either spike-selection path. That guard is
appropriate for `Packet.units()`, which offers to choose the packet's unit set. It is not a choice
when the caller supplies a packet-unique `unit_id` or an explicit table of units. Keeping the guard
there prevents deliberate inspection of an exact non-preferred result and can let an ambiguity in
an unrelated scope block the selected unit.

`session_id` has a separate operational role. It may restrict returned rows and select the
session's reference clock and origin, but the multi-unit path currently narrows only its clock
lookup and not its spike rows. That can retain rows from sessions other than the one named and
attach a missing or wrong clock. Retaining the parameter as query scope therefore requires applying
it consistently; it does not restore it to unit identity.

### 2.3 Identifier types are another projection of the registry

The affected public reader annotations describe several logical identifiers as strings. The
current registry declares the direct session, unit, clock, event-stream, sorting-run, curation,
and processing-run identifiers exposed there as `int32`. Channel helpers and the dataset's
session record already use host-language integers.

The correction is not a suffix rewrite. The packet catalog's session inventory contains external
`session_name` strings, and packet, profile, extension, resource, schema, activity, and
discriminator-scope names remain strings under their own declarations. A bounded mapping from
public symbols to logical registry columns can derive the expected host type without maintaining
a second type table or treating every `_id` alike.

### 2.4 Session-scope placement and impact

Part 00 §3.3 copies the former 33-of-35 session-scope count, reader behavior, and performance
evidence into architecture. Re-running `registry/check.py` against registry `0.2.0` finds 43 core
and analysis tables: 41 are session-scoped and two are not. Part 02 §7.1 already owns the graph
definition and the required `session_id` declaration. Part 05 is the normative operational owner
for reader behavior, while Part 07 is informative.

Four extension tables expose a separate disagreement: Part 02 §7.1 literally asks each
session-scoped table to reference `core.sessions` directly, while those tables carry `session_id`
inside a composite reference to another session-scoped table. `registry/check.py` presently checks
the weaker transitive interpretation. This revision does not select between redundant direct
references and a generalized transitive rule; uniform registry-document conformance remains the
dependent P4 work.

The final reverse-impact scan covered Part 00 §§3.3, 4.3, and 9; Part 01 §3.13; Part 02 §§7.1 and
12.1; Part 07 §7; and Part 08 §4. It found 117 citation occurrences across current implementation,
documentation, lifecycle records, and immutable history. Current citers must be repointed during
incorporation; accepted records remain unchanged.

## 3. Decision

### 3.1 Unit meaning and logical identity

Part 01 **MUST** define a Unit as a sorted or curated spiking entity that belongs to one sorting
run and one curation version, without prescribing a logical key.

Within one packet, `unit_id` **MUST** identify a unit on its own and **MUST** be the primary key of
`core.units`. The packet **MUST** assign that identifier by the deterministic rule Part 02 §12.1
states. `sorting_run_id`, `curation_id`, and `local_unit_label` **MUST** remain facts about the unit
on `core.units`; they **MUST NOT** become additional components of the unit's packet-local
identity.

A core, analysis, or extension table that references `core.units` **MUST** make that reference on
`unit_id` alone. A session-scoped table may carry `session_id`, and a relation may have other
columns in its own primary key, but `session_id`, `sorting_run_id`, and `curation_id` **MUST NOT**
be added to the reference in order to identify the unit. Outside the packet, a consumer **MUST**
use the source-facing relation Part 02 §12.1 defines rather than treating the packet-assigned
number as globally stable.

### 3.2 Resources required by units

A packet that carries `core.units` **MUST** carry `core.sorting_runs` and
`core.curation_versions`. This obligation **MUST** be stated with the logical unit rules in Part 02
until an incorporated declarative requiredness mechanism expresses and enforces the same
condition.

### 3.3 Session scope and reader presentation

Part 02 §7.1 **MUST** remain the sole owner of the logical definition of a session-scoped table. A
reader presenting one or more packets as one relation **MUST** carry a session discriminator on
every session-scoped table and **MUST NOT** carry one on a table that is not session-scoped.

The discriminator **MUST** distinguish the packet a row came from together with that packet's
`session_id`. A reader **MUST NOT** derive it from `session_name` or another `*_name`. A reader
**SHOULD** expose a compact integer for each such packet-and-session pair and **SHOULD** carry
`session_name` beside it as a non-identifying label.

Within one packet, a reader **MUST** join a unit-keyed relation to `core.units` through `unit_id`
alone. Across packets, it **MUST** include the session discriminator with `unit_id`; it **MUST NOT**
widen the packet-local unit reference itself. A reader **SHOULD** add the discriminator and label
as scalar projections over `session_id` rather than joining them from `core.sessions`, so an engine
can prune values a query does not select.

### 3.4 Exact unit selection and currency

A reader operation given an exact packet-assigned `unit_id` or an explicit table of units
**MUST** treat that input as the selected unit or units. It **MUST NOT** reject that selection
solely because the packet leaves a sorting or curation preference unresolved, and **MUST NOT**
require `sorting_run_id` or `curation_id` as redundant identity arguments.

An operation that offers to choose the packet's current unit set **MUST** continue to report an
unresolved alternative rather than silently select or concatenate competing results. Passing the
result of that guarded operation into an exact spike read remains guarded at the selection step.
Exact selection does not declare a non-preferred result current and does not make a packet that
violates Part 05 §12 conforming.

Where an exact-unit reader operation accepts `session_id`, it **MUST** use it only as query and
time-conversion scope. It **MUST** apply the restriction to every selected spike row and to the
clock and origin used for conversion, and **MUST NOT** use it to disambiguate `unit_id`.

### 3.5 Reader projections of identifier types

Where a reader publishes a static type for a parameter, return value, or field that directly
carries a logical-table identifier, it **MUST** derive the corresponding host-language scalar type
from the incorporated registry's declared logical type. It **MUST NOT** infer the type from an
`_id` suffix or apply a logical-table identifier mapping to a catalog, manifest, vocabulary, or
discriminator-scope name governed by another declaration.

### 3.6 Ownership and informative projections

Part 00 **MUST** retain the packet concept and architectural ownership map and **MUST NOT** own
exact unit keys, copied registry counts, reader selection algorithms, or implementation
measurements. Its Part 05 subject entry **MUST** include reader operations, consistent with the
dependency direction already stated there.

Part 01 **MUST** own the substrate-independent Unit meaning, Part 02 **MUST** own unit identity and
logical session scope, and Part 05 **MUST** own the reader obligations in §§3.3–3.5. Part 07 and
Part 08 **MUST** remain informative projections and **MUST NOT** state a second normative version
of those rules. The structural incorporation **MUST** follow the crosswalk in §1.1 without treating
relocation alone as authority to change meaning.

## 4. What this does not change

- The registry meta-schema, registry `0.2.0` declarations, and Tier 1 or Tier 2 rules do not change.
  They already use the selected unit identity.
- Current generated packets do not change shape and require neither migration nor regeneration for
  conformance. Obsolete standalone test packets are fixtures, not a supported legacy format.
- The unit-number assignment algorithm, run and curation models, local labels, and cross-packet
  entity reconciliation do not change.
- Part 05 §12 still requires a conforming committed packet to resolve competing run currency.
  Exact selection specifies what a reader does with selected rows; it is not another preference
  mechanism and does not waive packet validation.
- The direct-versus-transitive session-reference question for four extension tables remains for
  P4. This revision neither weakens Part 02 §7.1 nor changes those declarations.
- The conditional resource obligation remains prose until P6 establishes a declarative packet
  requiredness mechanism.
- Physical profiles, the packet catalog schema, resource encodings, and release identifiers do not
  change.

## 5. Consequence

The packet contract converges without a byte migration. The behavioral compatibility change is in
the unreleased reader API: `Packet.spike_times()` loses its nonfunctional `sorting_run_id` and
`curation_id` parameters, treats explicit units as exact selections, and applies `session_id`
consistently as a query and conversion scope. There are no released consumers or remote
compatibility commitments. The broader identifier-annotation correction changes static API
descriptions from strings to host-language integers where the registry declares `int32`; manifest
and catalog strings remain strings.

The structural incorporation requires a metadata-only anchor bootstrap before final appraisal,
then an atomic accepted change that updates owners, live citations, ledger destinations, generated
renderings, implementations, fixtures, tests, and human documentation.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Remove the composite logical key from Part 01 §3.13; retain Unit meaning and one sorting/curation relationship. | Anchored Part 01 text and semantic review against §3.1. |
| logical prose and registry | Keep Part 02 §§7.1 and 12.1 as owners; add the conditional resource sentence to §12.1. Registry and rules remain byte-identical. | Registry diff is empty; structural checks show `core.units` primary key and every unit reference; ledger resolves §§3.1–3.3. |
| physical profiles | Unchanged because no encoding, ordering, partition, or storage rule changes. | No authored or generated Part 03 diff beyond repointed citations, if any. |
| packet catalog and JSON Schemas | Unchanged because the catalog does not encode a unit key and the manifest session inventory remains external names. | Schema and vendored-schema generation preserve candidate bytes. |
| validation and import | Add no new packet verdict; retain the prose-only conditional resource obligation pending P6. Reconcile the validator's standalone fixture with registry `0.2.0`. | Existing valid corpus verdict is unchanged; validator fixture and focused suite pass. |
| extensions | Keep declarations unchanged; correct the Part 08 and extension-test joins to `unit_id`. Defer the four session-reference declarations to P4. | Extension structural checks and executable unit-QC join pass. |
| reader, writer, validator, adapters | Correct reader selection, alignment, support, run rationale, session filtering, and identifier types. Writer and adapters remain behaviorally unchanged; review their citations. | Focused reader suite; registry-derived symbol-type test; current writer-built packet opened by reader and validated; repoint check. |
| conformance fixtures and tests | Replace legacy unit shapes in standalone reader and validator fixtures; add exact-selection, session-scope, current-schema integration, and positive/negative type-mapping cases. | Named tests collect and pass; complete 28-packet corpus remains unchanged in verdict. |
| revision process and tooling | Use structural crosswalk, bootstrap six anchors, repoint R81/R86 ledger targets, update headings and one evidence manifest. Process semantics do not change. | Anchor-bootstrap check, headings, ledger, evidence, impact, stages, and citation checks pass. |
| generated publications and developer documentation | Regenerate the combined specification and column views; correct specification/root/registry/reader summaries, examples, API docs, placement inventory, status, and TODO facts. | Generators preserve candidate state; documentation examples match callable APIs and current declarations. |

## 6. Conformance and implementation evidence

The following cases distinguish the completed change from the contradictory baseline:

1. Registry inspection finds primary key `unit_id` on `core.units` and a one-column `unit_id`
   reference from every core, analysis, and extension table that references it. A negative
   structural test rejects a restored composite unit reference.
2. The current writer end-to-end fixture builds and validates one packet, the reader opens that
   same packet, and both `spike_times(unit_id=…)` and
   `spike_times(units=packet.units(...))` return rows without binding removed fields.
3. A packet fixture with unresolved sorting alternatives shows the behavioral boundary:
   `Packet.units()` raises the existing ambiguity, while a known `unit_id` and an explicit unit
   table read exactly the selected spikes. The test does not treat that packet as conforming.
4. A multi-session fixture verifies that `session_id` restricts both single- and multi-unit spike
   rows and selects the same session's reference clock and origin. A mismatched scope cannot attach
   another session's clock or seconds.
5. Alignment and observation results contain the current columns, preserve clock mapping and
   attached support, and never filter support by removed run or curation columns.
6. The Part 08 quality query executes against current core and `aind_unit_qc` tables using
   `unit_id` and returns its expected groups.
7. A checked mapping names each public reader symbol that directly exposes a logical identifier,
   obtains its declared type from the current registry, maps that logical scalar to the reader's
   host type, and compares resolved annotations. Separate assertions keep manifest session names,
   packet IDs, resource IDs, and discriminator scopes as strings.
8. Dataset tests establish that both Arrow and SQL paths project the same session discriminator
   only on session-scoped resources, never derive it from a name, use `unit_id` alone within a
   packet, and use the discriminator plus `unit_id` across packets. Query-plan evidence confirms
   the SQL view projects rather than joins the discriminator; no unrefreshed timing ratio is needed
   for acceptance.
9. Focused reader, validator, writer, and extension suites pass, followed by the complete
   conformance corpus and repository verifier. Citation, repoint, ledger, evidence, heading, and
   generation-preservation checks pass on the same candidate.

### 6.1 Required anchor bootstrap

Before the final acceptance appraisal, a separate metadata-only commit must add one canonical
anchor immediately before each of these existing headings:

| current heading | canonical anchor |
|---|---|
| Part 00 §4.3 | `ew-unit-identity-architecture` |
| Part 01 §3.13 | `ew-unit-concept` |
| Part 02 §7.1 | `ew-session-scope` |
| Part 02 §12.1 | `ew-unit-identity` |
| Part 07 §7 | `ew-reference-performance-notes` |
| Part 08 §4 | `ew-example-queries` |

Part 00 §§3.3 and 9 already have canonical anchors. The new Part 05 headings receive their anchors
when created. After the bootstrap, this draft's `Based on` value, counts, impact scan, and citation
inventory must be refreshed before final appraisal.

## 7. Open

The broader meaning-preserving placement inventory in Parts 01 and 02 remains ordinary P2
maintenance after this revision. Any discovered semantic difference starts a separate proposal.
P4 retains the direct-versus-transitive extension session-reference decision, P6 retains
declarative conditional resource requiredness, and P10 retains generation and execution of the
complete example packet. None changes the Decision above.
