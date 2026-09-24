# A Validator Checks Every Unit Value Against UCUM

| | |
|---|---|
| **Status** | **Accepted** 2026-09-23 |
| **Based on** | `cd2a612ed689c937e76518b2f36c0c0c6f74df18` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§8.4, 9.3, and 13; Part 05 §5.3 |
| **Depends on** | None |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3 |

Section 3 is normative. Sections 1, 2, and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A table column holding a physical unit, such as `core.units.amplitude_unit`, supplies the unit of
another column through that column's `unit_from` declaration.
[Part 02 §8.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-unit-and-clock-context)
requires such a column to hold UCUM codes, but no check reads its values:
[Part 02 §13](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-logical-schema-normative-references)
assigns them to packet validation, and
[Part 05 §5.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-shim)
defines no such check.
[Part 02 §9.3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-vocabularies)
appears to forbid one twice. It bars a validator from rejecting an unrecognized value of an `open`
column, which every unit column is, and from rejecting a value for being absent from a column's
authority. Neither rule distinguishes an authority that lists its values from UCUM, whose codes a
grammar defines.

This revision names the columns that hold unit codes, exempts them from both non-rejection rules,
and adds a shim check that fails a packet holding a value that is not a code. The check covers the
tables the core registry declares, which hold every unit column in the current registries, and its
findings are core's.
[Part 05 §14.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validator-registry-boundary)
leaves extension-table byte validation undefined, and this revision does not define it.

The change is structural because it replaces sentences inside four existing sections: the
§8.4 rule on unit columns, the §9.3 non-rejection rules, the §13 statement of where the UCUM grammar
applies, and the §5.3 list of shim checks. Appending new sections would leave each current sentence
stating a narrower or contrary rule beside its replacement.

### 1.1 Structural crosswalk

Every affected section already carries a canonical anchor, so no anchor bootstrap is needed.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 02 §8.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-unit-and-clock-context), a `unit_from` target is a string column carrying the UCUM authority, and a column holding a physical unit holds a UCUM code | replace in place | same section | defines a unit column, requires a UCUM 2.2 code in each of its non-null values and in each literal `unit`, and keeps the annotation rule | §3.1 |
| [Part 02 §9.3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-vocabularies), the vocabulary table's `open` row, under which a validator rejects no unrecognized value, and the sentence under which a validator neither dereferences an authority URI nor rejects a value absent from it | replace in place | same section | neither non-rejection rule covers a unit column's value that is not a unit code, and the dereference prohibition names packet validation as well as registry validation; the naming rule and writer spelling rule are unchanged | §3.2 |
| [Part 02 §13](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-logical-schema-normative-references), UCUM applies to literal `unit` declarations, and row values are validated with packet data | replace in place: the UCUM entry says unit codes use its syntax, and the closing paragraph becomes citations of Part 02 §9.3 and Part 05 §5.3 | Part 02 §§8.4 and 9.3, and Part 05 §5.3 | UCUM applies to every unit code; the dereference prohibition extends to packet validation and is stated once, in §9.3; the packet check is Part 05 §5.3's | §§3.1–3.3 |
| [Part 05 §5.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-shim), the shim's checks | extend in place with one paragraph after the session-inventory check | same section | adds the unit-code check | §3.3 |

## 2. Background

Section 2 is informative. The measurements were rerun at the recorded baseline.

### 2.1 Nine core columns hold units

The core registry declares the UCUM authority on 9 columns, and the same 9 are the targets of every
`unit_from`: `unit` in `core.array_assets`, `analysis.array_assets`, `core.array_channels`, and
`core.coordinate_frame_axes`; `coordinate_unit` in `core.array_dimensions` and
`analysis.array_dimensions`; `input_unit` and `output_unit` in `core.calibrations`; and
`core.units.amplitude_unit`. The four example extension registries declare no UCUM authority and
no `unit_from`, though they carry 52 literal `unit` declarations. The counts come from
`registry/logical_schemas.json` and `registry/extensions/*.json`.

### 2.2 Both development packets hold invalid unit codes

