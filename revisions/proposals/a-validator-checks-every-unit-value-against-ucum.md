# A validator checks every unit value against UCUM

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-23 |
| **Based on** | `7bee7a43d8ed0a2e10ba8a1dc449437d4b972d5b` |
| **Decision domain** | specification |
| **Affects** | Part 02 §§8.4, 9.3, and 13; Part 05 §5.3; the reference validator; the writer's NWB, sorter, and waveform sources |

## 1. Problem

A table column that holds a physical unit, such as `core.units.amplitude_unit`, supplies the unit of
another column through that column's `unit_from` declaration.
[Part 02 §8.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-unit-and-clock-context)
requires such a column to hold UCUM codes and requires every `unit_from` target to be a string
column whose `authority` includes `https://ucum.org/ucum`. Registry validation checks those
declarations and parses every literal `unit` under UCUM 2.2, dated 2024-06-17.
[Part 02 §13](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-logical-schema-normative-references)
then assigns the row values to packet validation, and no packet check reads them.

[Part 02 §9.3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-vocabularies)
appears to forbid such a check, because it bars a validator from rejecting a value for being absent
from a column's authority. The clause does not distinguish an authority that lists its values from
UCUM, whose codes a grammar of prefixes, atoms, and operators defines.

This decision depends on
[A packet passes only when its manifest, core, and every bound extension pass](a-packet-passes-only-when-its-manifest-core-and-every-bound-extension-pass.md)
for the registry a unit finding is attributed to.

## 2. Evidence

All observations below were reproduced at the recorded baseline.

### 2.1 Nine core columns hold units

The core registry declares the UCUM authority on 9 columns, and the same 9 are the targets of every
`unit_from`: `unit` in `core.array_assets`, `analysis.array_assets`, `core.array_channels`, and
`core.coordinate_frame_axes`; `coordinate_unit` in `core.array_dimensions` and
`analysis.array_dimensions`; `input_unit` and `output_unit` in `core.calibrations`; and
`core.units.amplitude_unit`. The four example extension registries declare neither. The counts come
from `registry/logical_schemas.json` and `registry/extensions/*.json`.

### 2.2 Both development packets hold invalid unit codes

Two local development packets, for sessions 776259 and 786867, were built by the writer before the
registry-binding manifest, and their Parquet tables remain readable. Each distinct non-null value of
the 9 columns was parsed with the validator's UCUM 2.2 parser:

| column | 776259 | 786867 |
|---|---|---|
| `core.array_assets.unit` | `volts` ×12 (invalid), `uV` ×2 | `volts` ×10 (invalid), `uV` ×1 |
| `core.array_dimensions.coordinate_unit` | `sample` ×2 (invalid), null ×28 | `sample` ×1 (invalid), null ×22 |
| `core.calibrations.input_unit`, `output_unit` | `s`, `ul` | `s`, `ul` |
| `core.coordinate_frame_axes.unit` | `um` ×5 | `um` ×5 |
| `core.units.amplitude_unit` | `uV` ×6,781 | `uV` ×4,505 |

`core.array_channels.unit` is null in every row, and neither packet carries an analysis array. The
invalid values occupy 14 rows of the first packet and 11 of the second.

### 2.3 Three writer sources emit the invalid spellings

The NWB source copies an acquisition series' `unit` attribute, which NWB spells `volts`. The waveform
source writes `sample` as the `coordinate_unit` of its sample axis. The sorter and waveform sources
write `adc` when an analyzer does not return microvolts. The parser rejects `adc`, `sample`,
`volts`, `Volts`, and `µV` and accepts `V`, `uV`, `{adc}`, and `{sample}`. No rule, reader, or
consumer compares these literal spellings.

### 2.4 The reference validator always holds the parser

`ucumvert` is a required dependency of the reference validator. Its registry check reports
`unsupported`, not a finding, when the exact UCUM edition is unavailable, so a row check can report
the same state.

## 3. Desired outcome and constraints

A packet whose unit column holds a value that is not a UCUM code fails validation, with a finding
naming the column and the value, attributed to the registry that declares the column. The
resolution preserves:

- Part 02 §9.3's rule that an authority names a nomenclature without making an unrecognized value an
  error, for every authority other than UCUM;
- Part 02 §13's rule that validation is offline and dereferences no identifier;
- the registry, its meta-schema, and the registry contract; and
- the treatment of a null unit, which presence rules and Tier 2 rules such as
  `core.units.amplitude_unit_declared` already govern.

## 4. Options and tradeoffs

