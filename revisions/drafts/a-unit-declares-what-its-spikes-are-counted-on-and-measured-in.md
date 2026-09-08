# A Unit Declares What Its Spikes Are Counted On and Measured In

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
height in the unit of measure `core.sorting_runs.amplitude_unit` names; `t_tick` is a count on the
clock `core.sorting_runs.clock_id` names. Both facts belong to the run, and a spike cannot reach
the run: R56 §2.3 admits one hop, and spike → unit → run is two.

The two columns fail differently. `amplitude` declares no unit of measure at all, so 418,293,098
spikes carry a number nothing interprets. `t_tick` takes a copy of `clock_id` on every row, so
286,896,563 of them repeat a value twelve rows already hold.

This part moves both facts to `core.units`, which a spike references directly, and declares the
hops that then resolve.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25).

## 2. Background

Informative.

### 2.1 R56 admits one hop; a spike reaches its run in two

R56 §2.1 gave a column a machine-readable unit and §2.2 a machine-readable clock, and §2.3 admits
two forms for each: a column of the same table, or `resource.column` resolved through a reference
**that table declares**. One hop, because "a path of two would be a query language".

`core.spike_events` reached `core.sorting_runs` only through `core.units`, so R56 declared a direct
reference from the spike to the run and resolved both columns across it. Its §6 recorded the strain: *"One hop was nearly not enough… A second
case needing two hops would be evidence §2.3 is drawn too tight."*

R81 §2.3 then narrowed every unit reference to `unit_id` alone and struck `sorting_run_id` from six
tables, `core.spike_events` among them, removing the reference with the column. `build.py` drops
the `unit_from` rather than leave it naming a hop that cannot be followed, and R81 §5 recorded the
loss as *"the same shape as the gap R70 §4 left."*

Nine columns declare a `unit_from` today and **two** use the one-hop form:
`core.calibration_points.input_value` and `output_value`, each reaching its calibration's declared
unit of measure (R89 §2.3). Six `clock_from` declarations use it too —
`core.clock_anchors.parent_tick` through `core.clocks.parent_clock_id`, `core.events.t_tick`
through its stream (R91 §3.2), and four more. The form §3.3 needs for a spike is therefore one the
registry already resolves in both halves, on a calibration's values and on an event's tick.

### 2.2 Three declared paths run from a spike to its run

Widening §2.3 to two hops would not resolve either column, because three paths of declared
references run from `core.spike_events` to `core.sorting_runs`:

| via | hops |
|---|---|
| `unit_id` → `core.units`, `sorting_run_id` → `core.sorting_runs` | 2 |
| `unit_id` → `core.units`, `curation_id` → `core.curation_versions`, `sorting_run_id` → | 3 |
| the same, through `parent_curation_id` → `core.curation_versions` first | 4 |

A rule admitting two hops must choose among them, and `registry/check.py` has no ground to prefer
one — which is what R56 §4 anticipated in warning that "the reference to use is not the only one".
Relaxing the rule trades a gap that is honest for a resolution that is ambiguous.

### 2.3 Every reader of the run's clock is asking what clock a unit is on

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

### 2.4 Neither storage nor query time justifies the copy

| packet | spikes | `clock_id` compressed | share of the table |
|---|---:|---:|---:|
| `ecephys_776259` | 286,896,563 | 1,026,681 B | 0.152% |
| `ecephys_786867` | 131,396,535 | 470,536 B | 0.136% |

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

The copy therefore buys a declaration rather than access. `t_tick` declares no `clock_from`,
because R56 §2.2 resolves a coordinate to its own table's `clock_id`, so striking the column while
the clock stayed on the run would leave the tick with no clock at all.

### 2.5 One rule spells the join the schema cannot declare

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

Both are moves rather than copies: one fact keeps one home, so nothing can disagree and no check
finds out (R3 §3.0). The run still determines both values, because `core.units.sorting_run_id`
stays required — so R11 §2's reasoning and R38 §3's survive the move rather than being overturned:
a unit names its sorting context in a reference it MUST carry.

`core.units.first_spike_tick` and `last_spike_tick` then declare nothing. Their `clock_from` is
struck, because R56 §2.2 resolves a coordinate to its own table's `clock_id` and the table now has
one. The registry's `CONTEXT` block carries entries only where that default does not apply.

### 3.3 A spike resolves both facts in one hop

`core.spike_events.amplitude` **MUST** declare `unit_from: "core.units.amplitude_unit"`, and
`core.spike_events.t_tick` **MUST** declare `clock_from: "core.units.clock_id"`.
`core.spike_events` declares a reference on `unit_id` to `core.units`, so both are R56 §2.3's
one-hop `resource.column` form resolving through a reference the table already has — the form
R89 §2.3 first used for a unit of measure and R91 §3.2 for a clock, resolved here for the largest
table either packet holds.

### 3.4 Two copies of the clock are struck

