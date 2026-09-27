# Part 06 — Analysis Layer

Informative, except §§2, 4, and 5, which are normative.

<a id="ew-analysis-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part describes resources whose Part 02 declaration has content class `analysis`: derived
products computed from canonical core or extension resources and kept because a query cannot
answer the same question at acceptable cost.

<a id="ew-analysis-rules" data-spec-anchor="canonical"></a>
## 2. Rules

Normative.

An analysis resource MUST satisfy Part 02 §2.7's required lineage policy. Its
lineage may name the canonical core or extension resources it consumed or an intermediate analysis
resource; the acyclic chain MUST terminate in canonical resources.

An analysis resource is disposable. A writer MAY delete and recompute any of them without loss.

A writer SHOULD materialize an analysis resource only where doing so materially reduces repeated computational or I/O cost, gives an access layout core cannot, preserves the result of an expensive transformation, or provides a stable interface to an explicitly parameterised derivation. A cheap filter, projection, rename or small join SHOULD remain a view.

Where the justification is an expensive transformation or a parameterised derivation and a writer records the materialization's run, §5 requires that run to carry the transformation's parameters and not merely that it ran. A spectrogram whose window and overlap are unrecorded is not reproducible, and an irreproducible derived asset fails the disposability test below.

An analysis resource MUST NOT be the only place a fact exists. Anything a consumer needs that is
not recomputable from the canonical resources belongs among them; which canonical layer
it belongs to is decided by Part 09 §3's test, not by this rule.

<a id="ew-analysis-layout-criterion" data-spec-anchor="canonical"></a>
## 3. A derived product earns its place by layout

Arithmetic does not earn it. Where the computation is cheap against data already held, a view is the correct answer and a materialized copy is a maintenance liability.

Measured on a real session, the arithmetic of aligning spikes to an event and a window costs 0.13 to 1.72 s against trains already in memory, while a materialized copy of four alignments comes to 100.6% of the spike table itself. A wide trial table is 708 rows in 7.5 ms.

The test is therefore: does materializing change the *shape* of access, or only pre-compute a cheap step?

<a id="ew-analysis-spike-events" data-spec-anchor="canonical"></a>
## 4. `analysis.spike_events`

Normative, except its measurement of a population window.

Core keeps each spike on the clock of the probe that measured it, sorted unit-major. That layout answers "this unit's spikes" well and "every unit's spikes in this window" not at all, because a window across many clocks means nothing.

`analysis.spike_events` is core's spikes mapped onto the session's reference clock and bucketed by time, so that a time filter and a unit filter both prune. Its `clock_id` is the session's reference clock, so the table holds no rows for a session declaring no reference clock. Part 03 §5.4 owns the order it is stored in, by unit within each time bucket, and its row groups.

<!-- columns: analysis.spike_events -->
| column | type | presence | |
|---|---|---|---|
| `session_id` | `int32` | required | Session ID. |
| `unit_id` | `int32` | required | Unit ID. |
| `t_tick` | `int64` | required | Spike tick on clock_id, mapped through core.clock_anchors. |
| `clock_id` | `int32` | required | The session's reference clock, which these ticks are on. |
| `time_bucket_tick` | `int64` | required | First tick of the bucket this spike falls in, on clock_id. |
<!-- /columns -->

The bucket width cannot be recovered from the data, so it is a parameter of a recorded materialization run (§5).

**Rows are not preserved.** A spike whose tick falls outside the region where the mapping is defined MUST be omitted by the writer rather than given an extrapolated value, so this table MAY hold fewer rows than core's. A writer that records the materialization's run MUST record among its parameters, for each clock from which it mapped spikes, how many of that clock's spikes it omitted, even when the count is zero: a derived table one row short otherwise looks exactly like a complete one, and a total does not say which clock's mapping fell short. No checker verifies this, since `parameters` names no key for the counts.

**A conversion that collides is not materialized.** This table is keyed on the converted tick, and a conversion preserves distinctness only where it expands. Where a writer finds two spikes of one unit landing on one reference tick, it MUST NOT materialize the table, and where it records the run, it MUST record the reason among the run's parameters as it does for omitted rows. A histogram built on collapsed spikes undercounts them, so a reference clock too coarse to separate one unit's spikes makes this table the wrong instrument rather than a broken one, and §2 makes not building it an ordinary outcome.

*Informative.* Measured on one session, a ten-second population window costs 0.025 s here against 7.7 s over a ragged per-unit representation.

<a id="ew-analysis-materialization-provenance" data-spec-anchor="canonical"></a>
## 5. Provenance of a materialization

Normative.

A writer MAY record a `core.processing_runs` row for a materialization and need not. Where it
records one, the row's parameters MUST carry every transform parameter the output cannot recover.
A singleton analysis catalog table and each analysis instance it catalogs are distinct packet
resources, each recording its own declaration-selected lineage.

<a id="ew-withdrawn-analysis-resources" data-spec-anchor="canonical"></a>
## 6. Withdrawn resources

Four resources proposed in v0.1 are withdrawn. They were specified before anything measured them:

| resource | disposition |
|---|---|
| `analysis.spikes_by_trial` | withdrawn; a table per (event, window) pair, and the alignment is cheap |
| `analysis.trials_wide` | withdrawn; 708 rows in 7.5 ms as a view |
| `analysis.unit_condition_rates` | withdrawn; its columns are a task's shape, not a format's |
| `analysis.good_units` | withdrawn; a filter, not a table |

The columns those tables carried — `condition_id`, `stimulus_id`, `block_id` — describe a particular task rather than the format, and belong in an extension (Part 09).

<a id="ew-analysis-views-and-materializations" data-spec-anchor="canonical"></a>
## 7. Views versus materialized products

Prefer a view where the query prunes and the result is small. Prefer a materialized product where
the physical layout of core cannot serve the access pattern at all, which in practice means a
different sort order or a different clock. View and materialization are realizations of a logical
kind, not kinds themselves.

<a id="ew-analysis-promotion" data-spec-anchor="canonical"></a>
## 8. Promotion into core

Promotion changes the resource declaration's content class through an explicit revision of this
specification or its owning extension registry. It is a schema decision, not an operational
Boolean or a validation-state transition.
