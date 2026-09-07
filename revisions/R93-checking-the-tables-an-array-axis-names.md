# R93 — Checking the Tables an Array Axis Names

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | `02` §8.3 (what a discriminator is), R20 §2.3 (the labelled axis), R55 §2.3 (its two resolution shapes) |
| **Depends on** | R46 (the references the registry never declared), R55 (a discriminated reference), R88 (the reference count this starts from) |
| **Profile** | all |

Informative, except §2, which is normative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

A dense array has axes, and an axis needs coordinates: what position 0 stands for, what position 1
stands for. R20 §2 gives four ways to declare them, and two of the four point at something else in
the packet.

A **labelled axis** says the positions are the rows of another table:
`core.array_dimensions.coordinate_resource` holds that table's dotted resource ID, and
`coordinate_position_column` names the column of it that holds the 0-based position. An
**irregular axis** says the positions are the values of a 1-D array, named by
`coordinate_array_asset_id`.

Neither is checked, in different ways and for different reasons.

### 1.1 A column naming a table is declared as data

`coordinate_resource` carries R48 role `data` and no vocabulary, so nothing checks that its value
is a dotted resource ID, that the packet declares that resource, or that it is a table at all. It
could hold an empty string and validate clean.

That is the state R55 was written to end. R55 §2.1 added `discriminator` as a sixth role precisely
for a column a consumer resolves to a **table**, so that something finally checks the value; §2.4
generates the resolution check from the structure rather than leaving it hand-written per site.
Three columns carry the role today — `core.intervals.interval_kind`, and `scope_kind` on
`core.preferred_runs` and `core.processing_runs`. `coordinate_resource` and its `analysis` copy are
the only other string columns in the registry shaped like a resource, and R55's sweep did not reach
them.

The rows are real. Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes,
6,781 sorted units) and **`ecephys_786867`** (ten probes, 4,505):

| | `ecephys_776259` | `ecephys_786867` |
|---|---:|---:|
| `core.array_dimensions` rows | 30 | 23 |
| …declaring a `coordinate_resource` | 14 | 11 |
| …naming `core.array_channels` | 12 | 10 |
| …naming `core.unit_electrodes` | 2 | 1 |
| …whose `coordinate_position_column` is `channel_index` | 14 | 11 |
| rows with one of the pair set and the other not | 0 | 0 |

So **25 rows carry a resource ID that no rule looks at**, and every one of them is right.

### 1.2 One table declares its array column as a foreign key; the other does not

`core.array_dimensions.coordinate_array_asset_id` names an array, so it is an ordinary foreign key
and declares a reference to `core.array_assets`. `analysis.array_dimensions` carries the identically
named column and declares nothing, so the two tables disagree about one column.

That is R46's defect: Tier 1 generates an anti-join from a declared reference and from nothing else,
so the analysis column is a foreign key no rule can see. It is also the cheapest kind to fix, since
the column has never held a value — `coordinate_array_asset_id` is non-null in **0 of 53** rows
across both packets, and `analysis.array_dimensions` and `analysis.array_assets` are absent from
both.

## 2. Decision

### 2.1 `coordinate_resource` is a discriminator

`coordinate_resource` **MUST** carry R48 role `discriminator` on `core.array_dimensions` and on
`analysis.array_dimensions`, declaring `resolves: required` (R55 §2.2). A row that names a resource
the packet does not declare is a defect rather than a fact: the axis has no positions, so the row
is uninterpretable, which is the test R55 §2.2 gives for `required`.

It carries no paired value, so it declares no `discriminates` (R55 §2.3.2). The positions are the
named resource's **rows**, not one identifier in its key space.

The name stays. `registry/check.py` requires a discriminator to be named `_kind`, and this one is
declared an exception with its reason: `_kind` reads as a category, and every column carrying it
holds one — an interval's kind, a run's scope kind — where this holds the table whose rows are the
data. R48 §3 measured that a role says what a name cannot, and R55 added the role so the name would
not have to.

### 2.2 The pair is set together or not at all

