# The profile descriptor declares the overriding orders

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-30 |
| **Based on** | `37316eb51287334b5b482dc7ffef542a656b6a9b` |
| **Decision domain** | specification |
| **Affects** | Part 03 §1's statement of what the descriptor owns; Part 03 §5.3's statement of the override and §5.4's table of overriding orders; Part 06 §4's summary of the stored order; Part 09's statement of what an extension controls; the incorporated physical-profile schema and the `escapewheel-portable-v0.1` descriptor |

## 1. Problem

Part 03 §1 divides the portable profile between two owners. The incorporated descriptor owns the
profile's exact facts, "identifiers, kind-to-interface mapping, interface forms, ownership
compatibility, variants, reader floors, floor roles, and anchors", and the prose owns their meaning
and the obligations of each actor. One exact fact escapes that division. Part 03 §5.3 stores every
table in its primary key's order unless §5.4 gives it another, and §5.4 gives one:
`analysis.spike_events` is stored by `session_id, clock_id, time_bucket_tick, unit_id, t_tick`. That
order exists only as a row of a Markdown table.

A writer emits the order and a validator establishes it, so each implementation restates it, and
nothing checks the reference implementation's copy against Part 03 §5.4. The parts restate it too.
Part 00 §2.3 lets another artifact present a normative fact only as a mechanically checked
projection, an explicitly informative explanation linking its owner, or a consistency condition,
and Part 06 §4, which is normative, describes the order in its own words. The rule that an override itself settles its
key by adjacency is also unchecked where it was meant to be: R93 required a check made without a
packet, and no current part states one.

## 2. Evidence

Observed in the tracked files at the baseline commit.

### 2.1 The descriptor states no order

The descriptor's members are `$schema`, `id`, `logical_standard`, `kind_interfaces` and
`interfaces`, and the schema closes every object, so no order can be stated in it today. Part 03
§2's mapping table is generated from the descriptor; §5.4's table is written by hand, and §5.4 has
no stable anchor.

The order is restated in hand-written prose twice more. Part 03 §5.3 names the table and the two
columns that let its order satisfy the section. Part 06 §4, which is normative, says the table is
stored "by unit within each time bucket".

### 2.2 One unchecked constant in the reader serves four consumers

`escapewheel-reader/src/escapewheel_reader/ordering.py` declares `OVERRIDES`, mapping
`analysis.spike_events` to the five columns, and `stored_order`, which returns an override or else
the primary key. Its docstring places the copy in the reader because the writer and validator both
depend on the reader and neither depends on the other. It is read by:

- the writer, to order each table before writing (`arrow.py`);
- the validator, to scan each table's order and to decide whether adjacency settles uniqueness
  (`validator.py`, `generate.py`); and
- the conformance corpus's builder, to order each table of its 120 packets (`fixtures/build.py`),
  the builder's only import from an implementation.

No check compares `OVERRIDES` with Part 03 §5.4. Validator tests patch the constant to exercise the
adjacency argument, and none reads the part.

### 2.3 R93's check of an override without a packet did not reach the parts

R93 §3.3 removed the per-table `sort` field from the registry because stored order is a physical
property, and it left Part 03 §5.4's table as "the only statement an override has". The same
section required that a validator refuse an override that does not settle its key by adjacency, "a
check made with no packet in hand". No current part states that check. The ledger disposes of R93
§3.3 as `registry`, with a note naming the reader's constant as the machine copy. The reference
validator has no check of that kind. Where an override does not settle its key, the validator settles
uniqueness by aggregate when it scans each packet.

R129 then made the descriptor the profile's machine-readable owner and stated that it did "not
change … stored-order rules". Neither revision decided that the order should stay out of machine
form: R93 moved it to the profile before the profile had a descriptor, and R129 scoped it out.

### 2.4 A descriptor change need not change the profile identifier

R137 changed the descriptor's Zarr floor incompatibly. It advanced the schema's `$id` to 0.2.0 and
kept the profile identifier `escapewheel-portable-v0.1`, "as it has through earlier candidate
changes to the profile's floors". Every packet records `profile_id`, and the reference validator
treats it as part of an amendment's identity, so keeping the identifier keeps every existing packet
and every amendment of one conforming.

### 2.5 An extension already chooses its order through its key

A table with no override is stored in its primary key's order, and an extension declares its own
tables' keys, so an extension already chooses any ordering of its key columns. What only an
override adds is a column outside the key, and declared `determined_by` a subset of it, placed ahead
of a key column, as `analysis.spike_events` places its time bucket. When R93 removed the `sort`
field, each of the eleven extension tables declaring one sorted by its own primary key. None of the
four extension registries in the repository needs an override.

## 3. Desired outcome and constraints

A writer, a validator and any tool built from the specification alone read each overriding order
from an incorporated artifact, and every copy an implementation keeps is generated from it or checked
against it. The rule that an override settles its key by adjacency is checked without a packet. The
resolution preserves:

