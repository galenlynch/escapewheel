# R81 — Unit IDs Are Assigned by the Packet

| | |
|---|---|
| **Status** | **Accepted** 2026-09-05 |
| **Amends** | `02` (`core.units` and the six tables keyed on it), R53 §2.3 (`unit_id` is carried), R28 §2.1 (`default_electrode_id`) |
| **Depends on** | R53 (an identifier is an integer), R28 (a unit sits on many electrodes), R3 §3.0 (tables do not restate what the data declares), R75 (determinism is logical) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

### 1.1 The sorter's label is stored twice

R53 §2.3 declares `unit_id` **carried** — the sorter's own label. R5 §5 gives that same label a
column of its own, `local_unit_label`, a string no consumer may use as an offset. Both are
populated. On the measured session they hold the same value in **6,781 of 6,781 rows**.

One fact in two columns is what R3 §3.0 forbids. Nothing caught it because R53 introduced integer
identifiers, R5 renamed the local labels, and no check compares the two.

### 1.2 The label repeats across runs

A sorter numbers its units from zero within each run. A run covers one probe. This session
therefore holds **810 distinct `unit_id` values across 6,781 distinct `(unit_id, sorting_run_id)`
pairs over 12 runs** — the carried label recurs about eight times over.

Identity had to grow to match. It is `(session_id, unit_id, sorting_run_id, curation_id)`, and that
composite is repeated by `core.spike_events`, `analysis.spike_events`, `core.unit_electrodes`,
`core.unit_coordinates`, `core.unit_quality_labels` and `core.unit_observation_intervals`, and by
the six references declared into `core.units`.

### 1.3 Four identity columns read slower than one

The same 286,896,563 spike rows were written twice by one writer at one compression and row-group
size, differing only in how a unit is identified:

| | size | twelve unit lookups | one probe's spikes |
|---|---:|---:|---:|
| four-column identity | 819 MB | 142.2 ms | 74.2 ms |
| one numbered `unit_id` | 819 MB | **117.9 ms** | 95.8 ms with the join |

Storage does not move. A repeated low-cardinality column under a clustered sort compresses to
nothing, which is why the four columns looked free. What moves is the read: **1.2x on the question
asked most often**, against 22 ms added to a probe-scoped one that now joins a 6,781-row table.

That join is not a real cost. Measured over an object store, the same shape came out at **1.02 s
with the join and 1.20 s without** — the small side is one 40 KB request, issued while the large
side's footer is being read, and it never reaches the critical path.

### 1.4 A merge leaves no sorter label to carry

Curation merges clusters and splits them. After either, the label a unit carries is the curation's
rather than the sorter's: a merged unit descends from several clusters and can hold at most one of
their labels, and split units need more labels than the cluster they came from had. R53 §2.3
describes `unit_id` as "the sorter's label", and a curated packet is where that description stops
being true.

Two curations of one run then disagree about what label 5 means — which is exactly why identity
grew `curation_id` in §1.2, and exactly what a number the packet assigns does not need.

The packets measured here have not exercised it. `ks_unit_id` equals `original_cluster_id` in
**6,781 of 6,781** units in one session and **4,559 of 4,559** in the other, and no original cluster
is used by more than one unit on a probe. That is what has kept §1.1's duplication invisible: while
every label survives curation unchanged, storing it twice looks like storing it once.

## 2. Decision

### 2.1 A packet numbers its units

`core.units.unit_id` becomes R53 `assigned`: an integer the packet gives each unit, unique within
it. The primary key becomes `["unit_id"]`.

`core.curation_versions` already has that shape — one assigned identifier, with `session_id` and
`sorting_run_id` as ordinary columns — so this is the pattern core already uses rather than a new
one.

`session_id` stays a required column of every unit table. `03` partitions by it and R1's
multi-session extension needs it. It simply leaves the key.

### 2.2 The numbering is deterministic

A writer MUST number units by ascending `(sorting_run_id, curation_id, local_unit_label)`, starting
at zero. Rebuilding a packet from the same inputs then reproduces the same numbers.

R75 §2 makes determinism a logical property rather than a byte-identical one. This is the logical
part: two builds of one session MUST agree about which unit is which.

### 2.3 A unit table carries one identity column

`core.spike_events`, `analysis.spike_events`, `core.unit_electrodes`, `core.unit_coordinates`,
`core.unit_quality_labels` and `core.unit_observation_intervals` carry `unit_id` alone in place of
the composite. Their references into `core.units` become single-column. `session_id` stays on each
for partitioning.

### 2.4 The spike table's sort follows its key

`core.spike_events` is sorted `(session_id, sorting_run_id, curation_id, unit_id, t_tick)` by
`03` §5.3, which names two columns §2.3 removes. Its sort becomes `(session_id, unit_id, t_tick)`
and its primary key the same, so `03`'s override for this table is struck.

