# A Float Column Declares Whether It Admits Non-Finite Values

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `bca96ae475c220f7b8329ab47b42e6a07e6a51b2` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§3, 5, 9.2, 9.4, and 10.1; Part 03 §5.6; Part 05 §5.1; Part 08 §§2 and 3; `registry/registry.schema.json`; the registry-contract descriptor; the core registry and `registry/rules.json` |
| **Depends on** | R101 §3.10; R125 §3.5 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A registry column typed `float32` or `float64` holds binary floating-point values, and three of
those values are not finite: NaN, positive infinity, and negative infinity. Part 03 §5.6 treats NaN
as a value of a float column rather than an absent one. No declaration says whether a column admits
these values, so every float column admits all three, and only a Tier 2 rule written for one column
can reject them. Of the 21 float columns in `core`, 18 have no rule that reads their values.

Where a rule does read a value, its comparison can still pass a non-finite one. Part 11 §5 orders
approximate values `-infinity < finite values < +infinity < NaN`, so a rule that flags a value
below a lower bound passes NaN and positive infinity. A NaN clock rate and a NaN alignment bound
both pass the rules written to reject a bad one.

This revision gives every float column a required boolean, `finite`, and has a validator generate
a Tier 1 check from it. Every float column the core registry declares takes `finite: true`, and so
does every float column of the four repository extension registries. The core registry also gains
a rule that a clock's `transform_slope` is positive, a defect of the same column found while
probing it.

The change is structural because it revises rules inside Part 02 §§3, 9.2, 9.4, and 10.1,
Part 03 §5.6, and Part 05 §5.1; appended sections would leave Part 03 §5.6 saying NaN reaches every
float column and Part 02 §10.1 listing an incomplete set of generated checks. One subsection is
added at the end of Part 02 §5.

### 1.1 Structural crosswalk

Part 02 §§3, 9.2, and 9.4 and Part 08 §§2 and 3 carry canonical anchors. The anchor bootstrap
`06b11fb` added `ew-tier-1-rules` to Part 02 §10.1, `ew-one-null` to Part 03 §5.6, and
`ew-tier-1-validation` to Part 05 §5.1, so no further bootstrap is needed. The subsection added to
Part 02 §5 takes `ew-finite-values` when it is created. No section moves, splits, merges, or
retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §3, the table of column attributes | add one row | same section | `finite` is required on a `float32` or `float64` column | §3.1 |
| none | add | last subsection of Part 02 §5, "Finite values" (`ew-finite-values`) | defines a non-finite value and the two values of `finite` | §3.1 |
| Part 03 §5.6, NaN "reaches the registry's float columns and none of the rest" | replace that clause in place | same section, citing the new Part 02 subsection | NaN reaches only a column declaring `finite: false` | §3.1 |
| Part 02 §10.1, the Tier 1 checks a validator generates | extend in place | same section | adds the finiteness check | §3.2 |
| Part 05 §5.1, the list of Tier 1 checks | extend in place | same section | lists the finiteness check | §3.2 |
| Part 02 §9.2, the meta-schema `$id` and the core registry's version | revise in place | same section | both advance to 0.7.0 | §3.3 |
| Part 02 §9.4, the descriptor ID and the meta-schema it selects | revise in place | same section | `escapewheel-registry-contract-v0.4` selects meta-schema 0.7.0; the invariant inventory is unchanged | §3.3 |
| Part 08 §§2 and 3, the example's core registry version | revise the informative example | same sections | none | none |

## 2. Background

Section 2 is informative. Every count was taken at the recorded baseline from
`registry/logical_schemas.json` and `registry/extensions/*.json` by a script that parsed every
column and rule declaration. Each probed rule passed the reference validator's static rule check and
ran on DuckDB 1.5.5 against tables created from the registry's declarations, holding one or two rows
with the tested value.

### 2.1 The registries declare 105 float columns, and 31 rules read one

The core registry document declares 26 float columns: 20 `float64` and 1 `float32` in `core`, and
5 `float64` in `analysis`. The four extension registries declare 79, all `float64`: 10 in
`aind_opto`, 30 in `aind_unit_qc`, 31 in `dynamic_foraging`, and 8 in `vr_foraging`. No float column
is `optional`.

Of the 121 Tier 2 rules, 76 in the core document and 45 in the extensions, 31 name a float column.
A whole-word match on column names found them, and reading each rule's SQL confirmed the match.

