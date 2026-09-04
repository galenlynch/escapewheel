# R44 — A Run Declares Its Scope

| | |
|---|---|
| **Status** | **Accepted** 2026-09-01 |
| **Amends** | R41 §2.2 (`core.processing_runs`), R41 §2.4 (what a consumer does) |
| **Depends on** | R9 (light provenance), R23 (a stream names its run), R41 (currency) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R41 §2.4 states the rule a consumer must follow:

> Where a session has **more than one** run for an activity and declares no preference, a
> consumer MUST NOT silently choose one.

**A consumer cannot evaluate it.** The rule groups runs by activity; the preference table is
keyed `(session_id, activity_type, scope)`; and `core.processing_runs` carries **no `scope`
column**. So the grouping the rule needs and the grouping the answer is filed under are
different groupings, and only one of them is computable from the packet.

Read literally, the rule fires on the packet R41 was built to demonstrate:

```text
grouped by (session_id, activity_type), packets/r41:
  (ecephys_776259_2025-04-09_17-25-12, spike_sorting)  ->  12 runs   << ambiguous
  (ecephys_776259_2025-04-09_17-25-12, curation)       ->  12 runs   << ambiguous
  (ecephys_776259_2025-04-09_17-25-12, import)         ->   1 run
```

Those twelve runs are **twelve probes sorted once each** — 12 sorting runs over 12 distinct
probe IDs, no probe sorted twice. R41 §4 says exactly this: *"The twelve sorting runs are one
logical sorting split per probe."* They are complementary, not alternatives, and nothing about
reading them is ambiguous.

So a conforming consumer implementing R41 §2.4 as written must refuse to return units from a
packet that has no ambiguity in it — and must refuse for **every** packet that adopts R41 §2.1,
since naming a run is what makes the runs countable at all. R41 §2.4's assurance that "every
packet written before this revision therefore stays readable" holds only because those packets
name no runs; adopting R41 is what breaks them.

**The missing fact is small and structural.** A run is *about* something — a probe, an array
asset, a camera. R41 §2.3 already named that thing `scope` and required it on the preference.
It is a property of the run, and the preference is where it is recorded.

## 2. Decision

### 2.1 `core.processing_runs` gains `scope`

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `scope` | string | no | What this run is about: a `probe_id`, an `array_asset_id`, a camera name — or the `session_id` itself where the run is session-wide. `since: R44`. |

Same vocabulary and same meaning as `core.preferred_runs.scope` (R41 §2.3), so the two join
directly. Open, as `activity_type` is (R9 §6).

**Optional**, because R9 §5 makes provenance SHOULD rather than MUST and a packet recording no
runs stays conforming. A run that omits it is a run whose ambiguity cannot be evaluated, which
§2.3 says what to do about.

A writer that records `processing_run_id` on a derived record **SHOULD** set `scope` on the run,
because §2.1 is what makes §2.2 checkable.

### 2.2 The rule gains its missing term

**Strike** R41 §2.4's first paragraph and replace it with:

> Where a session has more than one run for the same `(activity_type, scope)` and declares no
> preference, a consumer MUST NOT silently choose one. It refuses, or reports the ambiguity, as
> R39 §2.3 requires of a consumer asked for seconds without an origin.

R41 §2.4's remaining paragraphs are unchanged: exactly one run is the preference by
construction, and picking the newest or the first produces numbers that cannot be compared.

With this, the demonstration packet is unambiguous by computation and not only by inspection —
twelve `(spike_sorting, probe)` groups of one run each.

### 2.3 A run without a scope is not silently assumed unique

A consumer that finds more than one run for an `activity_type` where **any** of those runs
declares no `scope` **MUST NOT** conclude the group is unambiguous. The runs may be
alternatives or may be complementary and the packet does not say which.

It reports that the ambiguity is **undeterminable**, distinctly from reporting that the runs are
ambiguous. The two call for different fixes — declare a preference, against record the scopes —
and collapsing them into one message sends a writer to the wrong one.

### 2.4 Why not derive the scope by joining

A scope is recoverable today for the two core activities: `spike_sorting` through
`core.sorting_runs.probe_id`, `curation` through `core.curation_versions.sorting_run_id`. A
reader could hard-code that mapping and be right about this packet.

**It is the approach R41 §1 rejected**, and for the reason that still holds:

> A mechanism aimed at sorting would be the wrong mechanism. Pose estimation over behaviour
> video is an R17 namespaced extension, not a core table; quality metrics are another. Anything
> keyed on specific core tables cannot reach them.

A join table hard-codes `activity_type` → the core table that names the run → the column that
holds the scope. An extension's outputs are not in that mapping and cannot be added to it
without the core reader knowing the extension, which is what R41 §2.1 exists to avoid. It is
also rules-as-code where this project keeps rules as data.

A column on the run costs one nullable string per run — 26 rows in the demonstration packet —
and reaches every activity including ones the core registry has never heard of.

## 3. What this does not do

- **No change to `core.preferred_runs`.** R41 §2.3's table and its key are untouched; this
  gives the other side of the join the column it was already assumed to have.
- **No new requirement to record provenance.** `scope` is optional under an optional
  `processing_run_id` on records in an optional provenance model. A packet carrying none is
  conforming and unaffected.
- **No claim about which run is preferred.** `scope` says what a run is about. R41 §2.3 says
  which one to use, and remains the only thing that does.
- **No validation of the scope's referent.** `scope` names a probe, an asset or a camera, so no
  single foreign key covers it — the same reason R41 §2.3 left it a plain string.

## 4. Cost

`packets/r41`, the demonstration packet:

| | |
|---|---|
| rows to add a column to | **26** |
| `(activity_type, scope)` groups it creates | 12 sorting, 12 curation, 1 import, 1 materialization |
| groups with more than one run | **0** |
| runs whose scope is not recoverable by any join today | **2** — the `import` and the `materialization` |

The last row is the argument in one number. Both are session-wide and would carry the session as
their scope, and neither is reachable by §2.4's join because neither is named by a core table
that has a scope-shaped column.

## 5. Open

- **Whether `scope` should be required when `processing_run_id` is recorded anywhere.** §2.1
  makes it SHOULD. A MUST conditional on the record existing is expressible as a Tier 2 rule and
  would remove §2.3's third state entirely, at the cost of failing packets that record a run and
  nothing else.
- **Whether a session-wide run should name the session or leave `scope` null.** R41 §2.3 chose
  the session for the *preference*, because a nullable key column makes uniqueness ill-defined.
  `scope` is not part of a key here, so null would be available — but two spellings for one
  meaning across two tables that join is worse than one redundant string.