The clustering does not change. §2.2 numbers units by ascending
`(sorting_run_id, curation_id, local_unit_label)`, so ascending `unit_id` **is** run-major order:
a probe's spikes stay contiguous and one probe's row groups stay skippable. Measured, that
clustering is worth 7.0x on reading a whole probe — 74.2 ms against 518.5 ms for the same rows in
unit-major order.

What the numbering buys is that the key, the physical order and the uniqueness check now agree on
one column list, which is the outcome R47 §2 reached for `core.intervals` by striking a column that
made them disagree.

`analysis.spike_events` follows: `(session_id, clock_id, time_bucket_tick, unit_id, t_tick)`,
keeping R30 §3.2's time bucket ahead of the unit.

### 2.5 The sorter's label keeps its column

`local_unit_label` is unchanged. R53 §2.3 requires an assigned identifier's owner to carry a
`*_name` recording what the source called the thing, and this is it.

A consumer relating a unit to anything outside the packet MUST use
`(sorting_run_id, local_unit_label)`. It MUST NOT use `unit_id`, which means something only inside
the packet that assigned it.

### 2.6 A second curation adds rows

Where a packet holds two curations of one sorting run, their units receive different numbers.
`core.units` still records each unit's `sorting_run_id` and `curation_id`, so the two are told
apart by columns rather than by key width.

R41's currency machinery is untouched. `core.preferred_runs` keys on the producing run and a unit
still names its run. What changes is that expressing the possibility stops costing three columns on
every spike.

### 2.7 `default_electrode_id` is struck

`core.units.default_electrode_id` names a unit's peak electrode. R28 §2.1 gives that same fact to
`core.unit_electrodes.is_primary`. Two homes for one fact is R3 §3.0's case, and the registry rule
that keeps the two agreeing exists only because there are two.

The column is also unwritable where it sits. A sorter adapter produces `core.units`, the extremum
channel is known only to the waveform adapter, and the column is **null in 6,781 of 6,781 rows** in
the measured packet. `is_primary` is the route that works, and §1.3 removes the argument for
keeping a denormalised copy to avoid a join.

The rule checking that a declared `default_electrode_id` is one of the unit's electrodes is struck
with the column.

## 3. What this does not change

- **No new table and no vocabulary.** One column changes its `identity`, one is struck, six
  references narrow.
- **No capability is lost.** Two sortings or two curations of one recording stay expressible, by
  rows rather than by key width (§2.6).
- **No change to R41 or R44.** Currency keys on the producing run, which a unit still names.
- **No change to the spike table's size or its clustering.** 819 MB either way, and §2.4's sort
  orders the same rows the same way while naming two fewer columns.
- **No lineage column is added here.** Recording which clusters a unit descends from is §5's
  question, not this revision's.

## 4. Consequence

Seven tables change shape. Six declared references narrow to one column. Migration is regeneration,
which is what R53 §5 said of the same class of change when it made every identifier an integer.

A writer gains one step: number the units in §2.2's order before writing any table that references
one. A reader's accessors lose the four-column join key.

`registry/rules.json` loses the `default_electrode_id` consistency rule. Tier 1's uniqueness check
for `core.units` narrows from four columns to one.

## 5. Open

- **Whether `curation_id` belongs on `core.units`.** It is 1:1 with `sorting_run_id` in both
  measured packets — 12 runs, 12 curations, 12 pairs — and exists to distinguish interpretations no
  packet has yet carried. This revision keeps it as a column, which costs 6,781 rows instead of
  286,896,563, and leaves the question to whoever first ships two.
- **Whether `core.units.probe_id` is derivable.** `core.sorting_runs` names a probe too, so
  while a run covers one probe the unit's probe is a join away and R3 §3.0 would strike the
  column. Measured: one run per probe in both packets, 12 and 10. The two stop agreeing when a
  run spans probes or a probe is sorted twice, and `probe_id` is nullable on both tables, so
  neither is currently obliged to answer. Same shape as `curation_id` above and left open for
  the same reason.
- **How merge and split lineage gets recorded.** A merged unit descends from several clusters, so
  R3 §3.0 makes that a child table rather than an `original_cluster_id` column, and no packet has
  one yet. Numbering is what makes such a table cheap when it arrives: keyed on a single `unit_id`
  it is two columns, where the composite identity would have made it five.
- **Whether `is_primary` is complete enough to replace what §2.7 strikes.** It is missing for
  **609 of 6,781 units** in one session. In the other, **183 of 4,505 units** have no
  `core.unit_electrodes` rows at all. That is a writer defect rather than a schema question, and it
  wants fixing whichever column survives.