Two local development packets, for sessions 776259 and 786867, were built by the writer before the
registry-binding manifest, and their Parquet tables remain readable. Each value of the 9 columns
was parsed with `ucumvert` 0.3.2, the validator's UCUM 2.2 parser:

| column | 776259 | 786867 |
|---|---|---|
| `core.array_assets.unit` | `volts` ×12 (invalid), `uV` ×2 | `volts` ×10 (invalid), `uV` ×1 |
| `core.array_dimensions.coordinate_unit` | `sample` ×2 (invalid), null ×28 | `sample` ×1 (invalid), null ×22 |
| `core.calibrations.input_unit` | `s` ×2, null ×1 | `s` ×2 |
| `core.calibrations.output_unit` | `ul` ×2, null ×1 | `ul` ×2 |
| `core.coordinate_frame_axes.unit` | `um` ×5 | `um` ×5 |
| `core.units.amplitude_unit` | `uV` ×6,781 | `uV` ×4,505 |

`core.array_channels.unit` is null in all 1,152 and 960 rows, and neither packet carries an
analysis array. The invalid values occupy 14 rows of the first packet and 11 of the second, and
each column holds at most two distinct values.

### 2.3 Four writer sources emit the invalid spellings

Every `volts` row in both packets is an LFP asset. The writer's LFP source copies the `unit`
attribute of an NWB electrical series, which NWB spells `volts`, and its NWB source copies the same
attribute for an acquisition series. The waveform source writes `sample` as the `coordinate_unit` of
its sample axis. The sorter and waveform sources write `adc` when an analyzer does not return
microvolts. The parser rejects `adc`, `sample`, `volts`, `Volts`, and `µV`, and accepts `V`, `uV`,
`{adc}`, and `{sample}`. No rule, reader, or consumer compares these literal spellings. The AIND
session source in `escapewheel-aind` copies a calibration's parenthesized unit label unchanged; the
labels in both packets, `s` and `ul`, are codes.

Part 02 §9.3 already requires a writer to spell a value as the named nomenclature does, so each
source maps its format's spelling: `volts` to `V`, `adc` to `{adc}`, and `sample` to `{sample}`.
The braces make `{adc}` and `{sample}` UCUM annotations, which denote dimensionless quantities, as
Part 02 §8.4 already allows. A spelling a source cannot map reaches the packet unchanged, fails the
check, and stops publication under Part 05 §9.2. Declaring a unit map in the session recipe was
rejected because every recipe reading one format would repeat a fixed property of that format.

### 2.4 A valid core registry already requires the UCUM edition

The core registry declares 9 literal `unit` values, and its registry check
`registry.unit.ucum_2_2_cs` parses them under UCUM 2.2, dated 2024-06-17. A validator lacking that
edition obtains an `unsupported` core result, and Part 05 §14.5 then directs no packet check. The
new check therefore runs only where the edition is present, and the reference validator already
depends on `ucumvert` to supply it.

### 2.5 Alternatives

A Tier 2 rule cannot express the check without adding a UCUM function to the rule language, which
would make a nomenclature part of the SQL profile. A `warning` would let a conforming packet break
Part 02 §8.4's requirement. Scanning only `unit_from` targets would miss a column that declares the
UCUM authority with no dependent column; the authority is how a declaration says a column holds
unit codes, and the two sets are equal in every current registry.

## 3. Decision

Three subsections define the columns holding unit codes, bound the rules against rejecting
unrecognized values, and add the packet check.

### 3.1 Unit codes

A **unit code** is an expression in the case-sensitive syntax of UCUM version 2.2, revision date
2024-06-17, as Part 02 §13 identifies it. A **unit column** is a string column whose `authority`
entries include `https://ucum.org/ucum`. A `unit_from` target MUST be a unit column. A column's
literal `unit` MUST be a unit code, and a packet MUST hold a unit code in every non-null value of a
unit column. An annotation in curly braces, such as `{adc}`, is a unit code and denotes a
dimensionless quantity, which is the unit of a quantity normalized by something the packet
measured.

### 3.2 Unrecognized values

