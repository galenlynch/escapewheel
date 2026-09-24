# A validator checks every unit value against UCUM

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-23 |
| **Based on** | `7bee7a43d8ed0a2e10ba8a1dc449437d4b972d5b` |
| **Decision domain** | specification |
| **Affects** | Part 02 §§8.4, 9.3, and 13; Part 05 §5.3; the reference validator; the writer's NWB, sorter, and waveform sources |
| **Depends on** | [A packet passes only when its manifest, core, and every bound extension pass](a-packet-passes-only-when-its-manifest-core-and-every-bound-extension-pass.md), for the subject a finding is attributed to |

## 1. Problem

Part 02 §8.4 requires row values to be UCUM codes: a column holding a physical unit holds a UCUM
code. A column declaring `unit_from` names such a column, and Part 02 §8.4 requires that
target to be a string column whose `authority` includes `https://ucum.org/ucum`. Registry
validation checks the declaration and parses every literal `unit` under UCUM 2.2, dated
2024-06-17. Part 02 §13 then leaves the values: "row values selected by `unit_from` are validated
with packet data rather than as registry declarations". No packet check does so.

Part 02 §9.3 also appears to forbid the check, since it bars a validator from rejecting a value for
being absent from a column's authority. A UCUM code is not drawn from an enumerable list, since UCUM is a
grammar over prefixes, atoms, and operators, but the clause does not make that distinction.

The writer emits values that are not UCUM codes, and nothing reports them.

## 2. Evidence

- **Which columns hold units.** In the core registry, 9 columns declare the UCUM authority, and
  the same 9 are the targets of every `unit_from`: `unit` in `core.array_assets`,
  `analysis.array_assets`, `core.array_channels`, and `core.coordinate_frame_axes`;
  `coordinate_unit` in `core.array_dimensions` and `analysis.array_dimensions`; `input_unit` and
  `output_unit` in `core.calibrations`; and `core.units.amplitude_unit`. The four example extension
  registries declare neither. Counted from `registry/logical_schemas.json` and
  `registry/extensions/*.json` at the baseline.
- **What real packets hold.** Two local development packets, for sessions 776259 and 786867,
  were built by the writer before the registry-binding manifest; their Parquet tables are still
  readable. Each distinct non-null value of the 9 columns was parsed with the validator's UCUM 2.2
  parser:

  | column | 776259 | 786867 |
  |---|---|---|
  | `core.array_assets.unit` | `volts` ×12 (invalid), `uV` ×2 | `volts` ×10 (invalid), `uV` ×1 |
  | `core.array_dimensions.coordinate_unit` | `sample` ×2 (invalid), null ×28 | `sample` ×1 (invalid), null ×22 |
  | `core.calibrations.input_unit`, `output_unit` | `s`, `ul` | `s`, `ul` |
  | `core.coordinate_frame_axes.unit` | `um` ×5 | `um` ×5 |
  | `core.units.amplitude_unit` | `uV` ×6,781 | `uV` ×4,505 |

  `core.array_channels.unit` is null in every row, and neither packet carries an analysis array.
- **Where the invalid values come from.** The NWB source copies an acquisition series' `unit`
  attribute, whose NWB convention is `volts`; the waveform source writes `coordinate_unit: "sample"`
  for its sample axis; and the sorter and waveform sources write `adc` when an analyzer does not
  return microvolts. `adc`, `sample`, `volts`, `Volts`, and `µV` fail the parser, and `V`, `uV`,
  `{adc}`, and `{sample}` pass. No rule, reader, or consumer compares these literal spellings.
- **The parser is always present.** `ucumvert` is a required dependency of the reference
  validator, and its registry check reports `unsupported` rather than a finding when the exact UCUM
  edition is unavailable.

## 3. Desired outcome and constraints

A packet whose unit column holds a value that is not a UCUM code fails validation, with a finding
naming the column and the value, attributed to the registry that declares the column. The
resolution preserves:

- Part 02 §9.3's rule that an authority names a nomenclature without making an unrecognized value an
  error, for every authority other than UCUM;
