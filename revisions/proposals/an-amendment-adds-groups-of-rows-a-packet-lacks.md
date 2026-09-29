# An amendment adds groups of rows a packet lacks

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-29 |
| **Based on** | `87a44339a1bb6bb215a1e6a9b8d6699a00a479df` |
| **Decision domain** | specification |
| **Affects** | Part 05 §15.2's amendment scope and §4.3's identifier assignment; Part 03 §9's realisation of a table that gains rows; the numbering rules of the drafts `an-interval-is-numbered-by-its-packet` and `unit-labels-order-by-length-then-by-unicode-scalar-value`; the registry meta-schema and the core registry's declarations |

## 1. Problem

Part 05 §15.2 lets an amendment add a resource and add rows to the three provenance tables, and
forbids it to change the content of any other core resource. The reason it gives is that an
amendment extends what a packet says and never revises it, because anything derived from the old
core would be silently invalidated and nothing in the format detects that. The rule counts
resources, and several core tables hold many independent groups of rows: one per interval kind,
curation, event stream or coordinate frame. Adding a group the packet lacks changes no row, but it
adds rows to an existing table, so §15.2 forbids it. A packet built with task trials can gain
optotagging pulses only by being rebuilt as a new packet.

§15.2 also forbids an amendment to change a packet's standard versions, so a packet is amended
under the rules it was built under. Whatever v0.2 forbids an amendment to add, no v0.2 packet can
gain, even after a later release permits it.

Two drafts add a second barrier. `an-interval-is-numbered-by-its-packet` numbers intervals densely
from 0 by session, kind, clock and bounds, and checks that order.
`unit-labels-order-by-length-then-by-unicode-scalar-value` does the same for units by run, curation
and label. Under either rule, a group added later that sorts before an existing one moves every
identifier after it. That would change content §15.2 protects, and it would break every reference
held outside the packet. So even with §15.2 loosened, a v0.2 packet could gain a kind of interval
only where the kind's resource ID sorts after every kind it already holds.

## 2. Evidence

The measurements use the `packet-r147` builds of the two session packets:

- `ecephys_786867`: 450 trials and 4,505 units in 10 sorting runs;
- `ecephys_776259`: 708 trials and 6,781 units in 12 sorting runs.

Each packet's intervals were renumbered by the interval draft's order, as that draft's §2.5 did.
Queries ran in DuckDB 1.5.5.

### 2.1 Seven additions change no row, and §15.2 forbids each

Each addition below adds rows to core tables the packet already holds, and changes none of their
rows.

| addition | core tables that gain rows |
|---|---|
| a kind of interval, such as optotagging pulses in a packet holding trials | `core.intervals`, beside the extension resource the kind names |
| a curation of an existing sorting run | `core.curation_versions`, `core.units`, `core.spike_events`, `core.unit_electrodes`, `core.unit_observation_intervals` |
| a second sorting of a probe | `core.sorting_runs`, `core.sorting_run_channels`, the curation's tables, and `core.preferred_runs`, which Part 05 §12 requires once two runs share a scope |
| an event stream derived after the build | `core.event_streams`, `core.events`, `core.event_stream_observation_intervals` |
| an atlas registration made after the session | `core.coordinate_frames`, `core.coordinate_frame_axes`, `core.electrode_coordinates`, `core.electrode_coordinate_values`, `core.unit_coordinates`, `core.unit_coordinate_values` |
| quality labels from a new source | `core.unit_quality_labels` |
| a video or array added after the build | `core.media_assets` and `core.media_frames`, or `core.array_assets` and its axis tables, and often `core.devices` and `core.clocks` |

### 2.2 The drafts' numbering rules move identifiers when a group sorts first

Each addition was numbered after the largest existing identifier, and each draft's rule was run
over the result. The per-group rule is §2.3's. Each cell gives the first packet's rows, then the
second's.

| addition | the draft's rule | the per-group rule |
|---|---:|---:|
| 120 intervals of `aind_opto.pulses`, a kind sorting before `dynamic_foraging.trials` | 570 / 828 | 0 / 0 |
| the same 120 intervals under a kind sorting after it | 0 / 0 | 0 / 0 |
| a curation of the first sorting run, one unit per unit of that run | 4,505 / 6,781 | 0 / 0 |
| a curation of the last sorting run | 0 / 0 | 0 / 0 |

Whether an addition keeps identifiers therefore depends on how its kind's resource ID or its run's
identifier sorts. Numbering the first packet with pulses by the interval draft's order satisfies
that draft's rule, and leaves none of the 450 trials with its identifier.

### 2.3 A per-group rule keeps every other finding

The per-group rule requires two things of identifiers:

