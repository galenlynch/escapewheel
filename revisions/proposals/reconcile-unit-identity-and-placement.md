# Reconcile Unit Identity and Its Immediate Placement Defects

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-21 |
| **Based on** | `46b1c048a84bdb7f27d89a1605a53b9c0143690c` |
| **Decision domain** | specification |
| **Affects** | Part 00 §§3.3, 4.3, and 9; Part 01 §3.13; Part 02 §§7.1 and 12.1; Part 05 reader behavior; Part 07 §7; Part 08 §4; unit-facing registry, extension, reader, fixture, and integration surfaces |

## 1. Problem

The current specification candidate gives a unit two incompatible identities. Part 00 §4.3 and
Part 01 §3.13 identify it by `(session_id, unit_id, sorting_run_id, curation_id)`. Part 02 §12.1
instead says that `unit_id` identifies the unit on its own, and Part 02 incorporates a registry in
which `core.units` has primary key `unit_id` and every reference to it uses that one column. The
Part 08 query and parts of the reference reader still implement the older tuple.

The conflict also demonstrates a placement problem. Exact logical identity belongs to Part 02 and
the registry it incorporates, not to the architectural map in Part 00 or the substrate-independent
concept definition in Part 01. Part 00 §3.3 likewise combines a logical session-scope definition,
reader composition behavior, copied registry counts, and implementation measurements. Part 02
§7.1 already owns session scope, Part 05 is the operational owner for reader obligations, and Part
07 owns implementation-dependent performance evidence.

The result is not merely editorial. The public reader accepts sorting and curation filters that it
applies to columns absent from current spike tables, and its standalone fixtures make those tests
pass by reconstructing the obsolete schema.

## 2. Evidence

### 2.1 Baseline and current owners

The baseline is commit `46b1c048a84bdb7f27d89a1605a53b9c0143690c`. The quick repository
verifier passed all 27 stages at that commit, including all 28 corpus packets. There were no other
open proposals or drafts.

Part 02 §12.1 states that the packet assigns `unit_id`, that it identifies a unit on its own, and
that a table keyed on a unit carries `unit_id` rather than the run or curation. The incorporated
`registry/logical_schemas.json`, registry version `0.2.0`, agrees:

- `core.units` has primary key `unit_id`;
- `core.spike_events` and `analysis.spike_events` have primary key
  `(session_id, unit_id, t_tick)` and reference `core.units` on `unit_id`;
- `core.unit_electrodes`, `core.unit_coordinates`, `core.unit_quality_labels`, and
  `core.unit_observation_intervals` reference `core.units` on `unit_id`; and
- all three unit-keyed tables in `aind_unit_qc` reference `core.units` on `unit_id`.

R81 records the decision that produced those declarations. R122 subsequently assigned logical
identities and references to Part 02 and its expressly incorporated registry. No open artifact
competes with either decision.

Part 00 §4.3 nevertheless says that a unit's identity is the four-column tuple and never
`unit_id` alone. Part 01 §3.13 repeats that rule as part of the semantic concept. Part 08 §4 joins
`core.units`, `aind_unit_qc.metrics`, and `core.unit_quality_labels` through the four obsolete
columns, even though the latter two tables do not carry the run or curation columns.

Part 00 §4.3 also says that a packet carrying sorted units carries `core.sorting_runs` and
`core.curation_versions`. That is a distinct, still-correct conditional resource obligation and
cannot be deleted with the bad tuple. `core.units` declares required identifiers and references to
both resources, but the current validator omits a foreign-key check when its target resource is
absent. Part 02 §12.1 is therefore the current logical owner to which this clause can move without
changing meaning. P6 can later express conditional resource requiredness as data rather than leave
that condition solely in prose.

### 2.2 Reproduced reader failure

The current generated valid packet has spike columns `session_id`, `unit_id`, `t_tick`, and
`amplitude`. Against that packet:

```text
packet.spike_times(0, clock=STORED)                         -> 30 rows
packet.spike_times(0, sorting_run_id=0, clock=STORED)       -> ArrowInvalid
```

The second call attempts to bind `sorting_run_id` against `core.spike_events`, where the field
does not exist. `Packet.spike_times()` also documents the obsolete composite identity,
`_unit_support()` attempts the same obsolete filtering on observation intervals, and the alignment
queries select and group by the removed run and curation columns.

`session_id` has a different role and should not be removed with those columns. Other packet
accessors use it as an ordinary session filter, and time conversion can use it to select one
session's reference clock and origin. The `units=` branch of `spike_times()` currently applies the
argument only to its `core.units` clock lookup, however, not to the selected spike rows. A unit
table spanning sessions can therefore retain spikes outside the named session and then attach a
missing or wrong clock. Reconciliation needs to retain `session_id` as query and conversion scope,
apply it consistently to both branches, and stop describing it as part of unit identity.

