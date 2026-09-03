# R55 — A Discriminated Reference

| | |
|---|---|
| **Status** | **Proposed** 2026-09-03 |
| **Amends** | R48 §2.1 (the closed role vocabulary), R49 §2.2 and §2.5 (`scope_kind` and what checks it), R17 §2 (the reason core may not reference an extension) |
| **Depends on** | R17 (extension registries), R48 (column roles), R49 (a scope names what kind of thing it is), R53 (an identifier is an integer) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R49 §2.2 added `scope_kind`, holding a dotted resource ID so a polymorphic scope resolves
generically: read the kind, take that resource's primary key from the registry, resolve. R54 §2.1
adds `interval_kind` on the same principle. The pattern has two instances and no name, and each
site decides its own semantics silently.

**They decide differently, and both are right.** R49's column description says an unresolvable
kind *"means the scope is not a packet resource"* — a run may be about a camera or a rig the
packet does not hold, so it is a **fact**. R54 §2.4a needs the opposite: a kind that resolves to
nothing leaves the interval uninterpretable, which is precisely NWB's failure mode, so it is a
**defect**. Nothing records that this is a choice, so the next discriminator will make it by
accident.

### 1.1 The role vocabulary cannot express it

R48 §2.1 closes `role` to `data`, `identifier`, `coordinate`, `structural_index` and
`sequence_position`, *"because a consumer derives behaviour from it, so an unrecognised value
would be unsafe."* A discriminator is exactly a column a consumer derives behaviour from — it
resolves it to a table — and it is currently declared `data`, which says a consumer may read it
and nothing more.

So nothing checks that a discriminator holds a resource ID at all. `scope_kind` could hold
`"probe"`, `"Neuropix-PXI-100.46110"` or an empty string and no rule would see it.

### 1.2 The check that exists does not cover extensions

R49 §2.5's `core.processing_runs.scope_resolves` and `core.preferred_runs.scope_resolves` check
that a scope's **value** exists within its declared kind, through a `UNION ALL` generated over the
known kinds. That union is built from the **core** registry, so a `scope_kind` of
`"dynamic_foraging.trials"` — which R49 §2.4 explicitly permits, *"open, so an R17 extension can
scope to its own tables"* — matches no branch and passes unchecked.

The mechanism R49 designed for extensions is the one case its check does not reach.

## 2. Decision

### 2.1 `discriminator` is a role

R48 §2.1's closed set gains a sixth value. A column with `role: discriminator` holds a **dotted
resource ID** naming a table in the packet's registry or in one of its extensions.

A discriminator **MUST** be `string`, and every non-null value **MUST** be a well-formed resource
ID — a namespace and a table name, each lowercase snake_case, separated by a dot. That is
checkable without knowing which resources exist, and nothing checks it today.

### 2.2 A discriminator declares whether it must resolve

Required wherever `role` is `discriminator`, closed, and with no default — the same shape R53
§2.3 gives `identity`, and for R48 §2.2's reason: a default makes a forgotten decision look
deliberate.

- **`resolves: "required"`** — the value **MUST** name a resource the packet declares. Use where
  the discriminator is what gives the row meaning, so a kind resolving to nothing leaves the row
  uninterpretable. `core.intervals.interval_kind` (R54 §2.1).
- **`resolves: "optional"`** — a value naming no declared resource is a **fact**, not a finding:
  it says the thing is not a packet resource. `core.processing_runs.scope_kind` (R49 §2.2), where
  a run may be about a rig or a camera the packet does not hold.

### 2.3 Resolution is mechanical, and that is the point

Given a discriminator's value, a consumer resolves it without knowing the target: read the kind,
take that resource's primary key from the registry, join. Two shapes use it:

- **A shared key.** The discriminated row and the named table share a primary key, so the join is
  on that key. This is R54's `core.intervals` and its per-kind detail tables — the
  class-table-inheritance mapping.