| what the rule does with the float value | core document | extensions |
|---|---:|---:|
| compares it with one bound | 2 | 3 |
| compares it with two bounds or a tolerance | 1 | 10 |
| counts distinct values | 0 | 1 |
| tests only whether it is null | 11 | 3 |
| total | 14 | 17 |

### 2.2 A one-sided bound passes NaN and positive infinity

Each rule ran four times: with a finite value it exists to reject, then with NaN, positive infinity,
and negative infinity in the tested column. "flag" means the rule returned rows.

| rule | tested column | bad finite | NaN | +inf | -inf |
|---|---|---|---|---|---|
| `core.clocks.tick_rate_positive` | `tick_rate_hz` | flag | pass | pass | flag |
| `core.sessions.alignment_bound_at_least_default` | `alignment_bound` | flag | pass | pass | flag |
| `aind_unit_qc.waveform_metrics.a_width_is_positive` | each of `peak_to_trough_duration`, `peak_half_width`, and `trough_half_width` | flag | pass | pass | flag |
| `aind_unit_qc.synchrony.larger_is_rarer` | `sync_spike` at the smaller size | flag | pass | pass | flag |
| `aind_unit_qc.synchrony.larger_is_rarer` | `sync_spike` at the larger size | flag | flag | flag | pass |
| `dynamic_foraging.sessions.a_range_is_ordered` | `block_max` | flag | pass | pass | flag |
| `dynamic_foraging.sessions.a_range_is_ordered` | `block_min` | flag | flag | flag | pass |
| `core.array_assets.sample_rate_matches_axis` | `sample_rate_hz` | flag | flag | flag | flag |
| four of the ten two-sided extension bounds | the bounded column | flag | flag | flag | flag |

The side a rule bounds decides its result. A rule flagging `x < lo` misses NaN and positive
infinity, and one flagging `x > hi` catches them, because NaN sorts above everything.
`sample_rate_matches_axis` flags NaN only because `ABS(NaN - r) > 1e-6` is true under that order.
The ten two-sided rules are the six `aind_unit_qc.metrics.*_is_bounded` rules,
`aind_unit_qc.synchrony.a_fraction_is_a_fraction`,
`dynamic_foraging.trials.a_probability_is_a_probability`,
`dynamic_foraging.trials.a_draw_is_a_draw`, and
`vr_foraging.site_odors.a_concentration_is_a_percentage`; the four probed were
`presence_ratio_is_bounded`, `silhouette_is_bounded`, `a_probability_is_a_probability`, and
`a_concentration_is_a_percentage`, and the other six share one of their predicate forms.

`dynamic_foraging.trials.a_block_holds_one_probability_pair` counts distinct probabilities in a
block. It flags a block holding NaN and 0.5 and passes a block holding NaN twice, treating NaN as an
ordinary value.

### 2.3 A presence rule reads NaN as a stated value

The 14 rules that test only for null use `IS NULL`, and a NaN is not null.
`core.clocks.tick_rate_declared` flags a clock with a null `tick_rate_hz` and no rational rate, and
passes the same clock with `tick_rate_hz` NaN or either infinity, a declared rate that places no
tick. `aind_opto.stimulations.pulsing_needs_a_frequency` likewise accepts a non-finite
`frequency_hz` as the frequency it requires.

No rule reads the value of `core.clocks.transform_slope`, which the registry describes as parent
ticks per tick of the child clock. A child clock with slope NaN, positive infinity, 0, or -1, or
with offset NaN, passes both `core.clocks.transform_pair_complete` and
`core.clocks.alignment_declared_for_conversion`, and each of those values leaves the clock's
alignment meaningless. A zero or negative slope is a defect of the column's domain rather than of
finiteness, so it needs a rule of its own.

### 2.4 No scanned packet holds a non-finite value

A scan counted `NOT isfinite(x)` over every `FLOAT` and `DOUBLE` column of every Parquet file in two
populations: the 44 fixture packets `fixtures/build.py` writes, with 1,325 files and 847 float
columns; and three packets the reference writer built between 2026-09-06 and 2026-09-17 from two
extracellular sessions carrying dynamic-foraging tables, one session built twice, with 110 files and
208 float columns. Neither held a non-finite value. The two packets built on 2026-09-17 also carry
`aind_unit_qc` tables, 56 of those float columns, written by per-packet scripts before that extension
had an adapter.

The reference writer's NWB adapter writes null where its source holds NaN, and the `aind_unit_qc`
adapter in `escapewheel-aind` writes null for every non-finite metric its SpikeInterface analyzer
holds. Over two local sortings of 4,559 and 13,234 units, the metrics that adapter maps hold 40,436
NaN values and no infinity.