The reader's test registry declares the old composite primary and foreign keys and its packet rows
carry the removed columns. The validator's standalone fixture repeats the same old shape. Those
fixtures allow package tests to pass without exercising registry `0.2.0`. The writer fixtures and
the generated conformance packet already use the one-column reference model.

The public reader annotations also lag the incorporated declarations. Direct registry identifiers
such as `unit_id` and `session_id` are annotated as strings in several public functions even though
the current registry declares assigned `int32` identifiers. This is observable to callers and
static tooling even where Python does not enforce the annotation at runtime.

The current registry declares every direct identifier exposed by the affected reader surfaces as
`int32`, including session, unit, clock, event-stream, sorting-run, curation, and processing-run
identifiers. A complete annotation sweep therefore has a single current target rather than a type
choice to infer from test data.

That sweep has a bounded interface inventory. It covers registry-backed identifiers exposed by
`Packet` accessors; the clock, observation, and alignment functions; and run-resolution parameters,
results, and `Ambiguity` fields, together with their internal carriers. The channel helpers and
`Dataset.Session` already use integers. It does not infer types from an `_id` suffix: manifest
`sessions` are external `core.sessions.session_name` strings, and packet, profile, extension,
resource, schema, activity, and discriminator-scope names remain strings under their own catalog or
logical declarations. A focused test can map each affected public symbol to its registry column,
derive the expected Python scalar from that column's current declared type, and inspect the type
hints; this avoids both a hand-maintained duplicate type table and an unsafe suffix rule.

The root and reader README examples also demonstrate the obsolete surface: they pass string
session identifiers, call a nonexistent `trials()` method, and pass a list of unit-name strings to
the `units=` parameter that accepts an Arrow table. Those examples are executable-interface drift,
not an alternative unit model, and would be corrected with the public API.

### 2.3 Session-scope placement

Part 00 §3.3 reports 33 of 35 tables as session-scoped and eight as reaching `core.sessions`
without carrying `session_id`. Those copied measurements are stale: the current registry has 43
core and analysis tables, 41 are session-scoped, and Part 02 §7.1 now requires every
session-scoped table to carry and reference `session_id`.

The same Part 00 section prescribes the discriminator a reader adds when presenting packets
together and includes query-planner measurements. Part 02 §7.1 already owns the logical graph
property. Part 00 §9's accepted dependency direction assigns operation under upstream contracts to
Part 05, while Part 07 §7 already owns the implementation-specific projection measurement. The
architectural section is therefore neither the narrowest owner nor a stable home for those facts.

Part 00 §9's subject table currently describes Part 05 as validation, import, writer lifecycle,
reporting, and packet publication, while the dependency direction immediately below says Part 05
specifies how writers, readers, and validators operate. Moving the reader rule therefore also
requires making that Part 05 subject projection internally consistent; it does not require
choosing a new owner.

The session-scope citation review exposed a separate registry-conformance defect. Part 02 §7.1
literally requires every session-scoped table to declare a direct `session_id` reference to
`core.sessions`. Four extension tables instead carry `session_id` inside a composite reference to
another session-scoped table. `registry/check.py` documents the difference and deliberately checks
the weaker transitive form. Choosing between redundant direct references and a generalized
transitive rule changes registry semantics and belongs to P4's uniform core-and-extension
conformance work. This proposal neither changes Part 02 §7.1 nor claims that the known mismatch is
resolved by moving its reader consequences.

### 2.4 Overlap and citations

The affected accepted decisions are R81 for packet-assigned unit identifiers and R86 for
session-scoped multi-packet reader projection. This proposal preserves both outcomes; it corrects
the current owners and projections that drifted after them. R122 supplies the ownership rules, and
R120 supplies the structural-editing procedure.

The initial impact scan for Parts 00 §§3.3 and 4.3, 01 §3.13, 02 §§7.1 and 12.1, and 08 §4 found
48 citation occurrences to read. Adding the Part 00 §9 ownership row and Part 07 §7 evidence
destination expands the final scan to 117 occurrences, including this proposal and immutable
accepted records. The live implementation citations mostly point to Part 00 §3.3 from the dataset
reader and its tests or to Part 02 §7.1 from writer and registry checks. Part 00 §4.3 and Part 01
§3.13 are otherwise cited only by the placement-defect inventory; Part 08 §4 has no external
citers. Structural incorporation will need stable anchors on every moved source and destination
before headings move. Historical accepted records remain unchanged.

The exact anchor bootstrap inventory is six existing headings: Part 00 §4.3, Part 01 §3.13, Part
02 §§7.1 and 12.1, Part 07 §7, and Part 08 §4. Part 00 §§3.3 and 9 already have canonical anchors.
The new Part 05 reader section can receive its anchor when created. Under the structural procedure,
the six insertions would form a metadata-only commit before the structural draft's final appraisal.