- **A paired value.** A separate column holds an identifier in the named table's key space, and
  the join is value-to-key. This is R49's `scope` with `scope_kind`.

A reader **SHOULD** offer the resolution, because a discriminator nothing reads is a free-form
name with extra steps — which is the observed fate of NWB's `TimeIntervals`, where a table *is*
its name and so two labs' optotagging tables are named differently and nothing generic finds
either.

### 2.4 Tier 1 generates the resolution check

Where `resolves` is `required`, a check is generated from the structure — an anti-join against the
resources the manifest declares — as R2 §7's other Tier 1 checks are. It is not hand-written per
site, because R46 exists because sixteen hand-written references were never written at all.

Where `resolves` is `optional`, no such check is generated, and a value naming no declared
resource is reported as `info` rather than passed over in silence.

### 2.5 R49 §2.5's check reaches extension kinds

`scope_resolves` builds its `UNION ALL` over the core registry's tables. It **MUST** be generated
over every resource the packet declares, extensions included, so the case R49 §2.4 designed the
mechanism for is the case it checks. A kind naming a resource the packet does not declare is
`resolves: "optional"`'s `info`, not a silent pass.

### 2.6 Core may name an extension, and may not reference one

R17 §2 forbids core to reference an extension, giving as its reason that *"core resources must
stay interpretable when no extension is present."* That reason is the weakest available and does
not survive examination: a packet **embeds** the extension registries it declares (`09` §6), so
the schema travels with the data and is essentially never absent.

Two reasons do survive, and replace it.

**Separable verdicts.** R17 §4 requires a core validator to check that declared extension files
exist and **MUST NOT** require their schemas, and requires a finding against an extension not to
be a finding against core conformance. A core foreign key into an extension inverts that: the
Tier 1 anti-join cannot run without the extension, so core's verdict becomes *incomplete* rather
than clean, and a consumer holding only core could no longer say whether the packet is
core-conformant.

**Independent versioning.** R17 §5 lets an extension carry its own `registry_version` and even
track a core version it predates — *"nothing requires them to move together."* A core foreign key
couples core's referential integrity to a schema free to move underneath it.

A **discriminator** has neither problem, which is why it is the mechanism core is allowed: it
names without depending. Core stays checkable alone, an absent target is a reportable fact rather
than an unrunnable check, and no integrity constraint couples the versions.

Note which direction the useful case wants. In the class-table mapping the reference runs
**extension → core** — a detail table references the row it specialises — and that is already
permitted. Core would only want to point the other way where a core row's meaning is *completed*
by extension data, which is exactly the case where core is not standalone. The rule and the use
case coincide.

## 3. What this does not do

- **No new resolution semantics.** R49 §2.2's rule is what §2.3 states generally; this names it
  and makes the per-site policy declarable, rather than changing how anything resolves.
- **No change to R48's other roles.** A discriminator is not an identifier: it names a *table*,
  not a row, so R48 §2.3's "a reference relates columns of the same role" is untouched.
- **No requirement that a discriminator have a paired value column.** §2.3's two shapes are both
  legitimate, and which one a site uses is visible from whether it declares a paired column.

## 4. Open

- **`core.processing_runs.scope`'s own type.** It holds an identifier and is declared `string`,
  which was consistent while every identifier was a string. R53 §2.1 made them `int32`, so a
  scope naming a probe now holds `"3"` as text. Either `scope` becomes `int32` — which R53 makes
  uniform and which nothing prevents — or the inconsistency is deliberate and should say why.
  This revision does not settle it, because it is R53's consequence rather than this one's.
- **Whether a discriminator should be `int32` too.** It holds a resource ID, and resource IDs are
  dotted strings everywhere else in the format, including in the manifest. Keeping it a string is
  consistent; the cost is that a discriminator in a fact table repeats a long string per row,
  where R53 measured that an identity column's cost comes from exactly that.
