# R99 — A Packet Records Its Clock Alignment in Columns

| | |
|---|---|
| **Status** | **Accepted** 2026-09-08 |
| **Amends** | Part 02 §5.2 (`core.processing_runs.parameters`), `core.sessions`, `core.clocks`; adds `core.clock_phase_steps` |
| **Depends on** | R37 (bounding alignment by error), R40 (a tolerance that gates on quality), R56 (a column declares its context), R88 (a session-scoped table names its session), R98 (a clock declares when it was observing) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

Three facts decide how a consumer reads a packet's clocks: how far the writer mapped beyond its
anchors, which terminal anchors it withheld, and where a parent clock's phase stepped. All three
are recorded today inside `core.processing_runs.parameters`, an optional `json_string` that Part 02
describes in one word: *Parameters.*

They do not belong there. A consumer that does not parse that string maps at a different bound and
disagrees with the writer about which rows have a time, so the facts are required to interpret the
data — which Part 02 §8.6 puts in a column and never in a key. This part moves the three that are, and
leaves in `parameters` the ones that are not.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25).

## 2. Background

Informative.

### 2.1 A reader must parse JSON to place a tick

R37 §3.3 lets a writer map a clock further than R27 §5.3's one median anchor interval once it has
measured the estimator at the intended distance. It does not say where that measurement goes, and
no other clause does: R37 §4 places the **withheld-anchor** record in `parameters` and says nothing
about the bound, and R40 §2.3 places a **dropped-row** count there on R37 §4's authority.

The reference reader reads one anyway. `escapewheel_reader.clocks.declared_bound` parses every
run's `parameters`, takes `alignment_bound.used`, and maps at the widest value any run declared;
where no run declares one it maps at `BOUND = 1.0`. The name appears in no part of the
specification and in no revision — the writer chose it — and the reader's own docstring attributes
it to R37 §4, which placed a different record.

Part 02 §5.2 confines a `json_string` to an optional column so that a conforming reader satisfies
every required column without a JSON parser. That guarantee is about columns and this breaks it
anyway: a reader that skips `parameters` does not merely learn less, it maps at one median anchor
interval where the writer mapped at more and refuses to place ticks the writer placed. Because the
key is missing rather than malformed, it refuses them silently.

### 2.2 The record is shaped like the schema the format forbids

One entry of each, from `ecephys_776259`:

```json
"withheld_anchors": {
  "experiment1.Neuropix-PXI-100.45883-1.samples":
    {"anchors": ["first"], "first": 4.9, "last": -1.0, "n_withheld": 1, "threshold": 4.0}},
"phase_discontinuities": {
  "experiment1.Neuropix-PXI-100.45883-1.samples":
    [{"anchor_intervals": 2, "parent_tick": 361815998198, "seconds": -0.001504, "t_tick": 67068844}]}
```

Three things the format forbids elsewhere, in eight lines.

**It is nested.** Part 02 §5.2 forbids `list`, `struct` and `map`, and a repeated value becomes a child
table. `withheld_anchors` is a map to an object and `phase_discontinuities` a map to a *list* of
objects. R3 §3.4 already converted `core.clocks.transform_to_parent` from `struct/map/json` to
typed columns, which is this subject decided once.

**It joins on a name.** The keys match `core.clocks.clock_name` in **12 of 12** entries and
`clock_id` in **0 of 12**. Every identifier has been an `int32` since R53 §2.1, so this record can
reach `core.clocks` only through a name — which R86 §2.2 refuses as a discriminator, and which no
declared reference can express, so Tier 1 generates nothing for it.

**It carries two coordinates and cannot say what clocks they are on.** `t_tick` and `parent_tick`
are on a clock and its parent. That is R56 §1's motivating defect exactly — `core.clock_anchors`
held the same pair with the difference recorded in a description — and R56 §2.3 fixed it with
`clock_from`, a declaration a JSON string cannot carry.

### 2.3 What the two packets record

| key | `ecephys_776259` | `ecephys_786867` |
|---|---|---|
| `alignment_bound` | absent | absent |
| `withheld_anchors` | 12 clocks, 10 anchors withheld | 10 clocks, 5 withheld |
| `phase_discontinuities` | 12 clocks, 24 steps | absent |

Each packet holds one `import` run among 26 and 22 `core.processing_runs` rows, and every sorting
and curation row carries no parameters at all. The blob is 9,479 and 7,100 bytes.

`alignment_bound` is absent from both, and not because the sessions did not need one. The writer
measures how far it must reach by comparing each clock's anchors against that clock's observation
window, and **no clock in either packet has both**: `ecephys_776259` declares 13 clocks, 12 with
anchors and 1 with a window, and `ecephys_786867` declares 11, 10 and 1. The window in each case
belongs to the reference clock, which has no anchors of its own. So the comparison runs over an
empty intersection, the distance needed comes out as zero, and the writer records the default
without measuring anything.

The fact that most changes how a packet is read is therefore one that no packet has yet stated,
and that no writer could state while a clock could decline to say when it was observing. R98 §3.1
closed that, so a packet built after it is the first that can measure a bound at all. Whether
either session needs a wider one is still unknown, and answerable only by the rebuild.

## 3. Decision

### 3.1 `core.sessions.alignment_bound`

`core.sessions` gains `alignment_bound`, `float64` nullable, role `data`, unit `median anchor
intervals`. It holds the bound the writer mapped at, and a writer establishing one wider than
R27 §5.3's default **MUST** record it there.

A consumer reading a session whose `alignment_bound` is null **MUST** map at R27 §5.3's default of
one median anchor interval. A null is a fact and not a defect: the writer stayed within the default
and had nothing to add.

The column is on the session rather than on the run because the bound is a property of the times
the packet states, as R39 §2.1 made `t_zero_tick` a property of the session for the same reason.
One session declares one bound, so R37's record needs no rule about which of several runs wins.