- they are dense from 0 across the packet;
- within each session and kind, or each run and curation, they are contiguous and follow the
  draft's order.

For intervals:

```sql
SELECT numbered.interval_id
FROM (
  SELECT interval_id, session_id, interval_kind,
    ROW_NUMBER() OVER (ORDER BY interval_id) - 1 AS dense,
    ROW_NUMBER() OVER (
      PARTITION BY session_id, interval_kind
      ORDER BY clock_id, start_tick, stop_tick, interval_id) - 1 AS rank_in_kind
  FROM core.intervals
) AS numbered
JOIN (
  SELECT session_id, interval_kind, MIN(interval_id) AS first_id
  FROM core.intervals
  GROUP BY session_id, interval_kind
) AS kinds
  ON kinds.session_id = numbered.session_id AND kinds.interval_kind = numbered.interval_kind
WHERE numbered.interval_id <> numbered.dense
   OR numbered.interval_id <> CAST(kinds.first_id AS DECIMAL(38,0)) + numbered.rank_in_kind
```

On the first packet it draws what the interval draft's rule draws for each of these variants:

| variant | rows drawn |
|---|---:|
| two swapped trials | 2 |
| a gap after the hundredth identifier | 350 |
| a numbering from 1 | 450 |
| two kinds numbered in time order across kinds | 565 |
| one kind's intervals on two clocks, numbered by tick value | 448 |

For two kinds numbered out of Unicode order it draws nothing, where the draft's rule draws 570.

Both per-group rules pass the Part 11 static check. The unit rule was checked with
`CHARACTER_LENGTH` replaced, since the baseline rule language lacks it and the unit-label draft
admits it.

### 2.4 The portable profile rewrites a table that gains rows

Part 03 §9 writes a resource that gains rows as a new file the amended manifest names, and §5.1
makes a table one Parquet file, so a table gaining a group is rewritten whole. `core.units` is keyed
by its assigned identifier, and so is `core.intervals` under the interval draft. For either, a group
numbered after the largest identifier follows every existing row in key order, so the new file is
the old rows followed by the new.

The cost is the rewrite. `core.spike_events` holds 131,396,535 rows (0.3 GB) in the first packet and
286,896,563 (0.7 GB) in the second, and a sorting added by amendment rewrites it. Part 03 §5.2
leaves member files to a future interface.

### 2.5 Provenance

R32 §3 set the scope table and its asymmetry. R32 §8 left open whether the provenance exception
should become a general append mechanism. R92 §6 left open whether an amendment may append
rows at all, and how a later batch's order would relate to an earlier one's.

R41 §2.5 described changing a preference as an amendment whose only new file is
`core.preferred_runs`. That clause is recorded as rationale, and Part 05 §15.2 as incorporated
forbids it.

§15.2's table names only core and analysis resources. It does not say what an amendment may do to
an extension, compatibility-projection or documentation resource.

### 2.6 An amendment cannot read a source

Part 00 §2.4 defines a build as one execution of a writer against one recipe. Part 05 §2's pipeline
binds a build, and Part 12's rules bind a build and the adapters it reaches, "and bind no other
build". Part 05 §15 says nothing of recipes, sources, adapters, normalization or provenance, and
Part 05 §8 places derivation into a committed packet in an amendment. Nothing in the specification
lets an amendment read a source through an adapter.

The recipe also describes a whole packet. Part 05 §3.1 has it declare the packet's clocks and their
parents. Part 05 §3.5 refuses two things before any source opens:

- a required foreign key to a table nothing supplies;
- a clock referenced but absent, or parented to nothing.

A recipe adding a sniff sensor's device, clock and array parents the new clock to one the packet
already holds, which the recipe does not declare, and §3.5 refuses it. The added rows' required
references to tables only the packet supplies, such as `core.sessions`, draw the other refusal
unless the recipe supplies those tables again.

Part 05 §7 has a writer record one import run declaring its scope. The reference writer takes an
import as session-wide and scopes it to the session, as R44 §2.1 has a session-wide run do. A
second import into the same packet then shares (`session_id`, `activity_type`, `scope_kind`,
`scope`) with the first. Part 05 §12 has a packet
holding two such runs carry a `core.preferred_runs` row naming one of them, and has a writer refuse
to commit one that does not, although the two imports supplied different groups and neither is an
alternative to the other.

The reference writer's amendment takes only resources a caller stages through its API. Its
recipe-driven command builds a new packet, and its identifier numbering starts empty.

## 3. Desired outcome and constraints

A resolution lets an amendment add a group of rows to a canonical table without changing any row,
for the cases in §2.1. It keeps §15.2's asymmetry: an amendment never grows a group a consumer may
have read whole, such as a session's trials or a curation's units, since nothing in a packet records
which derived results read which rows (R32 §7).

