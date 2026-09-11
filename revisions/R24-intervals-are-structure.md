# R24 — Rule Templates, and Intervals as the First One

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | R2 §7.2 (how Tier 2 rules are authored), R18 §4 |
| **Depends on** | R2 (registry format), R18 (unit observation intervals) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Four of the registry's Tier 2 rules are the same three rules written twice.

**`interval_valid` exists on two tables**, differing only in what it projects:

```sql
SELECT session_id, trial_id, start_tick, stop_tick FROM core_trials WHERE stop_tick < start_tick
SELECT session_id, unit_id, interval_index, start_tick, stop_tick
FROM core_unit_observation_intervals WHERE stop_tick < start_tick
```

**R18's three rules mention nothing about units.** Strip the table name and they are
parameterized by `(subject columns, index column, start/stop columns, overlap operator)` and
by nothing else.

Support is about to appear in more places — event streams need observation windows for the
same reason units did, and a session's extent is derived from them. Each new one currently
costs three hand-copied rules that then drift apart independently.

## 2. Why this is not a Tier 1 vocabulary change

The obvious fix is to make `intervals` a structural key in the registry, alongside
`primary_key` and `references`, and generate the three checks as Tier 1. That was the first
draft of this revision. It is the wrong shape, and the reason is a cost asymmetry that is easy
to miss:

| | where it lives | cost to a new implementation |
|---|---|---|
| **Tier 2** | inline in the registry a packet embeds, as SQL | **none** — it executes what it is given |
| **Tier 1** | generated from structure, at validation time | must reproduce every generation rule identically |

A Julia validator today must implement four generation rules to be conformant. Promoting
intervals to Tier 1 would make it seven, permanently, in every implementation that ever
exists — to save four rules in one JSON file.

That trades against the specification's own thesis. R3 §2.1 bans nested Parquet types
specifically so a native reader stays viable in a language without an embedded SQL engine; the
same reasoning applies to a native validator. **The cheap place for a rule is inside the
packet, not inside every implementation.**

Only one party ever needs to know that a table carries intervals: the thing that writes the
rules, which runs once, at build time.

## 3. Rule templates

`registry/rules.json` MAY declare a rule by naming a template and its parameters instead of
writing SQL:

```json
"core.unit_observation_intervals": [
  {
    "use": "interval",
    "start": "start_tick",
    "stop": "stop_tick",
    "partition_of": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
    "index": "interval_index",
    "overlap_op": "<=",
    "overlap_message": "observation windows overlap, which would double-count observed time"
  }
]
```

`registry/build.py` expands invocations while merging `rules.json`, so
`logical_schemas.json` carries plain SQL exactly as it does today. **The registry format does
not change**, `registry.schema.json` does not change, and no validator changes. A packet
written before this revision and one written after are indistinguishable.

An unknown template name is a build failure, on the same terms as `rules.json` naming a table
the registry does not define.

### 3.1 The `interval` template

| Parameter | Required | Meaning |
|---|:---:|---|
| `start`, `stop` | yes | The interval's bounds. |
| `partition_of` | no | Columns identifying whose timeline these rows partition. |
| `index` | with `partition_of` | Ordering column within a subject. |
| `overlap_op` | with `partition_of` | `<=` for closed intervals, `<` for half-open. |
| `overlap_message` | with `partition_of` | What an overlap means for this table. |

It emits `interval_valid` always, and `index_contiguous` and `non_overlapping` when
`partition_of` is given. Identifiers are unchanged, so a validation report's `check` field
keeps its meaning and `fixtures/corpus.py` keeps matching.

`core.trials` declares only `start`/`stop`: a session's trials are not a partition of its
timeline, so no overlap test applies to them.

The template MUST be invoked explicitly. A generator MUST NOT infer it from column names —
Part 06's `analysis.spikes_by_trial` carries `t_bin_start_tick`/`t_bin_stop_tick` and
`core.clock_anchors` carries `t_tick`/`parent_tick`, and neither is an observation window.

## 4. The template reports the primary key, and that fixes two rules

The projection is derived from the table's declared `primary_key` plus the interval bounds,
rather than from whatever each author chose. Expanding the existing rules changed two of them:

| Rule | Reported before | Identifies the row? |
|---|---|:---:|
| `core.unit_observation_intervals.interval_valid` | `session_id, unit_id, interval_index, start_tick, stop_tick` | **no** |
| `core.unit_observation_intervals.non_overlapping` | `clock_id, session_id, unit_id, interval_index` | **no** |
| `core.trials.interval_valid` | `session_id, trial_id, start_tick, stop_tick` | yes |
| `core.unit_observation_intervals.index_contiguous` | the full subject | yes |

Unit identity is contextual on `(session_id, unit_id, sorting_run_id, curation_id)` and never
on `unit_id` alone. Two of these rules reported two of those four columns, so a packet with the
same `unit_id` under two sorting runs would produce a finding that does not say which unit is
wrong. One of them reported `clock_id`, which is not part of identity at all.

Neither was caught by review, by `registry/check.py`, or by the corpus, because all three
check that a rule *fires*, not that its finding is usable. Deriving the projection from the
primary key removes the opportunity.

## 5. Closure had never been decided

`02:281` says only `stop_tick >= start_tick`. Whether an interval is closed `[start, stop]` or
half-open `[start, stop)` is unstated everywhere in the specification, and the overlap test
*is* the closure:

| | `[0, 100]` then `[100, 300]` |
|---|---|
| `overlap_op: "<="` (closed) | **overlap** |
| `overlap_op: "<"` (half-open) | no overlap |

Measured on both forms: windows touching at exactly one tick are flagged under `<=` and not
under `<`.

R18's rule uses `<=`, so observation intervals are closed. That is right — two windows that
touch are one window, and writing them as two double-counts the shared tick in every rate
denominator R18 §5 exists to provide. But it was never written down as a decision, and it
would be wrong for `core.trials`, where back-to-back trials sharing an endpoint is ordinary.

`overlap_op` is a required parameter rather than one defaulting to `<=` for exactly this
reason. A table declaring `partition_of` MUST state it, so the next interval table chooses
rather than inherits.

**This revision does not settle closure for `core.trials`.** `core.trials` declares no
`partition_of` and gets no overlap test, so nothing forces the question. Whether a trial's
`stop_tick` is inclusive belongs to Part 02 and deserves its own argument.

## 6. What changes

| | before | after |
|---|---|---|
| Tier 2 rules in the registry | 31 | 31 |
| hand-written SQL in `rules.json` | 31 | 27 |
| `logical_schemas.json` format | — | unchanged |
| validator implementations affected | — | none |

The rule count is deliberately identical: this generates the same rules, from a shorter source.
Two of them gain columns in their findings (§4). Every `WHERE` clause is byte-identical, and
executing both forms against overlapping, non-contiguous, inverted and endpoint-touching
fixtures flags the same rows.

## 7. What this does not do

- **No new table, no new column, no registry-format change.**
- **Not a general macro language.** One template, for one shape that demonstrably recurs. A
  second template earns its own revision and its own evidence that it recurs — two independent
  instances is the bar this one met.
- **Not inference.** §3.1 forbids deriving the template from column names.
- **Nothing about `core.sessions`.** Session extent depends on support tables existing and is a
  separate question.

## 8. Open

- **Whether `interval_valid` should reject zero-length intervals.** `02:281`'s `>=` permits
  `stop == start`. A zero-length *observation* window observes nothing and is probably a writer
  bug, but that is a claim about observation rather than about intervals, and would belong to
  `partition_of` rather than to the template's base.