### 2.5 Alternatives

Keeping the current design costs no migration and leaves a packet unable to say that a clock rate is
a number. Adding `OR NOT isfinite(x)` to each one-sided rule reaches only the three `core` float
columns that already have a value rule, and leaves every future rule author to remember which side
of a bound NaN falls on, which the five existing one-sided rules show authors do not reliably do.
Forbidding non-finite values in every float column needs no registry field, but a future column
giving infinity a meaning, such as an unbounded interval end, would then need the field this
revision adds. Defaulting an absent `finite` to `true` saves 105 mechanically set fields and makes
an absent declaration a claim, which Part 02 §9.3 rejects for `vocabulary`. A three-valued field
that admits infinity and rejects NaN serves no current column, and a later meta-schema change can
add it. Declaring the `aind_unit_qc` quotients `isi_violations_ratio`,
`main_peak_to_trough_ratio`, `l_ratio`, and `d_prime` `finite: false` would publish an infinite
quotient where the metric was not computable, a meaning Part 03 §5.6 assigns to null.

### 2.6 Feasibility and overlap

The check needs no new language feature. Part 11 §2 admits `isfinite`, and Part 11 §5 defines it to
return null for null, so a query of the form `WHERE NOT isfinite(col)` leaves null rows out and
presence remains the only rule about nulls. DuckDB 1.5.5 agrees on both types: `isfinite` is false
for NaN and both infinities, null for null, and true for 1.0 and -0.0. The query
`SELECT clock_id, tick_rate_hz FROM core.clocks WHERE NOT isfinite(tick_rate_hz)` passes the static
rule check and, over NaN, positive infinity, negative infinity, null, and 30000.0, returns the first
three. Over the 286,896,563 rows of one session packet's `core.spike_events`, the same form on the
`float32` column `amplitude` took 0.05 s, the best of five runs on 8 threads with the file cached.

No open proposal or draft touches Part 02 §§3, 5, or 10.1, Part 03 §5.6, Part 05 §5.1, or the
`core.clocks` rules, and none of R136–R138 did. The nomenclature draft, applied after this one,
revises Part 02 §9.3's authority text, which this revision cites without changing. R136 rewrote the
resource entries of Part 08 §3's manifest excerpt and left its registry bindings, whose core version
this revision advances, so this revision's edit applies to the current excerpt. Two sections cite
Part 02 §10.1: Part 03 §5.3, for how a profile establishes primary-key uniqueness, which is
unchanged, and Part 05 §5.1, revised here.

## 3. Decision

Five subsections declare a float column's finiteness, generate its check, advance the registry
identifiers, set the core declarations, and add a rule on a clock's transform slope. The crosswalk
in §1.1 places each.

### 3.1 A float column declares `finite`

A value of a `float32` or `float64` column is **non-finite** when it is NaN, positive infinity, or
negative infinity. Every other non-null value of those types is finite, and null is neither.

Every column whose type is `float32` or `float64` MUST declare `finite`, a boolean, and a column of
any other type MUST NOT declare it. There is no default, so an absent declaration is a defect
rather than a claim.

- `finite: true` declares that the column holds no non-finite value. A packet MUST NOT hold a
  non-finite value in such a column.
- `finite: false` admits non-finite values. A Tier 2 rule reading such a column sees them in
  Part 11 §5's order.

A NaN is therefore a value only of a float column declaring `finite: false`. An absent value remains
null under Part 03 §5.6, so a source's NaN or infinity meaning that a value was not recorded or not
computable becomes null in any float column.

### 3.2 A validator checks every column declaring `finite: true`

A validator MUST generate from the declaration alone, for every column declaring `finite: true`, a
check that reports each row holding a non-finite value in that column, at level `error`, under the
check ID `<declaration_id>.<column>.finite`, such as `core.clocks.tick_rate_hz.finite`. Where the
column is `optional` and a table omits it, the check reports nothing. The finding belongs to the
registry holding the declaration under Part 05 §9.5, and Part 05 §5.4 applies the check to the
columns an extension declares.

### 3.3 The registry identifiers advance

The registry meta-schema MUST declare `finite` as a boolean member of a column, require it where
`type` is `float32` or `float64`, and forbid it otherwise. The shape phase of Part 02 §9.4 therefore
decides §3.1's declaration rule, and the registry-contract descriptor adds no invariant.

These incorporated identifiers MUST advance:

