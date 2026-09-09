# What a Run Records About Clock Alignment

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `02` (`core.processing_runs.parameters`) |
| **Depends on** | R9 (provenance is light and optional), R37 (bounding alignment by error), R40 (a tolerance that gates on quality) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.processing_runs.parameters` is an optional `json_string`, and `02` describes it in one word:
*Parameters.* Three of the facts recorded there decide how a consumer reads a packet's clocks —
how far the writer mapped, which anchors it withheld, and where a parent clock's phase stepped —
and no document says under what name any of them is written.

This part names the three, says what a consumer does with each, and settles what an absent one
means. It adds no column, no reference and no rule.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25).

## 2. Background

Informative.

### 2.1 Three names the code uses and no document states

R37 §3.3 lets a writer map a clock further than R27 §5.3's one median anchor interval once it has
measured the estimator at the intended distance. It does not say where that measurement goes, and
no other clause does either: R37 §4 places the **withheld-anchor** record in `parameters` and says
nothing about the bound, and R40 §2.3 places a **dropped-row** count there on R37 §4's authority.
The bound is the one of the three whose home was never stated.

The reference reader nonetheless reads it. `declared_bound` parses every run's `parameters`, takes
`alignment_bound.used`, and maps at the widest value any run declared
(`escapewheel-reader/src/escapewheel_reader/clocks.py:222`); where no run declares one it maps at
`BOUND = 1.0`, which is R27 §5.3's default. The name appears in no part of the specification and in
no revision — the writer chose it, at
`escapewheel-writer/src/escapewheel_writer/session.py:966` — and the reader's own docstring
attributes it to R37 §4, which placed a different record. A second reader implementing R37 from the
documents therefore cannot find it and maps at one median anchor interval, refusing to place ticks
the writer placed. The key is missing rather than malformed, so it refuses them silently.

`withheld_anchors` and `phase_discontinuities` are named the same way, written beside it at
`session.py:961` and `:964`. R37 §3.2 requires the first to be recorded at all, and does so without
saying under what name.

### 2.2 What the two packets record

| key | `ecephys_776259` | `ecephys_786867` |
|---|---|---|
| `alignment_bound` | absent | absent |
| `withheld_anchors` | 12 clocks, 10 anchors withheld | 10 clocks, 5 withheld |
| `phase_discontinuities` | 12 clocks, 24 steps | absent |

Each packet holds one `import` run among 26 and 22 `core.processing_runs` rows; every sorting and
curation row carries no parameters at all.

`alignment_bound` is absent from both because neither session needed a bound wider than the
default, and a writer that stays within it records nothing. So the key that most changes how a
packet is read is the one nothing has yet written, and the reader's parse path for it has never met
a real packet.

## 3. Decision

### 3.1 `alignment_bound`, the distance the writer mapped at

A writer establishing a bound wider than R27 §5.3's one median anchor interval **MUST** record it
in the import run's `parameters` under the key `alignment_bound`, whose `used` member holds the
bound in median anchor intervals. R37 §3.3 requires the measurement; this says where it goes.

A consumer **MUST** map at the widest `used` any run in the packet declares, since the run that
widened the bound is the one that wrote the ticks in question.

The object **MUST** also carry `median_error_seconds`, `p95_error_seconds` and
`max_error_seconds`, which R40 §2.2 already requires of a writer recording its measurement and
which this places by name; it **SHOULD** carry `distance`, `tolerance_seconds` and `per_clock`
besides. R40 §2.2 fixes the statistic at the 95th percentile for the writer's own decision, and a
consumer judging the packet by a stricter rule needs the distribution rather than the verdict.

### 3.2 `withheld_anchors`, the anchors R37 §3.2's test removed

A writer running R37 §3.2's terminal-anchor test **MUST** record its outcome under
`withheld_anchors`, an object keyed by `clock_id`. R37 §3.2 already requires the record — count and
clock, in the producing run's parameters — and this gives it a name and a shape: each entry holds
`n_withheld`, the count, and `anchors`, naming which terminals went as `first`, `last`, or both.

Every clock the test examined **MUST** appear, including one that lost nothing. That is R40 §2.3's
rule for a dropped row carried to a withheld anchor, and it holds for the same reason: a recorded
zero is the evidence that nothing was withheld, where an absent entry is indistinguishable from a
clock the test never examined.

An entry **SHOULD** also carry what the decision was made on: `first` and `last`, the terminal
residuals in parent ticks, and the `threshold` they were judged against.

### 3.3 `phase_discontinuities`, steps in the parent's alignment

A writer detecting a step in a clock's alignment to its parent **MUST** record it under
`phase_discontinuities`, an object keyed by `clock_id` whose values are lists of events. Each event
holds `t_tick` and `parent_tick`, locating it on both clocks, and `seconds`, how far the parent's
phase moved.

A step is reported and never corrected, so this key is the only place a consumer can see one.
R13's map is exact at every anchor, so it carries the step faithfully rather than smoothing it
away. Correcting it would need to know whether the step also moved the devices timestamped on that
parent, which the packet does not record, so subtracting it would be wrong wherever it did.

### 3.4 An absent key

A writer with nothing to record writes no key: no `alignment_bound` where the mapping stayed within
R27 §5.3's default, no `withheld_anchors` where no clock was aligned, and no
`phase_discontinuities` where none was found. A consumer **MUST** take the default named in §3.1 to
§3.3 rather than refuse the packet, which is what R37 §3.3 means when it says a packet that says
nothing is unchanged by that revision. An absent key is a fact and not a defect, which is what
R80 §2.4 settles for an unresolvable source and holds here for the same reason: the writer had
nothing to say, and silence is what it said.

## 4. What this does not change

- **No table, column, reference or rule.** All three keys are content of a column that already
  exists, and R37 §4 declined a column for the first of them. This does not reopen that.
- **Nothing new must be carried.** Each key is written by a writer that had something to record,
  and R9 §5 leaves provenance a SHOULD, so a packet holding no import run at all is conforming.
- **No packet is invalidated and this forces no rebuild.** Both packets already spell every key
  this way, so this records the spelling rather than changing it.
- **`parameters` stays optional and otherwise unspecified.** `recipe` and `compensations` sit
  beside these three and no consumer reads either, so only what changes the reading of data is
  named.
- **No rule can check any of this.** A value inside a JSON string is invisible to SQL (R66 §1.4,
  R70 §2), which is the cost R37 §4 accepted when it chose the column it did.

## 5. Consequence

`02`'s one-word description of `core.processing_runs.parameters` names the three keys and what a
consumer does with each, through one `build.py` block in the form R45 §2.4 used to restate
`core.trials`' tick descriptions.

No writer and no reader changes. `escapewheel_reader.clocks.declared_bound` already reads
`alignment_bound.used` and already defaults to one median anchor interval, and the writer already
emits all three names.

## 6. Open

- **Whether a materialization should use the same name.** `analysis.spike_events`'s materialization
  reads `declared_bound` and records the result under `bound`
  (`escapewheel-writer/src/escapewheel_writer/materialize.py:413` and `:446`), so one packet spells
  one quantity two ways. `declared_bound` scans for `alignment_bound` alone and cannot see the copy.
  The import row carries the authoritative value, so nothing is wrong today.
- **Whether `spikes_without_a_defined_mapping` is a fourth such key.** The materialization records
  it under R40 §2.3 for the same reason `withheld_anchors` exists (`materialize.py:450`), and a
  consumer reading `analysis.spike_events` needs it to know that rows are missing. It sits on a
  materialization run rather than an import run, which is why it is not in §3.
- **Whether `code_uri` should say it holds a digest.** `02` describes it as *"Code reference"* and
  `05` §3.2 makes it the recipe's digest, which the writer writes as `sha256:<hex>`. A consumer
  meeting a digest under a column named `_uri` has to know the convention to parse it, and this
  part is about `parameters` rather than about the column beside it.
