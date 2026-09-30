# The profile descriptor declares the overriding orders

| | |
|---|---|
| **Status** | **Accepted** 2026-09-30 |
| **Based on** | `b548bd01a38ca46478b93be5891db87b484fb8d3` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §§1, 5.3, 5.4 and 6.4; Part 06 §4; Part 09 §5.1; the physical-profile schema; the `escapewheel-portable-v0.1` descriptor |
| **Depends on** | R93 §3.3 (the separation of stored order from the registry, which this completes); R137 §3.3 (the descriptor schema identifier this advances from) |
| **Profile** | `escapewheel-portable-v0.1` |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 03 §1 divides the portable profile between two owners. The incorporated descriptor owns the
profile's exact facts, and the prose owns their meaning and each actor's obligations. The one
overriding stored order escapes that division. Part 03 §5.3 stores every table in its primary key's
order unless Part 03 §5.4 gives it another, and that section gives `analysis.spike_events` the order
`session_id, clock_id, time_bucket_tick, unit_id, t_tick` as a row of a hand-written table. No
machine-readable artifact states it, and two further passages restate it: Part 03 §5.3 names the
table and the columns that let its order satisfy the section, and Part 06 §4, which is normative,
says the table is stored "by unit within each time bucket".

This revision puts the overriding orders in the descriptor, as a member of the interface that stores
tables, and makes Part 03 §5.4's table a projection generated from it. It defines a table's primary
key's order as the key's columns in the order its registry lists them, and states that only the
descriptor declares an override. That leaves an extension to choose its tables' order through its
keys. It restores the check R93 §3.3 required of an override without a packet, as a consistency
condition between the descriptor and the core registry. It says what a validator reports where a
packet's bound registry lacks a column an override names. The descriptor schema advances to 0.3.0,
and the profile identifier is unchanged.

The change is structural because it revises rules inside Part 03 §§5.3 and 5.4, moves the schema
identifier out of Part 03 §6.4, and removes the restatements in Part 03 §5.3 and Part 06 §4.
Appended sections would leave Part 03 §5.4's hand-written table beside a generated one, Part 03 §5.3
and Part 06 §4 restating what the descriptor owns, and Part 03 §6.4, a section about codecs, stating
the identifier of a schema that changed for another reason.

### 1.1 Structural crosswalk

The `Based on` commit is a metadata-only bootstrap adding `ew-overriding-orders` before Part 03
§5.4's heading, and changes nothing else. `e512bc6` regenerated the heading index and the combined
rendering. Every other affected section already carried an anchor. No section moves, splits, merges
or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03 §1, what the descriptor owns | extend in place | same section | the descriptor owns the overriding orders; the schema identifier is stated here | §3.1; §3.5 |
| Part 03 §5.3, the default order | revise in place | same section | a primary key's order is its columns in the order the registry lists them | §3.2 |
| Part 03 §5.3, the paragraph naming `analysis.spike_events` | revise in place | same section | cites Part 03 §5.4 and its consistency condition instead of naming the table's columns; the rationale for `core.events` and `core.spike_events` stays | none |
| Part 03 §5.4, the table and the writer's obligation | replace in place | same section | the table is generated from the descriptor; a writer stores each named table in its order; only the descriptor declares one; an override is consistent with the core registry; a table lacking an override's column departs from its order | §3.2; §3.3; §3.4 |
| Part 03 §6.4, the schema's identifier | move | Part 03 §1 | the identifier is 0.3.0; Part 03 §6.4 keeps the v3 floor's definitions | §3.5 |
| Part 06 §4, the order `analysis.spike_events` is stored in | revise in place | same section | cites Part 03 §5.4 without describing the order | none |
| Part 09 §5.1, what an extension supplies | extend in place | same section | cites Part 03 §5.3 for the order an extension's tables are stored in | none |

## 2. Background

### 2.1 The descriptor states no order

The descriptor's members are `$schema`, `id`, `logical_standard`, `kind_interfaces` and
`interfaces`, and the schema closes every object, so no order can be stated in it. Part 03 §2's
mapping table is generated from the descriptor, and Part 03 §5.4's table is written by hand.

The reference implementation keeps its one copy of the order as a constant in the reader package,
which the writer, the validator and the conformance corpus's builder all import. No check compares
it with Part 03 §5.4. R93 §3.3 removed the registry's per-table `sort` field because stored order is
physical, and required that a validator refuse an override that does not settle its key by
adjacency, "a check made with no packet in hand". No current part states that check, and the
reference validator has none: where an override does not settle its key, it settles uniqueness by
aggregate while scanning each packet. R129 made the descriptor the profile's machine-readable owner
and did "not change … stored-order rules", so neither revision decided that the order should stay
out of machine form.