- the order itself and every packet's bytes;
- the profile identifier `escapewheel-portable-v0.1`, so that no packet's `profile_id` or amendment
  identity changes;
- R93 §3.3's separation, under which the logical registry states no stored order;
- Part 00 §8's dependency direction, under which a registry represents resources without selecting a
  storage technology; and
- Part 03 §5.3's adjacency rule.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the prose as the only statement | every implementation and specification-side tool restates the order; the reference implementation's copy and R93's check stay unchecked |
| keep the prose as the owner and parse its table | one hand-written statement, and implementations generate or check their copies from it; but it inverts Part 03 §1's division, making a Markdown table the interface for an exact fact the descriptor would own everywhere else |
| return the order to the registry | reverses R93 §3.3 and states a physical property in every registry's shape, against Part 00 §8's dependency direction |
| the descriptor declares the overriding orders (preferred direction) | the one exact fact Part 03 §1's division misses joins the others; §5.4's table becomes a projection generated from it, as §2's mapping is; every consumer reads the order from the descriptor or a vendored copy |

Under the preferred direction the descriptor declares each resource whose stored order is not its
primary key's, and the columns of that order. Part 03 §1 adds the overriding orders to what the
descriptor owns. Part 03 §5.4 keeps what the prose owns: that a writer emits each order, why
`analysis.spike_events` has one, and the row-group advice. Part 03 §5.3 and Part 06 §4 cite §5.4
rather than restating the order's columns.

R93's check becomes a check of the candidate's consistency rather than a validator obligation, since
a validator has no override to refuse but the specification's own. Each override names a resource
the core registry declares, contains every key column, and places only key columns, or columns
declared `determined_by` a subset of the key, ahead of the last key column. A descriptor that
disagrees with the core registry makes the candidate internally inconsistent under Part 00 §2.3.

The check compares the descriptor with the core registry the same candidate incorporates, which is
the one a packet built under the candidate binds. A packet binding another core registry version, in
which the resource lacks a column an override names, cannot be stored in that order, and a validator
reports its order as not established.

Only the profile declares an override. An extension controls its tables' stored order through the
column order of its primary key (§2.5), and Part 09 states this. An extension needing a column
outside its key ahead of a key column, as a bucketed layout does, has no declaration in this
candidate. It needs a profile revision, or a later extension-side mechanism at the physical level,
such as a member of the adapter declaration Part 12 §7 incorporates. Nothing here forecloses that
mechanism, and no current extension needs it.

Where the declaration sits within the descriptor is left to the draft. A member of the `parquet`
interface confines it to the interface that stores rows, which is the only interface with a row
order. A member at the descriptor's root, keyed by resource, matches Part 03 §5.3, which states its
rule of a table rather than of an interface.

The cost is small but not nil:

- a descriptor carrying the declaration fails the current schema, so under the rule R137 followed
  the schema's `$id` advances from 0.2.0 and the profile identifier stays;
- the descriptor under `escapewheel-portable-v0.1` changes content once more, which the choice of
  final identifiers after the field test accounts for with the rest;
- the reader's vendored schema and descriptor regenerate, and its constant is replaced by a read of
  the descriptor;
- a generator writes §5.4's table; and
- the consistency check and its failure cases are added.

The benefit is that a second implementation's writer and validator read one JSON member instead of
a Markdown table, and that the one copy the reference implementation keeps can no longer drift.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 states no stored order. |
| logical prose and registry | Unchanged. The registry declares no order (R93 §3.3), and its `determined_by` declarations are what the consistency check reads. |
| physical profiles | Part 03 §1 names the overriding orders among the descriptor's facts. §5.4's table becomes a generated projection and §5.4 gains a stable anchor. §5.3 cites §5.4 instead of naming the override's columns. The schema declares the member and advances its `$id`; the descriptor declares the one override; the profile identifier is unchanged. |
| packet manifest and JSON Schemas | Unchanged. No manifest member names an order. |
| validation and import | A validator reads the order from the descriptor. A table whose bound registry lacks an override's column is reported as not in its required order. Part 06 §4 cites Part 03 §5.4 instead of describing the order. |
| extensions | Part 09 states that an extension controls its tables' order through its keys' column order and declares no override. No extension document changes. |
| reader, writer, validator, adapters | The reader reads the orders from its vendored descriptor, and its vendored copies regenerate. The writer is unchanged, since it takes the order from the reader. The validator reports a missing override column as an ordering finding. Adapters are unchanged. |
| existing packets | Unchanged. Every packet's order, bytes, `profile_id` and amendment identity are as before. |
| conformance fixtures and tests | The corpus builder reads the order from the descriptor instead of importing the reader. The consistency check gains cases for an override naming an undeclared resource, lacking a key column, and placing an undetermined column ahead of the last key column. A validator test covers a bound registry lacking an override's column. |
| revision process and tooling | Unchanged. |
| generated publications and developer documentation | Part 03 §5.4's table and the combined rendering regenerate. The reader's guide says where the order comes from. |

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