| artifact | from | to |
|---|---|---|
| registry meta-schema `$id` | `https://escapewheel.org/schemas/registry/0.6.0` | `https://escapewheel.org/schemas/registry/0.7.0` |
| registry-contract descriptor ID | `escapewheel-registry-contract-v0.3` | `escapewheel-registry-contract-v0.4`, selecting meta-schema 0.7.0 with the same invariants |
| core registry `registry_version` | `0.6.0` | `0.7.0` |

An extension registry migrated to meta-schema 0.7.0 MUST carry a `registry_version` different from
the one it carried under 0.6.0; the core specification does not assign it. No checker verifies this,
since a checker reads only the document before it and not the version that document replaced.

### 3.4 The core registry declares every float column finite

The incorporated core registry MUST declare `finite: true` on each of these 26 columns, and on no
other column:

| resource | columns |
|---|---|
| `core.array_assets` | `sample_rate_hz`, `conversion`, `offset` |
| `core.array_channels` | `inter_sample_shift`, `offset`, `conversion` |
| `core.array_dimensions` | `step_value`, `origin_value` |
| `core.calibration_points` | `input_value`, `output_value` |
| `core.clock_phase_steps` | `shift_seconds` |
| `core.clocks` | `tick_rate_hz`, `transform_slope`, `transform_offset` |
| `core.electrode_coordinate_values` | `axis_value` |
| `core.electrodes` | `impedance_ohm` |
| `core.sessions` | `alignment_bound` |
| `core.spike_events` | `amplitude` |
| `core.unit_coordinate_values` | `axis_value` |
| `core.unit_quality_labels` | `confidence` |
| `core.units` | `firing_rate_hz` |
| `analysis.array_assets` | `sample_rate_hz`, `conversion`, `offset` |
| `analysis.array_dimensions` | `step_value`, `origin_value` |

Each holds a rate, a duration, a scale or offset, a coordinate, a confidence, or a measured
quantity, where a non-finite value either carries no meaning or means that the value was not
computed.

### 3.5 A clock's transform slope is positive

A packet MUST NOT carry a `core.clocks` row whose `transform_slope` is zero or negative. The core
registry MUST carry this Tier 2 rule on `core.clocks`:

| field | value |
|---|---|
| `id` | `core.clocks.transform_slope_positive` |
| `level` | `error` |
| `message` | `transform_slope is not positive` |
| `sql` | `SELECT clock_id, transform_slope FROM core.clocks WHERE transform_slope <= 0` |

The rule passes the static rule check. It flags 0, -0.0, -1, and negative infinity, and passes a
positive slope and null; §3.2's check reports NaN and positive infinity in the same column.

## 4. What this does not change

Part 11 §5's order and its definition of `isfinite` are unchanged, and so is every existing rule.
A rule over a `finite: true` column still sees a non-finite value in its own comparison; the value
now also draws §3.2's finding, which names the column rather than the rule's predicate.

## 5. Consequence

Every packet is rebuilt to bind core registry 0.7.0, as after any meta-schema change; a packet
binding 0.6.0 names a meta-schema a checker that knows only 0.7.0 does not select. No table's values
change, because no packet scanned in §2.4 holds a non-finite value or a slope that is zero or
negative. A writer publishing a non-finite value in a float column now fails validation instead of
passing it; the reference writer's adapters that pass source floats through unchanged, such as the
sorter's spike amplitudes, reach the new check only on such a value.

