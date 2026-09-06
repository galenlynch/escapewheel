# R4 — Schema Reconciliation

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02_core_logical_schemas.md`, `09_metadata_minimalism_and_extensions.md` |
| **Blocks** | R2 (schema registry) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`09` §4 restates required and recommended field lists for several core tables that `02`
defines independently. Where the two disagree, the column set is undefined, and a machine-
readable schema registry (R2) cannot be written against an undefined column set.

This revision reconciles those disagreements and resolves the remaining type ambiguities in
`02`. It adds no fields and changes no semantics.

## 2. Scope of the disagreement

A mechanical sweep of both documents establishes the bound
(`conformance/spec-sweep/`, §6):

```text
02 defines            22 tables, 196 columns
09 §4 restates         5 tables, 39 field claims
                       (array_assets, clocks, processing_runs, sessions, subjects)
02 tables not restated in 09 §4                            17
fields named in 09 but absent from 02                       5
requirement-level mismatches (09 MUST vs 02 optional)        0
```

The drift surface is small because `09` duplicates only five tables' field lists, and no
claim conflicts on requirement level — every disagreement is a field `09` names that `02`
does not define.

`09` §4.4 (devices, probes, electrodes, channels) is descriptive prose spanning several
tables rather than a field-list restatement. It names concepts — "channel label or channel
ID", "electrode coordinates", "coordinate frame" — not columns. It is NOT normative as to
column names, and MUST NOT be read as defining any.

## 3. Resolutions

`02` is authoritative in each case and `09` is corrected. `02` is the schema definition;
`09` is a policy document that restates schemas for illustration.

### 3.1 `core.clocks` — `exact_tick_rate`

`09` §4.3 requires "`tick_rate_hz` or `exact_tick_rate`". No field named `exact_tick_rate`
exists. `02` expresses the exact form as two columns, `tick_rate_num` and `tick_rate_den`.

**Resolution:** strike `exact_tick_rate` from `09` §4.3; the requirement reads
"`tick_rate_hz`, or both `tick_rate_num` and `tick_rate_den`", matching `02`'s existing
validation rule.

### 3.2 `core.clocks` — `sync_quality`, `sync_method`

`09` §4.3 lists both as SHOULD-include. Neither is defined in `02`.

**Resolution:** strike both from `09` §4.3. Synchronization *quality* is quality-control
metadata, not information required to interpret a tick, so it belongs in `core.clocks.metadata`
under `09`'s own tier-3 rule. This is narrower than R3 §3.4, which promotes the alignment
*transform* to typed columns because interpretation depends on it.

### 3.3 `core.processing_runs` — `created_at`

`09` §4.6 lists `created_at` as SHOULD-include. `02` defines `started_at` and `ended_at`.

**Resolution:** strike `created_at` from `09` §4.6, replacing it with `started_at`. A
processing run has a start and an end; a separate creation time duplicates the start.

### 3.4 `core.subjects` — `age_at_session`

`09` §4.1 lists "`date_of_birth` or `age_at_session`". No `age_at_session` field exists in
`02`.

**Resolution:** strike `age_at_session` from `09` §4.1.

The case for the field is recorded here rather than lost. `01` permits sensitive subject
metadata to be redacted, and an age is less identifying than a date of birth, so a packet
withholding `date_of_birth` has no way to express age. Adding it is nonetheless a new field
rather than a reconciliation, and `age_at_session` is session-relative while `core.subjects`
is not session-scoped, so it would belong on `core.sessions`. Deferred; raise separately if a
packet requires redaction.

### 3.5 `09` inline type annotations

`09` §4.1 and §4.2 annotate the optional metadata field as `metadata: struct/map/json`.
R3 §2.1 withdraws struct and map.

**Resolution:** amend both to `metadata: json_string`.

### 3.6 `core.subjects.date_of_birth` — ambiguous scalar type

`02` types this column `date or timestamp`. It is the only ambiguous scalar type in `02`;
every other disjunction is a nested-type alternative withdrawn by R3 §2.1.

**Resolution:** pin to `date`. A birth date has no meaningful time-of-day component, and R3
§2.1 pins the physical encoding to Parquet `DATE` (int32 days since the Unix epoch).

## 4. Conditional requirements

Three columns carry requirement level `conditional` rather than `yes`/`no`:
`core.clocks.tick_rate_hz`, `tick_rate_num`, `tick_rate_den`.

This is not drift — `02`'s validation rule states the condition ("either `tick_rate_hz` OR
both `tick_rate_num` and `tick_rate_den` MUST be present"). It is recorded here because the
registry (R2) must express it, and a two-state required flag cannot. R2's three-state
nullability model MUST accommodate a conditional whose predicate references sibling
columns, or express this particular case as a named cross-column validation rule.

## 5. What the sweep found compliant

Recorded so that R2 need not re-derive it, and so that a future sweep can detect regression.

Against R3's rules, `02` is otherwise compliant:

- **Nested types.** 31 columns use `list`, `struct`, `map`, or `json_string`. All 31 are
  accounted for in R3 §2.2; none is unlisted.
- **Tick columns.** 7 columns end in `_tick`. All are already `int64`, consistent with
  R3 §2.1.
- **Wall-clock columns.** 10 columns are `timestamp` or `date`, all of them administrative
  or provenance times. None carries experimental time, confirming R3 §2.1's scoping of the
  timestamp rule to wall-clock columns is both correct and complete.
- **Index columns.** 6 end in `_index`. R3 §6 classifies five; the sixth,
  `core.unit_spike_chunks.chunk_index`, is withdrawn with its table under R3 §4.

## 6. Reproducing the sweep

`conformance/spec-sweep/` parses both documents and reports drift, requirement mismatches,
and R3 compliance. Re-run it after any revision touching `02` or `09`.

```bash
python3 conformance/spec-sweep/sweep.py       # 09 vs 02 drift
python3 conformance/spec-sweep/compliance.py  # 02 vs R3 rules
```

## 7. Resulting table count

For R2's registry, after R3 and R5:

```text
02 as written                                    22
  - core.unit_spike_chunks   (R3 §4 / R5)        -1
  + core.trial_tags          (R3 §3.2)           +1
  + core.array_dimensions    (R3 §3.3)           +1
  + core.session_experimenters (R3 §3.1)         +1
                                                 --
                                                 24
```
