# R11 — Column Definitions

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02_core_logical_schemas.md` |
| **Depends on** | R8 (open-vocabulary pattern) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

An audit of all 178 registry columns against their `02` descriptions found four defects that
a writer or reader could act on wrongly. They are unrelated except in kind: each is a column
whose stated definition does not determine what a conforming value means.

R8 addressed vocabularies declared with "etc."; these are columns whose definition is absent,
self-referential, or refers to something the specification does not define.

## 2. `core.spike_events.amplitude` — units

`02` gives the column as `float32`, "Spike amplitude if available", with no unit. Amplitudes
are consequently not comparable between packets, or interpretable within one.

The unit cannot be fixed by this specification, because producers legitimately emit either
form. SpikeInterface 0.104.8 carries `return_in_uV` on the `SortingAnalyzer` — not on the
amplitude computation — so the choice between microvolts and raw ADC counts is a property of
the whole sorting context, and `return_in_uV=False` yields counts that are incomparable
across probes.

`core.sorting_runs` therefore gains:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `amplitude_unit` | string | no | Unit of `core.spike_events.amplitude` for this run, e.g. `uV`, `adc`. |

`core.spike_events.amplitude` is unchanged. Where any spike in a run carries an amplitude,
that run MUST declare `amplitude_unit`:

```sql
-- core.sorting_runs.amplitude_unit_declared  (error)
SELECT DISTINCT s.sorting_run_id
FROM core_spike_events s JOIN core_sorting_runs r USING (sorting_run_id)
WHERE s.amplitude IS NOT NULL AND r.amplitude_unit IS NULL
```

This is the pattern `02` already applies to arrays through `core.array_assets.unit`. A
`conversion` factor recovering microvolts from counts is not added; knowing which form is
present is the load-bearing part, and a gain can follow when an importer needs one.

`amplitude_unit` is an open vocabulary on R8 §4's terms.

## 3. `core.units.quality_label` — closed vocabulary

`02` gives the column as "Quality label" with no vocabulary, while `06`'s
`analysis.good_units` depends on interpreting it, through `quality_policy_id` and `is_good`.

Existing tools agree on the categories and disagree on the spelling. SpikeInterface's own
auto-labelers are not consistent with each other:

```text
bombcell_label_units            good, mua, noise
threshold_metrics_label_units   good, noise
unitrefine_label_units          sua,  mua, noise
Phy cluster_group.tsv           good, mua, noise
```

Three categories recur — a well-isolated single unit, multi-unit activity, and noise — and
only `noise` is spelled consistently. Closing the vocabulary therefore selects a spelling for
an existing taxonomy rather than imposing a new one.

Permitted values:

```text
sua     single unit, well isolated
mua     multi-unit activity
noise   noise cluster
```

A null records that no quality judgment was made. A validator MUST reject any other value.

`sua` is chosen over the more widespread `good` because `good` collides with `06`: a
`quality_label` of `good` alongside `analysis.good_units.is_good`, derived independently from
a `quality_policy_id`, gives "is this unit good?" two answers that need not agree. `sua` and
`mua` are also parallel categories, where `good` and `mua` mix a judgment with a category.

An importer MUST map source labels onto this set — `good` becomes `sua` for Phy and bombcell
output. Because the sources disagree with one another, an importer must make this decision
regardless of what this specification says.

Because the mapping is lossy, an importer SHOULD record the source label in
`core.units.metadata` — for example `{"source_quality_label": "good", "source": "phy"}` — so
that the mapping is auditable and can be re-derived if this vocabulary changes.

Finer gradations belong in `core.units.metadata` as well, or in a namespaced extension table
(`09` §5) where a lab wants them typed and validated. Promotion into core is available for a
field that proves broadly necessary, on `02:66` and `09` §8's terms.

With the set closed, `analysis.good_units` becomes portable: a policy expressible as
`quality_label = 'sua'` means the same thing in packets from different sources, which it did
not before.

## 4. `core.events.event_type` — declared open, with reserved values

`02` gives the column as "Event type" — required, the primary filter column for the events
table, and with no guidance at all. `01` lists six examples that never reach the schema.

Declared open on R8 §4's terms, with `01`'s examples reserved:

```text
stimulus_onset     stimulus presentation began
reward             reward delivered
lick               lick detected
threshold_crossing a monitored signal crossed a declared threshold
ttl_edge           a TTL line changed state
sync_pulse         a synchronization pulse
```

A validator MUST NOT reject an unrecognized value. A value outside the reserved set MUST NOT
be used for an event the reserved set describes.

Snake case is used because `02` requires it of column names and nothing else in the
specification uses another convention for enumerated values.

## 5. `core.sessions.session_start_time` — dangling exception

`02` describes the column as "Session start time if known; if unknown use explicit null only
in non-strict test packets."

Neither "non-strict" nor "test packet" is defined anywhere in the specification. The clause
carves out an exception referring to a conformance mode that does not exist, and it
contradicts the column's own requirement level: `02` marks it required, `09` §4.2 lists it as
MUST-include, and a required column admits no nulls.

**Resolution:** strike the clause. The column is required and non-null, as `02` and `09`
already state jointly.

No strictness mechanism is introduced. Adding conformance modes to accommodate one column
would be a substantial addition on no evidence; if a real import encounters sessions whose
start time is unrecoverable, that is evidence for a change and this decision is revisited.

## 6. `core.events.trial_id` — withdrawn

`02` describes the column as "Trial if known/materialized". Those are different facts: an
authored trial membership known at acquisition, and a derived range join against
`core.trials`. A consumer reading a populated value cannot tell which it has, so the column
does not determine what a conforming value means — the defect this revision addresses
throughout.

**Resolution:** strike the column, and its `(session_id, trial_id) -> core.trials`
reference, applying R5 §2.1's reasoning to the identically-worded column it left in place.
Derived assignment belongs in `06`'s `analysis.spikes_by_trial`, which carries `trial_id`
alongside `t_rel_tick` and `alignment_event`.

An event whose trial membership is genuinely authored — a reward attributed to trial 7 by
task logic rather than by timing — can record it in `payload` until a column with
unambiguous semantics is warranted. Adding one later is additive and breaks no packet, on
the grounds R3 §3.1 records; a column that may mean either thing cannot be narrowed later
without invalidating packets already written.
