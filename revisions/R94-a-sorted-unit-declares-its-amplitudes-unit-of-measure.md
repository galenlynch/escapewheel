# R94 — A Sorted Unit Declares Its Amplitudes' Unit of Measure

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | R11 §2 (which table declares `amplitude_unit`), R81 §5 (retracts the gap it recorded) |
| **Depends on** | R56 (unit and clock declarations), R81 (why the hop was lost), R11 (the unit of measure is the sorting context's) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

Throughout, a **unit** without qualification is a row of `core.units`, a sorted neuron. A **unit
of measure** is what `amplitude_unit` holds: microvolts, or ADC counts.

## 1. Scope

`core.spike_events.amplitude`, a nullable `float32`, is the height of one detection. R11 §2 put its
unit of measure one table away, in the open string `core.sorting_runs.amplitude_unit`. The choice
between microvolts and ADC counts belongs to the sorting context rather than to one detection, so
the spike holds the number and the run says what it means.

No declaration connects them. R56 §2.3 resolves a column's `unit_from` through a reference the
column's own table declares, and `core.spike_events` stopped declaring one to `core.sorting_runs`
when R81 narrowed spike identity. This part moves `amplitude_unit` to `core.units`, which the
spike does reference, and declares the `unit_from` that then resolves.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25).
`amplitude` is filled on **418,293,098 of 418,293,098 spikes** across them — every row of both
packets, 324.5 MB of column — and `amplitude_unit` reads `uV` on all 22 runs.

## 2. Background

Informative.

### 2.1 The declaration R56 made

R56 §2.1 gave a column a machine-readable unit, and §2.3 admits two forms: a column of the same
table, or `resource.column` resolved through a reference **that table declares**. One hop, because
"a path of two would be a query language".

`core.spike_events` reached `core.sorting_runs` only through `core.units`, so R56 declared a direct
reference for the purpose. Its §6 recorded the strain: *"One hop was nearly not enough… A second
case needing two hops would be evidence §2.3 is drawn too tight."*

R81 §2.3 then narrowed every unit reference to `unit_id` alone and struck `sorting_run_id` from six
tables, `core.spike_events` among them, removing the reference with the column. `build.py` drops
the `unit_from` rather than leave it naming a hop that cannot be followed, and R81 §5 recorded the
loss as *"the same shape as the gap R70 §5 left."*

Of the seven columns declaring a `unit_from` today, all seven name a column of their own table. Five
`clock_from` declarations do use the one-hop form — `core.clock_anchors.parent_tick` through
`core.clocks.parent_clock_id`, and four more — so no unit of measure has ever been reached across a
reference, which is the half R56 built for this column.

### 2.2 Reference paths from a spike to its run

Widening §2.3 to two hops would not resolve this column, because three paths of declared references
run from `core.spike_events` to `core.sorting_runs`:

| via | hops |
|---|---|
| `unit_id` → `core.units`, `sorting_run_id` → `core.sorting_runs` | 2 |
| `unit_id` → `core.units`, `curation_id` → `core.curation_versions`, `sorting_run_id` → | 3 |
| the same, through `parent_curation_id` → `core.curation_versions` first | 4 |

A rule admitting two hops must choose among them, and `registry/check.py` has no ground to prefer
one — which is what R56 §6 anticipated in warning that "the reference to use is not the only one".
Relaxing the rule trades a gap that is honest for a resolution that is ambiguous.

### 2.3 The rule that writes the join out

`core.sorting_runs.amplitude_unit_declared` fires where a spike carries an amplitude and its run
declares no unit of measure. Unable to state the path, it spells it:

```sql
SELECT DISTINCT r.sorting_run_id FROM core_spike_events s
  JOIN core_units u USING (unit_id)
  JOIN core_sorting_runs r USING (sorting_run_id)
 WHERE s.amplitude IS NOT NULL AND r.amplitude_unit IS NULL
```

Two joins over 286,896,563 spikes, because the schema cannot declare what the rule can query.

## 3. Decision

### 3.1 Where `amplitude_unit` is declared

`core.sorting_runs.amplitude_unit` is **struck**. `core.units` gains `amplitude_unit`, `string`,
nullable, vocabulary open as R11 §2 made it, holding the unit of measure of
`core.spike_events.amplitude` for every spike of that unit.

