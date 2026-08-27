# R5 — Flat Spike Representation

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02`, `03`, `04`, `05`, `06`, `07` |
| **Depends on** | R3 (decision recorded in R3 §4) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R3 §2.1 forbids nested Parquet types. `core.unit_spike_chunks.spike_ticks` is a required
`list<int64>` column, so the rule cannot be adopted without replacing it. R3 §4 records the
decision and defers the schema surgery here.

R3 §7.3 records the measurements (`conformance/parquet-probe/`): with delta encoding applied
to both forms the size difference is 1%, and the chunked table is slower at every access
pattern tested, including single-unit retrieval. Sorted by unit, the flat table is fastest at
single-unit and multi-unit retrieval and within 7% of a tick-sorted layout at range
selection.

This revision performs the surgery. It changes no semantic concept: a spike is still one
timestamp for one unit on one clock.

## 2. `core.spike_events` — canonical

One row per spike. Promoted from "optional or derived" to the sole canonical spike
representation.

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `t_tick` | int64 | yes | Spike tick, signed (R3 §2.1). |
| `clock_id` | string | yes | Clock for `t_tick`. |
| `amplitude` | float32 | no | Spike amplitude if the sorter reports one. |
| `metadata` | json_string | no | Additional metadata. |

**Primary key:** `(session_id, unit_id, sorting_run_id, curation_id, t_tick)`.

`02` declares no primary key for this table. One is required here because the registry (R2)
needs it and because uniqueness is a meaningful check: two spikes from one unit at the same
tick in one sorting/curation context is a defect, not a legitimate observation.

References:

- `session_id` -> `core.sessions.session_id`
- `clock_id` -> `core.clocks.clock_id`
- `(session_id, unit_id, sorting_run_id, curation_id)` -> `core.units`

Physical ordering MUST follow `03:120` — `session_id, sorting_run_id, curation_id, unit_id,
t_tick` — which R3 §7.3 measures as the best all-around layout.

### 2.1 `trial_id` is withdrawn from core

`02` defines an optional `trial_id` on `core.spike_events`, "if trial assignment has been
materialized."

**Resolution:** strike it. Trial assignment is a derived alignment that `06` already owns
through `analysis.spikes_by_trial`, which carries it along with `t_rel_tick` and
`alignment_event` — information a bare `trial_id` cannot express. A column that is populated
in some packets and not others also complicates every query and validation rule that touches
it, for no access the analysis materialization does not provide.

This applies R3 §3.0: the duplication must buy access otherwise unavailable, and here the
analysis layer already provides it.

## 3. `core.unit_spike_chunks` — withdrawn

The table is removed in its entirety, with its columns `chunk_index`, `t_min_tick`,
`t_max_tick`, `n_spikes`, and `spike_ticks`, and its four chunk-specific validation rules in
`02`:

```text
- spike_ticks MUST be sorted ascending within each row
- n_spikes MUST equal the length of spike_ticks
- t_min_tick and t_max_tick MUST bound all ticks in spike_ticks
- chunks for one unit SHOULD be non-overlapping and ordered by chunk_index
```

None applies to a flat table.

`02`'s "Spike representation policy" section is struck. With one canonical representation
there is no declaration to make, no equivalence to validate, and no per-`(session_id,
sorting_run_id, curation_id)` choice to record.

## 4. `core.units` — summary columns

`core.units` SHOULD gain:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `n_spikes` | int64 | no | Total spikes for this unit in this sorting/curation context. |
| `first_spike_tick` | int64 | no | Lowest `t_tick` for this unit. |
| `last_spike_tick` | int64 | no | Highest `t_tick` for this unit. |

These are derived from `core.spike_events` and so must satisfy R3 §3.0's test, which they
do: they turn a 9M-row aggregate into a 500-row scan, recovering the one pattern the chunked
table won. Present-and-wrong is worse than absent, so all three MUST be validated when
present:

```sql
-- core.units.spike_summary_consistent  (error)
SELECT u.session_id, u.unit_id
FROM core_units u
LEFT JOIN (
  SELECT session_id, unit_id, sorting_run_id, curation_id,
         COUNT(*) AS n, MIN(t_tick) AS lo, MAX(t_tick) AS hi
  FROM core_spike_events
  GROUP BY session_id, unit_id, sorting_run_id, curation_id
) s USING (session_id, unit_id, sorting_run_id, curation_id)
WHERE (u.n_spikes         IS NOT NULL AND u.n_spikes         IS DISTINCT FROM s.n)
   OR (u.first_spike_tick IS NOT NULL AND u.first_spike_tick IS DISTINCT FROM s.lo)
   OR (u.last_spike_tick  IS NOT NULL AND u.last_spike_tick  IS DISTINCT FROM s.hi)
