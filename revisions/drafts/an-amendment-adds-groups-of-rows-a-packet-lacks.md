# An amendment adds groups of rows a packet lacks

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `4d4501063a42b2c9815f8a0dd97555c4dcc5f2e3` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§1, 2.3, 9.2 and 9.4, and a new subsection of Part 02 §2; Part 03 §9; Part 05 §§1, 3.1, 3.3, 3.5, 3.6, 4.3, 7, 8, 11, 12, 15.1 and 15.2, and a new subsection of Part 05 §15; Part 08 §§2 and 3; the registry meta-schema; the registry-contract descriptor; the recipe schema; the core registry; the four extension registries |
| **Depends on** | `an-interval-is-numbered-by-its-packet` §3.2 and `unit-labels-order-by-length-then-by-unicode-scalar-value` §3.1 (the per-group numbering an amending build continues); `unit-labels-order-by-length-then-by-unicode-scalar-value` §§3.3 and 3.4 (the rule language and the registry identifiers this advances from) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8; §3.9; §3.10 |

Section 3 is normative. Sections 1, 2 and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 05 §15 lets a writer publish a new version of a packet, an **amendment**, which extends what
the packet says and never revises it. Part 05 §15.2 counts in resources: an amendment may add a
resource and add rows to the three provenance tables, and must not change the content of any other
core resource. Several core tables hold many independent groups of rows, one per interval kind,
curation, event stream or coordinate frame. Adding a group the packet lacks changes no row, and
Part 05 §15.2 still forbids it, so a packet built with task trials can gain optotagging pulses only
by being built again as a new packet, losing every identifier held outside the old one.

Part 05 §15.2 also forbids an amendment to change a packet's standard versions, so a packet is
amended under the rules it was built under. Whatever v0.2 forbids an amendment to add, no v0.2
packet can gain.

Three further gaps stand between a packet and an amendment adding a group:

- **Nothing lets an amendment read a source.** Part 05 §15 says nothing of recipes, adapters or
  normalization, and a recipe describes a whole packet, so Part 05 §3.5 refuses one whose added
  clock is parented to a clock only the packet holds.
- **Two imports collide.** Part 05 §12 requires a preference among runs sharing an activity and
  scope, and a second import into a packet shares both with the first.
- **Nothing checks an amendment's scope.** Every check reads the current version alone, and a table
  gaining a group is a new file, so only a comparison of rows with the superseded version shows that
  no row changed.

This revision has each table declare the groups an amendment may add, restates Part 05 §15.2 by
content class, and lets a recipe perform an amendment through the adapters any build uses. It
exempts imports from Part 05 §12, has a validator compare an amendment with the version it
supersedes, and gives a recipe a member declaring the preferred runs Part 05 §12 requires. The
drafts `an-interval-is-numbered-by-its-packet` and
`unit-labels-order-by-length-then-by-unicode-scalar-value` check their numbering within each group,
so an amending build continues it.

The change is structural because it replaces Part 05 §15.2's table and revises rules inside
Part 05 §§4.3, 7, 8, 11 and 12 and Part 03 §9. Appended sections would leave Part 05 §15.2
forbidding what they permit.

### 1.1 Structural crosswalk