An authority URI is identity rather than a fetch instruction. A validator MUST NOT dereference one
when checking a registry or a packet. A validator MUST NOT reject an unrecognized value of an
`open` column, and MUST NOT reject a value for being absent from its column's authority. Neither
prohibition covers a unit column's value that is not a unit code, which §3.1 makes nonconforming,
because UCUM defines its codes by a grammar rather than a list.

### 3.3 Unit-code check

The shim MUST parse each distinct non-null value of each unit column in every table resource whose
declaration the core registry holds, under the UCUM edition of §3.1. It MUST report each value that
is not a unit code at `error` under the check ID `<declaration_id>.<column>.ucum_code`, such as
`core.units.amplitude_unit.ucum_code`, naming that value once. The finding is core's. The shim
declares each such table as an input.

## 4. What this does not change

A null unit remains governed by presence rules and by Tier 2 rules such as
`core.units.amplitude_unit_declared`; §3.3 reads only non-null values. An unreadable table leaves
the evaluation incomplete under
[Part 05 §9.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-incomplete-validation)
rather than producing a finding.

## 5. Consequence

Packets holding `volts`, `adc`, or `sample` in a unit column become nonconforming. Both development
packets fail on 14 and 11 rows until rebuilt. They predate the registry-binding manifest and are
rebuilt regardless. No registry, meta-schema, registry contract, or manifest changes, so no
version identifier advances. The registry contract's anchors for `registry.context_source.resolves`,
`registry.unit.ucum_2_2_cs`, and `registry.authority.uri` keep their sections, whose registry-level
rules §§3.1–3.2 restate unchanged.

No accepted clause is superseded. R101 §§3.1 and 3.6 and R107 §3.3 keep their `applied`
dispositions, and §3.2 narrows them only at unit columns. R126 §3.9 left unit-column values to
packet validation, which §3.3 supplies.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. UCUM remains the unit nomenclature. | None required. |
| logical prose and registry | Part 02 §§8.4, 9.3, and 13 take §§3.1–3.3 in place. Declarations, meta-schema, rules, and the registry contract are unchanged, because the 9 unit columns already carry the authority. | `evidence/R131.json` names the three anchors; `columns.py` and the registry build are unchanged. |
| physical profiles | Unchanged. The check reads logical values. | None required. |
| packet manifest and JSON Schemas | Unchanged. No manifest field carries a unit. | None required. |
| validation and import | Part 05 §5.3 gains the unit-code check. | The corpus variant named under conformance fixtures. |
| extensions | Unchanged. No extension declares a unit column, and this revision does not define extension-table byte validation. | None required. |
| reader, writer, validator, adapters | The validator adds the §3.3 check. The writer's LFP and NWB sources map `volts` to `V`, the sorter and waveform sources write `{adc}`, and the waveform source writes `{sample}`. The AIND session source is unchanged, because its current labels are codes and a label that is not one fails the check. Out-of-process adapters are unchanged; a value they deliver is checked like any other. | Validator tests of the check; writer source tests of each mapping. |
| conformance fixtures and tests | Add a corpus variant holding `microvolts` in `core.units.amplitude_unit`, expecting `core.units.amplitude_unit.ucum_code` at `error`. The valid corpus packet, which already uses `uV` and `um`, stays valid. Rewrite the LFP, sorter, and waveform tests that assert the old spellings. | `fixtures/corpus.py` and the package suites. |
| revision process and tooling | Unchanged except for the ordinary revision and evidence records. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied`: §3.1 at Part 02 §§8.4 and 13, §3.2 at Part 02 §9.3, and §3.3 at Part 05
§5.3, each by its canonical anchor.

The negative case is the corpus variant holding `microvolts`, which the current validator accepts
and the revised one reports. Validator tests add a packet whose unit columns hold `V` and
`{sample}` with no finding, a null unit with no finding, and a value repeated across rows reported
once. Writer tests assert that the LFP and NWB sources write `V` for an NWB `volts` series, that the
sorter and waveform sources write `{adc}` for an analyzer that does not return microvolts, and that
the waveform source's sample axis carries `{sample}`. A rebuild of either development packet passes
the check.