```

A unit with no spikes has `n_spikes = 0` and null tick bounds.

## 5. `*_index` renamed to `*_label`

R3 §6 classifies three columns as opaque source-provenance values with undefined base, and
proposes renaming them here. Applied:

| `02` name | Becomes |
|---|---|
| `core.electrodes.local_electrode_index` | `local_electrode_label` |
| `core.electrodes.local_channel_index` | `local_channel_label` |
| `core.units.local_unit_index` | `local_unit_label` |

Type is unchanged (`int64`, optional). The rename removes a real hazard: `_index` invites
readers to use these as offsets into arrays or tables, when their base is whatever the
acquisition or sorting software used and some systems number channels from 1.

After this, every remaining `*_index` column in the specification is a 0-based structural
offset, so R3 §6's rule becomes uniform rather than a classification readers must remember:
`core.array_channels.channel_index`, `core.array_dimensions.axis_index`, and
`core.media_frames.frame_index`.

## 6. Downstream deletions

| Document | Struck |
|---|---|
| `02` | Spike representation policy section; `core.unit_spike_chunks` schema; `core.spike_events.trial_id` |
| `03` | `unit_spike_chunks.parquet` from the layout; its recommended ordering; the partitioned-dataset example keyed on it |
| `04` | The `canonical_representations` block, its required-declaration rule, and the partitioned-table example built on `core.unit_spike_chunks` |
| `05` | "Convert NWB units/spike_times to `core.unit_spike_chunks`"; the "explode chunks into `analysis.spike_events`" materialization; `core.unit_spike_chunks` in the minimum acceptance criteria, replaced by `core.spike_events` |
| `06` | `analysis.spike_events` in its entirety — it existed only as the flat materialization of chunks, and is now the canonical core table |
| `07` | Round-trip "spike chunk -> spike event -> chunk equivalence" from the testing strategy; `pkt.materialize("analysis.spike_events")` from the API examples; `spike_chunks` from the minimum API |
| `08` | The `core.unit_spike_chunks` example rows and manifest entry; the chunk-count SQL example |

The `canonical_representations` block in `04` exists solely to reconcile two canonical spike
forms. With one canonical form it has no function and is removed entirely.

## 7. Validation rules

Replacing the chunk rules struck in §3. Under the rules-as-data model (R2), each returns
offending rows; empty is a pass.

```sql
-- core.spike_events.ticks_sorted_within_unit  (warning)
-- Physical ordering per 03:120 is a performance property, not correctness.
SELECT session_id, unit_id, t_tick FROM (
  SELECT *, LAG(t_tick) OVER (
    PARTITION BY session_id, sorting_run_id, curation_id, unit_id ORDER BY (SELECT NULL)
  ) AS prev
  FROM core_spike_events
) WHERE prev IS NOT NULL AND t_tick < prev
```

```sql
-- core.spike_events.clock_resolves  (error)
SELECT DISTINCT s.clock_id FROM core_spike_events s
LEFT JOIN core_clocks c USING (clock_id) WHERE c.clock_id IS NULL
```

```sql
-- core.spike_events.unit_resolves  (error)
SELECT DISTINCT s.session_id, s.unit_id, s.sorting_run_id, s.curation_id
FROM core_spike_events s
LEFT JOIN core_units u USING (session_id, unit_id, sorting_run_id, curation_id)
WHERE u.unit_id IS NULL
```

Primary-key uniqueness and required-column presence are generated from the registry
structure and are not written by hand.

## 8. Open

- Whether bursty real firing or AIND-scale sessions change R3 §7.3's ranking. Re-run
  `conformance/parquet-probe/access.py` against a real session before treating the layout as
  settled at scale. Should a chunked form ever earn its place it belongs in `analysis`, with
  declared lineage per `06`, never in `core`.
