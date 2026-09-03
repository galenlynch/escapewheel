# R55 — A Discriminated Reference

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
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

### 2.3.1 The named resource must be joinable, and must say how

Resolution is only mechanical if the two keys correspond, and nothing says they must.

**For a shared key**, a resource a discriminator may name **MUST declare a reference to the
discriminated table**. The reference already carries the column mapping — `columns` to
`resource_columns` — so the join is explicit rather than inferred from names matching, and R46's
generated anti-join enforces the integrity as a side effect. `dynamic_foraging.trials` already
declares one; the rule is that it is not optional.

**And it must cover the discriminated table's whole key.** R54 §2.2 puts the kind *in* the key —
`(session_id, interval_kind, interval_id)` — so that each kind may carry its source's own
numbering, and trial 0 and block 0 can both exist. A reference on `(session_id, interval_id)`
alone therefore targets a set that is not unique: it identifies a row of *some* kind, which is not
a foreign key at all, and the generated anti-join would pass while resolving to several rows.

So a detail table carries the discriminator as a constant column and references all three. That
restates in every row what the table's own identity implies, which looks wasteful and is not:
`core.spike_events` already carries `sorting_run_id` and `curation_id` on every one of
286,896,563 rows for the same reason, and R53 §1 measured the pair at **0.06 bit/row**, because a
column holding one value run-length encodes to nothing. The cost is a rounding error and what it
buys is a reference that identifies a row.

This also fixes the direction. The reference runs extension → core, which R17 §2 permits and
§2.6 explains, so the discriminator names downward while the integrity constraint points upward.

**For a paired value**, the named resource's primary key **MUST** be a single column, because the
paired column holds one value. R49 never said so, and the constraint is real: `scope_kind` may
name `core.units`, whose key is `(session_id, unit_id, sorting_run_id, curation_id)`, and a
`scope` of one value cannot hold it. R49 §2.5's generated `UNION ALL` takes one column per kind
and so quietly assumes this; the assumption becomes a rule that `registry/check.py` enforces.

Both are structural: they are decidable from the registry with no packet in hand, which is where
this format puts a check it can make without data.

### 2.3.2 A paired-value discriminator names its paired column

§3 says which shape a site uses is *"visible from whether it declares a paired column"*, and
nothing above says how it declares one. Implementation needs it mechanically — the generated
resolution differs between the two shapes — so a discriminator carries `discriminates`, naming the
column that holds the value. Absent means the shared-key shape.

### 2.3.3 What a paired value matches

A paired value **MUST** be `string`, and it matches the named resource's key **or** that key's
`*_name`, decided by R53 §2.3's `identity`:

- the key is **`carried`** — the source's own number, stable across builds, so a value written
  before the build can hold it and the join is on the key;
- the key is **`assigned`** — a number this format chose at build time, so a value written before
  the build *cannot* hold it, and the join is on the `*_name` R53 §2.3.1 requires the owner to
  carry for exactly this purpose.

That is derivable from the registry, so resolution stays mechanical and no writer has to renumber
anything. It is also why the column is a string: one discriminator resolves against several kinds,
mixing an assigned key's name with a carried key's number, so the union it joins mixes types by
construction.

A single-column key is necessary and not sufficient. An assigned identifier a table does not
**own** — it is exported through a reference, so the name lives on the owner — leaves nothing a
paired value could match, and the resource is simply not namable. Measured on the current
registry: **14 of 35 core tables** have a single-column key and all 14 resolve by name;
`vr_foraging.sessions` has one and is not namable, because its `session_id` belongs to
`core.sessions`.

`core.processing_runs.scope_kind` declares `discriminates: "scope"`. Inferring it from the name
instead would be the guess R48 §3 measured as unsafe, and `registry/check.py` can only check a
declaration: that the named column exists in the same table, and that `resolves` and
`discriminates` appear on a discriminator and nowhere else.

Measured on the current registry: **14 of 35 tables have a single-column primary key**, so a
paired-value discriminator can name those and not the other 21 — including `core.units`,
`core.spike_events` and `core.array_channels`. That is a real limit on `scope`, and it is one
`registry/check.py` can report rather than leave to be discovered by a rule that quietly matches
no branch.

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

- ~~**`core.processing_runs.scope`'s own type.**~~ **Settled 2026-09-03 in §2.3.3.** It stays
  `string`, and what it holds is the name rather than the number.

  Implementing §2.4 sharpened the question from *what type* to **who assigns the value**.
  `session_id` and `probe_id` are `assigned` (R53 §2.3), so a writer chooses their values at build
  time; `nwb_lake_writer.arrow.number` renumbers a foreign key through its target's map, and does
  so for *declared references* only. A discriminated reference is by construction not a declared
  reference — that is the whole mechanism — so nothing renumbers `scope`, and a value written
  before the build can never equal a number chosen during it. Measured: the corpus's
  `undeclared_currency` carries `scope = "probe0"` against a `probe_id` that is now an integer,
  and the generated check found it.

  Making the writer number it was the alternative, and it fails a test this format keeps passing:
  a hand-authored packet could no longer write a scope at all, because the author cannot know the
  assignment. Matching the `*_name` instead needs no writer change, keeps a scope readable in the
  file it is stored in, and has no coverage gap — all 14 namable core resources carry one, which
  is what R53 §2.3.1 put them there for. The cost is a string join rather than an integer one,
  which is R53 §1's measurement pointing the other way; it does not bite, because a run table is
  dozens of rows where that was measured on 286,896,563.
- **Whether one extension declaring several kinds needs anything further.** It does not:
  `interval_kind` names a *resource*, and one extension has many, so `dynamic_foraging.trials`
  and `dynamic_foraging.blocks` are two kinds from one document. Each carries its own constant
  discriminator and references the full key; a trial naming its block is then an ordinary
  extension-internal reference between two detail tables. Nothing in §2 treats the one-extension
  case specially, which is the point, but no packet yet carries it.
- **Whether a discriminator should be `int32` too.** It holds a resource ID, and resource IDs are
  dotted strings everywhere else in the format, including in the manifest. Keeping it a string is
  consistent; the cost is that a discriminator in a fact table repeats a long string per row,
  where R53 measured that an identity column's cost comes from exactly that.