Part 05 §§3.6 and 12 lacked canonical anchors. The commit this draft is based on adds
`ew-declared-fact-authority` and `ew-alternatives-resolved` before their headings and changes
nothing else. Every other affected section already carries an anchor, and the two new sections are
created with theirs. No section moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §1, the incorporated descriptor file | revise in place | same section | the v0.8 descriptor is incorporated | §3.10 |
| Part 02 §2.3, the members of a `table` object | revise in place | same section | a `table` object also carries amendment groups | §3.1 |
| none | add | a new final subsection of Part 02 §2, *Amendment groups*, anchor `ew-amendment-groups` | a table declares the groups an amendment may add | §3.1 |
| Part 02 §9.2, the meta-schema identifier, the core registry version and an extension's migration | revise in place | same section | meta-schema 0.10.0 and core registry 0.12.0; an extension migrated to 0.10.0 changes its version | §3.10 |
| Part 02 §9.4, the descriptor identifier, the meta-schema it selects, the invariant table and the resource invariants | revise and extend in place | same section | the v0.8 descriptor selects meta-schema 0.10.0 and adds `registry.amendment_groups.resolves` | §3.1; §3.10 |
| Part 03 §9, the file a resource gaining rows is written as | revise in place | same section | every resource an amendment writes is a new file | §3.3 |
| Part 05 §1, the validator's sections | revise in place | same section | a validator is also bound by *Comparison with the superseded version* | §3.4 |
| Part 05 §3.1, the recipe's members and the recipe schema's identifier | revise and extend in place | same section | a recipe may name the version it amends and declare preferred runs; the schema is 0.2.0 | §3.5; §3.8; §3.10 |
| Part 05 §3.3, ownership | extend in place | same section | a packet being amended is not a source | §3.5 |
| Part 05 §3.5, the refusals of a recipe | extend in place | same section | an amending build's refusals; two preferred runs sharing a key are refused | §3.5; §3.8 |
| Part 05 §3.6, the authority for a declared fact | extend in place | same section | a packet's session and subject rows stand in for declarations | §3.5 |
| Part 05 §4.3, normalization | revise and extend in place | same section | an amending build numbers after the packet's identifiers and settles each row against the packet; determinism covers the packet version | §3.6; §3.9 |
| Part 05 §7, the import run | revise in place | same section | an import run's activity is `import`; an amending build adds only new roots | §3.7 |
| Part 05 §8, derivation into a committed packet | revise in place | same section | an amending build derives from the staged amended packet | §3.5 |
| Part 05 §11, the fifth criterion | revise in place | same section | determinism is over the recipe, the sources and the packet version amended | §3.9 |
| Part 05 §12, alternatives | revise in place | same section | import runs are not alternatives; a build writes the preferences its recipe declares | §3.7; §3.8 |
| Part 05 §15.1, what an amendment is | extend in place | same section | what an amendment writes, and what an amending build is | §3.3; §3.5 |
| Part 05 §15.2, the scope table and its rationale | replace in place | same section | the scope is stated by content class and by group, a preference may be replaced, and a stale derived resource is derived again or removed | §3.3 |
| none | add | a new final subsection of Part 05 §15, *Comparison with the superseded version*, anchor `ew-amendment-comparison` | a writer and a validator compare an amendment with the version it supersedes | §3.4 |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | regenerate the informative example | same sections | none | none |

## 2. Background

Section 2 is informative. The measurements use the `packet-r147` builds of the two session packets:

- `ecephys_786867`: ten probes, 450 trials, and 4,505 units in 10 sorting runs;
- `ecephys_776259`: twelve probes, 708 trials, and 6,781 units in 12 sorting runs.

Each packet's intervals were first numbered by `an-interval-is-numbered-by-its-packet` §3.2, which
reproduces every existing identifier. Queries ran in DuckDB 1.5.5 over the packets' Parquet tables.

### 2.1 Seven additions change no row, and Part 05 §15.2 forbids each

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

Some tables serve two additions. `core.unit_coordinates` gains rows for a new curation's units in an
existing frame, and for existing units in a new registration. `core.electrode_coordinates` gains
rows for a new registration of existing electrodes, and for a new probe's electrodes in an existing
frame.

### 2.2 A packet-wide order moves identifiers when a group sorts first

Numbering a table in one order across the packet moves identifiers wherever an added group sorts
before a group the packet holds. Each addition below was numbered after the largest existing
identifier, and two rules were run over the result:

- a rule checking one order across the packet, by session, kind, clock and bounds for intervals, and
  by run, curation and label for units;
- the per-group rule of `an-interval-is-numbered-by-its-packet` §3.2 and
  `unit-labels-order-by-length-then-by-unicode-scalar-value` §3.1, which checks that identifiers are
  dense from 0, and that each group's are contiguous and in the group's order.

Each cell gives the rows drawn in the first packet, then the second.

| addition | one order across the packet | per group |
|---|---:|---:|
| 120 intervals of `aind_opto.pulses`, a kind sorting before `dynamic_foraging.trials` | 570 / 828 | 0 / 0 |
| the same intervals under a kind sorting after it | 0 / 0 | 0 / 0 |
| a curation of the first sorting run, one unit per unit of the run | 4,505 / 6,781 | 0 / 0 |
| a curation of the last sorting run | 0 / 0 | 0 / 0 |

Whether a packet-wide order keeps identifiers therefore depends on how the added kind's resource ID
or run's identifier sorts. Renumbering the first packet with its pulses in the one order satisfies
the packet-wide rule and leaves none of the 450 trials with its identifier. For every misnumbering
those drafts test, the per-group rule draws as many rows as the packet-wide rule, or one fewer. Both
per-group rules pass the Part 11 static check, the unit rule with `CHARACTER_LENGTH` admitted as
`unit-labels-order-by-length-then-by-unicode-scalar-value` admits it.

### 2.3 An amendment cannot read a source

Part 00 §2.4 defines a build as one execution of a writer against one recipe. Part 05 §2's pipeline
binds a build, and Part 12's rules bind a build and the adapters it reaches. Part 05 §15 says
nothing of recipes, sources, adapters, normalization or provenance, and Part 05 §8 places derivation
into a committed packet in an amendment. Nothing in the specification lets an amendment read a
source through an adapter.

