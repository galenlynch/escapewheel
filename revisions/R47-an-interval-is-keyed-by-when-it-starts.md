# R47 — An Interval Is Keyed by When It Starts

| | |
|---|---|
| **Status** | **Proposed** 2026-09-02 |
| **Amends** | R18 §2 (`core.unit_observation_intervals`), R25 §2 (`core.event_stream_observation_intervals`), R38 §2.1 (`core.clock_observation_intervals`), R24 §3 (the `interval` template) |
| **Depends on** | R7 (every table declares a key), R10 (sort by the primary key), R24 (rule templates), R45 (a tick interval is closed) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

The three observation-interval tables each carry an `interval_index`, described as *"0-based
position in this clock's interval sequence"* and forming the last component of the primary key.

**It is `0` in every row of every packet** — 123 rows across the corpus, no other value — and the
writer emits the literal `0` at all three sites. Nothing reads it: the reader resolves windows
from `start_tick` and `stop_tick`, and the validator touches it only through the two rules R24's
template generates for it.

R3 §3.0 is the test it fails. *Duplication must buy otherwise-unavailable access.* The column
keys the table and orders it, and `start_tick` does both — uniquely, by construction, since
`non_overlapping` requires a start to exceed the previous stop and `interval_valid` requires a
stop to be at least its start, so two rows of one partition cannot share a `start_tick`.

### 1.1 And it carries an obligation nobody wrote down

The overlap rule reads:

```sql
LAG(stop_tick) OVER (PARTITION BY session_id, clock_id ORDER BY interval_index) AS prev_stop
... WHERE start_tick <= prev_stop
```

Comparing consecutive-by-*index* pairs is a correct overlap test **only if index order is time
order.** Nothing requires it. `core.clock_anchors` states the equivalent obligation explicitly —
its `monotonic` rule asserts `t_tick` and `parent_tick` both increase with `anchor_index` — and
these three tables have no such rule.

Measured, the consequence is a false positive rather than a miss. The rule is sound: if every
consecutive pair satisfies `start > prev_stop` then starts and stops increase together and the
intervals are globally disjoint, so a real overlap is always caught. But intervals that are
disjoint and merely *numbered out of time order* are reported as overlapping:

| rows, by index | actually overlapping | rule fires |
|---|:---:|:---:|
| `(0,100) (200,300) (400,500)` | no | no |
| `(0,100) (50,150)` | yes | yes |
| `(400,500) (200,300) (0,100)` | **no** | **yes** |
| `(0,100) (400,500) (200,300)` | **no** | **yes** |

The message such a packet receives is *"observation windows overlap, which would double-count
observation"*, about windows that do not overlap. The rule is really enforcing an ordering
requirement while describing an overlap.

**The requirement is real and should not be documented — it should be made unnecessary.**

## 2. Decision

### 2.1 `interval_index` is struck

**Strike** `interval_index` from `core.clock_observation_intervals` (R38 §2.1),
`core.unit_observation_intervals` (R18 §2) and `core.event_stream_observation_intervals`
(R25 §2).

### 2.2 The primary key becomes the partition plus `start_tick`

| table | primary key |
|---|---|
| `core.clock_observation_intervals` | `(session_id, clock_id, start_tick)` |
| `core.unit_observation_intervals` | `(session_id, unit_id, sorting_run_id, curation_id, start_tick)` |
| `core.event_stream_observation_intervals` | `(event_stream_id, start_tick)` |

Each is the same width as the key it replaces. Uniqueness is not an assumption: §1 shows two rows
of one partition cannot share a `start_tick` while `interval_valid` and `non_overlapping` hold.

R10 §2 sorts a table by its primary key, so the file is now in time order as well — the key, the
physical order and the overlap check all agree on one column, where previously the check's
correctness depended on a convention the other two did not enforce.

### 2.3 The `interval` template's index becomes optional

**Amend R24 §3.** The `interval` template's `index` parameter becomes optional. When it is
absent:

- the generated rule orders by `start` rather than by `index`;
- **no `index_contiguous` rule is generated**, there being no index to be contiguous.

