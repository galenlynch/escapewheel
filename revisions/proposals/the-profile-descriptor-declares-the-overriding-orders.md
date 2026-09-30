# The profile descriptor declares the overriding orders

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-30 |
| **Based on** | `37316eb51287334b5b482dc7ffef542a656b6a9b` |
| **Decision domain** | specification |
| **Affects** | Part 03 §1's statement of what the descriptor owns; Part 03 §5.4's table of overriding orders; the incorporated physical-profile schema and the `escapewheel-portable-v0.1` descriptor |

## 1. Problem

Part 03 §5.3 stores every table in its primary key's order unless §5.4 gives it another, and §5.4
gives one: `analysis.spike_events` is stored by `session_id, clock_id, time_bucket_tick, unit_id,
t_tick`. A writer emits that order and a validator establishes it, so both need it in machine form.
The specification states it only as a row of a Markdown table.

Every implementation therefore restates it. The reference implementation keeps its one copy as a
constant in the reader package, from which the writer, the validator and the conformance corpus's
builder all take it, and nothing compares that constant with Part 03 §5.4. A tool that must build
or check packets from the specification alone, such as a corpus builder that imports no
implementation, has to restate the order a further time.

## 2. Evidence

Observed in the tracked files at the baseline commit.

### 2.1 The descriptor owns the profile's other exact facts and not this one

Part 03 §1 incorporates `registry/physical_profile.schema.json` and
`registry/physical_profiles/escapewheel-portable-v0.1.json`, and gives the descriptor "the profile's
exact identifiers, kind-to-interface mapping, interface forms, ownership compatibility, variants,
reader floors, floor roles, and anchors". The descriptor's members are `$schema`, `id`,
`logical_standard`, `kind_interfaces` and `interfaces`; none states an order. Part 03 §2's mapping
table is generated from the descriptor, and §5.4's table is written by hand.

### 2.2 One constant in the reader serves four consumers

`escapewheel-reader/src/escapewheel_reader/ordering.py` declares `OVERRIDES`, mapping
`analysis.spike_events` to the five columns, and `stored_order`, which returns an override or else
the primary key. Its docstring places the copy in the reader because the writer and validator both
depend on the reader and neither depends on the other. It is read by:

- the writer, to order each table before writing (`arrow.py`);
- the validator, to scan each table's order and to decide whether adjacency settles uniqueness
  (`validator.py`, `generate.py`); and
- the corpus builder, to order each table of its 120 packets (`fixtures/build.py`), the builder's
  only import from an implementation.

No check compares `OVERRIDES` with Part 03 §5.4. Validator tests patch the constant to exercise the
adjacency argument, and none reads the part.

### 2.3 The order left the registry for the profile and never reached the descriptor

R93 §3.3 removed the per-table `sort` field from the registry because stored order is a physical
property, leaving Part 03 §5.4's table as "the only statement an override has". R129 made the
descriptor the profile's machine-readable owner and stated that it did "not change … stored-order
rules". Neither revision decided that the order should stay out of machine form; R93 moved it to the
profile before the profile had a descriptor, and R129 scoped it out.

### 2.4 A descriptor change need not change the profile identifier

R137 changed the descriptor's Zarr floor incompatibly. It advanced the schema's `$id` to 0.2.0 and
kept the profile identifier `escapewheel-portable-v0.1`, "as it has through earlier candidate
changes to the profile's floors". Every packet records `profile_id`, and the validator treats it as
part of an amendment's identity, so keeping the identifier keeps every existing packet and every
amendment of one conforming.

## 3. Desired outcome and constraints

A writer, a validator and any tool built from the specification alone read the overriding orders
from an incorporated artifact, and every copy an implementation keeps is generated from it or
checked against it. The resolution preserves:

- the order itself and every packet's bytes;
- the profile identifier `escapewheel-portable-v0.1`, so that no packet's `profile_id` or amendment
  identity changes;
- R93 §3.3's separation: the logical registry states no stored order;
- Part 03 §5.3's rule that an override settles its primary key by adjacency; and
- the rule that an extension table is stored in its primary key's order, since the profile states no
  order for a resource outside the core registry.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the prose as the only statement | every implementation and specification-side tool restates the order; the reference implementation's copy stays unchecked, and a corpus builder that imports no implementation needs a third copy and a check that it agrees |
| return the order to the registry | reverses R93 §3.3, putting a physical property back into the logical standard and into every registry's shape |
| the descriptor declares the overriding orders (preferred direction) | one machine-readable owner, in the artifact that already owns the profile's exact facts; Part 03 §5.4's table becomes a projection generated from it, as §2's mapping is; every consumer reads the order from the descriptor or a vendored copy of it |

Under the preferred direction the descriptor declares, for the table interface, each resource whose
stored order is not its primary key's and the columns of that order. Part 03 §1 adds the overriding
orders to what the descriptor owns, and §5.4 keeps what the prose owns: that a writer emits the order,
why the order exists, and the row-group advice. Part 03 §5.3's adjacency rule then becomes checkable
without a packet: every override names a resource the core registry declares, contains every key
column, and puts only key columns or columns declared `determined_by` a subset of the key ahead of
the last key column. A candidate whose descriptor and core registry disagree is internally
inconsistent under Part 00 §2.3.

The declaration sits in the `parquet` interface rather than at the descriptor's root. Stored order
is how that interface stores a table, and Part 03 §5.2 leaves the ordering of a future partitioned
interface to that interface.

The descriptor's shape gains a member, so a descriptor carrying it fails the current schema; under
the rule R137 followed, the schema's `$id` advances and the profile identifier stays. The reader's
vendored copies regenerate, and the reader's constant is replaced by a read of the descriptor.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 states no stored order. |
| logical prose and registry | Unchanged. The registry declares no order (R93 §3.3), and its `determined_by` declarations are what the new static check reads. |
| physical profiles | Part 03 §1 names the overriding orders among the descriptor's facts. Part 03 §5.4's table becomes a generated projection, and §5.4 gains a stable anchor for the descriptor to cite. The schema declares the member and advances its `$id`. The descriptor declares the one override. The profile identifier is unchanged. |
| packet manifest and JSON Schemas | Unchanged. No manifest member names an order. |
| validation and import | Unchanged in behavior. The validator reads the same order from the descriptor, and a static check of the candidate verifies each override against the core registry. |
| extensions | Unchanged. An extension table is stored in its primary key's order, as now. |
| reader, writer, validator, adapters | The reader reads the orders from its vendored descriptor and its schema copy regenerates. The writer and validator are unchanged, since they take the order from the reader. Adapters are unchanged. |
| existing packets | Unchanged. Every packet's order, bytes, `profile_id` and amendment identity are as before. |
| conformance fixtures and tests | The corpus builder reads the order from the descriptor instead of importing the reader. The descriptor check gains cases for an override naming an undeclared resource, lacking a key column, and placing an undetermined column ahead of the key. |
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
