# R90 — Declaring and Resolving a Discriminator

| | |
|---|---|
| **Status** | **Accepted** 2026-09-08 |
| **Supersedes** | R55 §2.1–§2.6, R72 §2.1–§2.3 |
| **Amends** | `02` §8.3 (the compiled statement of all of it), R54 §2.1 (the role it gave a detail table's kind column), the registry declarations of `interval_kind` on two extension tables |
| **Depends on** | R55 (the mechanism), R54 (the first discriminator), R49 (the first paired value), R72 (the reverse check), R17 (what core may say about an extension) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R55 §2 defines the discriminated reference in nine subsections, and three amendments now reach it
from three directions. Reading the mechanism whole means reading them in order and holding the
corrections in your head. Two columns have carried the role since R54 §2.1 without anything
noticing that they resolve nothing, which is what a mechanism nobody can read in one place
produces.

This part restates the mechanism in one place. It adds two rules — which table may carry the column,
and which column is not one — and folds in what has amended R55 §2 since it was written. Nothing
else changes: every rule R55 §2 and R72 §2 state is restated here with the same force.

## 2. Why restating

Informative.

### 2.1 What has reached R55 §2

| | reaches | what it changes |
|---|---|---|
| R72 §2.1–§2.3 (accepted) | R55 §2.4 | a required discriminator implies a reverse anti-join, shared key only |
| this part | R55 §2.1, §2.3 | which table carries the column, which column is not one, and a third resolution shape |

R55 §2.3 says "two shapes exist" and there are three. The third was found by
`checking-the-tables-an-array-axis-names`, which met a column resolving by neither: that draft
stated the shape itself until this part took the mechanism, and now applies §3.5's third rather
than declaring a fourth amendment to the same clause.

R55 §2.1 says what a discriminator holds and not where it sits. Neither statement is wrong where it
was written; both are incomplete where a reader arrives.

### 2.2 Two columns resolve nothing

`dynamic_foraging.trials.interval_kind` and `vr_foraging.sites.interval_kind` are declared
discriminators. Each holds a constant naming its own table, so a consumer resolving one learns
which table it is already reading.

R54 §2.1 gave them the role because R55 §2.3.1 requires a detail table to carry the discriminated
table's **whole key**, and `interval_kind` is a key column of `core.intervals`. It is carried for
the same reason `session_id` and `trial_id` are, and nobody calls the child's `session_id` an
identifier placed on another table.

Measured against the generated checks, the role buys one: `is_a_resource_id`, a regex asking
whether the value is shaped like `a.b`. `not_null` comes from `presence: required` and the
anti-join `session_id_interval_kind_trial_id_resolves` from the declared reference, neither of
which needs a role — and the anti-join is the stronger of the two, requiring the value to match a
real `core.intervals` row where the regex asks only that a wrong value look plausible.

### 2.3 One case wants the column elsewhere

`an-event-is-an-occurrence-on-a-stream` moves everything constant across a stream's events onto the
stream, and the table specialising those events is one of them. On the event it is a string
repeated across 5,485 and 6,256 rows; on the stream it is ten. The resolution does not change — a
detail table still carries the event's key — but the column naming it is one join from the rows it
describes, which R55 §2.1 does not admit.

## 3. Decision

### 3.1 The role

R48 §2.1's closed set includes `discriminator`. A column with that role holds a dotted resource ID
naming a table in the packet's registry or in one of its extensions.

A discriminator **MUST** be `string`, and every non-null value **MUST** be a well-formed resource
ID: a namespace and a table name, each lowercase snake_case, separated by a dot. Well-formedness is
checkable without knowing which resources exist.

### 3.2 Which column carries it

A discriminator **MAY** be declared on the table whose rows it specialises, or on a table those
rows reach through one declared reference. Where it is not on the specialised table, it **MUST**
declare `discriminates_via`, holding the **referencing** column as a dotted `resource.column` —
`core.event_streams.detail_kind` declares `discriminates_via: "core.events.stream_id"`, which reads
as *the rows I specialise are in `core.events`, reached through its reference on `stream_id`*.

The referencing side rather than the referenced one, because a reference carries no identifier in
the registry — it is an entry in a table's `references` list — so there is nothing else to name.
Naming it this way gives the specialised table and the path in one string, and settles the
direction by construction: a value can only mean the table that points here.

One reference and no more, which is R56 §2.3's limit for a unit or a clock and holds for the same
reason: a second hop would need a consumer to choose among the paths that exist. A discriminator
further away, or reachable by no declared reference, is a defect `registry/check.py` refuses —
without that bound a consumer must search the registry for a column that might apply.

### 3.3 Which column is not one

A column carrying a discriminator's value as part of §3.5's shared key is **not** a discriminator
and **MUST NOT** declare the role or `resolves`. `dynamic_foraging.trials.interval_kind` and
`vr_foraging.sites.interval_kind` become `data`.

§3.1 makes a discriminator a column a consumer resolves to a table, and §2.2 measures that these
resolve nothing. Keeping the role would make it mean "holds a value shaped like a resource ID",
which is a claim about the type where R48 §2.1's roles say what a consumer may do with a column.
The check it generated is subsumed rather than lost; what goes is a check that cannot fail unless a
stronger one already has, which is coverage in the report that is not coverage (R82 §2).

`registry/check.py` requires a `_kind` column to be a discriminator, so each of the two is declared
a naming exception with that reason rather than renamed: matching the parent's column name is what
makes the composite reference legible, and an exception is checked to still break a convention, so
it cannot go stale.

One further rule bends, and only as far as its own reason reaches. R48 §2.3 requires a reference to
relate columns of the same role, and after this a detail table's `data` column references the
parent's `discriminator`. That rule exists because "a client converting one side and not the other
would break the join" — a statement about a `structural_index` and its index base. Nothing converts
a discriminator or the value carried from one, so the pair `data` → `discriminator` is exempt and
`registry/check.py` names it as such. No other mismatch is admitted.

### 3.4 Whether it must resolve

`resolves` is required wherever `role` is `discriminator`, closed, and has no default — the shape
R53 §2.3 gives `identity`, for R48 §2.2's reason: a default makes a forgotten decision look
deliberate.

- **`required`** — the value **MUST** name a resource the packet declares. Use it where the
  discriminator gives the row its meaning, so a kind resolving to nothing leaves the row
  uninterpretable. `core.intervals.interval_kind` (R54 §2.1).
- **`optional`** — a value naming no declared resource is a fact rather than a finding: it says the
  thing is not a packet resource. `core.processing_runs.scope_kind` (R49 §2.2), where a run may be
  about a rig the packet does not hold, and `core.calibrations.detail_kind` (R89 §2.5), where a
  calibration's content may be recorded nowhere.

### 3.5 The three resolution shapes

A consumer resolves a discriminator without knowing its target: read the kind, take that resource's
primary key from the registry, join. A reader **SHOULD** offer that resolution — a discriminator
nothing reads is a free-form name with extra steps, which is the observed fate of NWB's
`TimeIntervals`, where a table *is* its name and nothing generic finds either lab's.

- **A shared key.** The discriminated row and the named table share a primary key, so the join is
  on that key. R54's `core.intervals` and its per-kind detail tables: the class-table-inheritance
  mapping.
- **A paired value.** A separate column holds an identifier in the named table's key space, and the
  join is value-to-key. R49's `scope` with `scope_kind`.
- **By position.** The named resource's **rows are the positions** the discriminated column
  indexes, located by a column that resource declares. Resolution is neither a key join nor a
  value-to-key join, so §3.6's joinability rules do not apply and **MUST NOT** be read as applying.
  `checking-the-tables-an-array-axis-names` §2.1 is the case; how the named resource's rows are
  narrowed to one axis is that resource's own business.

A discriminator declares which shape it uses by declaring `discriminates` or not (§3.7), except
for the third, which a column reaches only by naming a resource whose rows are positions.

### 3.6 What a named resource must guarantee

**For a shared key**, a resource a discriminator may name **MUST** declare a reference to the
discriminated table, and that reference **MUST** cover that table's whole key. A reference carries
the column mapping, so the join is explicit rather than inferred from matching names, and R46's
generated anti-join enforces the integrity.

The whole key, because R54 §2.2 puts the kind in it — `(session_id, interval_kind, interval_id)` —
so each kind may carry its source's own numbering and trial 0 and block 0 can both exist. A
reference on `(session_id, interval_id)` alone targets a set that is not unique: the anti-join
passes while resolving to several rows. So a detail table carries the discriminator's value as a
constant column and references all three; §3.3 settles that such a column is not itself a
discriminator.

Carrying it costs nothing. R53 §1 measured a repeated constant at **0.06 bit/row** across
`core.spike_events`' 286,896,563 rows, because a column holding one value run-length encodes away.
What the rounding error buys is a reference that identifies a row rather than a set.

**For a paired value**, the named resource's primary key **MUST** be a single column, because the
paired column holds one value. `scope_kind` may otherwise name `core.units`, and one `scope` value
cannot hold a four-column key.

A single-column key is necessary and not sufficient. An assigned identifier a table does not own —
exported through a reference, so the name lives on the owner — leaves nothing a paired value could
match. Measured on the current registry: **16 of 38** core tables have a single-column key, 18 of
49 with extensions, and `registry/check.py` reports which of them are namable rather than leaving
it to a rule that quietly matches no branch.

Both rules are structural, decidable from the registry with no packet in hand.

### 3.7 The paired column, and what its value matches

A paired-value discriminator carries `discriminates`, naming the column holding the value. Absent
means the shared-key shape. `core.processing_runs.scope_kind` declares `discriminates: "scope"`.
Inferring it from the name would be the guess R48 §3 measured as unsafe, and only a declaration is
checkable.

A paired value **MUST** be `string`, and it matches the named resource's key or that key's `*_name`,
decided by R53 §2.3's `identity`: a **carried** key is the source's own number and stable across
builds, so the join is on the key; an **assigned** key is a number this format chose at build time,
which a value written before the build cannot hold, so the join is on the `*_name` R53 §2.3.1
requires the owner to carry. That is also why the column is a string — one discriminator resolves
against several kinds, mixing an assigned key's name with a carried key's number.

### 3.8 What Tier 1 generates

Where `resolves` is `required`, two checks are generated from the structure, not hand-written per
site:

- **Forward.** An anti-join against the resources the manifest declares: a value naming no declared
  resource is an error.
- **Reverse.** Per named kind, every row of the discriminating table whose key has no counterpart
  in the resource its discriminator names. Level **error**, matching `required`.

The reverse check is generated over the kinds a packet's rows actually name rather than every
resource it declares, since a kind naming a resource the packet does not carry is already the
forward check's finding and reporting it twice tells a reader nothing. It applies to the shared-key
shape only: a paired value names a resource through one column and has no shared key to join on, so
the forward value-to-key check is its whole coverage. It does not apply to §3.5's third shape,
which has no key correspondence at all.

Where `resolves` is `optional`, neither is generated, and a value naming no declared resource is
reported as `info` rather than passed over in silence.

Every generated check **MUST** be built over each resource the packet declares, extensions
included, so the case R49 §2.4 designed the mechanism for is the case it checks.

### 3.9 Core names an extension and does not reference one

R17 §2 forbids core to reference an extension. Its stated reason — that core must stay
interpretable when no extension is present — does not hold, because a packet embeds the extension
registries it declares (`09` §6). Two others do.

**Separable verdicts.** R17 §4 requires a core validator to check that declared extension files
exist, **MUST NOT** require their schemas, and to keep a finding against an extension out of core
conformance. A core foreign key into an extension inverts all three: the anti-join cannot run
without the extension, so core's verdict becomes incomplete rather than clean.

**Independent versioning.** R17 §5 lets an extension carry its own `registry_version`. A core
foreign key would couple core's referential integrity to a schema free to move underneath it.

A discriminator has neither problem, which is what makes it the mechanism core is allowed: core
stays checkable alone, an absent target is a reportable fact, and no integrity constraint couples
the versions. **It names without depending.** The useful case wants the other direction anyway — in
the class-table mapping a detail table references the row it specialises, so the reference runs
extension → core, which R17 §2 already permits.


## 4. What this does not change

- **No rule is dropped.** Every clause of R55 §2 and R72 §2 is restated above with the same force;
  §3.2, §3.3 and §3.5's third shape are the only additions.
- **No packet changes and no rebuild is owed.** §3.3 changes what two columns are declared to be,
  not what they hold; both keep their type, presence and reference.
- **R72 §2.4 stands and is not restated.** What a packet's verdict covers when an extension fails
  is a statement about conformance rather than about discriminators, and lands in another part, so
  it is outside the clause-set this part consolidates; restating it would put one rule in two
  places.
- **`02` §8.3 is replaced, not extended.** It compiles R55 §2; it now compiles this.

## 5. Consequence

Six discriminators become **four**, all in core, and two generated `is_a_resource_id` checks go
with them. Two extension registries are edited and `registry/check.py` gains two
`NAMING_EXCEPTIONS` entries, two checks for §3.2's placement, and a `discriminates_via` property in
`registry.schema.json` that no declaration uses until
`an-event-is-an-occurrence-on-a-stream` §3.4.

Nine `applied.toml` entries for R55 §2 and three for R72 §2 become `superseded`, naming this part.
`02` §8.3 is rewritten from §3 rather than amended.

No table, column, reference or Tier 2 rule changes, no packet is invalidated, and no rebuild is
owed.

## 6. Open

- **Whether a fourth resolution shape is waiting.** §3.5 states three, and the third was a third
  shape when R55 was written — `coordinate_resource` predates it and nobody looked. Two sweeps
  looked now and found no fourth: every string column of every table under five million rows in
  both packets was tested against the resource-ID pattern, and the only column holding one without
  the role is `core.array_dimensions.coordinate_resource`, which is the third shape; a registry
  sweep for columns describing themselves as naming a resource returned only the four declared
  discriminators. Neither sweep can see a column no packet writes and no description mentions, and
  `coordinate_resource` is the reason to doubt the second — it names a resource and its description
  never says so, which is why only the value sweep found it.
