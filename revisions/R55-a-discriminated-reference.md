# R55 — A Discriminated Reference

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | R48 §2.1 (the closed role vocabulary), R49 §2.2 and §2.5 (`scope_kind` and what checks it), R17 §2 (the reason core may not reference an extension) |
| **Depends on** | R17 (extension registries), R48 (column roles), R49 (a scope names what kind of thing it is), R53 (an identifier is an integer) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R49 §2.2 added `scope_kind`, holding a dotted resource ID so a polymorphic scope resolves
generically: read the kind, take that resource's primary key from the registry, resolve. R54 §2.1
adds `interval_kind` on the same principle. The pattern now has two instances, no name, and no
record that each site chose its own semantics.

They chose differently, and both were right. R49's column description says an unresolvable kind
*"means the scope is not a packet resource"*: a run may be about a camera or a rig the packet does
not hold, so the value is a fact. R54 §2.4a needs the opposite, since a kind resolving to nothing
leaves the interval uninterpretable, which is NWB's failure mode — so there the value is a defect.
With the choice unrecorded, the next discriminator will make it by accident.

### 1.1 The role vocabulary cannot express it

R48 §2.1 closes `role` to `data`, `identifier`, `coordinate`, `structural_index` and
`sequence_position`, *"because a consumer derives behaviour from it, so an unrecognised value
would be unsafe."* A consumer derives behaviour from a discriminator by resolving it to a table,
and the vocabulary has no value for that, so a discriminator is declared `data` — which promises
only that it may be read.

Nothing therefore checks that a discriminator holds a resource ID at all. `scope_kind` could hold
`"probe"`, `"Neuropix-PXI-100.46110"` or an empty string, and no rule would see it.

### 1.2 The check that exists does not cover extensions

R49 §2.5's `core.processing_runs.scope_resolves` and `core.preferred_runs.scope_resolves` check a
scope's value against its declared kind, through a `UNION ALL` over the known kinds. That union is
built from the core registry alone. A `scope_kind` of `"dynamic_foraging.trials"` — which R49 §2.4
explicitly permits, *"open, so an R17 extension can scope to its own tables"* — therefore matches
no branch and passes unchecked. The check does not reach the case R49 designed the mechanism for.

## 2. Decision

### 2.1 `discriminator` is a role

R48 §2.1's closed set gains a sixth value. A column with `role: discriminator` holds a dotted
resource ID naming a table in the packet's registry or in one of its extensions.

A discriminator **MUST** be `string`, and every non-null value **MUST** be a well-formed resource
ID: a namespace and a table name, each lowercase snake_case, separated by a dot. Well-formedness is
checkable without knowing which resources exist, and nothing checks it today.

### 2.2 A discriminator declares whether it must resolve

Required wherever `role` is `discriminator`, closed, and with no default — the same shape R53
§2.3 gives `identity`, and for R48 §2.2's reason: a default makes a forgotten decision look
deliberate.

- **`resolves: "required"`** — the value **MUST** name a resource the packet declares. Use where
  the discriminator is what gives the row meaning, so a kind resolving to nothing leaves the row
  uninterpretable. `core.intervals.interval_kind` (R54 §2.1).
- **`resolves: "optional"`** — a value naming no declared resource is a fact rather than a
  finding: it says the thing is not a packet resource. `core.processing_runs.scope_kind`
  (R49 §2.2), where a run may be about a rig or a camera the packet does not hold.

### 2.3 Resolution is mechanical

A consumer resolves a discriminator without knowing its target: read the kind, take that resource's
primary key from the registry, join. Two shapes exist.

- **A shared key.** The discriminated row and the named table share a primary key, so the join is
  on that key. This is R54's `core.intervals` and its per-kind detail tables, the
  class-table-inheritance mapping.
- **A paired value.** A separate column holds an identifier in the named table's key space, and
  the join is value-to-key. This is R49's `scope` with `scope_kind`.

A reader **SHOULD** offer that resolution. A discriminator nothing reads is a free-form name with
extra steps, which is the observed fate of NWB's `TimeIntervals`: a table there *is* its name, so
two labs name their optotagging tables differently and nothing generic finds either.

### 2.3.1 The named resource must be joinable, and must say how

Resolution is mechanical only if the two keys correspond, and nothing says they must.

