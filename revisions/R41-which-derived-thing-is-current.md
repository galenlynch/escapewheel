# R41 — Which Derived Thing Is Current

| | |
|---|---|
| **Status** | **Accepted** 2026-09-01 |
| **Amends** | R9 §2 (the provenance tables), R31 §3 (what names a producing run) |
| **Depends on** | R9 (light provenance), R31 (materialization provenance), R32 (amending a committed packet) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

A real project does not sort once. It re-sorts, re-curates, runs a second pose model over the
same video, and recomputes quality metrics against a new registry. The format already lets those
alternatives coexist — unit identity is `(session_id, unit_id, sorting_run_id, curation_id)`
(`02`), so a second sorting collides with nothing — and R32 already lets a packet gain them
without modifying a file. **What is missing is any way to say which one to use.**

**Three axes keep being conflated, and only one of them is built.**

| | answers | today |
|---|---|---|
| snapshot (R32) | the whole bundle as of time T | manifest versions, retained |
| lineage | which run derived from which | only `core.curation_versions.parent_curation_id` |
| **currency** | which of several coexisting alternatives to use *now* | **nothing** |

Snapshots cannot express currency. "The packet as of T" does not say which of three sortings
inside it is preferred, because all three are inside it. The git analogy is exact: R32 gives the
commit graph, and a ref is a different object.

**And `core.sorting_runs` carries no answer.** It records the sorter, its version and its
parameters. It has no status beyond R8's `succeeded`/`failed`/`partial`, which says whether the
run finished, not whether it is the one to read. On `ecephys_776259_2025-04-09` a consumer facing
two sortings has 287 M spike rows and no basis to choose between them.

**A mechanism aimed at sorting would be the wrong mechanism.** Pose estimation over behaviour
video is an R17 namespaced extension, not a core table; quality metrics are another. Anything
keyed on specific core tables cannot reach them. What every case *does* share is that its output
was produced by a run — which is what R9 already models.

**Except that the model is not wired up.** `core.processing_runs` exists, and R31 puts
`processing_run_id` on a manifest resource, but of the 34 tables only `core.event_streams`
references it (R23) — deliberately, for exactly this reason. `core.sorting_runs` and
`core.curation_versions` do not, so the provenance graph does not reach the two things a project
most often replaces.

## 2. Decision

### 2.1 A derived record names the run that produced it

`core.sorting_runs` and `core.curation_versions` each gain `processing_run_id` (optional,
references `core.processing_runs`, `since: R41`), as `core.event_streams` has since R23.

Optional because R9 §5 makes provenance SHOULD rather than MUST, and a packet that records none
stays conforming. But it is the hinge: **currency is only expressible for a record that names its
run.** A packet that wants §2.3 records provenance for the things it wants to choose between.

An extension (R17) makes its own outputs reachable the same way, by naming a run. Nothing in the
core registry needs to know the extension's tables.

### 2.2 A run may name the run it replaces

`core.processing_runs` gains `supersedes` (optional, references `core.processing_runs`,
`since: R41`). This generalises `parent_curation_id` from curation to every activity.

The chain MUST be well-founded — a run MUST NOT supersede itself, directly or transitively.

Superseding is a claim about *intent*, not about correctness, and it removes nothing: the
superseded run's rows stay queryable. Comparing an old sorting against a new one is the reason to
keep both, and R32 already guarantees the files are still there.

### 2.3 A session declares which run it prefers

New table `core.preferred_runs`.

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session. References `core.sessions`. |
| `activity_type` | string | yes | Which kind of output this preference is about. Open (R9 §6). |
| `scope` | string | yes | What it applies to: a `probe_id`, an `array_asset_id`, a camera name — or the `session_id` itself where the preference is session-wide. |
| `processing_run_id` | string | yes | The preferred run. References `core.processing_runs`. |
| `chosen_at` | timestamp | no | When the choice was made. |
| `reason` | string | no | Why, in one line. |

Primary key `(session_id, activity_type, scope)`, so at most one preference per purpose.

`scope` is required rather than nullable because R7 wants a real key and a nullable key column
makes uniqueness ill-defined; a session-wide preference naming the session as its own scope is
self-describing and needs no sentinel.

`activity_type` is open and already is, so pose estimation, re-curation and metric recomputation
need no vocabulary change.

**Why a table and not a flag on the run.** `core.processing_runs` is a log of what ran and should
never be revised; a preference changes whenever someone changes their mind. Separating them keeps
the log append-only and makes each choice a dated record rather than an edit. It is the same split
as objects and refs.

### 2.4 What a consumer does

A consumer selecting derived data for an activity SHOULD use the preferred run where one is
declared for the matching scope.

Where a session has **more than one** run for an activity and declares no preference, a consumer
MUST NOT silently choose one. It refuses, or reports the ambiguity, as R39 §2.3 requires of a
consumer asked for seconds without an origin. Picking the newest, or the first, produces numbers
that cannot be compared with another consumer's.

Where exactly one run exists, it is the preference by construction and declaring it is optional.
Every packet written before this revision therefore stays readable and unambiguous.

### 2.5 Currency is not a version

Changing a preference is an amendment (R32): a new packet version whose only new file is
`core.preferred_runs`. Nothing else is rewritten, every prior manifest is retained, and the
history of *choices* is recoverable by reading the packet's earlier versions — which is what makes
"the analysis as it stood in March" answerable without keeping a copy of the data.

## 3. What this does not do

- **No removal.** A superseded run keeps its rows. Nothing here deletes, hides, or invalidates.
- **No requirement.** Both columns and the whole table are optional; a packet with one sorting is
  conforming and unambiguous without any of it.
- **No new vocabulary.** `activity_type` was already open (R9 §6).
- **No currency in the manifest.** Considered and rejected: alternatives coexist as *rows in one
  table* — three sortings inside one `core.spike_events` — which a manifest flag cannot select
  among even when the table is partitioned, since a partition is a file within one resource.
  Keying on the run covers row-level and resource-level alternatives with one mechanism.
- **No fix for the cost of adding one.** Appending a sorting still rewrites `core.spike_events`,
  because the table declares no partitioning. That is a separate change and this revision does
  not depend on it: currency is worth having at one sorting per session, and partitioning is worth
  having whether or not currency exists.
- **No opinion on Iceberg.** A preference is a fact about the data, not about its storage, so it
  survives a profile change unaltered (`03`).

## 4. Measured

On `ecephys_776259_2025-04-09`, one session:

| | |
|---|---:|
| `core.sorting_runs` | 12 (one per probe stream) |
| `core.curation_versions` | 12 |
| `core.processing_runs` | 2 (the import, the materialization) |
| `core.spike_events` | 286,896,563 |
| rows this revision would add | **12** |

The twelve sorting runs are one logical sorting split per probe, so a whole-session re-sort
declares twelve preferences with `scope` = `probe_id`, or one with `scope` = the session where a
consumer treats the sorting as a unit. Twelve rows against 287 M is the whole cost of making the
choice explicit.

Neither `core.sorting_runs` nor `core.curation_versions` names a processing run in this packet
today, so §2.1 is what the writer would have to start recording before §2.3 could be used at all.