The stale table-of-contents finding assigned to P2 is already resolved by R122: Part 00 and the
informational specification README both list Part 10 and the framework check verifies their
projection. No further part-inventory change is presently supported by evidence.

## 3. Desired outcome and constraints

A successful resolution would leave one coherent rule with these properties:

- Part 01 defines a Unit as the spiking entity produced by one sorting and curation without
  prescribing its logical key.
- Part 02 §12.1 and the incorporated registry remain the sole exact owners of in-packet unit
  identity: packet-assigned `unit_id`, unique within the packet, with run, curation, and local label
  retained as facts on `core.units`.
- The existing condition that units require their sorting-run and curation resources moves intact
  from Part 00 to the logical owner in Part 02; P6 later makes conditional resource requiredness
  declarative.
- A unit-keyed core, analysis, or extension table joins to `core.units` through `unit_id` alone.
- A reader may accept `session_id` to restrict a query or choose a session's clock and origin, but
  does not use it as part of unit identity and applies the restriction to every selected row.
- Relating a unit to its source outside the packet continues to use the source-facing relation
  Part 02 defines, rather than treating the assigned number as globally stable.
- Part 02 §7.1 owns the session-scope graph property; Part 05 owns reader composition obligations;
  Part 07 carries implementation measurements; and Part 00 retains only the architectural map,
  including a Part 05 subject row consistent with that ownership, and links needed to locate the
  rules.
- Current packet bytes and registry declarations remain valid. The work repairs prose, examples,
  implementations, fixtures, and evidence rather than migrating the already-correct current packet
  shape.
- The currency rule remains explicit. `Packet.units()` continues to refuse when selecting the
  packet's unit set would choose among unresolved sorting or curation alternatives. An exact
  `unit_id` or caller-supplied unit table already selects rows, so `Packet.spike_times()` does not
  repeat that guard or treat inspection of a selected non-preferred result as ambiguous.
- Every reader annotation that directly exposes a current logical-table identifier agrees with the
  incorporated registry. The sweep is limited by the symbol-to-column inventory in §2.2 and does
  not change catalog or manifest strings merely because their names end in `_id`.

The resolution would not redesign run or curation resources, cross-packet entity reconciliation,
session identity, or the registry's assignment algorithm. It would not use a compatibility layer
to make obsolete columns appear in current tables.

## 4. Options and tradeoffs

### 4.1 Restore the composite key

This option would change the registry and current packets back to four-column unit references,
restore those columns on every dependent table and extension, and retain the reader API. It would
reverse R81, duplicate context already reachable through `core.units`, and require packet
regeneration for an identity rule whose accepted motivation still applies. The current generated
packets and writer are evidence against this option.

### 4.2 Selected direction: packet-assigned `unit_id`

This is the selected contract. It treats Part 02 and the incorporated registry as the intended
design, removes the conflicting exact key from Parts 00 and 01, corrects examples and reader
operations, and updates fixtures to the current declaration. It changes no current packet bytes.

The narrowest API form removes `sorting_run_id` and `curation_id` from `spike_times()` while
retaining `session_id` as a session filter and time-conversion scope. Keeping the removed
parameters could be implemented by looking up `core.units` first and treating them as redundant
context assertions, but that would preserve an API whose stated purpose was the obsolete
identity. There are no released consumers or remote compatibility commitments, and the existing
filters already fail on current packets, so the selected design removes them instead of adding a
compatibility path.

The explicit-selection path does not invoke the run-currency guard. `Packet.units()` retains the
guard because it offers to choose the packet's unit set; `spike_times(unit_id=…)` and
`spike_times(units=…)` instead read an identifier or set the caller already selected. A caller who
wants the guarded current view can still compose `spike_times(units=packet.units())`. A caller who
deliberately wants another declared result can select rows from `table("core.units")` without the
reader making that result current.

### 4.3 Selected proposal boundary

This proposal covers the unit-identity reconciliation plus the directly coupled session-scope
placement in Part 00. It is one structural revision because the stale reader and join behavior
cannot be corrected while the current numbered parts still require the opposite.

The larger Part 01 and Part 02 placement inventories contain independent scalar-type, nullability,
manifest, validator, writer, and performance statements. Their meaning-preserving relocations can
be completed as separate ordinary P2 maintenance after the identity revision; any newly found
semantic difference would become its own proposal. Folding all of them into this proposal would
make acceptance of unit identity depend on unrelated editorial and operational questions.

P4 would retain the separately discovered direct-versus-transitive session-reference question.
That work already owns uniform registry-document semantics and extension conformance, while P2 can
move the existing session-scope and reader rules without selecting a different registry invariant.

