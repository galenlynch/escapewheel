# R48 — A Column Declares Its Role

| | |
|---|---|
| **Status** | **Proposed** 2026-09-02 |
| **Amends** | R2 §3 (the registry's column object); R3 §6 (the index-base taxonomy) |
| **Depends on** | R2 (the registry format), R3 (the cross-language floor), R8 (source labels are strings), R29 (`since`), R45 (a tick is a coordinate) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R3 §6 settled the base of every index-like column, and settled it as a cross-language decision
rather than a host-language one:

> **Structural indices** address positions in a stored resource. These MUST be 0-based offsets.
> Clients converting to 1-based languages MUST convert at the boundary.

**A client cannot tell which columns those are.** The obligation is real, it is stated in prose,
and nothing in a packet expresses it — so a Julia, R or MATLAB binding must carry a hard-coded
list of columns to convert, maintained by hand against a specification it cannot read. That is
the same failure the format avoids everywhere else: R2 §7 makes rules data so a validator need
not encode them, and this is the one obligation left encoded in a document.

**The taxonomy has also fallen behind.** R3 §6 names two kinds and lists three columns each.
Since then: `anchor_index` (R13), three `interval_index` (R18, R25, R38) and `channel_ordinal`
(R28) were added and fit neither list, and R45 §2.5 identified a third kind — the *coordinate* —
which is why R38's prose could describe a `stop_tick` wrongly without contradicting anything.

The symptom is measurable. **Seven columns added since R3 §6 each restate "0-based" in their own
description**, because an author facing two categories that did not fit reasonably wrote the base
inline instead of citing it. The rule is now stated seven times and centrally once, and nothing
checks that the eight agree. Meanwhile two of the three columns R3 §6 *does* list —
`channel_index` and `frame_index` — say nothing about base at all.

## 2. Decision

### 2.1 Every column declares a role

The registry's column object gains `role`, **required**, from a closed vocabulary. `since: R48`.

| role | meaning | obligation on a consumer |
|---|---|---|
| `data` | a measured or declared value | none beyond its type |
| `identifier` | an opaque handle naming a row, here or in another table | MUST NOT be parsed for meaning, or used as an offset |
| `coordinate` | a point on a clock's axis, whose zero `core.clocks.origin` declares | MUST NOT be re-based (R45 §2.5); differences are base-free |
| `structural_index` | a 0-based offset addressing a position in a stored resource | a 1-based client MUST convert at the boundary (R3 §6) |
| `sequence_position` | a 0-based position ordering rows within a partition | MUST NOT be used as an offset into any resource |

The vocabulary is **closed**, unlike `activity_type` or `event_type`. A consumer derives behaviour
from a role — which columns to convert, which to leave alone — so an unrecognised value would be
unsafe rather than merely unknown. Adding a role is a revision.

### 2.2 Required, with no default

`role` is required on every column and has no default. A registry that omits one for any column
is invalid.

This is the whole of the enforcement, and the reason it is not merely a rule: **a default would
make a forgotten classification indistinguishable from a deliberate one.** If absent meant `data`,
a new offset column that nobody classified would silently declare itself base-free, which is
exactly the drift this revision exists to stop. A generator SHOULD therefore take the role as a
required argument, so that adding a column without deciding is an error where the column is
written rather than a finding later.

### 2.3 What it replaces in R3 §6

R3 §6's two categories become the vocabulary above, and its lists become data. Specifically:

- **Structural indices** keep their meaning and their obligation verbatim; the list moves into
  the registry as `role: structural_index`.
- **Source labels are not a role.** R3 §6 defined them as *"integers copied verbatim from
  acquisition or sorting software"* whose base is unknown, and the hazard was such an integer
  being used as an offset. **R8 §2 removed the hazard by changing the type**: `local_*_label` are
  `string`, and a string cannot be an offset. Where a type can enforce a distinction, the type
  enforces it and no role is needed. They are `data`.

R3 §6's prose is retained as the rationale for `structural_index`; what changes is that the
classification is no longer only prose.

### 2.4 A description states meaning, not base

A column whose role is declared **SHOULD NOT** restate its base in its description. The seven that
do today are the symptom §1 measures, and the role makes them redundant.

## 3. What a role is not

- **Not derivable from the keys.** `identifier` in particular: 20 `_id` columns appear in no
  primary key and no reference — `core.sorting_runs.probe_id` and
  `core.curation_versions.sorting_run_id` among them — and 19 columns appear in a key or a
  reference without being identifiers, being composite-key members like `axis_index`, `t_tick`,
  `tag` and `experimenter`. The near-match of 108 against 109 is a coincidence, not a derivation.
  (R46 declares sixteen of those references; it does not change this, since a composite key still
  contains non-identifiers.)
- **Not derivable from the type.** All 110 identifiers are `string`, but so are `name`,
  `event_type` and `coordinate_frame`, which are not identifiers.
- **Not derivable from the name.** `step_ticks` is a *count of ticks* — a duration under R33's
  rational step — and `t_tick` is a coordinate. One letter separates them. A name heuristic gets
  this right by luck, which is the argument for declaring rather than inferring.
- **Not a validation rule.** No Tier 1 or Tier 2 check is generated from a role. It describes what
  a column *is*, so that a consumer can decide what to do with it.

## 4. Cost

Over the registry as it stands, 293 columns:

| role | columns |
|---|---:|
| `data` | 153 |
| `identifier` | 110 |
| `coordinate` | 20 |
| `structural_index` | 6 |
| `sequence_position` | 4 |

**Ten columns require a human decision.** The other 283 follow from two conventions the
specification already fixes: `_id` names a stable ID and `_tick` names a tick value. The ten are
the six structural indices and the four sequence positions, each already carrying its base in its
own description.

Every packet already written stays valid: `role` describes columns whose values are unchanged, and
a packet embeds the registry it was written against (R2 §8), so an older packet keeps validating
against an older registry with no role at all.

## 5. Relationship to R47

Independent. R47 strikes the three `interval_index` columns, which would leave
`sequence_position` with one member, `core.clock_anchors.anchor_index`. The role survives that:
it is a real kind — a position in a logical sequence rather than an offset into a stored
resource — R13 §3's interpolation uses it operationally, and an R17 extension may add more. If
R47 is not accepted, the three `interval_index` columns are `sequence_position` as well.

Neither revision depends on the other landing.

## 6. Open

- **Whether `scope` is an identifier.** `core.preferred_runs.scope` and
  `core.processing_runs.scope` (R41 §2.3, R44 §2.1) hold an identifier's *value* — a `probe_id`,
  an `array_asset_id`, a camera — but their referent's table varies by row, which is why neither
  revision could declare a foreign key for them. Calling them `identifier` would be true of the
  values and misleading about the reference. Left as `data` here; a `polymorphic_identifier` role
  is the alternative and is not worth a sixth value until something needs it.
- **Whether a generated client should be part of the evidence.** The justification in §1 is that a
  1-based binding must hard-code the conversion list. Nothing in this repository is such a
  binding, so the claim is argued rather than demonstrated. A minimal Julia reader converting
  exactly the `structural_index` columns from the registry it finds in a packet would settle it,
  and would test R3 §9's Zarr.jl assumptions at the same time.