### 4.1 Scanned columns

**Scan every `unit_from` target.** This follows Part 02 §8.4's requirement on targets exactly, and
misses a column that declares the UCUM authority without another column depending on it.

**Scan every column whose `authority` includes `https://ucum.org/ucum`.** The authority entry is how
a declaration says a column holds unit codes, and Part 02 §8.4 already requires it of every
`unit_from` target, so this set contains the first. This proposal prefers it. The two sets are equal
in every registry today, so the choice changes no current outcome.

### 4.2 Finding level

**Report a non-UCUM value at `warning`.** No packet fails and the values in §2.2 are reported without
a rebuild, but a conforming packet could then break a requirement of Part 02 §8.4.

**Report it at `error`.** The packet fails, as it does for any other violated requirement of Part 02.
This proposal prefers it; the cost is the writer changes in §4.4.

### 4.3 Check layer

**Express the check as a Tier 2 rule.** The rule language has no UCUM function, and adding one would
make a nomenclature part of the SQL profile.

**Make it a shim check under
[Part 05 §5.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-shim).** The
validator reads each distinct non-null value of each scanned column and parses it under the UCUM
edition Part 02 §13 selects. Where that edition is unavailable, or a table is unreadable, the
evaluation is `incomplete` under
[Part 05 §9.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-incomplete-validation)
rather than a finding. The cost grows with the number of distinct values, at most two per column in
the packets of §2.2. This proposal prefers it.

### 4.4 Source spellings

**Map spellings in each source.** The NWB source maps NWB's unit names to UCUM, `volts` to `V`, and
the sorter and waveform sources write `{adc}` and `{sample}`, curly-brace annotations that Part 02
§8.4 already admits as dimensionless UCUM codes. A spelling a source cannot map reaches the packet
unchanged, fails validation, and stops publication. This proposal prefers it. A source spelling is
knowledge of a file format, which belongs to the source that reads the format, and Part 02 §9.3
already requires a writer to spell a value as the named nomenclature does.

**Declare a unit map in the recipe.** A recipe could declare replacements, as `[overrides]` does for
declared facts, but every recipe reading a format would then repeat a fixed property of that format.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. UCUM remains the unit nomenclature. |
| logical prose, registry meta-schema, registry declarations, and declarative rules | Part 02 §8.4 states which columns hold unit codes; §9.3 exempts UCUM from the non-rejection rule because a grammar defines its codes; §13 points the row check at Part 05. Meta-schema, declarations, and rules unchanged. |
| physical profiles | Unchanged. The check reads logical values. |
| packet manifest and incorporated JSON Schemas | Unchanged. No manifest field carries a unit. |
| validation and import | Part 05 §5.3 gains one shim check, with a named check ID, at `error`. |
| extension registries | Unchanged. None declares a UCUM column, and one that does is checked the same way. |
| reader | Unchanged. A reader does not validate unit values. |
| writer | The NWB, sorter, and waveform sources emit UCUM codes. |
| validator | One shim check over the distinct values of every UCUM-authority column, attributed to the declaring registry. |
| adapters and code generation | Out-of-process adapters are unchanged; a value they deliver is checked like any other. |
| existing packets and migration | Both development packets fail until rebuilt, on 14 and 11 rows. They predate the registry-binding manifest and are rebuilt regardless. Fixtures are regenerated. |
| conformance fixtures and tests | Add a corpus variant holding `volts` in `core.array_assets.unit`, a passing packet using `V` and `{sample}`, a null unit that produces no finding, and a source test for each mapping. |
| revision lifecycle, ledger, evidence, and process tooling | Unchanged except for the ordinary revision and evidence records. |
| generated publications and developer documentation | The combined specification regenerates. |

## 6. Resolved direction

1. A validator scans every non-null value of every column whose `authority` includes
   `https://ucum.org/ucum`, parsing it under the UCUM edition Part 02 §13 selects.
2. A value that does not parse is an `error`, attributed to the registry declaring the column.
   Part 02 §9.3's rule against rejecting a value absent from an authority does not apply to UCUM,
   whose codes a grammar defines rather than a list.
3. The check is a Part 05 §5.3 shim check. An unavailable UCUM edition or an unreadable table
   makes the evaluation `incomplete` rather than producing a finding.
4. Each writer source maps its own spellings to UCUM: `volts` to `V`, `adc` to `{adc}`, and
   `sample` to `{sample}`. A spelling a source cannot map fails validation, and the writer refuses
   to publish the packet.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