## 5. Impact sketch

- **Semantic prose — affected.** Part 01 §3.13 would retain what a Unit means and its relationship
  to one sorting and curation, while removing the exact logical tuple. Other semantic concepts are
  unchanged.
- **Logical prose and declarations — affected prose, unchanged data.** Part 02 §§7.1 and 12.1
  remain the logical owners and may be tightened to distinguish packet-local identity from
  cross-packet presentation. Part 02 §12.1 would also preserve the current condition that carrying
  units entails carrying the sorting-run and curation resources they reference. The registry
  meta-schema, core registry declarations, and Tier 1 or Tier 2 rules do not need a shape change.
- **Physical profiles — unchanged.** No Parquet, Zarr, media, ordering, or encoding rule changes.
- **Packet catalog and incorporated JSON Schemas — unchanged.** The catalog does not encode a unit
  key. No manifest migration follows.
- **Validation and import — affected placement, unchanged packet verdict.** Part 05 would gain the
  current reader-composition obligation now misplaced in Part 00. The writer already assigns and
  emits the current key. Validator behavior stays data driven from the packet registry, while its
  standalone test fixture changes to exercise the current shape.
- **Extension registries — declarations unchanged, examples and tests affected.** The current
  `aind_unit_qc` declaration already uses `unit_id`; its example join and any fixture assertions
  would be reconciled. The AIND adapter's source-facing `(device_name, local_unit_label)` lookup to
  the assigned `unit_id` already follows Part 02 and needs no behavioral change. P4 retains the
  independent question of direct versus transitive session references in four extension tables.
- **Reader — affected.** Obsolete filters, alignment columns, support filtering, composite-key
  documentation, run-module rationale, and registry-field annotations would be corrected. The
  surviving `session_id` filter would be applied consistently as query and time-conversion scope,
  not identity. Explicit unit selections would bypass the run-currency guard, while
  `Packet.units()` would retain it. The bounded symbol-to-column inventory in §2.2 would determine
  which identifier annotations change. Dataset citations would point to the new logical and
  operational owners.
- **Writer and adapters — behavior unchanged.** Existing unit assignment, extension production,
  and current-registry output already agree. Requirement citations and stale comments would be
  reviewed and repointed where necessary.
- **Existing packets — unchanged.** Current generated packets already use the selected key. No
  migration is needed. Obsolete standalone package fixtures would be regenerated or rewritten;
  they would not be retained as compatibility fixtures without a supported legacy contract.
- **Conformance fixtures and implementation tests — affected.** Reader and validator fixtures
  would use current types, columns, primary keys, and references. Alignment, observation, accessor,
  extension-query, and type tests would assert the current design. One writer-built packet would be
  opened by the reader and validated to prevent the package fixtures from defining a private
  schema again. The existing module-scoped writer end-to-end fixture already builds and validates
  such a packet and imports the reader, so adding the public unit reads there needs no second build.
  Generated test-only registry snapshots can keep the reader and validator suites standalone
  without bundling a core registry in either runtime package.
- **Lifecycle, ledger, and evidence — affected.** This is a structural specification change under
  R120. Source and destination anchors, a crosswalk, updated R81/R86 clause dispositions, and one
  evidence manifest would accompany incorporation. The broader placement inventory remains the
  observation-level tracker rather than becoming specification history.
- **Generated publications and human documentation — affected.** The combined specification,
  rendered references, registry README example, root and package examples, API documentation, and
  generated root status and TODO facts would be regenerated or corrected. Historical accepted
  revisions and the frozen POC remain unchanged.

### 5.1 Distinguishing evidence

The completed change would be distinguishable through the following evidence:

1. structural checks show one `unit_id` primary key and only one-column unit references in core and
   every extension;
2. a current writer-built packet supports both a one-unit read and a table-of-units read without
   binding removed columns;
3. single- and multi-unit reads restricted by `session_id` contain only rows from that session and
   use that session's declared clock and origin without treating the field as a unit-key column;
4. the Part 08 extension query executes against current tables using `unit_id` and returns the
   expected groups;
5. alignment and observation operations return current-schema columns and preserve clock/support
   behavior;
6. standalone reader and validator fixtures contain no obsolete unit-key columns and their suites
   still pass;
7. a symbol-to-column mapping test derives expected types from the current registry and confirms
   every mapped public reader annotation, without treating manifest or catalog names as logical
   identifiers;
8. multi-packet dataset tests still project the packet-and-session discriminator only for
   session-scoped tables and join cross-packet unit results through that discriminator plus
   `unit_id`; and
9. focused package suites, the complete conformance corpus, citation and ledger checks, generated
   artifact checks, and the full repository verifier pass.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [x] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
