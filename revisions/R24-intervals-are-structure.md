# R24 — Intervals Are Structure

| | |
|---|---|
| **Status** | **Proposed** 2026-08-27 |
| **Amends** | R2 §7.1 (what Tier 1 generates), R18 §4, `02` `core.trials` |
| **Depends on** | R2 (registry format), R18 (unit observation intervals) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R2 §7.1 draws the Tier 1 / Tier 2 line at *what structure implies*:

> Tier 1 is generated from structure: required-column non-null, primary-key uniqueness,
> foreign-key anti-joins, closed-vocabulary membership.

Intervals are structure and are not on that list, so every interval rule is hand-written.
Two consequences are already visible in the registry.

**`interval_valid` exists twice.** `core.trials` and `core.unit_observation_intervals` each
carry a hand-written rule whose SQL differs only in the columns projected:

```sql
SELECT session_id, trial_id FROM core_trials WHERE stop_tick < start_tick
SELECT session_id, unit_id, interval_index, start_tick, stop_tick
FROM core_unit_observation_intervals WHERE stop_tick < start_tick
```

Two copies of one rule is one copy too many; a third table makes it three.

**R18's rules mention nothing about units.** Strip the table name and they are parameterized
by `(subject columns, index column, start/stop columns)` and by nothing else:

```sql
… GROUP BY <subject> HAVING MAX(<index>) <> COUNT(*) - 1 OR MIN(<index>) <> 0
… LAG(<stop>) OVER (PARTITION BY <subject> ORDER BY <index>) …
```

That is the signature of a rule that should be generated. Tier 2 exists for what structure
*cannot* imply (R2 §7.2); these are structure, written out by hand because the registry had
no vocabulary to declare them in.

The immediate motivation is that support is about to appear in more places — event streams
need it for the same reason units did, and a session's extent is derived from it. Adding each
one currently costs a table plus three hand-copied rules that can drift apart.

## 2. Declaration

A table MAY carry an `intervals` key:

```json
"core.unit_observation_intervals": {
  "columns": [...],
  "primary_key": [...],
  "intervals": {
    "start": "start_tick",
    "stop": "stop_tick",
    "closure": "closed",
    "partition_of": {
      "subject": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
      "index": "interval_index"
    }
  }
}
```

It decomposes into two independent pieces:

- **`start` / `stop` / `closure`** — this table's rows are intervals. `core.trials` declares
  only this.
- **`partition_of`** — these rows partition each subject's timeline, ordered by `index`.
  Observation tables add this; `core.trials` does not, because two trials may legitimately
  interleave with anything else and a session's trials are not a partition of its timeline.

`intervals` MUST be declared explicitly. A generator MUST NOT infer it from column names:
`06`'s `analysis.spikes_by_trial` carries `t_bin_start_tick`/`t_bin_stop_tick` and
`core.clock_anchors` carries `t_tick`/`parent_tick`, and neither is a subject's observation
window. Naming conventions are for readers, not for generators.

`registry.schema.json` gains `intervals` as an optional per-table key. This is a change to the
registry's **vocabulary**, not only its content, which is why it is a revision of its own.

## 3. What is generated

| Check | Emitted when | Meaning |
|---|---|---|
| `<resource>.interval_valid` | `intervals` present | `stop` precedes `start` |
| `<resource>.index_contiguous` | `partition_of` present | `index` is not contiguous from 0 |
| `<resource>.non_overlapping` | `partition_of` present | a subject's windows overlap |

All three keep their current identifiers, so a validation report's `check` field does not
change meaning and existing expectations in `fixtures/corpus.py` keep matching.

## 4. Closure has to be pinned, and it never was

`02:281` says only `stop_tick >= start_tick`. Whether an interval is closed `[start, stop]` or
half-open `[start, stop)` is unstated everywhere in the specification.

That gap is invisible while every interval rule is hand-written and becomes unavoidable the
moment one is generated, because the overlap test depends on it:

| | closed | half-open |
|---|---|---|
| overlap test | `start <= prev_stop` | `start < prev_stop` |
| `[0, 100]` then `[100, 300]` | **overlap** | no overlap |

Measured on both forms (§5): windows touching at exactly one tick are flagged under closed
semantics and not under half-open.

R18's rule uses `<=`, so `core.unit_observation_intervals` is **closed** — two windows may not
share an endpoint. That is right for observation: windows that touch are one window, and
writing them as two would double-count the shared tick in any rate denominator.

It would be wrong for `core.trials`, where back-to-back trials sharing an endpoint is ordinary.
`core.trials` declares no `partition_of` and so gets no overlap test, which is why the conflict
has not surfaced — but a future interval table will have to choose, and the registry should
make it choose explicitly rather than inherit R18's accident.

Hence `closure`, with `closed` the default because it is what the one existing rule already
means.

**This revision does not settle closure for `core.trials`.** It only requires that a table
declaring `partition_of` state its closure. Whether a trial's `stop_tick` is inclusive is a
question for `02`, and answering it in passing here would be exactly the kind of silent
convention this section objects to.

## 5. Evidence

A generator built to §2 and run against the registry emits SQL that agrees with the
hand-written rules on which subjects it flags. Fixture: five subjects, one clean, one with
overlapping windows, one with a non-contiguous index, one with an inverted interval, and one
whose windows touch at a single tick.

| Check | hand-written rows | generated rows | subjects flagged | agree |
|---|---|---|---|---|
| `interval_valid` | 1 | 1 | `u4` | yes |
| `index_contiguous` | 1 | 1 | `u3` | yes |
| `non_overlapping` | 2 | 2 | `u2`, `u5` | yes |

The projected column lists differ — the hand-written rules select what their author found
useful — and the offending rows are the same. A validator's finding carries the rows, so a
generated projection SHOULD include the subject and the index, which is what identifies the
offending window.

## 6. What moves

| | before | after |
|---|---|---|
| Tier 2 rules | 31 | 27 |
| generated Tier 1 checks | 179 | 183 |
| hand-written interval rules | 4 | 0 |

`core.trials.interval_valid` and R18's three rules leave `rules.json` and become generated.
The next interval table costs a declaration.

## 7. What this does not do

- **No new table, no new column.** Registry content is unchanged; only how four of its rules
  come to exist changes.
- **No inference.** §2 forbids deriving `intervals` from column names.
- **Not a general constraint language.** This adds one declaration for one recurring shape,
  the way `primary_key` and `references` already do. A rule that is not an interval rule stays
  Tier 2. If a second such shape appears, it earns its own revision and its own argument that
  it recurs — two instances is the bar this one met.
- **Nothing about `core.sessions`.** Session extent depends on support tables existing and is
  a separate question.

## 8. Open

- **Whether `core.trials` should declare `closure`.** It gets no overlap test either way, so
  the declaration would document intent without being enforced. Documenting an unenforced
  convention in a machine-readable file invites a reader to rely on it; leaving it out invites
  the next author to guess. Neither is obviously right.
- **Whether `interval_valid` should be `stop < start` or `stop <= start`.** Zero-length
  intervals are legal under `02:281`'s `>=`. A zero-length *observation* window observes
  nothing and is arguably a writer bug, but that is a claim about observation, not intervals,
  and would belong to `partition_of` rather than to `intervals`.