A recipe also describes a whole packet. Part 05 §3.1 has it declare the packet's clocks and their
parents, and Part 05 §3.5 refuses two things before any source opens:

- a required foreign key to a table nothing supplies;
- a clock referenced but absent, or parented to nothing.

A recipe adding a sniff sensor's device, clock and array parents the new clock to one the packet
already holds, which the recipe does not declare, and §3.5 refuses it. The added rows' required
references to tables only the packet supplies, such as `core.sessions`, draw the other refusal
unless the recipe supplies those tables again.

Part 05 §7 has a writer record one import run declaring its scope. The reference writer takes an
import as session-wide and scopes it to the session, as R44 §2.1 has a session-wide run do. A second
import into the same packet then shares `session_id`, `activity_type`, `scope_kind` and `scope` with
the first. Part 05 §12 has a packet holding two such runs carry a `core.preferred_runs` row naming
one of them, and has a writer refuse to commit one that does not, although the two imports supplied
different groups and neither is an alternative to the other. Neither session packet holds more than
one import run, so excluding import runs from the rule changes no finding on either, and the rule so
revised passes the Part 11 static check.

The reference writer's amendment takes only resources a caller stages through its API. Its
recipe-driven command builds a new packet, and its identifier numbering starts empty.

### 2.4 Nothing writes a preferred run

No recipe member declares a preferred run, and neither the reference writer nor any adapter in the
repository writes `core.preferred_runs`, although Part 05 §12 requires a row wherever a build yields
two runs sharing a scope. The recipe's `preference` table arbitrates between sources (Part 05 §3.3)
and chooses no run.

`core.processing_runs.scope` is a `string` paired value, which Part 02 §8.3 has hold the scoped
row's `*_name` where that row's key is assigned. Both packets' sorting runs carry a probe's
`probe_name`, such as `46101`, and each curation carries its sorting run's name. A recipe author can
therefore write a preference's scope before any identifier is assigned. The registry's descriptions
of `scope` and `scope_kind`, on `core.processing_runs` and `core.preferred_runs`, still say that
`scope` holds a primary-key value.

R41 §2.5 described changing a preference as an amendment whose only new file is
`core.preferred_runs`. That clause is recorded as rationale, and Part 05 §15.2 as incorporated
forbids it.

### 2.5 Nothing compares an amendment with the version it supersedes

Part 05 §15.4 has a writer validate the whole amended packet, and every check it re-runs reads the
current version alone. A comparison of the two manifests shows most of what Part 05 §15.2 asks,
since Part 05 §15.3 keeps the superseded manifest and a resource that names the same file in both is
unchanged. A table that gains a group is a new file, so only a comparison of rows shows that no
superseded row changed and no group grew. The reference validator reads no superseded manifest.

That comparison has two parts: the superseded rows the current version no longer holds unchanged,
and the added rows sharing their values under every declared group list with some superseded row. On
the first packet's `core.intervals`, grouped by session and kind:

| amendment | superseded rows missing or changed | added rows in an existing group |
|---|---:|---:|
| none | 0 | 0 |
| a new kind, 120 intervals | 0 | 0 |
| 120 trials added | 0 | 120 |
| one trial's bounds changed | 1 | 1 |
| one trial removed | 1 | 0 |

On the second packet's `core.spike_events`, 286,896,563 rows plus one added unit's spikes, grouped
by session and unit, both parts drew nothing in 12.0 s on 24 threads under a 32 GB memory limit.

Nothing reports a derived resource an amendment leaves stale either. R32 §7 recorded that nothing
detected one. Part 02 §2.2 gives every analysis and compatibility-projection resource lineage, and
Part 04 §7 records it as `derived_from`, so the amended manifest shows which of them read a table
the amendment wrote.

### 2.6 The portable profile rewrites a table that gains rows

Part 03 §9 writes a resource that gains rows as a new file the amended manifest names, and
Part 03 §5.1 makes a table one Parquet file, so a table gaining a group is rewritten whole, in key
order. Where a table is keyed by an assigned identifier and the group is numbered after the largest
one, the new file is the old rows followed by the new.

The cost is the rewrite. `core.spike_events` holds 131,396,535 rows (0.3 GB) in the first packet and
286,896,563 (0.7 GB) in the second, and a sorting added by amendment rewrites it. Part 03 §5.2
leaves member files to a future interface.

### 2.7 Accepted revisions left appending open

R32 §3 set Part 05 §15.2's scope table and its asymmetry, and R32 §8 left open whether the
provenance exception should become a general append mechanism. R92 §6 left open whether an amendment
may append, reading a table's order either per file or per table. Part 05 §15.2's table names only
core and analysis resources, and does not say what an amendment may do to an extension,
compatibility-projection or documentation resource.

### 2.8 Alternatives