It also meets these constraints:

- no identifier a packet holds moves;
- numbering stays dense and checkable on one packet;
- an extension can declare the same for its own tables, and core stays checkable alone;
- the portable profile's realisation, a new file, stands, and no physical interface is added.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep §15.2 and the drafts' packet-wide orders | no v0.2 packet ever gains a kind of interval, a curation, a stream or a registration; each is a new packet, and every identifier held outside the old one is lost |
| keep the packet-wide orders, and let an amendment add a group only where it sorts after every existing group | whether a group can be added depends on its name: `aind_opto.pulses` could never follow `dynamic_foraging.trials` |
| each table declares the groups an amendment may add, and numbering runs within each group (preferred direction) | one registry field, and the two drafts' rules become per-group; described below |
| list the groups an amendment may add in Part 05 §15.2 | no registry change, but an extension cannot declare its own, and each new case needs a revision of Part 05 |
| let an amendment add rows to any group | a group a consumer read whole grows, and nothing in the packet says which results read it, so §15.2's asymmetry is gone |
| record which amendment added each row, and number by that first | the packet-wide order stays checkable, at the cost of a column in every table that can gain rows; a single build over the same sources still numbers differently |
| split `core.intervals` into one resource per kind | adding a kind becomes adding a resource, which §15.2 permits; no single identifier names an interval, which the interval draft exists to fix |

Under the preferred direction, a table declares the groups an amendment may add, each as a list of
its columns. An amendment may add a row only where, for at least one declared list, no row of the
superseded version shares the row's values. It changes and removes no row, and a table declaring no
list gains no rows. The provenance tables declare their whole key, which restates the present
exception.

More than one list is needed where one table serves two additions. `core.unit_coordinates` gains
rows both for a new curation's units in an existing frame and for existing units in a new
registration.

An array or a video is an instance of `core.array_asset_instances` or `core.media_asset_instances`,
which `core.array_assets` and `core.media_assets` catalogue one row per instance. An instance is
therefore added with the catalogue row an amendment adds, and no instance a superseded row
catalogues changes.

An amendment numbers a name the superseded version holds with that version's identifier, since
Part 02 §8.2 makes a name unique within a packet, and numbers a name the packet lacks after the
largest identifier. An added array thus names the clock or device the packet already holds rather
than a copy of it. A recipe performing an amendment names only the sources whose rows it adds, and
its `owns` and preferences (Part 05 §3.3) govern only those rows.

An amendment performed from a recipe is a build as Part 00 §2.4 defines one, so Part 05 §2's
pipeline and Part 12 bind it unchanged. Four steps read the superseded packet:

- its recipe names the packet it amends, and its clock table declares only added clocks, each
  parented to a clock the recipe or the packet declares;
- Part 05 §3.5 counts what the packet holds, so a foreign key or clock parent the packet supplies
  is satisfied;
- Part 05 §4.3 numbers names against the packet, as above;
- Part 05 §7 adds one import run with the amendment's recipe, and a `core.source_files` row for
  each root the packet lacks.

Part 05 §12 then needs to exempt one import from another. Two imports into one packet supply
disjoint groups, which adding only new groups guarantees, so neither is an alternative to the
other.

Where a declared rule numbers a table's assigned identifier, the numbering follows these rules:

- the rule's order holds within each group, and each group's identifiers are contiguous;
- identifiers are dense across the packet;
- a writer numbers the groups one build or amendment adds after the largest identifier the packet
  holds, ordered among themselves by the group's columns.

No check on one packet can tell which groups arrived together, so that order binds the writer and
no packet check tests it. A writer performing an amendment holds the superseded version, so it can
refuse an added row whose group already exists.

§15.2 is restated by content class (Part 02 §2.2):

- a canonical resource, core or extension, may be added and may gain the groups it declares, and
  is never changed or removed;
- an analysis, compatibility-projection or documentation resource may be added or removed.

The cost is that identifiers depend on a packet's history as well as its sources. A single build
over all an amended packet's sources orders its groups by their columns. Where an added group sorts
before an existing one, the build's identifiers therefore differ from the amended packet's. Every
identifier is stable across the versions of one packet, which is where references outside it are
made. A build's determinism (Part 05 §11) is unchanged. An amendment's numbering is a function of
the superseded packet and the amendment's own recipe and sources.