- Part 02 §13's offline rule: no identifier is dereferenced;
- the registry, its meta-schema, and the registry contract unchanged; and
- a null unit, which presence rules and Tier 2 rules such as `core.units.amplitude_unit_declared`
  already govern.

## 4. Options and tradeoffs

### 4.1 Which columns are scanned

**Every `unit_from` target.** Follows §8.4's requirement on targets exactly. It
misses a column that declares the UCUM authority without another column depending on it.

**Every column whose `authority` includes `https://ucum.org/ucum`.** The authority entry is how a
declaration says a column holds unit codes, and §8.4 already requires every `unit_from` target to
carry it, so this set contains the first. This proposal prefers it. The two sets are identical in
every registry today, so the choice changes no current outcome.

### 4.2 How severe a finding is

**`warning`.** No packet would fail, and the invalid values above would be reported without a
rebuild. It leaves a requirement of Part 02 §8.4 that a conforming packet can break.

**`error`.** The packet fails, as it would for any other violated requirement of Part 02. This
proposal prefers it; the cost is the writer changes in §4.4.

### 4.3 Where the check lives

**A Tier 2 rule.** The rule language has no UCUM function, and adding one would make a nomenclature
part of the SQL profile.

**A shim check under Part 05 §5.3.** The validator reads each distinct non-null value of each
scanned column and parses it under the UCUM edition Part 02 §13 selects. This proposal prefers it.
Where that edition is unavailable, or a table is unreadable, the evaluation is `incomplete` under
Part 05 §9.4 rather than a finding. The cost is proportional to the distinct values, which number
at most two per column in the packets above.

### 4.4 How the writer's values become UCUM codes

**Each source maps its own spellings.** The NWB source maps NWB's unit names to UCUM (`volts` to
`V`), and the sorter and waveform sources write `{adc}` and `{sample}`, which Part 02 §8.4 already
names as the form for a dimensionless count. A spelling a source cannot map reaches the packet
unchanged, fails validation, and the writer refuses to publish. This proposal prefers it: source
spellings are source-format knowledge, which belongs to the source that reads the format, and
Part 02 §9.3 already requires a writer to "spell a value as the named nomenclature does".

**A recipe-level unit map.** A recipe could declare replacements, as `[overrides]` does for facts.
That puts a fixed property of a file format into every recipe that reads it.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. UCUM remains the unit nomenclature. |
| logical prose, registry meta-schema, registry declarations, and declarative rules | Part 02 §8.4 states which columns hold unit codes; §9.3 exempts UCUM from the non-rejection rule because UCUM is a grammar; §13 points the row-value check at Part 05. Meta-schema, declarations, and rules unchanged. |
| physical profiles | Unchanged. |
| packet manifest and incorporated JSON Schemas | Unchanged. |
| validation and import | Part 05 §5.3 gains one shim check with a named check ID, at `error`. |
| extension registries | Unchanged. None declares a UCUM column; one that does is checked the same way. |
| reader | Unchanged. |
| writer | The NWB, sorter, and waveform sources emit UCUM codes. |
| validator | One shim check over the distinct values of every UCUM-authority column, attributed to the declaring registry. |
| adapters and code generation | Out-of-process adapters are unchanged; a value they deliver is checked like any other. |
| existing packets and migration | Both development packets fail until rebuilt, on 14 and 11 rows respectively. They predate the registry-binding manifest and are rebuilt regardless. Fixtures are regenerated. |
| conformance fixtures and tests | Add a corpus variant holding `volts` in `core.array_assets.unit`, a passing packet using `V` and `{sample}`, a null unit that produces no finding, and source tests for each mapping. |
| revision lifecycle, ledger, evidence, and process tooling | Unchanged except for the ordinary revision and evidence records. |
| generated publications and developer documentation | The combined specification regenerates. |

## 6. Open questions

1. **Scan set.** Scan every column declaring the UCUM authority rather than only `unit_from`
   targets (§4.1)?
2. **Severity.** Report a non-UCUM value at `error` (§4.2)?
3. **Normalization.** Have each source map its own spellings to UCUM, with an unmappable value
   refused through validation (§4.4)?

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