| alternative | why it falls short |
|---|---|
| keep Part 05 §15.2 and number each table in one order across the packet | no v0.2 packet ever gains a kind of interval, a curation, a stream or a registration; each is a new packet, and every identifier held outside the old one is lost |
| keep the packet-wide order, and let an amendment add a group only where it sorts after every existing group | whether a group can be added depends on its name: `aind_opto.pulses` could never follow `dynamic_foraging.trials` |
| list the groups an amendment may add in Part 05 §15.2 | an extension cannot declare its own, and each new case needs a revision of Part 05 |
| let an amendment add rows to any group | a group a consumer read whole, such as a session's trials, grows, and nothing records which results read it |
| record which amendment added each row, and number by that first | a column in every table that can gain rows, and a single build over the same sources still numbers differently |
| split `core.intervals` into one resource per kind | adding a kind becomes adding a resource, and no single identifier names an interval, which `an-interval-is-numbered-by-its-packet` exists to give |
| amend only through resources a caller stages, with no recipe | no adapter delivers into an amendment, so every addition in §2.1 needs code outside the pipeline Part 12 binds |
| check an amendment's scope only in the writer | a validator given an amended packet cannot tell whether a row changed |
| make `amendment_groups` optional, absent meaning none | an absent declaration would claim that a table gains no rows, where Part 02 §9.3 makes every absent vocabulary a defect for the same reason |

## 3. Decision

Ten subsections define the groups a table declares, declare them on the core tables, restate what an
amendment may change, check it against the version it supersedes, let a recipe amend a packet,
continue its numbering, separate imports from alternatives, declare preferred runs, state
determinism over the amended packet, and advance the registry identifiers. The crosswalk in §1.1
places each.

### 3.1 A table declares the groups an amendment may add

Every `table` object carries `amendment_groups`, an array of **group lists**, beside its columns,
primary key, references and rules. A group list is a nonempty array of distinct column names of the
table. Under one group list, the rows whose listed columns hold equal values, a null equal to a
null, form one **group**. A table an amendment may not add rows to declares `[]`. Part 05 §15.2 lets
an amendment add rows to a table only in groups its superseded version lacks.

A group list MUST name only columns whose presence is `required` or `nullable`. Two group lists of
one table MUST NOT name the same set of columns. A table whose content class is not canonical MUST
declare `[]`, since an amendment may replace such a resource whole (§3.3).

The incorporated registry meta-schema MUST require `amendment_groups` in the `table` object, after
`rules`, declared as:

```json
{
  "type": "array",
  "uniqueItems": true,
  "items": {
    "type": "array",
    "minItems": 1,
    "uniqueItems": true,
    "items": { "$ref": "#/$defs/name" }
  }
}
```

The registry-contract descriptor MUST append the invariant `registry.amendment_groups.resolves`,
phase `semantic`, classes `core` and `extension`, anchors `ew-amendment-groups` and
`ew-registry-conformance`, after `registry.resource.canonical_targets`. A checker reports it for a
group-list member naming no column of its table or a column whose presence is `optional`, for two
group lists of one table naming the same set, and for a nonempty `amendment_groups` on a
non-canonical table. Its outcome points at the offending group list.

### 3.2 Core tables declare their groups

The incorporated core registry MUST declare one group list, the table's primary key, on each of
these tables: `core.sorting_runs`, `core.curation_versions`, `core.event_streams`,
`core.coordinate_frames`, `core.preferred_runs`, `core.array_assets`, `core.media_assets`,
`core.devices`, `core.clocks`, `core.probes`, `core.calibrations`, `core.processing_runs`,
`core.source_files` and `core.processing_run_inputs`.

It MUST declare these group lists, in this order, on these tables:

| tables | `amendment_groups` |
|---|---|
| `core.intervals` | `[["session_id", "interval_kind"]]` |
| `core.units` | `[["sorting_run_id", "curation_id"]]` |
| `core.spike_events`, `core.unit_electrodes`, `core.unit_observation_intervals` | `[["session_id", "unit_id"]]` |
| `core.sorting_run_channels` | `[["session_id", "sorting_run_id"]]` |
| `core.events` | `[["session_id", "stream_id"]]` |
| `core.event_stream_observation_intervals` | `[["event_stream_id"]]` |
| `core.coordinate_frame_axes` | `[["session_id", "coordinate_frame"]]` |
| `core.electrode_coordinates`, `core.electrode_coordinate_values` | `[["session_id", "coordinate_frame", "coordinate_basis"], ["electrode_id"]]` |
| `core.unit_coordinates`, `core.unit_coordinate_values` | `[["session_id", "unit_id"], ["session_id", "coordinate_frame", "coordinate_basis"]]` |
| `core.unit_quality_labels` | `[["session_id", "unit_id"], ["session_id", "source"]]` |
| `core.array_dimensions`, `core.array_labels`, `core.array_channels` | `[["array_asset_id"]]` |
| `core.media_frames` | `[["media_asset_id"]]` |
| `core.clock_anchors` | `[["clock_id"]]` |
| `core.clock_observation_intervals`, `core.clock_phase_steps` | `[["session_id", "clock_id"]]` |
| `core.electrodes` | `[["probe_id"]]` |
| `core.calibration_points`, `core.calibration_devices` | `[["calibration_id"]]` |