The three tables above invoke it without an `index`. `core.clock_anchors` is unaffected and
continues to pass one.

The `non_overlapping` rule becomes:

```sql
SELECT <key>, start_tick, stop_tick FROM (
  SELECT *, LAG(stop_tick) OVER (PARTITION BY <partition> ORDER BY start_tick) AS prev_stop
  FROM <table>)
WHERE prev_stop IS NOT NULL AND start_tick <= prev_stop
```

which is an overlap test and nothing else. A packet whose rows arrive in any order gets the same
verdict, because the order is computed rather than stored.

### 2.4 `core.clock_anchors` keeps `anchor_index`

The same redundancy argument reaches it — the reader sorts anchors by `t_tick` and ignores the
index — and it is **not** applied, for three reasons:

- It holds real values: 754,222 rows of genuine sequence, against a constant `0`.
- Its obligation is **stated**, by the `monotonic` rule, rather than smuggled into an `ORDER BY`.
- A position in an anchor sequence is a concept the format uses: R13 §3's interpolation happens
  *between anchor i and i+1*, so consecutiveness is operational and not merely a validation
  device.

Changing a 754,222-row table for no operational gain is not worth it. This revision is about a
column that is always zero, not about indices in general.

## 3. Evidence

Every packet on disk:

| table | rows | distinct `interval_index` |
|---|---:|---|
| `core.clock_observation_intervals` | 65 | `[0]` |
| `core.event_stream_observation_intervals` | 58 | `[0]` |
| `core.unit_observation_intervals` | **0** | table absent from every packet |
| *(for contrast)* `core.clock_anchors` | 754,222 | `[0, 1, 2, 3, 4, 5, …]` |

`core.unit_observation_intervals` has never been written. R18 designed it expecting one window
per unit — 6,781 rows — and R38 moved observation to the clock, so a unit inherits and refines
only where something measured drift. Nothing has.

The rekeyed form was checked against the cases that matter, including the ones the current design
handles worst:

- **A stream that stops and restarts twice** — three rows, key unique, non-overlapping, 3,000
  observed ticks summed correctly.
- **A unit that drifts out and back, and the same `unit_id` under a second sorting run** — key
  unique, the two sortings kept apart, per-unit denominators correct.
- **A genuine overlap with rows inserted in any order** — caught, because the order is computed.
- **Disjoint intervals numbered out of order** — cannot arise; there is no numbering left.

## 4. Cost

123 rows in two tables, and a third that has never been written. `registry_version` is held at
0.1.0 while the schema is unreleased, so this is a rebuild rather than an R32 amendment — a cost
that rises once a release has been cut, which is why it is worth doing now rather than recording
as a known wart.

Three rules are removed (`index_contiguous` on each table) and none is added.

## 5. What this does not do

- **No change to `core.clock_anchors`.** §2.4.
- **No change to what an observation window means.** R38's inheritance, R45's closure and the
  denominator arithmetic are untouched; only the key changes.
- **No new mechanism.** The `interval` template already partitions and orders; §2.3 removes a
  required parameter rather than adding one.
- **No opinion on `core.trials`.** It invokes the template without `partition_of` and gets only
  `interval_valid`; R45 §2.4 declined an overlap test and that stands.

## 6. Open

- **Whether `analysis.array_dimensions` and `core.array_dimensions` should follow.** `axis_index`
  is also a position in a sequence, but it is a *structural* index — it addresses an axis of the
  stored array (R3 §6), and the array's axis order is what it names. It is not redundant with
  anything and is out of scope here; recorded so the next reader does not have to re-derive that
  it was considered.
- **Whether a column that is constant across every packet should be detectable.** `interval_index`
  was found by asking what values the corpus actually contains. A sweep reporting columns with one
  distinct value across the corpus would have found it, and would also have found
  `core.trials.stimulus_id`, which is null everywhere (`TODO.md` §7). Neither is a rule — a
  constant column can be legitimate — but as a report it is evidence a human can act on.
