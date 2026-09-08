# A Sorted Unit Declares Its Spikes' Context

| | |
|---|---|
| **Status** | Draft |
| **Amends** | R11 §2 (which table declares `amplitude_unit`), R38 §3 (which table declares a unit's clock), R81 §5 (retracts the gap it recorded), the registry declarations of `clock_id` on `core.sorting_runs`, `core.spike_events` and `core.unit_observation_intervals` |
| **Depends on** | R56 (a column declares its context), R81 (why the hop was lost, and unit identity), R38 (observation belongs to the clock), R11 (the unit of measure is the sorting context's) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

Throughout, a **unit** without qualification is a row of `core.units`, a sorted neuron. A **unit
of measure** is what `amplitude_unit` holds: microvolts, or ADC counts.

## 1. Scope

A row of `core.spike_events` carries two numbers that mean nothing on their own. `amplitude` is a
height, and what it is measured in is `core.sorting_runs.amplitude_unit`; `t_tick` is a count, and
which clock counted it is `core.sorting_runs.clock_id`. Both facts belong to the run, and a spike
cannot reach the run: R56 §2.3 admits one hop, and spike → unit → run is two.

The two columns have taken opposite ways out. `amplitude` declares no unit of measure at all, so
418,293,098 spikes carry a number nothing interprets. `t_tick` gets a copy of `clock_id` on every
row, so 286,896,563 of them carry a value twelve rows already hold.

This part moves both facts to `core.units`, which a spike references directly, and declares the
hops that then resolve.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25).

## 2. Background

Informative.

### 2.1 The hop R56 admits

R56 §2.1 gave a column a machine-readable unit and §2.2 a machine-readable clock, and §2.3 admits
two forms for each: a column of the same table, or `resource.column` resolved through a reference
**that table declares**. One hop, because "a path of two would be a query language".

`core.spike_events` reached `core.sorting_runs` only through `core.units`, so R56 declared a direct
reference for the purpose. Its §6 recorded the strain: *"One hop was nearly not enough… A second
case needing two hops would be evidence §2.3 is drawn too tight."*

R81 §2.3 then narrowed every unit reference to `unit_id` alone and struck `sorting_run_id` from six
tables, `core.spike_events` among them, removing the reference with the column. `build.py` drops
the `unit_from` rather than leave it naming a hop that cannot be followed, and R81 §5 recorded the
loss as *"the same shape as the gap R70 §5 left."*

Of the seven columns declaring a `unit_from` today, all seven name a column of their own table.
Five `clock_from` declarations do use the one-hop form — `core.clock_anchors.parent_tick` through
`core.clocks.parent_clock_id`, and four more — so no unit of measure has ever been reached across a
reference, which is the half R56 built for this column.

### 2.2 Reference paths from a spike to its run

Widening §2.3 to two hops would not resolve either column, because three paths of declared
references run from `core.spike_events` to `core.sorting_runs`:

| via | hops |
|---|---|
| `unit_id` → `core.units`, `sorting_run_id` → `core.sorting_runs` | 2 |
| `unit_id` → `core.units`, `curation_id` → `core.curation_versions`, `sorting_run_id` → | 3 |
| the same, through `parent_curation_id` → `core.curation_versions` first | 4 |

A rule admitting two hops must choose among them, and `registry/check.py` has no ground to prefer
one — which is what R56 §6 anticipated in warning that "the reference to use is not the only one".
Relaxing the rule trades a gap that is honest for a resolution that is ambiguous.

### 2.3 What asks for the run's clock

R38 §3 added `core.sorting_runs.clock_id`, "since a unit's clock was a string convention no rule
could see". Every consumer it has acquired since asks the same question:

| consumer | what it wants |
|---|---|
| `core.units.first_spike_tick`, `last_spike_tick` | `clock_from: core.sorting_runs.clock_id` |
| `escapewheel_reader/observation.py:169` | a `sorting_run_id` → `clock_id` map, to place a unit's window |
| `core.spike_events.within_observation` | joins `core_units` to `core_sorting_runs` to reach the clock |
| `core.units.observation_declared` | joins `core_units` to `core_sorting_runs` to reach the clock |

Four consumers, all answering **what clock is this unit on**, and no rule reads the column for
anything a run does independently of its units. The value is stored one table away from its only
question.

It is nevertheless determined at the run's granularity and stays so: 12 runs and 12 clocks against
6,781 units, with **0 of 6,781 units** having spikes on more than one clock. That follows by
construction, since `core.units.sorting_run_id` is required and a run names one clock.

### 2.4 What the copy on the spike costs

| packet | spikes | `clock_id` compressed | share of the table |
|---|---:|---:|---:|
| `ecephys_776259` | 286,896,563 | 1,026,681 B | 0.134% |
| `ecephys_786867` | 131,396,535 | 470,536 B | 0.123% |

Twelve `int32` values under a sort that clusters them compress almost to nothing, so storage does
not decide this. Nor does query cost. Three shapes against `ecephys_776259`, warm, as three-run
minimums, comparing the column on the spike row against reaching the clock through two joins:

| query | carried | reached through two joins |
|---|---:|---:|
| spikes of one probe's units, with their clock | 34.3 ms | **29.6 ms** |
| a tick window on one clock, no unit predicate | **29.8 ms** | 33.1 ms |
| a scan of the column across every row | **169.3 ms** | 247.5 ms |

The first two differ by 3 to 5 ms on about 30 and are a wash; carrying wins clearly only on the
third, which nobody runs. The first is the shape a real analysis takes — a spike table read
alongside the unit table it is keyed by — and there not projecting a column out of a 287 M-row file
saves more than joining a 12-row table costs.

What the copy buys is therefore a **declaration** rather than access: `t_tick` declares no
`clock_from` because R56 §2.2 resolves a coordinate to its own table's `clock_id`, and striking the
column with the clock still on the run would leave the tick with no clock at all.

### 2.5 The rule that writes the join out

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

### 3.1 `amplitude_unit` moves to the unit

`core.sorting_runs.amplitude_unit` is **struck**. `core.units` gains `amplitude_unit`, `string`,
nullable, vocabulary open as R11 §2 made it, holding the unit of measure of
`core.spike_events.amplitude` for every spike of that unit.

### 3.2 `clock_id` moves to the unit

`core.sorting_runs.clock_id` is **struck**. `core.units` gains `clock_id`, `int32`, **required**,
referencing `core.clocks`, holding the clock every tick of that unit is counted on.

Both are moves rather than copies: one fact keeps one home, so nothing can disagree and no check is
needed to find out (R3 §3.0). `core.units.sorting_run_id` stays required, so each value is still
determined by the run wherever it was determined before — R11 §2's reasoning and R38 §3's both
survive the move rather than being overturned, since a unit names its sorting context in a
reference it MUST carry.

`core.units.first_spike_tick` and `last_spike_tick` then declare **nothing**: their `clock_from` is
struck, because R56 §2.2 resolves a coordinate to its own table's `clock_id` and the table now has
one. The registry's `CONTEXT` block carries entries only where that default does not apply.

### 3.3 What a spike then declares

`core.spike_events.amplitude` **MUST** declare `unit_from: "core.units.amplitude_unit"`, and
`core.spike_events.t_tick` **MUST** declare `clock_from: "core.units.clock_id"`.
`core.spike_events` declares a reference on `unit_id` to `core.units`, so both are R56 §2.3's
one-hop `resource.column` form resolving through a reference the table already has. The
`unit_from` is that form's first use for a unit of measure anywhere in the registry.

### 3.4 The copies that are struck

`core.spike_events.clock_id` is **struck**, §3.3 having given `t_tick` a hop that resolves without
it. `core.unit_observation_intervals.clock_id` is **struck** on the same ground, its `start_tick`
and `stop_tick` declaring `clock_from: "core.units.clock_id"`: a table keyed on a unit reaches that
unit's clock in one hop, so the rule is uniform rather than applying to the large table and not the
small one. Nothing is measured for the second, which is unwritten in both packets.

### 3.5 The rules that change

`core.sorting_runs.amplitude_unit_declared` refiles as `core.units.amplitude_unit_declared` and
loses a join:

```sql
SELECT DISTINCT u.unit_id FROM core_spike_events s JOIN core_units u USING (unit_id)
 WHERE s.amplitude IS NOT NULL AND u.amplitude_unit IS NULL
```

It reports the units whose spikes carry an amplitude no unit of measure interprets, where before it
reported their runs — the narrower finding, and the one a reader can act on now that the column it
names is on that row.

Two more shorten and one lengthens. `core.spike_events.within_observation` and
`core.units.observation_declared` each drop a `core_sorting_runs` join that existed only to walk
from a unit to its clock; `core.spike_events.ticks_within_clock_span` gains one, having reached
`core_clocks` from the spike row.

## 4. What this does not change

- **No tick and no amplitude changes value.** Every number keeps what it had and the clock it was
  counted on; what changes is which column a consumer reads to learn the context.
- **`core.spike_events.amplitude` keeps its type.** `float32` is right: **99.71%** and **99.95%**
  of values are non-integral, so unlike `core.media_frames.pts` before R68 this is not an integer
  wearing a float type.
- **R56 §2.3 is not widened.** §2.2 measures why — two hops are ambiguous here, which is the
  opposite of the evidence R56 §6 said would justify relaxing the rule.
- **The clock is still a property of the run's recording.** A sorting run consumes one probe's
  recording and its outputs are counted on that recording's clock. §3.2 changes where the fact is
  written down, not what determines it.
- **R34 §3 is repaired rather than contradicted.** It kept `core.spike_events.amplitude` partly
  because "`core.sorting_runs.amplitude_unit` (R11 §2) already gives it a unit", true in prose and
  false in the registry since R81. It is true again.
- **Spike identity is not restored.** R81's narrowing stands; a consumer reaches the run through the
  unit rather than through columns returned to 418 million rows.
- **`analysis.spike_events.clock_id` and `core.events.clock_id` stay.** The first holds the
  session's *reference* clock and is declared `determined_by: ["session_id"]`; the second belongs to
  a stream, which R23 gives its own clock.

## 5. Consequence

`core.units` gains two columns and one reference; `core.sorting_runs` loses two columns and one
reference; `core.spike_events` and `core.unit_observation_intervals` each lose one of each. Net two
columns and two references leave the registry. The Tier 2 rules are unchanged in number, four of
them rewritten.

`core.units` grows by one nullable string holding one distinct value per packet and one required
`int32`. Measured by rewriting both tables with the string added: **+278 bytes each**, 149,394 →
149,672 B at 6,781 rows (**1.0019x**) and 95,507 → 95,785 B at 4,505 rows. `core.spike_events`
sheds 1,026,681 and 470,536 bytes.

Both packets **MUST** be rebuilt. Adding a required column fails an existing packet with
`schema.column_absent`, the validator checking the registry's columns against the file and never
the reverse. R87 §2.1 and R88 §2 already require that rebuild, so this adds none of its own.

`escapewheel_reader/observation.py` reads `core.units` where it read `core.sorting_runs`, the
sorter adapter writes both facts onto the unit row rather than the run row, and
`registry/rules.json` carries the shorter SQL.

## 6. Open

- **The scale that produced the amplitude is unrecorded.** The values are integer ADC counts times
  bitVolts: the quantum is **2.339966 µV** in `ecephys_776259` and **2.924988 µV** in
  `ecephys_786867`, and 100% of values are integer multiples of it. Neither number is in either
  packet. `core.array_channels.conversion`, which R19 added for exactly this, is filled on **0 of
  1,152** channels in one and **0 of 960** in the other, and `core.array_channels.unit` is empty in
  both. A consumer can read microvolts and can neither recover the count nor check the conversion.
- **What a run with no units is on.** After §3.2 a sorting run that produced nothing — every unit
  removed by curation, or a run that failed — records no clock, where today it records one. No
  consumer asks, and `core.processing_runs` carries the run's provenance either way, but a packet
  loses the ability to say what a barren run was counting in.
- **Whether a sorting may span two clocks.** §2.3's measurement holds because a run is one probe
  (R81 §2.1) and a probe is one sample clock. A sorting over two probes would break
  `core.sorting_runs.clock_id` today and `core.units.clock_id` afterwards, so this part neither
  creates nor removes the limit; R81 §5 records the merge case as untested and neither packet has
  one.
- **Whether `amplitude_unit` should be required where any spike carries an amplitude.** §3.5
  reports the gap and does not refuse it, so a packet with unscaled amplitudes stays conforming.
  Tightening is the order R82 §5 argued for: report first, refuse once nothing reports.