**For a shared key**, a resource a discriminator may name **MUST** declare a reference to the
discriminated table. A reference already carries the column mapping, `columns` to
`resource_columns`, so the join is explicit rather than inferred from matching names, and R46's
generated anti-join enforces the integrity. `dynamic_foraging.trials` declares one already; the
rule is that declaring it is not optional.

That reference **MUST** cover the discriminated table's whole key. R54 §2.2 puts the kind in the
key — `(session_id, interval_kind, interval_id)` — so each kind may carry its source's own
numbering and trial 0 and block 0 can both exist. A reference on `(session_id, interval_id)` alone
targets a set that is not unique: it identifies a row of some kind, which is not a foreign key, and
the generated anti-join passes while resolving to several rows.

A detail table therefore carries the discriminator as a constant column and references all three,
restating in every row what its own identity implies. The precedent is `core.spike_events`, which
carries `sorting_run_id` and `curation_id` on every one of 286,896,563 rows for the same reason:
R53 §1 measured the pair at 0.06 bit/row, because a column holding one value run-length encodes to
nothing. What the rounding error buys is a reference that identifies a row.

The direction follows. The reference runs extension → core, which R17 §2 permits and §2.6 explains,
so a discriminator names downward while the integrity constraint points upward.

**For a paired value**, the named resource's primary key **MUST** be a single column, because the
paired column holds one value. R49 never said so, and the constraint bites: `scope_kind` may name
`core.units`, whose key is `(session_id, unit_id, sorting_run_id, curation_id)`, and one `scope`
value cannot hold four. R49 §2.5's generated `UNION ALL` takes one column per kind and so assumes
this silently; the assumption becomes a rule `registry/check.py` enforces.

Both rules are structural — decidable from the registry with no packet in hand.

### 2.3.2 A paired-value discriminator names its paired column

§3 says which shape a site uses is *"visible from whether it declares a paired column"*, without
saying how it declares one. The generated resolution differs between the two shapes and so needs it
mechanically, so a discriminator carries `discriminates`, naming the column that holds the value.
Absent means the shared-key shape.

`core.processing_runs.scope_kind` declares `discriminates: "scope"`. Inferring it from the name
would be the guess R48 §3 measured as unsafe, and only a declaration is checkable:
`registry/check.py` verifies that the named column exists in the same table, and that `resolves`
and `discriminates` appear on a discriminator and nowhere else.

### 2.3.3 What a paired value matches

A paired value **MUST** be `string`, and it matches the named resource's key or that key's
`*_name`, decided by R53 §2.3's `identity`:

- a **`carried`** key is the source's own number and is stable across builds, so a value written
  before the build can hold it and the join is on the key;
- an **`assigned`** key is a number this format chose at build time, which a value written before
  the build cannot hold, so the join is on the `*_name` R53 §2.3.1 requires the owner to carry.

Both cases are derivable from the registry, so resolution stays mechanical and no writer renumbers
anything. They are also why the column is a string: one discriminator resolves against several
kinds, mixing an assigned key's name with a carried key's number, so the union it joins mixes types
by construction.

A single-column key is necessary and not sufficient. An assigned identifier a table does not own —
it is exported through a reference, so the name lives on the owner — leaves nothing a paired value
could match, and the resource is not namable. Measured on the current registry: 14 of 35 core
tables have a single-column key, all 14 resolve by name, and the other 21 cannot be named at all,
`core.units`, `core.spike_events` and `core.array_channels` among them. `vr_foraging.sessions` has
a single-column key and is still not namable, because its `session_id` belongs to `core.sessions`.
That is a real limit on `scope`, and `registry/check.py` reports it rather than leaving it to be
found by a rule that matches no branch.

### 2.4 Tier 1 generates the resolution check

Where `resolves` is `required`, a check is generated from the structure as R2 §7's other Tier 1
checks are: an anti-join against the resources the manifest declares. It is not hand-written per
site, because R46 exists to fix sixteen hand-written references that were never written.

Where `resolves` is `optional`, no such check is generated, and a value naming no declared
resource is reported as `info` rather than passed over in silence.

### 2.5 R49 §2.5's check reaches extension kinds

`scope_resolves` builds its `UNION ALL` over the core registry's tables. It **MUST** be generated
over every resource the packet declares, extensions included, so the case R49 §2.4 designed the
mechanism for is the case it checks. A kind naming a resource the packet does not declare is
`resolves: "optional"`'s `info`, not a silent pass.