Adding only new groups has a second cost. An added row may reference rows the packet holds, but no
row the packet holds can come to reference an added one. A stream written without a device cannot
be attached to a device an amendment adds, and a clock cannot be moved under an added parent.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 states no amendment rule. |
| logical prose and registry | Part 02 states the group declaration and the per-group numbering. The interval draft's numbering rule and Part 02 §12.1's unit order, which the unit-label draft rewrites, become per-group. The registry meta-schema gains the field, so the registry-contract descriptor advances, as the proposal `a-specialising-row-names-a-row-of-its-own-kind` would also advance it. The core registry declares groups on the tables §6's second question settles. |
| physical profiles | Part 03 §9 is unchanged in substance: a table gaining a group is a new file. Part 03 §5.2's partitioning stays deferred. |
| packet manifest and JSON Schemas | The registry meta-schema, as above. The packet manifest is unchanged. |
| validation and import | Part 05 §15.2 is restated by content class and gains groups. An amendment may be performed from a recipe: Part 05 §§3.1 and 3.5 admit a recipe naming the packet it amends, §4.3 states how an amendment continues numbering, §7 records the amendment's import run, and §12 exempts one import from another. §15.4's re-run rule already covers a written table. Part 12 is unchanged, since an amendment from a recipe is a build. |
| extensions | Each extension may declare groups on its canonical tables in its own registry version, and none needs to. An extension resource a new kind names is added as a resource, which §15.2 already permits. |
| reader, writer, validator, adapters | The writer's amendment takes new groups of canonical tables: it reads the superseded rows, numbers after the largest identifier, and refuses a row whose group exists. It also runs a recipe's sources into an amendment, seeding its numbering from the packet's names. The validator's generated checks are unchanged apart from the two numbering rules. The reader reads the current manifest and is unchanged. Adapters are unchanged: an adapter delivers the same way into an amendment as into a new packet. |
| existing packets | Both session packets pass both per-group rules unchanged. The drafts rebuild them anyway. |
| conformance fixtures and tests | An amended fixture packet gaining a kind that sorts before its trials, and a curation of its first run, both conforming. The drafts' negative variants carry over. A writer test refuses an amendment adding a trial. |
| revision process and tooling | Unchanged. |
| generated publications and developer documentation | `registry/tables.md` renders the groups, and the registry guide documents the field. |

## 6. Open questions

1. **Does an amendment add only groups a packet lacks, or also rows to a group it holds?** Resolved
   2026-09-29: only groups it lacks, since a grown group changes what a consumer read whole (§3).
2. **Which core tables declare groups in v0.2?** A v0.2 packet can gain only what v0.2 declares
   (§1), so this is settled now or never for v0.2 packets. Resolved 2026-09-29 in part: the
   additions of §2.1, including media and arrays. Devices and clocks are included as well, since a
   source the original build had no adapter for, such as a sniff sensor, brings its device, its
   clock and its array together:

   | tables | group |
   |---|---|
   | `core.intervals` | session and kind |
   | `core.sorting_runs`, `core.curation_versions`, `core.event_streams`, `core.coordinate_frames`, `core.preferred_runs`, `core.array_assets`, `core.media_assets`, `core.devices`, `core.clocks` | each row |
   | `core.units` | run and curation |
   | `core.spike_events`, `core.unit_electrodes`, `core.unit_observation_intervals` | session and unit |
   | `core.sorting_run_channels` | session and run |
   | `core.events` | session and stream |
   | `core.event_stream_observation_intervals` | stream |
   | `core.coordinate_frame_axes` | session and frame |
   | `core.electrode_coordinates`, `core.electrode_coordinate_values` | session, frame and basis |
   | `core.unit_coordinates`, `core.unit_coordinate_values` | session and unit, or session, frame and basis |
   | `core.unit_quality_labels` | session and unit, or session and source |
   | `core.array_dimensions`, `core.array_labels`, `core.array_channels` | array asset |
   | `core.media_frames` | media asset |
   | `core.clock_anchors` | clock |
   | `core.clock_observation_intervals`, `core.clock_phase_steps` | session and clock |
   | the provenance tables | each row, as today |

   Still open: probes, electrodes and calibrations. The sniff sensor's reasoning applies equally to
   a probe whose recording the original build had no adapter for, and to a calibration of an added
   device. The preferred direction declares them too: `core.probes` and `core.calibrations` each
   row, `core.electrodes` by probe, and `core.calibration_points` and `core.calibration_devices` by
   calibration. Only `core.sessions`, `core.subjects` and `core.session_experimenters`, which
   identify the packet, would then declare no group.
3. **Is an amendment from a recipe part of this decision, or its own proposal?** Without it no
   amendment reads a source (§2.6), so the sniff sensor's device, clock and array can be added only
   by hand through a writer's API. The preferred direction keeps it here, since the groups this
   proposal adds mostly come from sources.
4. **Is changing a preference part of this decision?** R41 §2.5 described it as an amendment. It
   revises a row, so the preferred direction leaves it forbidden here and treats it as a separate
   proposal.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