Every other table it declares MUST declare `[]`: `core.sessions`, `core.subjects` and
`core.session_experimenters`, which identify the packet, and the four analysis tables.

### 3.3 An amendment adds groups and changes no canonical row

An amendment **writes** a resource that the amended manifest names and the superseded manifest does
not name at the same `uri`. A resource an amendment writes is realized by its profile; the portable
profile writes it as a new file the amended manifest names, and changes no byte of the old one.

A writer performing an amendment MAY make, and MUST NOT make, these changes:

| change | |
|---|---|
| Add a resource the superseded manifest does not name | MAY |
| Add to a canonical table rows each forming, under at least one of the table's group lists, a group the superseded version lacks | MAY |
| Replace a `core.preferred_runs` row with a row of the same primary key | MAY |
| Remove or replace an analysis, compatibility-projection or documentation resource | MAY — Part 06 makes analysis resources disposable |
| Change or remove any other row of a canonical table | MUST NOT |
| Change a canonical resource that is not a table, or remove a canonical resource | MUST NOT |
| Change `packet_id`, `profile_id`, or the standard versions | MUST NOT |

A table's group lists are those its declaration carries in the registry the amended manifest binds.
An amendment never grows a group a consumer may have read whole, such as a session's trials or a
curation's units, because nothing in a packet records which derived results read which rows. A
packet whose canonical data was wrong is therefore a new packet, not a new version of an old one.

A preference is the one row an amendment may replace. Replacing one changes no row a run produced,
and the superseded version keeps the replaced row. An amendment removes no preference, so an
alternative Part 05 §12 resolved stays resolved.

A writer performing an amendment that writes a canonical table other than `core.processing_runs`,
`core.source_files` and `core.processing_run_inputs` MUST derive again from the amended packet, or
remove, every analysis and compatibility-projection resource whose `derived_from` chain (Part 04 §7)
reaches that table. The three provenance tables are exempt because their rows record what ran, not
what was measured.

### 3.4 An amendment is compared with the version it supersedes

A validator given a packet that retains a superseded manifest, and a writer validating an amendment
under Part 05 §15.4, MUST compare the current version with the superseded version whose
`packet_version` sorts last before the current one, and MUST report each of these at `error`:

| check | finding |
|---|---|
| `amendment.identity_changed` | the two manifests differ in `packet_id`, `profile_id`, `semantic_standard_version` or `logical_standard_version` |
| `amendment.resource_changed` | a canonical resource the superseded manifest names that the current manifest does not name, or names at another `uri` where the resource is not a table |
| `amendment.row_changed` | a row of a canonical table both manifests name and the amendment wrote, which the superseded version holds and the current version does not hold unchanged |
| `amendment.group_grown` | a row of such a table that the current version holds and the superseded version does not, where the table declares no group list, or where under every group list some superseded row shares its values |
| `amendment.derived_resource_stale` | an analysis or compatibility-projection resource both manifests name at the same `uri`, whose `derived_from` chain in the current manifest reaches a canonical table the amendment wrote other than the three provenance tables |

Two rows are equal where every column holds equal values, a null equal to a null. Neither
`amendment.row_changed` nor `amendment.group_grown` reports a replaced preference: a
`core.preferred_runs` row of the superseded version and the current version's row with the same
primary key. Group lists are those of §3.3. A validator attributes each finding under Part 05 §9.5.

Where the superseded version cannot be read, the comparison is an incomplete evaluation
(Part 05 §9.4) and not a finding. A packet that retains no superseded manifest has nothing to
compare.

### 3.5 A recipe may amend a packet

A build whose recipe gives `[packet].amends` is an **amending build**. It performs an amendment of
the packet at the root the build writes, and it is bound as an amendment wherever Part 05 binds a
build and an amendment differently. `amends` is a string matching `^\d+\.\d+\.\d+$`, the
`packet_version` of the packet's current manifest.

An amending build MUST refuse, before it opens any source:

- a packet root holding no published manifest, or one whose `packet_id` differs from `[packet].id`
  or whose `packet_version` differs from `amends`;
- a `[session]` member other than `session_id`, or a `session_id` the manifest's `sessions` does not
  list;
