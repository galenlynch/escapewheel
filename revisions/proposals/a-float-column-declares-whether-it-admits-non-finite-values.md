# A float column declares whether it admits non-finite values

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `2bb9f81cc2620b3b4c8a8ca29d5024b5e651a913` |
| **Decision domain** | specification |
| **Affects** | Part 02 §§3, 5, 9.2, 9.4 and 10.1; Part 03 §5.6; Part 05 §5.1; `registry/registry.schema.json` and the registry-contract descriptor naming it; `registry/build.py`, `registry/rules.json` and `registry/render.py`; the four extension registries; the validator's Tier 1 generator; packet fixtures |

## 1. Problem

A registry column typed `float32` or `float64` holds IEEE 754 binary values, and three of those
values are NaN, positive infinity and negative infinity.
[Part 03 §5.6](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#56-one-null) treats
NaN as a value of a float column rather than an absent one. No declaration says whether a column
admits these values, so every float column admits all three. Only a Tier 2 rule written for a
column can reject them, and 18 of the 21 float columns in `core` have no rule that reads their
values.

Where a rule exists, its comparison may still pass a non-finite value.
[Part 11 §5](../../escapewheel_poc_docs_v0.2/11_tier_2_rule_language.md#ew-tier-2-deterministic-semantics)
orders approximate values `-infinity < finite values < +infinity < NaN`, so a rule that flags a
value below a lower bound passes NaN and positive infinity. A NaN clock rate and a NaN alignment
bound both pass the rules written to reject a bad one.

A second defect sits in the core rules. `core.array_assets.sample_rate_matches_axis` divides by an
axis step's denominator where it should multiply by it, so it checks the wrong rate whenever the
denominator is not 1, and it skips a clock that states its rate as a rational.

## 2. Evidence

Every count was taken at the recorded baseline from `registry/logical_schemas.json` and
`registry/extensions/*.json`, by scripts that parsed every column and rule declaration. Each probed
rule passed the validator's rule-profile checker, `check_rule`, and ran on DuckDB 1.5.5 against
tables built from the registry's declarations, holding one or two rows with the tested value.

### 2.1 The registries declare 103 float columns, and 31 rules read one

The core registry document declares 26 float columns: 20 `float64` and 1 `float32` in `core`, and
5 `float64` in `analysis`. The extension registries declare 77: 10 in `aind_opto`, 28 in
`aind_unit_qc`, 31 in `dynamic_foraging` and 8 in `vr_foraging`. Of the 121 Tier 2 rules, 76 in
the core document and 45 in extensions, 31 name a float column. A whole-word match on column names
found them, and reading each rule's SQL confirmed the match.

| what the rule does with the float value | core document | extensions |
|---|---:|---:|
| compares it with one bound, so NaN or +infinity passes | 2 | 3 |
| compares it with two bounds or a tolerance, so every non-finite value is flagged | 1 | 10 |
| counts distinct values | 0 | 1 |
| tests only whether it is null | 11 | 3 |
| total | 14 | 17 |

### 2.2 Rules with a one-sided bound pass NaN and positive infinity

Each rule ran four times: with a finite value it exists to reject, then with NaN, +infinity and
-infinity. "flag" means the rule returned rows.

| rule | tested value | bad finite | NaN | +inf | -inf |
|---|---|---|---|---|---|
| `core.clocks.tick_rate_positive` | `tick_rate_hz` | flag | pass | pass | flag |
| `core.sessions.alignment_bound_at_least_default` | `alignment_bound` | flag | pass | pass | flag |
| `aind_unit_qc.waveform_metrics.a_width_is_positive` | `half_width` | flag | pass | pass | flag |
| `aind_unit_qc.synchrony.larger_is_rarer` | `sync_spike` at the smaller size | flag | pass | pass | flag |
| `aind_unit_qc.synchrony.larger_is_rarer` | `sync_spike` at the larger size | flag | flag | flag | pass |
| `dynamic_foraging.sessions.a_range_is_ordered` | `block_max` | flag | pass | pass | flag |
| `dynamic_foraging.sessions.a_range_is_ordered` | `block_min` | flag | flag | flag | pass |
| `core.array_assets.sample_rate_matches_axis` | `sample_rate_hz`, or the clock's `tick_rate_hz` | flag | flag | flag | flag |
| the 10 two-sided extension bounds | the bounded column | flag | flag | flag | flag |

The side a rule bounds decides its result. A rule flagging `x < lo` misses NaN and +infinity, and
one flagging `x > hi` catches them, because NaN sorts above everything. `sample_rate_matches_axis`
flags NaN only because `ABS(NaN - r) > 1e-6` is true under that order. The 10 two-sided rules are
the six `aind_unit_qc.metrics.*_is_bounded` rules, `aind_unit_qc.synchrony.a_fraction_is_a_fraction`,
`dynamic_foraging.trials.a_probability_is_a_probability`, `dynamic_foraging.trials.a_draw_is_a_draw`
and `vr_foraging.site_odors.a_concentration_is_a_percentage`.

`dynamic_foraging.trials.a_block_holds_one_probability_pair` counts distinct probabilities in a
block. It flags a block holding NaN and 0.5 and passes a block holding NaN twice, treating NaN as an
ordinary value.

### 2.3 A presence rule reads NaN as a stated value

The 14 presence rules test `IS NULL`, and a NaN is not null. `core.clocks.tick_rate_declared` flags
a clock with a null `tick_rate_hz` and no rational rate, and passes the same clock with
`tick_rate_hz` NaN, a declared rate that places no tick. `aind_opto.stimulations.pulsing_needs_a_frequency`
likewise accepts a NaN `frequency_hz` as the frequency it requires.

No rule reads `core.clocks.transform_slope`. A child clock with slope NaN, +infinity, 0 or -1, and
offset NaN, passes both `transform_pair_complete` and `alignment_declared_for_conversion`. The slope
counts parent ticks per tick of the child, so each of those values makes the clock's alignment
meaningless. A zero or negative slope is a domain defect separate from non-finiteness, and §6 asks
whether to fix it here.

### 2.4 `sample_rate_matches_axis` inverts the step's denominator

An axis on a regular tick grid advances `step_tick_num / step_tick_den` ticks per position, and
[R33 §3](../accepted/R33-rational-axis-steps.md) states the implied rate as
`tick_rate_hz * step_tick_den / step_tick_num`. The registry's rule computes
`tick_rate_hz / step_tick_num / step_tick_den`, and the two agree only where the denominator is 1.
On a 30,000 Hz clock:

| step (ticks) | true rate | rule's rate | rule on the true rate | rule on its own rate |
|---|---:|---:|---|---|
| 3/2 | 20,000 Hz | 5,000 Hz | flag | pass |
| 3/4 | 40,000 Hz | 2,500 Hz | flag | pass |
| 24/1 | 1,250 Hz | 1,250 Hz | pass | pass |

The rule also requires `c.tick_rate_hz IS NOT NULL`, so a clock stating 30000/1 through
`tick_rate_num` and `tick_rate_den` goes unchecked, and a sample rate of 1 Hz on it passes. Its
predicate `CAST(step_tick_num …) / CAST(COALESCE(step_tick_den, 1) …) IS NOT NULL` tests only that
`step_tick_num` is present.

The inverted form has been in the registry since R33 was applied. The only writer path that sets
`step_tick_den`, `escapewheel-writer/src/escapewheel_writer/sources/lfp.py`, writes 1, so no packet
the reference writer builds reaches the error, and no test names the rule.

### 2.5 No scanned packet holds a non-finite float

A scan counted `NOT isfinite(x)` over every `FLOAT` and `DOUBLE` column of every Parquet file in
two populations: the 32 fixture packets under `fixtures/packets/`, with 950 files and 615 float
columns; and three session packets built locally between 2026-09-06 and 2026-09-17, two
extracellular and one dynamic-foraging, with 110 files and 208 float columns. Neither held a
non-finite value. The writer's NWB source maps a NaN to null before a typed column receives it
(`_clean` in `sources/nwb.py`), and its canonical JSON encoding maps a non-finite float to null.

### 2.6 The rule language already expresses the check

[Part 11 §2](../../escapewheel_poc_docs_v0.2/11_tier_2_rule_language.md#ew-tier-2-query-profile)
admits `isfinite` and Part 11 §5 defines it. It returns null for null, so `WHERE NOT isfinite(col)`
leaves null rows out and presence remains the only rule about nulls. DuckDB 1.5.5 agrees on both
types:

| value | `isfinite` on `DOUBLE` | `isfinite` on `FLOAT` |
|---|---|---|
| NaN | false | false |
| +infinity, -infinity | false | false |
| null | null | null |
| 1.0, -0.0 | true | true |

`SELECT clock_id, tick_rate_hz FROM core.clocks WHERE NOT isfinite(tick_rate_hz)` passes
`check_rule` unchanged, and over NaN, +infinity, -infinity, null and 30000.0 it returns the first
three. The same form over the `float32` column `core.spike_events.amplitude` returns only the NaN
row.

On 100 million in-memory `FLOAT` values with 8 threads, the scan took 0.042 s against 0.019 s for
`IS NULL`. In a packet, reading the column should dominate that cost; this was not measured on
Parquet.

## 3. Desired outcome and constraints

- Every float column states whether it admits NaN and infinity, and a validator rejects a non-finite
  value in a column that does not, working from the declaration alone.
- A rule author need not know which side of a bound NaN falls on.
- Part 11 §5's comparison semantics stay as they are: whether a column admits a value is a question
  about its domain, separate from how the language orders approximate values.
- An absent value stays null, as Part 03 §5.6 requires, so a source's NaN meaning "not computed"
  becomes null.
- Existing packets stay conforming; the packets §2.5 scanned hold no value the check would reject.
- `sample_rate_matches_axis` checks the rate the axis implies, whichever form the clock uses for its
  rate.

## 4. Options and tradeoffs

### 4.1 Keep the current design

Every float column continues to admit non-finite values, five rules continue to pass NaN on the
columns they guard, and the other float columns stay unguarded. The option costs no migration and
leaves a packet unable to say that a clock rate is a number.

### 4.2 Add an `isfinite` guard to each rule

Five rules would gain `OR NOT isfinite(x)`. The guard reaches only columns that already have a value
rule: three of the 21 float columns in `core`, leaving 18, including `transform_slope` and
`transform_offset`, with no rule comparing their values. Every future rule author would also have
to remember Part 11's ordering and which side their bound falls on, which the five existing
failures show authors do not reliably do.

### 4.3 Forbid non-finite values in every float column

One Part 02 or Part 03 clause, with one generated check over every float column, would need no
registry field, and every current column would accept it. It removes the choice for a future column
that gives infinity a meaning, such as an unbounded interval end, and admitting one later would need
the field §4.4 adds now.

### 4.4 A declared `finite` property generates a Tier 1 check (preferred direction)

A column declaration gains `finite`, a boolean, required on a `float32` or `float64` column and
forbidden on any other type. It follows `vocabulary`:
[Part 02 §9.3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-vocabularies)
requires that field on every string column with no default, so an absent declaration is a defect
rather than a claim.

- **Meaning.** `finite: true` states that every non-null value is finite. `finite: false` admits
  NaN and both infinities, and a rule reading the column accounts for them itself.
- **Generated check.** For each column declaring `finite: true`, the Tier 1 generator emits
  `<resource>.<column>.finite` at level `error`:
  `SELECT <primary key>, <column> FROM <resource> WHERE NOT isfinite(<column>)`. It sits beside the
  required-column and closed-vocabulary checks
  ([Part 02 §10.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#101-tier-1-generated-from-structure)).
  No float column is optional today; an optional one would need the check skipped where the column
  is absent.
- **Placement.** A new subsection of Part 02's type system, after its fixed representations, states
  the rule, and [Part 02 §3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-column-declaration)'s
  column table gains a row. Part 05 §5.1 adds finiteness to its list of Tier 1 checks, and Part 03
  §5.6's NaN paragraph then says NaN reaches only a column declaring `finite: false`.
- **Values.** All 103 float columns declare `finite: true`. Each holds a rate, a duration, a scale,
  a coordinate, a probability, a quality metric or a measured quantity, where a non-finite value
  either carries no meaning or means "not computed", a meaning Part 03 §5.6 assigns to null. The core
  registry sets the field in one build block, run after R101's block that assigns `vocabulary`, and
  each extension registry sets it on its own columns.
- **Rules.** The five one-sided rules stay as written. The generated check fails the packet on the
  same value and names the column rather than the rule's predicate.

The writer carries no new obligation; the validator decides the check. Part 02 §5.3 makes the writer
refuse an out-of-range integer because the validator cannot see a wrapped value, whereas a NaN stays
visible to the validator.

### 4.5 `sample_rate_matches_axis` compares the rate the axis implies (preferred direction)

```sql
SELECT a.array_asset_id, a.sample_rate_hz
FROM core.array_assets AS a
JOIN core.array_dimensions AS d USING (array_asset_id)
JOIN core.clocks AS c ON c.clock_id = d.clock_id
WHERE a.sample_rate_hz IS NOT NULL AND d.step_tick_num IS NOT NULL
  AND ABS(a.sample_rate_hz
          - COALESCE(c.tick_rate_hz,
                     CAST(c.tick_rate_num AS DOUBLE PRECISION) / CAST(c.tick_rate_den AS DOUBLE PRECISION))
            * CAST(COALESCE(d.step_tick_den, 1) AS DOUBLE PRECISION)
            / CAST(d.step_tick_num AS DOUBLE PRECISION)) > 1e-6
```

`core.clocks.tick_rate_declared` and `tick_rate_one_form` make exactly one rate form present, so the
`COALESCE` always yields a rate. The text passes `check_rule`. Run on clocks stating 30,000 Hz as a
float, as 30000/1 and as 60000/2, with steps of 3/2, 3/4, 24/1 and 1/1, it passed every true rate
and flagged every rate §2.4's inverted form computes, a 1 Hz rate on a rational clock, and a NaN
sample rate.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged: the property constrains a logical column's value space, not a concept's meaning. |
| logical prose | Affected: Part 02 §3 gains a row, a new type-system subsection states the rule, and Part 02 §10.1 lists the generated check. |
| registry meta-schema | Affected: `column` gains `finite`, required when `type` is `float32` or `float64` and forbidden otherwise. An extension registry valid under 0.6.0 no longer validates, so the schema's `$id` moves, and Part 02 §§9.2 and 9.4 name the new version and a new contract descriptor. The shape phase decides the field, so no semantic invariant is added. |
| registry declarations and rules | Affected: one core build block sets `finite: true` on 26 columns; `rules.json` replaces `sample_rate_matches_axis`; `render.py` shows the declaration in `tables.md`'s Declares column. |
| physical profiles | Affected: Part 03 §5.6's NaN paragraph narrows to columns declaring `finite: false`. |
| packet manifest and schemas | Unchanged: no manifest field names a column property. |
| validation and import | Affected: Part 05 §5.1 lists the check. Part 11 is unchanged, because Part 11 §5 already defines `isfinite`. |
| extension registries | Affected: 77 columns across the four extension registries gain `finite: true`, and each registry's `$schema` moves to the new meta-schema. |
| reader, writer, validator, adapters | Validator affected: `generate.py` emits the check. Writer unchanged: its commit-time validation reports the check, and its NWB path already writes null for NaN. Reader unchanged: it may rely on the declaration and need not. Unknown for adapters: none in this repository writes the extension tables, so whether an external adapter emits a non-finite metric is not known. |
| existing packets | Unchanged in bytes: no packet §2.5 scanned holds a non-finite value. Revalidation against the new registry follows the rebuild or rebinding path of any meta-schema change. |
| conformance fixtures and tests | Affected: a fixture variant with NaN in `core.clocks.tick_rate_hz` draws `core.clocks.tick_rate_hz.finite`; registry checker cases reject a float column without `finite` and a string column with it; rule vectors cover §2.4's table and a clock with a rational rate. |
| revision tooling | Unchanged: the change needs only the ordinary ledger and evidence records. |
| publications and documentation | Affected: `tables.md`, the generated single-file specification, and the generated structure count in `registry/README.md`, which gains a finite-column line. |

The open proposal on nomenclature reference entries edits the authority text of Part 02 §9.3, which
this proposal cites as precedent without changing. No open proposal or draft touches Part 02 §§3, 5
or 10.1, Part 03 §5.6, or the rule. A reverse-citation scan found no citer of Part 02 §5.1, Part 03
§5.6 or Part 11 §5. Two sections cite Part 02 §10.1: Part 03 §5.3, for primary-key uniqueness,
which this proposal leaves alone, and Part 05 §5.1, listed above. R101 introduced the NaN paragraph
of Part 03 §5.6, and R125 the ordering in Part 11 §5.

## 6. Open questions

1. **Required or defaulted.** The property can be required on every float column, or default to
   finite with `finite: false` as the exception. Preferred: required, matching Part 02 §9.3's rule
   that a declaration has no default, at the cost of one mechanically set field on each of 103
   columns.
2. **Two values or three.** A column might admit infinity and reject NaN, for example as an
   unbounded interval end. Preferred: a boolean, since no current column needs the distinction; a
   finer value would need a later meta-schema change.
3. **Ratio metrics in `aind_unit_qc`.** `isi_violations_ratio`, `peak_trough_ratio`, `l_ratio` and
   `d_prime` are quotients, and a source might emit infinity for a zero denominator; this was not
   checked against the source. Preferred: `finite: true`, with the adapter writing null for a
   metric its source could not compute.
4. **A transform slope's sign.** A slope of 0 or -1 passes every rule (§2.3). Preferred: fold a
   `core.clocks.transform_slope_positive` rule into the same draft, which already edits
   `rules.json` and the `core.clocks` declarations.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
