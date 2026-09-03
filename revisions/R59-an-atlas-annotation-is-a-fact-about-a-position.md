# R59 — An Atlas Annotation Is A Fact About A Position

| | |
|---|---|
| **Status** | **Proposed** |
| **Amends** | `02` (`core.electrodes.brain_region`), R19 §3 (`core.electrode_coordinates`), R28 §3 (`core.unit_coordinates`) |
| **Depends on** | R3 §3.0 (no repeated values in a column), R48 (column roles), R53 (an identifier is an integer), R58 (a coordinate declares its basis) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Core carries one string, `core.electrodes.brain_region`, where the source carries as many as four
columns. Measured on two real AIND sessions:

| | `ecephys_786867_2025-09-25` | `ecephys_776259_2025-04-04` |
|---|---|---|
| electrodes | 3840 | 4608 |
| structure id | `brain_region_id`, int64, 56 distinct, 3840 of 3840 populated | `ccf_id` |
| label | `location`, 56 distinct | `location`, `ccf_acronym` |
| full name | — | `ccf_name` |
| ancestry | — | `ccf_structure_id_path`, `|O` with `vlen-utf8` |

Three things follow.

**The structure id is unmodelled and populated.** Every one of 3840 electrodes carries one, and
core has nowhere to put it. What core does model is the acronym, which is a label an atlas version
renames; the id is the identifier that survives renaming.

**`location` and the structure id are one fact twice.** Both hold 56 distinct values over the same
3840 rows, so the string column core already has was hiding the integer one it lacks.

**Two exporters of one pipeline disagree.** The 2025-09 session emits a single integer; the 2025-04
session emits four columns under different names. Neither shape is wrong and neither is stable,
which is what R17 exists for — except that this is core's `brain_region`, not an extension's.

`ccf_structure_id_path` is separately a defect: it is a list of ancestor ids in a delimited string,
which R3 §3.0 forbids by name, and it is derivable from the structure id given the atlas.

### 1.1 The column is on the wrong table

`core.electrodes.brain_region` states which region an electrode is in. An electrode is not in a
region; a *position* is, and an electrode has several positions — R19 §3 gives it one per frame and
R58 §2.1 one per basis. A planned insertion targets a structure and histology finds a structure,
and those are different claims that today share one column.

## 2. Decision

### 2.1 The annotation moves to the coordinate

`core.electrode_coordinates` and `core.unit_coordinates` each gain two nullable columns:

| | | |
|---|---|---|
| `region_id` | `int32` | role `identifier`, identity `carried`: the atlas's own structure number |
| `region_label` | `string` | role `data`, open: the atlas's short name for that structure |

`core.electrodes.brain_region` is **struck**. A consumer reads the annotation from the coordinate
row it belongs to, where R58 §2.1's `coordinate_basis` already distinguishes the structure a probe
was aimed at from the structure it reached.

### 2.2 The frame names the atlas

`region_id` is an identifier in a namespace the packet does not hold, and `coordinate_frame`
already says which namespace: a row in the `ccf` frame carries a CCF structure id. No discriminator
is added, because the frame is one — R55 §2.1's mechanism applied to a column that already existed.

Declaring it `carried` (R53 §2.3) is what says the number is the atlas's and not this format's, so
no writer renumbers it and no `*_name` is owed.

### 2.3 What is not carried

- **The full structure name** (`ccf_name`) is derivable from `region_id` given the atlas, so R3
  §3.0 excludes it: the duplication buys no otherwise-unavailable access.
- **The ancestry** (`ccf_structure_id_path`) is a list in a string, which R3 §3.0 forbids, and is
  likewise derivable. A consumer wanting an electrode's parent structure reads the atlas.

A writer **MUST NOT** carry either as a column. Where a packet wants the atlas available offline it
declares the atlas as a resource, which is out of scope here.

### 2.4 An annotation is optional

Both columns are nullable and no rule requires either. A session before histology has coordinates
and no annotation, and a probe that missed the brain has a position with no structure. A validator
**MUST NOT** treat an absent annotation as a finding.

Where `region_id` is present, `region_label` **SHOULD** be too, so that a consumer without the
atlas can still read the annotation.

## 3. What this does not change

- **No new table.** Two columns added to each of two tables, and one struck.
- **No change to `coordinate_frame` or `coordinate_basis`.** R19 §3's frames and R58 §2.1's bases
  are unaffected; the annotation attaches to whatever row they identify.
- **No stored coordinate changes value.**

## 4. Open

- **Which version of an atlas.** `coordinate_frame` says `ccf`, not which CCF: structure ids are
  stable across the versions AIND uses and structure names are not. A frame naming a version would
  settle it, and would settle the same question for the coordinates themselves, so it belongs to
  R19 §3 rather than here.
- **Whether an electrode may carry an annotation with no coordinate.** A source recording a
  structure without a position would have nowhere to put it under §2.1. Both sessions measured
  carry coordinates for every annotated electrode, so the case is left until one appears.