- a `[subject]` member; and
- a `clock` entry whose `clock_id` equals the `clock_name` of a `core.clocks` row the packet holds.

For every other refusal of Part 05 §3.5, the tables and clocks the packet holds count as supplied
and declared, so a required reference or a clock parent the packet satisfies draws no refusal.

The packet is not a source. Ownership and preferences (Part 05 §3.3) arbitrate among the recipe's
sources only, and §3.6 settles each delivered row against the packet. The packet's `core.sessions`
and `core.subjects` rows stand in place of declarations under Part 05 §3.6: a build reports a fact a
source states that differs from the packet's row, as it reports one differing from a declaration,
and refuses where that section refuses.

An amending build binds each registry its recipe names, and each registry the packet's current
manifest binds under an ID for which the recipe names none. In an amending build, materialization
(Part 05 §8) derives from the staged amended packet, and a derived resource replaces the resource of
the same ID the packet names.

### 3.6 An amending build numbers after the identifiers a packet holds

An amending build takes the packet's rows as delivered and normalized before any source runs, so the
terms of Part 12 §4 include them. It numbers a name the packet holds with the packet's identifier
for it, and every other name from one past the largest value the packet holds for that identifier,
or from 0 where it holds none. It orders the names it adds as a build orders a new packet's.

It then settles each row its sources deliver against the packet:

- a row of a table the packet's manifest does not name is added;
- a row equal, in every column but `metadata`, to a row the packet holds is dropped, together with
  any catalog instance the row catalogues;
- any other row is added where it forms, under at least one group list of its table (§3.3), a group
  the packet lacks.

An amending build MUST refuse every other delivered row, naming the table and the row.

### 3.7 An import run is no alternative to another

A writer MUST record the import's `core.processing_runs` row with `activity_type` `import`. An
amending build records a `core.source_files` row only for a root among its recipe's sources whose
`uri` no `core.source_files` row of the packet carries, and links its import run to the
`core.source_files` row of every root among the recipe's sources, held or added.

Runs whose `activity_type` is `import` are not alternatives to one another: two imports into one
packet supply disjoint groups (§3.3). Part 05 §12's requirement of a preference therefore reaches
only runs of another activity, and the incorporated core registry MUST declare
`core.processing_runs.undeclared_currency`, its level and message unchanged, as:

```sql
WITH grouped AS (
  SELECT session_id, activity_type, scope, COUNT(*) AS n
  FROM core.processing_runs
  WHERE scope IS NOT NULL
    AND activity_type <> 'import'
  GROUP BY session_id, activity_type, scope
  HAVING COUNT(*) > 1
)
SELECT g.session_id, g.activity_type, g.scope, g.n
FROM grouped AS g
WHERE NOT EXISTS(
  SELECT 1
  FROM core.preferred_runs AS p
  WHERE p.activity_type = g.activity_type
    AND p.scope = g.scope
    AND (p.session_id = g.session_id OR (p.session_id IS NULL AND g.session_id IS NULL))
)
```

### 3.8 A recipe declares preferred runs

A recipe MAY declare preferred runs in `preferred_run`, an array of tables, which the recipe schema
declares after `preference` as:

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["activity_type", "scope_kind", "scope", "processing_run_name"],
    "properties": {
      "activity_type": { "type": "string", "minLength": 1 },
      "scope_kind": { "type": "string", "minLength": 1 },
      "scope": { "type": "string", "minLength": 1 },
      "processing_run_name": { "type": "string", "minLength": 1 },
      "reason": { "type": "string", "pattern": "\\S" },
      "chosen_at": {}
    },
    "additionalProperties": false
  }
}
```

The schema leaves `chosen_at` untyped, since TOML dates and times decode to values JSON Schema has
no type for, and a build normalizes it to the column's type. The schema's `packet` object admits
`amends`, declared as `{"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"}`.

A build MUST write one `core.preferred_runs` row per entry, in the recipe's session, carrying the
entry's `activity_type`, `scope_kind`, `scope`, `reason` and `chosen_at`, and naming as
`processing_run_id` the run whose `processing_run_name` the entry gives. In an amending build, the
row replaces the packet's row with the same primary key. A build MUST refuse, before it opens any
source, a recipe with two entries sharing `activity_type`, `scope_kind` and `scope`. It MUST refuse
an entry whose `processing_run_name` names no run the packet holds or the build records, naming the
entry.

An entry's `scope` names the scoped row as Part 02 §8.3 has a `string` paired value name it. The
incorporated core registry MUST describe `scope`, on `core.processing_runs` and
`core.preferred_runs`, as the scoped row's key where that key is carried and its `*_name` where it
is assigned, and `scope_kind` on each as the resource holding that row.

### 3.9 Determinism covers the amended packet

A writer's normalization MUST be deterministic in the recipe and, for an amending build, in the
packet version it amends: two runs of one recipe over the same sources and the same packet version
produce the same packet. Part 05 §11's fifth criterion covers the same inputs, and identifier
assignment MUST be a function of the recipe, the sources and, for an amending build, the packet it
amends.

A packet's identifiers are therefore a function of the sequence of recipes that built and amended
it, each of which its import runs record (Part 05 §3.2). A single build over the same sources
reproduces them only where no group an amendment added sorts before one the packet held.

### 3.10 The registry identifiers advance

These incorporated identifiers MUST advance:

| artifact | from | to |
|---|---|---|
| registry meta-schema `$id` | `https://escapewheel.org/schemas/registry/0.9.0` | `https://escapewheel.org/schemas/registry/0.10.0` |
| registry-contract descriptor ID | `escapewheel-registry-contract-v0.7`, which `unit-labels-order-by-length-then-by-unicode-scalar-value` assigns | `escapewheel-registry-contract-v0.8` |
| core registry `registry_version` | `0.11.0`, which `unit-labels-order-by-length-then-by-unicode-scalar-value` assigns | `0.12.0` |
| recipe schema `$id` | `https://escapewheel.org/schemas/recipe/0.1.0` | `https://escapewheel.org/schemas/recipe/0.2.0` |