A value below one is meaningless, since the default already reaches that far. One Tier 2 rule
refuses it.

### 3.2 `core.clocks.withheld_first_anchor` and `withheld_last_anchor`

`core.clocks` gains two `bool` nullable columns of role `data`, recording the outcome of R37
§3.2's terminal-anchor test on that clock. A writer running the test **MUST** record both.

The three states are the point. **Null** means the test did not run on this clock. **False** means
it ran and kept that terminal. **True** means it ran and withheld it. R40 §2.3 requires a writer to
say so when it withheld nothing, because a silent zero and an untested clock are different facts,
and the presence rule carries that distinction structurally instead of leaving it to a MUST no rule
can observe.

A clock whose anchors the packet does not carry cannot have been tested, so a clock with no row in
`core.clock_anchors` **MUST NOT** declare either column. One Tier 2 rule checks it.

The count R37 §3.2 requires is these two columns and not a third: a terminal is first or last,
`withheld_first_anchor` and `withheld_last_anchor` give the count by addition, and a stored count
beside them would be one fact in two places (R3 §3.0).

### 3.3 `core.clock_phase_steps`

A step in a clock's alignment to its parent is one row of a new table, since a clock may have
several and a repeated value is a child table (R3 §3.0).

| column | type | presence | role | |
|---|---|---|---|---|
| `session_id` | `int32` | required | `identifier` | assigned; references `core.sessions` (R88 §2.1) |
| `clock_id` | `int32` | required | `identifier` | assigned; references `core.clocks`, the clock that stepped |
| `t_tick` | `int64` | required | `coordinate` | where the step is, on `clock_id` |
| `parent_tick` | `int64` | required | `coordinate` | the same instant on the parent; `clock_from` is `core.clocks.parent_clock_id` (R56 §2.3) |
| `shift_seconds` | `float64` | required | `data` | how far the parent's phase moved, unit `s`; signed |
| `anchor_interval_span` | `int32` | required | `data` | how many consecutive anchor intervals the step spans, unit `anchor intervals`; not `anchor_intervals`, since R50 §3 refuses a plural integer and `core.units.n_spikes` is the exception that shape already needed |

The primary key is `session_id, clock_id, t_tick`. A step is located by where it is, the shape
R47 §2.2 gives `core.clock_observation_intervals` — partition plus the coordinate.

A writer detecting a step **MUST** record it. A step is reported and never corrected: R13's map is
exact at every anchor, so it carries the step faithfully rather than smoothing it away, and
correcting it would need to know whether the step also moved the devices timestamped on that
parent, which the packet does not record.

A step is a fact about a clock's alignment **to a parent**, so a clock whose `parent_clock_id` is
null **MUST NOT** have rows here. One Tier 2 rule checks it.

### 3.4 What stays in `parameters`

`parameters` keeps the evidence behind each of these decisions, and nothing this part names is
required to be there as well. A writer **SHOULD** record the measurement R40 §2.2 requires —
`median_error_seconds`, `p95_error_seconds` and `max_error_seconds`, with `distance`,
`tolerance_seconds` and the per-clock statistics — beside `recipe` and `compensations`, which no
consumer reads either.

The line is Part 02 §8.6's: a fact required to interpret the data is a column, and a fact recording
why a writer decided as it did is not. A consumer needs the bound to place a tick and does not need
the residual that justified it.

## 4. What this does not change

- **No existing column changes type, presence or role.** The three columns and the table are added
  beside what is there; `parameters` stays an optional `json_string`.
- **R37 §4's decision is not reopened for what it decided.** It declined a table or column for the
  withheld-anchor *count* when that was one bookkeeping fact. It did not consider a map keyed by
  name whose values carry coordinates on two clocks, and it never placed the bound at all.
- **A packet that aligned nothing is unaffected.** All three additions are nullable or an absent
  table, and a packet carrying no clock anchors declares none of them.
- **No consumer must parse JSON to read a clock.** That is the change, stated as what it removes: a
  reader that never opens `parameters` now maps exactly as the writer did.

## 5. Consequence

38 tables become **39**, 321 columns become **330**, and 94 references become **96**. Three Tier 2
rules are added: a bound below one, a withheld record on a clock with no anchors, and a phase step
on a clock with no parent.

Both packets are rebuilt, which R87 §2.1, R88 §2, R91 §5, R95, R96, R97 and R98 already require.
The rebuild moves 12 and 10 withheld records into `core.clocks` and writes 24 and 0 rows of
`core.clock_phase_steps`. What it leaves in `core.sessions.alignment_bound` is not predictable from
here: R98 §3.1 gives every clock a window, so the same rebuild measures the bound for the first
time, and §2.3 says nobody knows yet whether either session needs a wider one.

The writer's `_alignment_parameters` emits columns instead of a blob, and
`escapewheel_reader.clocks.declared_bound` reads `core.sessions.alignment_bound` instead of parsing
every run. Both shrink: `declared_bound` loses its JSON parse, its per-run scan and its `max`.

## 6. Open

- **Whether `spikes_without_a_defined_mapping` should move too.** R40 §2.3 requires a
  materialization to record how many rows it omitted, and it does, in that run's `parameters`. A
  consumer reading `analysis.spike_events` needs it to know rows are missing, which is the test
  §3.4 applies — but it is a fact about a *materialization* rather than about a clock, and where it
  would go is `core.processing_runs` or the manifest.
- **Whether `code_uri` should say it holds a digest.** Part 02 describes it as *"Code reference"* and
  Part 05 §3.2 makes it the recipe's digest, which the writer writes as `sha256:<hex>`. A consumer
  meeting a digest under a column named `_uri` has to know the convention to parse it.