The meta-schema change is incompatible, so the core registry and each of the four repository
extension registries name meta-schema 0.7.0. Core's `registry_version` becomes 0.7.0, and each
extension advances its own from the 0.6.0 or 0.7.0 it carries now. No accepted clause is
superseded. R101 §3.10's statement that NaN reaches every float column is narrowed by §3.1, and its
ledger entry gains a note. The seven ledger destinations that name an affected section by number
move to its anchor: those of R2 §§8 and 9 and R57 §§2.1 and 2.2 at Part 02 §9.2, R92 §2.1 at
Part 02 §10.1, R107 §3.1 at Part 02 §3, and R101 §3.10 at Part 03 §5.6.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. The property constrains a logical column's value space, not a concept's meaning. | None required. |
| logical prose and registry | The new last subsection of Part 02 §5 and Part 02 §3's new row take §3.1; Part 02 §10.1 takes §3.2; Part 02 §§9.2 and 9.4 take §3.3. The meta-schema and descriptor take §3.3; the core registry build source takes §3.4's 26 declarations; `registry/rules.json` takes §3.5's rule. `registry/build.py` and `registry/check.py`, which name the three identifiers, follow them, and the vendored meta-schema and descriptor regenerate. | `evidence/R<N>.json` names each anchor and the meta-schema, descriptor, declaration, and rule pointers; `registry/check.py` passes. |
| physical profiles | Part 03 §5.6 says NaN reaches only a column declaring `finite: false`. | `evidence/R<N>.json` names the anchor. |
| packet manifest and JSON Schemas | Unchanged. No manifest field names a column property; the registry meta-schema changes under the row above. | None required. |
| validation and import | Part 05 §5.1 lists the finiteness check. Part 05 §5.4 already extends it to extension columns, and Part 11 already defines `isfinite`. | The corpus variants below. |
| extensions | Each of the 79 float columns of the four repository extension registries declares `finite: true`; each registry names meta-schema 0.7.0 and advances its own `registry_version`. The `aind_unit_qc` adapter in `escapewheel-aind` writes that registry's three tables and already writes every non-finite source value as null, so it is unchanged. No committed adapter writes the `aind_opto`, `dynamic_foraging`, or `vr_foraging` tables, so whether one emits a non-finite value is unknown beyond the session packets §2.4 scanned; an adapter that writes an uncomputable value as null already satisfies §3.1. | `registry/check.py` over every extension registry; the AIND suite, whose unit-QC tests assert that a NaN metric arrives as null, gains the same case for an infinite one. |
| reader, writer, validator, adapters | The validator generates §3.2's check and selects the v0.4 descriptor, and the validator and writer tests that pin meta-schema 0.6.0, the v0.3 descriptor, or core 0.6.0 follow the new identifiers. The writer's code is unchanged: its commit-time validation reports the finding, and its extension scaffold, which maps source float types to `float32` and `float64`, leaves `finite` to the extension author. The reader is unchanged; it may rely on the declaration and need not. | The validator suite and the corpus. |
| conformance fixtures and tests | A fixture variant with NaN in `core.clocks.tick_rate_hz` draws `core.clocks.tick_rate_hz.finite`; one with a child clock's `transform_slope` at -1 draws `core.clocks.transform_slope_positive`. Registry-checker cases reject a float column without `finite` and a string column with it. | `fixtures/corpus.py` and the registry-document tests. |
| revision process and tooling | The ordinary ledger and evidence records, and the seven numeric destinations move to anchors. `facts.py`, which names the v0.3 descriptor, and the interval-kinds probe, which names meta-schema 0.6.0, follow the new identifiers. The registry-codegen prototype's registry document, which `registry/check.py` validates against the meta-schema, names meta-schema 0.7.0 and declares `finite: true` on its one float column, `core.clocks.tick_rate_hz`. | `ledger.py`, `evidence.py`, and `registry/check.py`. |
| generated publications and developer documentation | `registry/render.py` shows `finite` in the Declares column of `registry/tables.md`, and the generated structure count in `registry/README.md` gains a finite-column line. The specification README's identifier table and its sentence naming the core registry version current packets use, the expected value `escapewheel_poc_docs_v0.2/framework.py` holds for that table, `registry/README.md`'s entry for the descriptor file, Part 08 §§2 and 3, the combined specification, and the heading index follow the new identifiers and anchors. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at the new Part 02 subsection, Part 02 §3, and Part 03 §5.6; §3.2 at Part 02 §10.1
and Part 05 §5.1; and §3.3 at Part 02 §§9.2 and 9.4, each by canonical anchor. §§3.4 and 3.5 are
`registry`, with targets in the core registry's column declarations and `registry/rules.json`.

These cases distinguish the new rules from the current ones:

- a clock with `tick_rate_hz` NaN draws `core.clocks.tick_rate_hz.finite` at `error`, where the
  current validator reports nothing;
- a clock with `tick_rate_hz` positive infinity draws the same finding, where
  `core.clocks.tick_rate_positive` passes it;
- a child clock with `transform_slope` -1 or 0 draws `core.clocks.transform_slope_positive`, where
  every current rule passes it;
- an extension table holding NaN in a float column draws that extension's
  `<declaration_id>.<column>.finite`, attributed to the extension;
- a registry declaring a `float64` column without `finite`, or a `string` column with it, fails the
  shape phase under meta-schema 0.7.0; and
- a registry naming meta-schema 0.6.0 selects no incorporated descriptor.

The positive case is the valid corpus packet, which draws neither new finding. A null in a
`finite: true` column draws no finiteness finding, which a validator test asserts beside a NaN in
the same column.