`core.spike_events.clock_id` is **struck**, §3.3 having given `t_tick` a hop that resolves without
it. `core.unit_observation_intervals.clock_id` is **struck** on the same ground, its `start_tick`
and `stop_tick` declaring `clock_from: "core.units.clock_id"`: a table keyed on a unit reaches that
unit's clock in one hop, so the rule is uniform rather than applying to the large table and not the
small one. Nothing is measured for the second, which is unwritten in both packets.

### 3.5 Four rules change

`core.sorting_runs.amplitude_unit_declared` refiles as `core.units.amplitude_unit_declared` and
loses a join:

```sql
SELECT DISTINCT u.unit_id FROM core_spike_events s JOIN core_units u USING (unit_id)
 WHERE s.amplitude IS NOT NULL AND u.amplitude_unit IS NULL
```

It names the units whose spikes have amplitudes and whose `amplitude_unit` is empty, where before
it named their runs. The finding is narrower and lands on the row a reader would fix.

Two more shorten and one lengthens. `core.spike_events.within_observation` and
`core.units.observation_declared` each drop a `core_sorting_runs` join that existed only to walk
from a unit to its clock; `core.spike_events.ticks_within_clock_span` gains one, having reached
`core_clocks` from the spike row.

## 4. What this does not change

- **No tick and no amplitude changes value.** Every number keeps what it had and the clock it was
  counted on; what changes is which column a consumer reads to learn the context.
- **`core.spike_events.amplitude` keeps its type.** The values are quantised — §6 measures every
  one as an integer multiple of 0.585 µV — but what the column stores is the scaled microvolt
  rather than the count, and **99.78%** and **99.62%** of those are non-integral. So unlike
  `core.media_frames.pts` before R68, this is not an integer wearing a float type: recovering the
  integer needs the conversion, which §6 measures as recorded and unreachable.
- **R56 §2.3 is not widened.** §2.2 measures why — two hops are ambiguous here, which is the
  opposite of the evidence R56 §4 said would justify relaxing the rule.
- **The clock is still a property of the run's recording.** A sorting run consumes one probe's
  recording and its outputs are counted on that recording's clock. §3.2 changes where the fact is
  written down, not what determines it.
- **R34 §3 is repaired rather than contradicted.** It kept `core.spike_events.amplitude` partly
  because "`core.sorting_runs.amplitude_unit` (R11 §2) already gives it a unit", true in prose and
  false in the registry since R81. It is true again.
- **Spike identity is not restored.** R81's narrowing stands; a consumer reaches the run through the
  unit rather than through columns returned to 418 million rows.
- **`analysis.spike_events.clock_id` stays.** It holds the session's *reference* clock and is
  declared `determined_by: ["session_id"]`, where §3.2 moves the column holding a probe's own.
- **`core.events` has already made this move.** R91 §3.2 struck its `clock_id` and resolved
  `t_tick` through the stream in one hop, which is the shape §3.2 gives a spike through its unit.

## 5. Consequence

`core.units` gains two columns and one reference; `core.sorting_runs` loses two columns and one
reference; `core.spike_events` and `core.unit_observation_intervals` each lose one of each. Net two
columns and two references leave the registry. The Tier 2 rules are unchanged in number, four of
them rewritten.

`core.units` grows by one nullable string holding one distinct value per packet and one required
`int32`. Measured by rewriting both tables with each column added: the string costs **+278 bytes**
in each, the `int32` **+364** and **+350**, so the table goes 149,394 → 150,033 B at 6,781 rows
(**1.0043x**) and 95,507 → 96,132 B at 4,505 rows (**1.0065x**). `core.spike_events` sheds
1,026,681 and 470,536 bytes, which is 3.7x and 1.5x what `core.units` gains.

Both packets **MUST** be rebuilt. Adding a required column fails an existing packet with
`schema.column_absent`, the validator checking the registry's columns against the file and never
the reverse. R87 §2.1 and R88 §2 already require that rebuild, so this adds none of its own.

`escapewheel_reader/observation.py` reads `core.units` where it read `core.sorting_runs`, the
sorter adapter writes both facts onto the unit row rather than the run row, and
`registry/rules.json` carries the shorter SQL.

## 6. Open

- **The scale that produced the amplitude is recorded and unreachable.** The values are integer ADC
  counts times bitVolts, and every one is an integer multiple of **0.585 µV** — 286,896,563 of
  286,896,563 in `ecephys_776259` and 131,396,535 of 131,396,535 in `ecephys_786867`. The packets
  record that quantum: `core.array_assets.conversion` holds **0.585, 2.34 and 2.925 µV** in volts
  across the LFP series, three gains standing at 1x, 4x and 5x. What no consumer can do is get from
  a unit to the asset carrying its own. `core.sorting_runs.input_array_asset_id` declares a
  reference to `core.array_assets` for exactly this and is null on all **22** runs;
  `core.array_assets.device_id`, which R65 added so an array names the instrument that made it, is
  null on all **14** assets of one packet and **11** of the other, so probe → device → asset joins
  **0** rows. Both are writer gaps rather than schema ones. Behind them is one the schema does not
  answer either: the recorded conversion is the LFP series', where a spike's amplitude comes from
  the AP band, which neither packet holds.
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
