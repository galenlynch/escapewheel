# The Alignment Keys in a Run's Parameters

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `02` (`core.processing_runs.parameters`) |
| **Depends on** | R9 (provenance is light and optional), R37 (bounding alignment by error), R40 (a tolerance that gates on quality) |
| **Profile** | all |

Normative, except §1, §3, §4 and §5, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`core.processing_runs.parameters` is an optional `json_string`, and `02` describes it in one word:
*Parameters.* Three facts that decide how a consumer reads a packet's clocks are nonetheless
recorded there, and no document says under what name.

### 1.1 A reader reads a key no document states

R37 §3.3 lets a writer map a clock further than R27 §5.3's one median anchor interval once it has
measured the estimator at the intended distance, and R37 §4 puts that record in `parameters`
*"rather than adding a column"*. The reference reader reads it: `declared_bound` parses every run's
`parameters`, takes `alignment_bound.used`, and maps at the widest value any run declared
(`escapewheel-reader/src/escapewheel_reader/clocks.py:222-261`). Where no run declares one it maps
at `BOUND = 1.0`, which is R27 §5.3's default.

The name `alignment_bound` appears in no part of the specification and in no revision.
`escapewheel-writer/src/escapewheel_writer/session.py:901` chose it. So a second reader
implementing R37 from the documents cannot find the record, maps at one median anchor interval,
and refuses to place ticks the writer placed — and because the key is missing rather than
malformed, it refuses them silently.

`withheld_anchors` and `phase_discontinuities` are in the same state. R40 §2.3 requires the first
to be recorded even when nothing was withheld, which is a requirement on a key whose name no
document gives.

### 1.2 What the two packets record

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units)
and **`ecephys_786867`** (ten probes, 4,505).

| key | `ecephys_776259` | `ecephys_786867` |
|---|---|---|
| `alignment_bound` | absent | absent |
| `withheld_anchors` | 12 clocks, 10 anchors withheld | 10 clocks, 5 withheld |
| `phase_discontinuities` | 12 clocks, 24 steps | absent |

Each packet holds one `import` run among 26 and 22 `core.processing_runs` rows; every sorting and
curation row carries no parameters at all.

`alignment_bound` is absent from both because neither session needed a bound wider than the
default, and a writer that stays within it records nothing. So the key that most changes how a
packet is read is the one nothing has yet written, and the reader's parse path for it has never
met a real packet.

## 2. Decision

### 2.1 `alignment_bound`, the distance the writer mapped at

A writer establishing a bound wider than R27 §5.3's one median anchor interval **MUST** record it
in the import run's `parameters` under the key `alignment_bound`, whose `used` member holds the
bound in median anchor intervals. R37 §3.3 requires the measurement; this says where it goes.

A consumer **MUST** map at the widest `used` any run in the packet declares. The widest wins
because the run that widened the bound is the run that wrote the ticks in question.

The object **SHOULD** also carry the measurement itself: `distance`, `tolerance_seconds`,
`p95_error_seconds`, `median_error_seconds`, `max_error_seconds` and `per_clock`. R40 §2.2 fixes
the statistic at the 95th percentile for the writer's own decision, and a consumer judging the
packet by a stricter rule needs the distribution rather than the verdict.

### 2.2 `withheld_anchors`, the anchors R37 §3.2's test removed

A writer running R37 §3.2's terminal-anchor test **MUST** record its outcome under
`withheld_anchors`, an object keyed by `clock_id`. Each entry holds `n_withheld`, the count, and
`anchors`, naming which terminals went as `first`, `last`, or both.

Every clock the test examined **MUST** appear, including one that lost nothing. R40 §2.3 makes a
count of zero the evidence that the bound was sufficient, so a packet omitting the clock is
indistinguishable from one that never looked.

An entry **SHOULD** also carry what the decision was made on: `first` and `last`, the terminal
residuals in parent ticks, and the `threshold` they were judged against.

### 2.3 `phase_discontinuities`, steps in the parent's alignment

A writer detecting a step in a clock's alignment to its parent **MUST** record it under
`phase_discontinuities`, an object keyed by `clock_id` whose values are lists of events. Each
event holds `t_tick` and `parent_tick`, locating it on both clocks, and `seconds`, how far the
parent's phase moved.

A step is reported and never corrected, so the key is the only place a consumer can see one.
R13's map is exact at every anchor, which means the map carries the step faithfully rather than
smoothing it away; whether the step also moved the devices timestamped on that parent is not
knowable from the packet, so subtracting it would be wrong wherever it did.

### 2.4 An absent key

A writer with nothing to record writes no key: no `alignment_bound` where the mapping stayed
within R27 §5.3's default, no `withheld_anchors` where no clock was aligned, and no
`phase_discontinuities` where none was found. A consumer **MUST** take the default named in §2.1
to §2.3 rather than refuse the packet, which is what R37 §3.3 means when it says a packet that
says nothing is unchanged by that revision. An absent key is a fact and not a defect (R90 §3.4).

## 3. What this does not change

- **No table, column, reference or rule.** All three keys are content of a column that already
  exists, and R37 §4 declined a column for the first of them. This does not reopen that.
- **Nothing new must be carried.** Each key is written by a writer that had something to record,
  and R9 §2 leaves provenance a SHOULD, so a packet holding no import run at all is conforming.
- **No packet is invalidated and none is rebuilt.** Both packets already spell every key this way,
  so this records the spelling rather than changing it.
- **`parameters` stays optional and otherwise unspecified.** `recipe` and `compensations` sit
  beside these three and no consumer reads either, so only what changes the reading of data is
  named.
- **No rule can check any of this.** A value inside a JSON string is invisible to SQL (R66 §1.4,
  R70 §2), which is the cost R37 §4 accepted when it chose the column it did.

## 4. Consequence

`02`'s one-word description of `core.processing_runs.parameters` names the three keys and what a
consumer does with each, through one `build.py` block in the form R45 §2.4 used to restate
`core.trials`' tick descriptions.

No writer and no reader changes. `escapewheel_reader.clocks.declared_bound` already reads
`alignment_bound.used` and already defaults to one median anchor interval, and the writer already
emits all three names.

## 5. Open

- **Whether a materialization should use the same name.** `analysis.spike_events`'s materialization
  reads `declared_bound` and records the result under `bound`
  (`escapewheel-writer/src/escapewheel_writer/materialize.py:288, 415`), so one packet spells one
  quantity two ways. `declared_bound` scans for `alignment_bound` alone and cannot see the copy.
  The import row carries the authoritative value, so nothing is wrong today.
- **Whether `spikes_without_a_defined_mapping` is a fourth such key.** The materialization records
  it under R40 §2.3 for the same reason `withheld_anchors` exists, and a consumer reading
  `analysis.spike_events` needs it to know that rows are missing. It sits on a materialization run
  rather than an import run, which is why it is not in §2.
- **Whether `code_uri` should say it holds a digest.** `02` describes it as *"Code reference"* and
  `05` §3.2 makes it the recipe's digest, which the writer writes as `sha256:<hex>`. A consumer
  meeting a digest under a column named `_uri` has to know the convention to parse it, and this
  revision is about `parameters` rather than about the column beside it.