A row declaring a `coordinate_resource` **MUST** declare a `coordinate_position_column`, and a row
declaring neither is a row using one of R20 §2's other three forms. A Tier 2 rule reports a row
with one and not the other, which is R49 §2.4's `scope_pair_complete` applied to a second pair and
returns **0 of 53 rows** today.

`coordinate_position_column` **MUST** name a column of the named resource whose R48 role is
`structural_index`. The value is a 0-based position (R3 §6), and a role is what says a column holds
one: both real values are `channel_index`, `int64` and `structural_index` in each of the two tables
that carry it.

### 2.3 A labelled axis resolves by rows, which is a third shape

R55 §2.3 states that two shapes exist — a shared key, and a paired value — and a labelled axis is
neither. The named resource's **rows are the positions**, located by the column §2.2 names, so
resolution is neither a key join nor a value-to-key join.

R55 §2.3.1's joinability rules therefore do not apply, and **MUST NOT** be read as applying.
`core.array_channels` happens to declare `(array_asset_id, axis_index)` → `core.array_dimensions`,
which ties its rows to the axis explicitly; `core.unit_electrodes` declares no such reference and
cannot, because it carries neither column — its rows are a waveform array's electrode axis, reached
through the unit that another axis of the same array identifies.

What a consumer may rely on is what §2.1 and §2.2 require: the resource is declared, and the column
named holds the position. How the rows of that resource are narrowed to one axis is the resource's
own business, and this part does not generalise it from two cases.

### 2.4 The analysis column declares its reference

`analysis.array_dimensions` **MUST** declare `coordinate_array_asset_id` →
`analysis.array_assets.array_asset_id`, matching what `core.array_dimensions` declares against
`core.array_assets`.

The target is the analysis table because its sibling `array_asset_id` already resolves there, and an
axis of an analysis array is labelled by an asset the analysis layer holds. Nothing yet contradicts
that: no packet carries either table, so the reference turns on a check that passes over zero rows,
which is R46 §4's result on its sixteen.

## 3. What this does not change

- **No column is added, renamed or struck.** Two columns change role and one reference is declared.
- **R20 §2's four forms stand.** A labelled axis is still one of them; this says what its two
  columns must satisfy, which R20 left to prose.
- **No packet is invalidated.** All 25 rows carrying a `coordinate_resource` name a resource their
  packet declares, and all 25 name `channel_index`, so every rule this adds passes on both packets
  as they stand.
- **The discriminator is not a reference.** R55 §2.6's rule holds: a discriminator **names** without
  depending, which is why `core.array_dimensions` may name a resource an extension supplies.

## 4. Consequence

Two columns gain a role and a `resolves`, so Tier 1's discriminator checks go from 6 to **10** (two
per discriminator, R55 §2.4), and references go from 90 to **91**. One Tier 2 rule is added for
§2.2's pair, on both tables. No table, no column, and no packet's rows change.

`registry/check.py` gains two entries in `NAMING_EXCEPTIONS`, each with §2.1's reason, and its
existing check that every declared exception still breaks a convention is what keeps them from going
stale.

Neither packet is rebuilt. Both already satisfy every rule this adds.

## 5. Open

- **Whether the position column should be checked against the registry.** §2.2 requires
  `coordinate_position_column` to name a `structural_index` column of the named resource, and
  nothing generates that check: it compares a value in a row against a role in the registry, which
  no Tier 2 SQL can see and no structural check can reach without the packet. R55 §2.4's resolution
  check is the model, and building it is more than declaring the rule.
- **Whether a labelled axis should say how its rows are narrowed.** §2.3 declines to generalise from
  two cases: `core.array_channels` ties its rows to one axis by a declared reference and
  `core.unit_electrodes` cannot. A third case would say whether the tie belongs in the registry or
  stays the named resource's own business.
- **Whether `analysis.array_dimensions` should exist at all.** It has never been written, and R43
  withdrew four of `06`'s five materialized resources. If the analysis layer settles on arrays it
  does not own, the table and §2.4's reference both go.