### 2.2 Alternatives

Keeping the prose as the only statement leaves every implementation and specification-side tool to
restate the order, unchecked. Keeping the prose as owner and parsing its table would check those
copies, but would make a Markdown table the interface for an exact fact the descriptor owns
everywhere else. Returning the order to the registry reverses R93 §3.3 and states a physical
property in every registry's shape, against Part 00 §8's dependency direction.

An extension-side declaration was considered and deferred. An extension already chooses any order
of its key columns, since its tables are stored in their primary key's order. What only an override
adds is a column outside the key, determined by it, placed ahead of a key column, as
`analysis.spike_events` places its time bucket. When R93 removed the `sort` field, each of the
eleven extension tables declaring one sorted by its own primary key, and none of the four extension
registries in the repository needs an override. A declaration in an extension's registry would
break Part 00 §8's rule that a registry selects no storage technology. A member of the adapter
declaration of Part 12 §7 would stay at the physical level but make the order a fact of each
packet. Either can follow a need; this revision forecloses neither.

### 2.3 Placement within the descriptor

The declaration is a member of the table interface rather than of the descriptor's root. Only an
interface that stores rows has a row order. The interface's `anchors` already name the sections that
own its facts, and Part 03 §5.4 joins them, as the Zarr interface's anchors name Part 03 §6.4's
floor.

### 2.4 Feasibility

The consistency condition of §3.3 was evaluated against the core registry at the baseline commit.
`analysis.spike_events` has the key `session_id, unit_id, t_tick`, declares `clock_id` determined
by `session_id` and `time_bucket_tick` determined by `t_tick`, and satisfies it. The condition
refuses:

- an order for a resource the registry does not declare;
- an order for `analysis.spike_events` without `t_tick`; and
- the order `session_id, amplitude, unit_id, t_tick` for `core.spike_events`, since `amplitude`
  is not determined by the key.

## 3. Decision

The subsections state the declaration, the order each table is stored in, the consistency of an
override with the core registry, a table that cannot take its order, and the schema identifier.

### 3.1 The descriptor declares the overriding orders

The physical-profile schema declares, as a member of `$defs.interface.properties`:

```json
"overriding_orders": {
  "type": "object",
  "minProperties": 1,
  "propertyNames": {"$ref": "#/$defs/resource_id"},
  "additionalProperties": {
    "type": "array",
    "minItems": 1,
    "uniqueItems": true,
    "items": {"$ref": "#/$defs/name"}
  }
}
```

and, as a member of `$defs`:

```json
"resource_id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$"}
```

`overriding_orders` is not required. Each key names a table and its value lists, in order, the
columns that table is stored by. Only the interface a descriptor's `kind_interfaces` maps `table`
to MAY declare it, and the generic cross-member checker Part 03 §1 names MUST refuse it on any other
interface.

The portable descriptor's `parquet` interface declares:

```json
"overriding_orders": {
  "analysis.spike_events": ["session_id", "clock_id", "time_bucket_tick", "unit_id", "t_tick"]
}
```

and its `anchors` are `ew-table-encoding`, `ew-overriding-orders` and `ew-parquet-reader-floor`, in
that order. The descriptor owns the overriding orders along with the profile's other exact facts,
and Part 03 §5.4's table is a generated projection of them.

### 3.2 A table is stored in its primary key's order unless the descriptor overrides it

A table's **primary key's order** lists its primary key's columns in the order its registry
declares them. A writer MUST store each table that the descriptor's `overriding_orders` names in
the order named, and every other table in its primary key's order.

Only a physical-profile descriptor declares an overriding order, and a registry document declares
none. A table of an extension is therefore stored in its primary key's order, and an extension
chooses that order by the order in which it declares its key's columns.

### 3.3 An override is consistent with the core registry

Each overriding order and the core registry the specification candidate incorporates MUST satisfy
all of the following:

- the order's key names a table that the core registry declares;
- every column the order names is a column of that table;
- the order names every column of the table's primary key;
- every column before the last primary-key column in the order is a primary-key column or is
  declared `determined_by` a subset of the primary key (Part 02 §8.5); and
- the order differs from the table's primary key's order.

These make each override satisfy Part 03 §5.3's adjacency rule without a packet. A descriptor and
core registry that fail them make the candidate internally inconsistent (Part 00 §2.3).

### 3.4 A table lacking an override's column departs from its order

Where a packet's bound core registry declares a table that `overriding_orders` names, but not every
column its order names, the table cannot be stored in its required order. A validator MUST report
that table's order as a departure under Part 03 §5.3.