### 2.6 Core may name an extension, and may not reference one

R17 §2 forbids core to reference an extension, on the grounds that *"core resources must stay
interpretable when no extension is present."* A packet embeds the extension registries it declares
(`09` §6), so the schema travels with the data and is essentially never absent, and that reason
does not hold. Two others do, and replace it.

**Separable verdicts.** R17 §4 requires a core validator to check that declared extension files
exist, **MUST NOT** require their schemas, and must keep a finding against an extension out of core
conformance. A core foreign key into an extension inverts all three: the Tier 1 anti-join cannot
run without the extension, so core's verdict becomes incomplete rather than clean, and a consumer
holding core alone can no longer say whether the packet conforms.

**Independent versioning.** R17 §5 lets an extension carry its own `registry_version` and track a
core version it predates — *"nothing requires them to move together."* A core foreign key would
couple core's referential integrity to a schema free to move underneath it.

A discriminator has neither problem, which is what makes it the mechanism core is allowed: core
stays checkable alone, an absent target is a reportable fact rather than an unrunnable check, and
no integrity constraint couples the versions.

The useful case wants the other direction anyway. In the class-table mapping a detail table
references the row it specialises, so the reference runs extension → core, which R17 §2 already
permits. Core would point the other way only where extension data completes a core row's meaning,
which is the case where core is not standalone.

## 3. What this does not do

- **No new resolution semantics.** §2.3 states generally what R49 §2.2 already ruled; this names
  the pattern and makes the per-site policy declarable.
- **No change to R48's other roles.** A discriminator names a table rather than a row, so R48
  §2.3's "a reference relates columns of the same role" is untouched.
- **No requirement that a discriminator have a paired value column.** §2.3's two shapes are both
  legitimate, and `discriminates` says which a site uses.

## 4. Open

- ~~**`core.processing_runs.scope`'s own type.**~~ **Settled 2026-09-03 in §2.3.3.** It stays
  `string`, and what it holds is the name rather than the number.

  Implementing §2.4 sharpened the question from what type the column is to who assigns its value.
  `session_id` and `probe_id` are `assigned` (R53 §2.3), so a writer chooses their values at build
  time, and `escapewheel_writer.arrow.number` renumbers a foreign key through its target's map for
  declared references only. A discriminated reference is by construction not a declared reference,
  so nothing renumbers `scope` and a value written before the build can never equal a number chosen
  during it. The corpus carries the instance: `undeclared_currency` has `scope = "probe0"` against
  an integer `probe_id`, and the generated check found it.

  The alternative was to make the writer number it, which costs a property this format keeps: a
  hand-authored packet could no longer write a scope, because its author cannot know the
  assignment. Matching the `*_name` needs no writer change, keeps a scope readable in the file it
  is stored in, and covers every namable resource, since R53 §2.3.1 put a name on all 14. It pays a
  string join where R53 §1 measured an integer one at 10.2x — on 286,896,563 spike rows, where a
  run table is dozens.
- **Whether one extension declaring several kinds needs anything further.** It does not:
  `interval_kind` names a *resource*, and one extension has many, so `dynamic_foraging.trials`
  and `dynamic_foraging.blocks` are two kinds from one document. Each carries its own constant
  discriminator and references the full key; a trial naming its block is then an ordinary
  extension-internal reference between two detail tables. Nothing in §2 treats the one-extension
  case specially, which is the point, but no packet yet carries it.
- ~~**Whether a discriminator should be `int32` too.**~~ **Settled 2026-09-03: it stays a string.**
  R53's measurement does not transfer, because it was taken on an identity column that is joined,
  grouped and sorted at high cardinality. Measured on the shape a discriminator has — 20 M rows
  over six kinds — the string costs **0.013 bit/row** against an int32 surrogate's 0.008, the two
  files differ by 0.05%, and the string is *faster*: 1.05x on filtering to one kind, **0.87x** on
  `GROUP BY`, and **0.60x** against the integer plus the join needed to name the kind at all.

  Parquet dictionary-encodes it either way, which is why. R53 §1.1's three pathologies are all
  about *keeping* the dictionary in Arrow, and a discriminator meets none of them: it is filtered
  against a constant rather than `is_in` over a large set, `unify_dictionaries` costs 0.01 s over
  six values, and nothing sorts by kind.