The v0.8 descriptor selects meta-schema 0.10.0, lists `escapewheel-rule-sql-v0.2` alone in
`rule_languages`, and otherwise differs from v0.7 only by §3.1's invariant. Part 02 §1 incorporates
it as `registry/registry_contracts/escapewheel-registry-contract-v0.8.json`.

An extension registry migrated to meta-schema 0.10.0 MUST carry a `registry_version` different from
the one it carried under 0.9.0; the core specification does not assign it (Part 09 §5.5). No checker
verifies this.

## 4. What this does not change

An adapter delivers into an amending build as into any build, so Part 12 is unchanged; the terms it
lists carry the packet's rows through Part 05 §4.3. The manifest, Part 04 and Part 05 §§15.3–15.5
are unchanged: an amended packet retains every superseded manifest, revalidates as before and cleans
up separately. A correction is still a new packet.

An added row may reference rows the packet holds, but no row the packet holds can come to reference
an added one. A stream written without a device cannot be attached to a device an amendment adds,
and a clock cannot move under an added parent; each is a correction. A canonical resource whose
`derived_from` reaches a table an amendment wrote is left as it is, since no amendment changes a
canonical resource. Part 03 §5.2's member files stay deferred, so a table gaining a group is
rewritten whole.

## 5. Consequence

Every packet is rebuilt, binding meta-schema 0.10.0 and core registry 0.12.0, at the rebuild the two
drafts this depends on already require. No row changes in either session packet or in any fixture
packet. Every repository registry declares `amendment_groups` on each of its tables, and the four
repository extension registries advance their versions without changing a rule; what an extension's
tables declare is the extension's own decision. A registry document without the member fails the
`shape` phase of Part 02 §9.4.

Identifiers now depend on a packet's history as well as its sources: a single build over all an
amended packet's sources numbers its groups by their columns, and differs from the amended packet
wherever an added group sorts before a held one. Every identifier is stable across a packet's
amendments, which is where references outside it are made.

These accepted clauses change:

- R32 §3, which set Part 05 §15.2's scope table, is superseded by §3.3.
- R32 §2's ledger entry, whose Part 03 §9 destination notes that a table gaining rows is a new file,
  gains a note that §3.3 extends the statement to every resource an amendment writes.
- R82 §§2.1, 2.3 and 2.4 gain notes that §3.7 exempts import runs, and the destinations of §§2.3 and
  2.4, which name Part 05 §12 by number, move to its anchor.
- R75 §§2.1–2.3 gain notes that §3.9 states determinism over the packet version an amending build
  amends.