A move, not a copy: one fact keeps one home, so nothing can disagree and no check is needed to find
out (R3 §3.0).

`core.units.sorting_run_id` is **required**, so every unit names exactly one run and the value stays
determined by the run wherever it was determined before. R11 §2's reasoning survives the move rather
than being overturned — the unit of measure is a property of the sorting context, and a unit names
its sorting context in a reference it MUST carry.

### 3.2 The `unit_from` on `amplitude`

`core.spike_events.amplitude` **MUST** declare `unit_from: "core.units.amplitude_unit"`.

`core.spike_events` declares a reference on `unit_id` to `core.units`, so this is R56 §2.3's one-hop
`resource.column` form resolving through a reference the table already has. R56's mechanism is
unchanged, and this is the first `unit_from` to use it.

### 3.3 The check on `core.units`

The rule refiles as `core.units.amplitude_unit_declared` and loses a join:

```sql
SELECT DISTINCT u.unit_id FROM core_spike_events s JOIN core_units u USING (unit_id)
 WHERE s.amplitude IS NOT NULL AND u.amplitude_unit IS NULL
```

It reports the units whose spikes carry an amplitude that no unit of measure interprets, where
before it reported their runs. A unit is the narrower finding and the one a reader can act on, the
column it names now being on that row.

## 4. What this does not change

- **`core.spike_events.amplitude` keeps its type.** `float32` is right: **99.71%** and **99.95%** of
  values are non-integral, so unlike `core.media_frames.pts` before R68 this is not an integer
  wearing a float type. No column is retyped.
- **No column is added or removed on balance.** One moves: 316 columns before and after, 90
  references, 68 Tier 2 rules.
- **R56 §2.3 is not widened.** §2.2 measures why — two hops are ambiguous here, which is the
  opposite of the evidence R56 §6 said would justify relaxing the rule.
- **R34 §3 is repaired rather than contradicted.** It kept `core.spike_events.amplitude` partly
  because "`core.sorting_runs.amplitude_unit` (R11 §2) already gives it a unit", true in prose and
  false in the registry since R81. It is true again.
- **Spike identity is not restored.** R81's narrowing stands; a consumer reaches the run through
  the unit rather than through a column returned to 418 million rows.

## 5. Consequence

`core.units` grows by one nullable string holding one distinct value per packet. Measured by
rewriting both tables with it added: **+278 bytes each**, 149,394 → 149,672 B at 6,781 rows
(**1.0019x**) and 95,507 → 95,785 B at 4,505 rows (**1.0029x**). Recording the value 6,781 times
where 12 sufficed costs what R81 measured for a repeated low-cardinality column under a clustered
sort, which is nothing.

Both packets **MUST** be rebuilt. Adding a nullable column fails an existing packet with
`schema.column_absent`, the validator checking the registry's columns against the file and never the
reverse. R87 §2.1, R88 §2 and R90 §3.1 already require that rebuild, so this adds no build of its
own.

The conformance corpus regenerates, the sorter adapter writes `amplitude_unit` onto the unit row
rather than the run row, and `registry/rules.json` carries the shorter SQL.

## 6. Open

- **The scale that produced the amplitude is unrecorded.** The values are integer ADC counts times
  bitVolts: the quantum is **2.339966 µV** in `ecephys_776259` and **2.924988 µV** in
  `ecephys_786867`, and 100% of values are integer multiples of it. Neither number is in either
  packet. `core.array_channels.conversion`, which R19 added for exactly this, is filled on **0 of
  1,152** channels in one and **0 of 960** in the other, and `core.array_channels.unit` is empty in
  both. A consumer can read microvolts and can neither recover the count nor check the conversion.
- **Whether a spike should carry the count instead.** Storing the integer needs a per-spike route to
  a gain, and a spike reaches a channel only through its unit's extremum channel — the resolution
  that named the wrong electrode for 5,071 of 6,781 units until R83. Coupling the simplest numeric
  column to the most error-prone join, to recover an integer that `round(amplitude / bitVolts)`
  already returns to within 0.0036 of exact, is rejected here and would need the scale recorded
  first in any case.
- **Whether `amplitude_unit` should be required where any spike carries an amplitude.** §3.3 reports
  the gap and does not refuse it, so a packet with unscaled amplitudes stays conforming. Tightening
  is the order R82 §5 argued for: report first, refuse once nothing reports.
