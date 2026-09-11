# R56 — A Column Declares Its Unit and Its Clock

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | R2 §5 (what a column declares), R48 §2.1 (what a `coordinate` role implies) |
| **Depends on** | R2 (registry format), R13 (clock alignment), R17 (extension registries), R48 (column roles) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R48 gives a column a `role`, so a consumer knows a `coordinate` is a tick and must not be treated
as an offset. It does not say **which clock** the tick is on, or **what unit** a `data` column is
in. Both are needed to do anything with the value, and both are currently prose.

### 1.1 Core already has the case that breaks

`core.clock_anchors` carries two coordinate columns:

```
t_tick        coordinate   "Tick on clock_id."
parent_tick   coordinate   "The corresponding tick on parent_clock_id."
```

They are on **different clocks**, and the difference is recorded in a description. Worse,
`parent_clock_id` is not a column of this table at all — it is on `core.clocks`, reached through
this table's reference.

So a consumer converting this table to seconds has two ways to be wrong and no way to be right:
convert both on `clock_id` and `parent_tick` is silently mis-scaled, or hard-code the exception.
This is not hypothetical and not an extension's problem — it is core, today.

Fifteen coordinate columns sit beside a `clock_id` and are unambiguous by convention. Four are
not: `core.clock_anchors.parent_tick` as above, `core.sessions.t_zero_tick` (on
`reference_clock_id`, a differently-named column of the same table), and
`core.units.first_spike_tick`/`last_spike_tick` (on the clock R38 §3 gives the sorting run).
Convention covers most and silently fails the rest.

### 1.2 An extension cannot use the clock machinery at all

R13's piecewise alignment, R27's well-founded chain, R37 and R40's error bounds and R39's origin
are this format's central competence. None of it is reachable from an extension's tick column,
because nothing says which clock the tick is on. An extension either restates the clock apparatus
or gives up on seconds — and the second is what will happen.

### 1.3 Units exist, inconsistently

Units are carried today as **sibling columns**: `core.array_assets.unit`,
`core.sorting_runs.amplitude_unit`, `core.array_dimensions.coordinate_unit`. That is right where
the unit genuinely varies per row — a sorting is µV *or* ADC counts (R11 §2) — and it leaves
nowhere to say that a duration is always seconds. `core.spike_events.amplitude` is in the unit
`core.sorting_runs.amplitude_unit` names, which is stated nowhere a machine can read.

## 2. Decision

### 2.1 A column may declare where its unit comes from

A column **MAY** declare exactly one of:

- **`unit`** — a literal, for a unit that does not vary. `"s"`, `"mm"`, `"uV"`.
- **`unit_from`** — the column that carries it, for a unit that does.

### 2.2 A coordinate may declare where its clock comes from

A column whose role is `coordinate` **MAY** declare **`clock_from`**, naming the column holding
the `clock_id` its ticks are on. Absent, the clock is the table's own `clock_id` where it has one,
and undetermined where it does not — which is the state of affairs today, made explicit rather
than changed.

### 2.3 Both resolve the same two ways

A `unit_from` or `clock_from` value is either:

- **a column of the same table** — `"clock_id"`, `"reference_clock_id"`; or
- **`resource.column`**, resolved through a reference **this table declares** — one hop, no
  search. `core.spike_events.amplitude` declares `unit_from: "core.sorting_runs.amplitude_unit"`,
  and the reference that resolves it is the one R46 §2 already requires.

One hop, deliberately. A path of two would be a query language, and R43's line is that a query is
the consumer's job; what a schema owes is enough to write the query without guessing.

### 2.4 What a validator checks

All of it is structural — decidable from the registry with no packet in hand, which is where this
format puts a check it can make without data:

- `unit` and `unit_from` are mutually exclusive.
- `clock_from` appears only on a `coordinate`.
- A same-table name is a column of that table.
- A `resource.column` name resolves through a reference the table declares, and names a column of
  that resource.
- A `clock_from` target holds a clock — an `identifier` referencing `core.clocks`.

### 2.5 What a reader may then do

A reader **MAY** convert any coordinate column to seconds, in any table, core or extension,
without knowing what the column means — which is what R48's `coordinate` role promised and could
not deliver. `core.clock_anchors.parent_tick` converts correctly for the first time.

A reader **MAY** label a quantity with its unit, and **MUST NOT** silently compare or combine two
columns whose declared units differ.

## 3. What this does not do

- **No unit vocabulary.** `unit` is an open string, as `core.sorting_runs.amplitude_unit` already
  is (R11 §2, R8 §4). Declaring a controlled vocabulary of units is a separate question and a
  larger one; this revision records what the writer knows rather than governing it.
- **No dimension or quantity kind.** A field saying a column holds "time" or "voltage" would need
  governance and buys little over the unit itself, and Part 07 puts generalized ontology machinery
  out of scope.
- **No change to the sibling columns.** `amplitude_unit` and `coordinate_unit` stay exactly as
  they are; `unit_from` makes them *declared* rather than conventional.
- **No requirement.** Both fields are MAY. A column declaring neither behaves as today.

## 4. Open

- **Whether `unit` should be required on a `data` column with a physical quantity.** It cannot be
  required generally — `choice` has no unit — and "has a physical quantity" is not decidable from
  the schema, so a MUST would need a list. Left as MAY, which risks it going unwritten, which is
  the same risk R53 §2.3.1 accepted for `*_name`.
- **`core.units.first_spike_tick`.** Its clock is R38 §3's `core.sorting_runs.clock_id`, reachable
  only through `sorting_run_id` — one hop, so §2.3 covers it, but the row's identity is the
  four-part unit key and the reference to use is not the only one. Worth checking that the
  declared reference is unambiguous before relying on it.
- **One hop was nearly not enough.** `core.spike_events.amplitude` is in the unit its sorting run
  names (R11 §2), and `core.spike_events` reached `core.sorting_runs` only *through* `core.units`
  — two hops. Rather than widen §2.3, the direct reference was declared: the column is in the
  table already, and §2.3 resolves through a reference the table **declares**, so declaring it is
  what makes the hop available. A second case needing two hops would be evidence §2.3 is drawn
  too tight.

  That anti-join is **not** dead weight, though it is transitively implied while
  `core.spike_events → core.units → core.sorting_runs` both stand. The implication is contingent
  rather than a theorem: it survives only while both references are declared, it says nothing
  where `core.units` is absent from the packet or external and unreachable (R14 §2.3, under which
  *"its rules cannot run at all"*), and R35 §5 bounds an amendment to the rules **naming** a
  written resource — which the direct check does and the chain does not.