- R54 §2.6's destination, which names Part 05 §4.3 by number, moves to its anchor.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 states no amendment rule. | None required. |
| logical prose and registry | Part 02 §2.3 names the member, Part 02 gains *Amendment groups* with its anchor, and Part 02 §§1, 9.2 and 9.4 take §3.10's identifiers and §3.1's invariant. `registry/registry.schema.json` requires the member; the core registry source declares §3.2's lists, §3.7's rule and §3.8's descriptions; `registry/check.py` implements the invariant and follows the new identifiers. | `evidence/R<N>.json` names each anchor and registry pointer; `registry/check.py` passes. |
| physical profiles | Part 03 §9's sentence covers every resource an amendment writes. Part 03 §5.2 is unchanged. | `evidence/R<N>.json` names the anchor. |
| packet manifest and JSON Schemas | The registry meta-schema, as above, and `registry/recipe.schema.json`, which admits `amends` and `preferred_run`; `registry/build.py` copies the recipe schema into the writer. The manifest schema is unchanged. | `registry/build.py` regenerates byte-identically. |
| validation and import | Part 05 §§1, 3.1, 3.3, 3.5, 3.6, 4.3, 7, 8, 11, 12, 15.1 and 15.2 take §§3.3–3.9, and Part 05 gains *Comparison with the superseded version*. Part 12 is unchanged. | `evidence/R<N>.json` names each anchor. |
| extensions | Each of the four repository extension registries declares `amendment_groups` on its tables and advances its `registry_version`; the core specification does not choose either. | `registry/check.py` over every extension registry. |
| reader, writer, validator, adapters | The writer runs a recipe with `amends` as an amending build: it seeds its numbering from the packet, drops delivered rows the packet holds, refuses a row growing a group, binds the packet's registries, records a new source file only for a new root, writes `core.preferred_runs` from the recipe, derives again or drops each stale derived resource, and runs §3.4's comparison. The validator reads the last superseded manifest and makes the same comparison. The reader reads the current manifest; its description of a preference's scope follows §3.8. Adapters are unchanged. | The writer and validator suites; both session packets rebuilt and validated with no error; an amending build of each adding intervals and a curation. |
| conformance fixtures and tests | Amended fixture packets as §6 lists, each carrying its superseded manifest. Negative registry variants for `registry.amendment_groups.resolves` and a table object lacking the member. Writer tests for each refusal of §§3.5, 3.6 and 3.8. | `fixtures/corpus.py`; the registry-conformance vectors. |
| revision process and tooling | The ordinary ledger and evidence records, R32 §3's supersession, and the notes above. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | `registry/tables.md` renders each table's group lists; Part 08 §§2 and 3 regenerate with the new registry versions; the registry guide documents the member; the writer's guide documents `amends` and `preferred_run`; the specification README's identifier table, `framework.py`'s expected version, the combined specification and the heading index follow. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 02 §§2.3, *Amendment groups* and 9.4. §3.2 is `registry`. §3.3 is
`applied` at Part 05 §§15.1 and 15.2 and Part 03 §9, and §3.4 at Part 05 §1 and *Comparison with the
superseded version*. §3.5 is `applied` at Part 05 §§3.1, 3.3, 3.5, 3.6, 8 and 15.1, and §3.6 at
Part 05 §4.3. §3.7 is `applied` at Part 05 §§7 and 12 and `registry` for its rule. §3.8 is `applied`
at Part 05 §§3.1, 3.5 and 12 and `registry` for its descriptions, §3.9 at Part 05 §§4.3 and 11, and
§3.10 at Part 02 §§1, 9.2 and 9.4 and Part 05 §3.1. Each is placed by canonical anchor.

These cases distinguish the new rules from the current ones:

- an amendment adding 120 intervals of a kind sorting before the packet's trials, numbered after the
  largest identifier, is conforming and draws nothing from §3.4, where Part 05 §15.2 forbids it
  today;
- an amendment adding a curation of the first sorting run, with its units, spikes and unit
  electrodes, is conforming;
- an amendment replacing a `core.preferred_runs` row is conforming;
- a packet holding two import runs sharing a session and scope draws no
  `core.processing_runs.undeclared_currency`, where today it draws the rule;
- an amendment adding a trial to a session's trials draws `amendment.group_grown`, and a writer
  refuses to build it;
- an amendment changing one trial's bounds draws `amendment.row_changed` and
  `amendment.group_grown`, and one removing a trial draws `amendment.row_changed`;
- an amendment adding a curation and keeping an analysis resource derived from `core.units` at its
  old `uri` draws `amendment.derived_resource_stale`;
- an amendment naming a canonical array instance at a new `uri` draws `amendment.resource_changed`,
  and one changing `profile_id` draws `amendment.identity_changed`;
- a packet whose superseded version's files were removed reports the comparison incomplete;
- a registry declaring a group list that names an absent or `optional` column, two group lists of
  one table naming one set, or a group list on an analysis table draws
  `registry.amendment_groups.resolves`, and a `table` object lacking the member fails the `shape`
  phase;
- an amending recipe whose `amends` names another version than the packet's current one, that
  carries a `[subject]` member, or that redeclares a clock the packet holds, is refused before any
  source opens, as is a recipe with two `preferred_run` entries sharing a key; and
- an amending build whose source delivers the packet's rows again drops them and adds only the new
  groups.

The positive cases also include the two rebuilt session packets and the valid corpus packet.
Feasibility rests on §2's measurements: both per-group numbering rules and §3.7's rule pass the Part
11 static check, and §3.4's comparison ran over the second packet's `core.spike_events`, the largest
table in either, in 12.0 s.
