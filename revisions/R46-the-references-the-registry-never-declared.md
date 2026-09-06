# R46 — The References the Registry Never Declared

| | |
|---|---|
| **Status** | **Accepted** 2026-09-02 |
| **Amends** | `02_core_logical_schemas.md` (references on eleven tables); R28 §2 (which fixed one instance of this) |
| **Depends on** | R2 (the registry format), R7 (every table declares a key), R9 (provenance tables), R28 (`core.array_channels.electrode_id`) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Tier 1 generates a foreign-key anti-join for every reference the registry declares. **Sixteen
references are not declared**, so sixteen checks do not exist, and a packet whose
`core.sorting_runs.probe_id` names a probe that is not in `core.probes` validates clean.

This is not a gap in the format. `references` supports everything these need and more — eight
composite references are in use, up to four columns wide; two are self-referencing
(`core.clocks.parent_clock_id`, `core.processing_runs.supersedes`); fourteen are nullable and
Tier 1 guards them with `IS NOT NULL`. **The references are simply absent**, and nothing notices
an absent one: a check that is never generated cannot fail.

R28 §2 found one instance and fixed it — *"gives `core.array_channels.electrode_id` the reference
it lacked"*. It was not an isolated case. Sixteen more were found by asking a different question:
not *which reference is wrong*, but *which column names a table whose primary key is exactly that
column, and says nothing about it*.

**The reader degrades too.** `escapewheel_reader.Packet.distinct` uses a reference to answer from the
parent table — *"a foreign key means the parent table holds every value the child may carry, and
it is the smaller table by construction"* — and falls back to scanning the fact table when none is
declared. `core.units` is thousands of rows where `core.spike_events` is hundreds of millions.

## 2. Decision

### 2.1 Sixteen references are declared

Each column below MUST reference the named resource. Every one is a column whose name is the
single-column primary key of the target, or is named for it (§2.2).

| table | column | references | presence |
|---|---|---|:---:|
| `core.sorting_runs` | `session_id` | `core.sessions` | required |
| `core.sorting_runs` | `probe_id` | `core.probes` | nullable |
| `core.sorting_runs` | `input_array_asset_id` | `core.array_assets` | nullable |
| `core.curation_versions` | `session_id` | `core.sessions` | required |
| `core.curation_versions` | `sorting_run_id` | `core.sorting_runs` | required |
| `core.curation_versions` | `parent_curation_id` | `core.curation_versions` | nullable |
| `core.processing_runs` | `session_id` | `core.sessions` | nullable |
| `core.devices` | `session_id` | `core.sessions` | nullable |
| `core.array_assets` | `session_id` | `core.sessions` | required |
| `core.array_assets` | `clock_id` | `core.clocks` | nullable |
| `core.array_dimensions` | `coordinate_array_asset_id` | `core.array_assets` | nullable |
| `core.media_assets` | `session_id` | `core.sessions` | required |
| `core.media_assets` | `clock_id` | `core.clocks` | nullable |
| `core.media_frames` | `clock_id` | `core.clocks` | required |
| `analysis.array_assets` | `session_id` | `core.sessions` | required |
| `analysis.array_assets` | `clock_id` | `core.clocks` | nullable |

A nullable one is guarded with `IS NOT NULL`, as the fourteen existing nullable references
already are: without the guard every null row reports as an unresolved reference.

### 2.2 Three columns are named for a key rather than after it

`parent_curation_id`, `input_array_asset_id` and `coordinate_array_asset_id` do not match their
target's primary-key name, because the name says which *role* the referent plays. That is correct
and stays; `references` names the target's columns explicitly, so nothing depends on the names
matching.

### 2.3 The layer decides an otherwise ambiguous target

`array_asset_id` is the primary key of **both** `core.array_assets` and `analysis.array_assets`,
so a column named for it has two candidate targets. The layering settles it: `core` is the sole
source of truth and `analysis` derives from it (`06`), so a **core table MUST NOT reference an
analysis resource**. `core.array_dimensions.coordinate_array_asset_id` and
`core.sorting_runs.input_array_asset_id` therefore reference `core.array_assets`.

`analysis.array_dimensions.coordinate_array_asset_id` is genuinely ambiguous — an analysis axis
may reasonably take its coordinates from either layer — and is **left undeclared**. See §5.

### 2.4 Three columns reference nothing, and that is correct

| column | why |
|---|---|
| `core.trials.condition_id` | no condition table exists; R43 §3 sends the concept to an R17 extension |
| `core.trials.stimulus_id` | as above, and null in all 708 rows of every packet |
| `core.sessions.source_session_id` | a foreign system's identifier, by definition outside this packet |

They stay as plain strings. A column ending in `_id` is not thereby a foreign key.

## 3. Evidence

Every packet on disk, all eleven references whose tables are present:

| | |
|---|---|
| rows checked | 1,263 |
| non-null values checked | 846 |
| **orphans** | **0** |

The six remaining references name tables absent from every packet — `analysis.array_assets`,
`core.media_assets`, `core.media_frames` and `analysis.array_dimensions` — so they are declared
against no data and cost nothing until a packet carries one.

Three of the eleven are present but entirely null: `parent_curation_id` (120 rows),
`input_array_asset_id` (108) and `coordinate_array_asset_id` (171). Declaring them adds a guarded
check that currently matches nothing, which is the point — it will match the first time a packet
records a re-curation lineage or a coordinate array.

So this revision **fails no packet that exists** and adds sixteen checks, taking the registry from
54 references to 70.

## 4. What this does not do

- **No format change.** `references` already expresses composite, nullable and self-referencing
  keys, and `additionalProperties: false` keeps it closed against drift.
- **No new column, no renaming.** §2.2.
- **No change to any packet.** The references describe relationships the data already satisfies.
- **No Tier 2 rule.** Every one of these is a plain anti-join that Tier 1 generates from
  structure; a hand-written rule here would be the thing R2 §7 exists to avoid.

## 5. Open

- **`analysis.array_dimensions.coordinate_array_asset_id` is left undeclared**, because its target
  may be in either layer and `references` names exactly one resource. Two ways out, neither
  needed until a packet carries an analysis coordinate array: a Tier 2 rule anti-joining against
  the union of both asset tables, which is precisely what Tier 2 is for; or a second column, which
  would be worse, since the axis has one coordinate array and not two.
- **Whether an undeclared reference should itself be detectable.** This revision was found by a
  sweep — a column whose name is a table's single-column primary key, and no reference — that took
  a few lines and would run in `registry/check.py`. It would be a heuristic rather than a proof,
  since `condition_id` and `source_session_id` match the shape and are correct as they are, so it
  would have to be a report a human reads rather than a rule that fails a build.
