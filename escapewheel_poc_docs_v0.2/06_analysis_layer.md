# Part 06 — Analysis Layer

Informative, except §2 and §5, which are normative.

## 1. Scope

This part describes the optional `analysis` layer: derived products computed from core, kept because a query cannot answer the same question at acceptable cost.

## 2. Rules

Normative.

An analysis resource MUST declare lineage naming each canonical resource it derives from — core
or extension (04 §7, R71 §2.3).

An analysis resource is disposable. A consumer MAY delete and recompute any of them without loss.

An analysis resource SHOULD be materialized only where doing so materially reduces repeated computational or I/O cost, gives an access layout core cannot, preserves the result of an expensive transformation, or provides a stable interface to an explicitly parameterised derivation (R78 §2.1). A cheap filter, projection, rename or small join SHOULD remain a view.

Where the justification is an expensive transformation or a parameterised derivation, the producing run MUST record the transformation's parameters and not merely that it ran (R78 §2.2). A spectrogram whose window and overlap are unrecorded is not reproducible, and an irreproducible derived asset fails the disposability test below.

An analysis resource MUST NOT be the only place a fact exists. Anything a consumer needs that is
not recomputable from the canonical resources belongs among them (R71 §2.3); which canonical layer
it belongs to is decided by Part 09 §3's test, not by this rule.

## 3. A derived product earns its place by layout

Arithmetic does not earn it. Where the computation is cheap against data already held, a view is the correct answer and a materialized copy is a maintenance liability.

Measured on a real session, the arithmetic of aligning spikes to an event and a window costs 0.13 to 1.72 s against trains already in memory, while a materialized copy of four alignments comes to 100.6% of the spike table itself (R43 §2). A wide trial table is 708 rows in 7.5 ms.

The test is therefore: does materializing change the *shape* of access, or only pre-compute a cheap step?

## 4. `analysis.spike_events`

Core keeps each spike on the clock of the probe that measured it, sorted unit-major. That layout answers "this unit's spikes" well and "every unit's spikes in this window" not at all, because a window across many clocks means nothing.

`analysis.spike_events` is core's spikes mapped onto the reference clock and bucketed by time, sorted by unit within each bucket, so that a time filter and a unit filter both prune (R30 §2).

<!-- columns: analysis.spike_events -->
| column | type | presence | |
|---|---|---|---|
| `session_id` | `int32` | required | Session ID. |
| `unit_id` | `int32` | required | Unit ID. |
| `t_tick` | `int64` | required | Spike tick on clock_id, mapped through core.clock_anchors. |
| `clock_id` | `int32` | required | The clock these ticks are on, normally the session's reference. |
| `time_bucket_tick` | `int64` | required | First tick of the bucket this spike falls in, on clock_id. |
<!-- /columns -->

A row group lies inside one time bucket, so a window filter prunes at the row-group level. The bucket width cannot be recovered from the data and is therefore recorded in the producing run's parameters.

**Rows are not preserved.** A spike whose tick falls outside the region where the mapping is defined MUST be omitted rather than given an extrapolated value (R30 §4), so this table MAY hold fewer rows than core's. The count omitted MUST be recorded in the producing run's parameters, even when it is zero (R40 §2.3): a derived table one row short otherwise looks exactly like a complete one.

**A conversion that collides is not materialized.** This table is keyed on the converted tick, and a conversion preserves distinctness only where it expands. Where a writer finds two spikes of one unit landing on one reference tick, it MUST NOT materialize the table, and MUST record the reason in the producing run's parameters as R40 §2.3 requires of an omitted row (R92 §2.4). A histogram built on collapsed spikes undercounts them, so a reference clock too coarse to separate one unit's spikes makes this table the wrong instrument rather than a broken one, and §2 makes not building it an ordinary outcome.

Measured on one session, a ten-second population window costs 0.025 s here against 7.7 s over a ragged per-unit representation.

## 5. Provenance of a materialization

Normative.

A materialization MUST record a `core.processing_runs` row and MUST name it from the resource's catalog entry (R31 §2). The run's parameters MUST carry any transform parameter that cannot be recovered from the output.

## 6. Withdrawn resources

Four resources proposed in v0.1 are withdrawn (R43 §2). They were specified before anything measured them:

| resource | disposition |
|---|---|
| `analysis.spikes_by_trial` | withdrawn; a table per (event, window) pair, and the alignment is cheap |
| `analysis.trials_wide` | withdrawn; 708 rows in 7.5 ms as a view |
| `analysis.unit_condition_rates` | withdrawn; its columns are a task's shape, not a format's |
| `analysis.good_units` | withdrawn; a filter, not a table |

The columns those tables carried — `condition_id`, `stimulus_id`, `block_id` — describe a particular task rather than the format, and belong in an extension (Part 09).

## 7. Views versus materialized products

Prefer a view where the query prunes and the result is small. Prefer a materialized product where the physical layout of core cannot serve the access pattern at all, which in practice means a different sort order or a different clock.

## 8. Promotion into core

An analysis resource becomes canonical only through an explicit revision of this specification. Promotion is a schema decision, not an operational one.