### 3.5 The schema identifier advances

The physical-profile schema's `$id`, and the `$schema` value it requires of a descriptor, are
`https://escapewheel.org/schemas/physical-profile/0.3.0`, and the portable descriptor's `$schema`
names it. Part 03 §1 states the identifier. The profile identifier remains
`escapewheel-portable-v0.1`.

## 5. Consequence

Every existing packet conforms unchanged. No table's order, no packet's bytes, and no manifest's
`profile_id` changes, so no amendment's identity changes either. A descriptor naming schema 0.2.0
fails the checker's `$schema` comparison, as R137 §3.3 made a 0.1.0 descriptor fail, so every
distributed copy regenerates with the schema. Only a packet binding a core registry whose
`analysis.spike_events` lacks one of the five columns draws §3.4's report, and no packet built
under a candidate since R93 binds one.

R93 §3.3's ledger note changes: the descriptor holds the machine-readable order, and its check
without a packet is §3.3's consistency condition. R30 §3.2 and R81 §2.4, placed at Part 03 §5.4,
gain notes that the descriptor declares the order Part 03 §5.4 projects. R137 §3.3 gains a note that
§3.5 supersedes its identifier, which moves to Part 03 §1.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 states no stored order. | None required. |
| logical prose and registry | Unchanged. The registry declares no order, and §3.3 reads its `determined_by` declarations. | None required. |
| physical profiles | Part 03 §1 takes §§3.1 and 3.5; Part 03 §5.3 takes §3.2's definition and cites Part 03 §5.4 in place of the override's columns; Part 03 §5.4 takes §§3.2–3.4 and its table becomes generated; Part 03 §6.4 loses the identifier. `registry/physical_profile.schema.json` declares `overriding_orders` and `resource_id` at 0.3.0, and the portable descriptor declares the override and the anchor. `registry/build.py` renders Part 03 §5.4's table. | `registry/check.py` over the descriptor and §3.3; `evidence/R<N>.json` names the anchors and the schema and descriptor pointers. |
| packet manifest and JSON Schemas | Unchanged. No manifest member names an order. | None required. |
| validation and import | Part 06 §4 cites Part 03 §5.4 without describing the order. §3.4 extends the departure Part 03 §5.3 already makes an error. | `evidence/R<N>.json` names the anchor. |
| extensions | Part 09 §5.1 cites Part 03 §5.3. No extension document changes: none declares an order, and each is stored in its key's order already. | None required. |
| reader, writer, validator, adapters | The reader takes the orders from its vendored descriptor, whose checker applies §3.1's interface rule, and its vendored schema and descriptor regenerate. The writer and validator take the order from the reader, as now. The validator reports §3.4's departure. Adapters are unchanged: no adapter orders a table. | The reader and validator suites; the writer suite unchanged. |
| conformance fixtures and tests | The corpus builder reads the order from the descriptor instead of importing the reader. §6's cases. | `fixtures/corpus.py`; the package suites; `registry/check.py`. |
| revision process and tooling | The ordinary ledger and evidence records, and the notes on R93 §3.3, R30 §3.2, R81 §2.4 and R137 §3.3. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | Part 03 §5.4's table, the combined specification and the heading index regenerate. The reader's guide says where the orders come from, and `registry/README.md` lists the descriptor's new member. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 03 §§1 and 5.4 and §3.5 at Part 03 §1. §§3.2, 3.3 and 3.4 are `applied`
at Part 03 §5.4, and §3.2 also at Part 03 §5.3. Each is placed by canonical anchor. The descriptor and
schema are evidence owners of §§3.1 and 3.5.

These cases distinguish the new rules from the current ones:

- the portable descriptor, with `overriding_orders`, passes schema 0.3.0 and the checker, where the
  current schema refuses the member;
- a descriptor naming schema 0.2.0 fails the checker's `$schema` comparison;
- `overriding_orders` on the `zarr` interface is refused by the checker;
- the consistency check refuses an override for an undeclared resource, one naming an undeclared
  column, one lacking a primary-key column, one placing an undetermined column before the last
  key column, and one equal to its table's primary key's order, and accepts the portable
  descriptor's;
- a packet whose bound core registry declares `analysis.spike_events` without `time_bucket_tick`
  draws a departure from its required order; and
- Part 03 §5.4's generated table equals the hand-written table it replaces.

The positive cases are every corpus packet and a session packet's `analysis.spike_events`, stored
in the order the descriptor declares and validated with no ordering finding. The corpus builder,
reading the order from the descriptor, writes every table with the digest it writes today.
