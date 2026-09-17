# R97 — The Free-Form Metadata Column

| | |
|---|---|
| **Status** | **Accepted** 2026-09-08 |
| **Amends** | Part 02 §5.2 (the clause against filling a `json_string` routinely), Part 09 §2 (the tier table), the 21 registry declarations of `metadata` and their descriptions |
| **Depends on** | R48 (a column declares its role), R46 (the references that make "its own" decidable), R53 (identity), R2 §5 (three-state presence), R91 §3.3 (what `core.events.payload` is for), R94 §3 (which asks this part for the presence rule) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`metadata` is an optional `json_string` column carrying what a source stated about a row that the
standard does not model. Twenty-one of the registry's 38 tables declare one.

Nothing says which tables should declare it, what may go in one, or what must not, and each gap has
produced a defect: a column on a 286,896,563-row table that nothing could usefully fill, a
description that restates the column's name on 16 tables, and three keys holding a fact a typed
column already holds. This part settles all three — which tables declare the column, whether a
writer may fill it, and what a key may not hold.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25).

## 2. Background

Informative.

### 2.1 The column's descriptions

The registry describes it as **"Additional metadata."** on 16 tables, "Free-form metadata." on one,
and "Additional ⟨table⟩ metadata." on three. A reader learns from that what the name already gave
them, and an adapter author learns nothing.

### 2.2 What the packets carry

The writer omits the column outright on ten of the twenty-one tables declaring it, and three of the
twenty-one exist in neither packet. The eight that are written are entity tables of 10 to 4,608 rows:
`core.electrodes`, `core.processing_runs`, `core.devices`, `core.array_assets`,
`core.curation_versions`, `core.probes`, `core.sorting_runs`, `core.event_streams`.

Across both packets **8,230 rows hold a `metadata` value at all**, and **8,064 of them — 98% — are
`core.electrodes`**, the one table whose content is a defect.

### 2.3 Keys that restate a column

| key | the column holding the same fact | agreeing rows | promoted by |
|---|---|---|---|
| `core.electrodes.metadata.ccf_id` | `core.electrode_coordinates.region_id` | 8,064 / 8,064 | R59 §2 |
| `core.electrodes.metadata.ccf_acronym` | `core.electrode_coordinates.region_label` | 7,012 / 7,012 | R59 §2 |
| `core.devices.metadata.port` | `core.devices.parent_port` | 7 headstage rows | R85 §2.1 |

Each arose the same way: a revision moved a fact from the bag into a typed column and nothing
removed the adapter's copy. The third is visible in one dict literal —
`sources/openephys.py:147` writes `parent_port` from `probe["port"]`, and line 148 writes
`{k: probe[k] for k in key}` where `CHAIN` gives a headstage `key = ("slot", "port")`.

Comparing names catches none of it. **Zero of the 20 distinct keys in either packet share a name
with any column anywhere in the registry**, because an adapter names a key in the source's
vocabulary — `ccf_id`, `port`, `spikeinterface_version` — and core names a column in its own:
`region_id`, `parent_port`. That divergence is what the column is for.

A list of retired keys would not close it either, and the same table shows why. `core.electrodes`
holds four `ccf_*` keys splitting two against two: `ccf_id` and `ccf_acronym` are forbidden, while
`ccf_name` and `ccf_structure_id_path` must stay, R59 §2 having declined both deliberately — the
name is derivable from the id, and the ancestry path is a delimited list Part 03 forbids as a column.
One JSON object, one prefix, opposite verdicts.

### 2.4 The cost of filling one

Part 02 §5.2 says a writer SHOULD NOT fill a `json_string` column routinely, because "a column present
on every row forces a parse on every row, in exactly the table where a consumer works."

Parquet reads the columns a query projects and no others, so the cost falls only on a consumer who
asks for it. Measured over 5,000,000 rows shaped after `core.electrodes`, with the real CCF payload
and zstd:

| | file | footer | **bytes read for the four typed columns** | time |
|---|---|---|---|---|
| without `metadata` | 61.81 MB | 2.9 kB | **61.81 MB** | 33.0 ms |
| with `metadata` | 63.68 MB | 4.8 kB | **61.81 MB** | 29.6 ms |
| with, projecting it | | | 63.68 MB | 394.6 ms (**11.95x**) |

The projected bytes are identical and the whole cost is 1.9 kB of extra footer. R2 §5's third
presence state compounds it: `optional` lets a writer omit the column entirely, which it does on
`core.spike_events` at 286,896,563 rows.

## 3. Decision

### 3.1 Which tables declare `metadata`

A table's registry entry **MUST** declare `metadata` where its primary key includes a column whose
R48 role is `identifier` and which is not part of a declared reference. It **MUST NOT** declare one
where every key column is part of a declared reference. Between those it **MAY**, and declares one
where a source has something to put in it.

The **MUST** rests on identity: an identifier of the table's own is what makes the row a thing
rather than a statement about other things. Seventeen of 38 tables have one — `unit_id`,
`device_id`, `interval_id`, `probe_id` among them — and **all seventeen already declare `metadata`,
none missing**.

Whether that identifier is `assigned` or `carried` (R53 §2.3) does not matter, and both occur:
`core.devices.device_id` is assigned where `core.intervals.interval_id` is carried from the
source's own trial number. What matters is that the table holds an identity rather than borrowing
one.

The **MUST NOT** rests on something narrower, and reaches three tables: `core.unit_electrodes`,
`core.processing_run_inputs` and `core.calibration_devices`, whose keys are made entirely of other
tables' identifiers. A row like that is a relationship, and nothing can be said about a
relationship that is not a fact about one of its ends.

Everything between is a measurement — another table's identifier plus a coordinate (`t_tick`,
`start_tick`) or a structural index (`frame_index`, `channel_index`) — and a measurement **may**
carry attributes of its own. A frame has a coding type, a channel a note about how it was
calibrated, an event a value. So the three columns §5 strikes are struck on the evidence that no
adapter writes them and no consumer asks, which is the standard R62 struck a file on, and not
because the shape of the key forbids them.

A `metadata` column **MUST** be declared `optional`. All 21 already are, so nothing changes in the
registry; what changes is that R94 §3's check becomes sound by construction rather than by
observation. That check refuses a Tier 2 rule naming an optional column and matches the bare name,
which is correct only while every column called `metadata` is optional — R94 §3 records the
exposure and names this part as the one that closes it.

Both bounds are decidable from the registry with no packet in hand, as R56 §2.4's is, so
`registry/check.py` enforces them: a table owing a `metadata` column and lacking one is a build
error, and so is a relationship table carrying one. An extension is a registry document in the
same format (R17 §2), so both bounds bind one as they bind core, and the check runs against all
four. What lies between is a declaration each table makes, which is the part that is a judgement
and should be.

A judgement can still be reported against evidence. A validator **SHOULD** report, at `info`, a
declared `metadata` column filled in no row of the packet — the same level and shape as R95 §3.3's
duplication report, and R62's standard mechanised. It is what would have found the three columns §5
strikes: someone declared one on `core.spike_events` because the middle band allowed it, and
286,896,563 rows carried a column no adapter ever filled.

### 3.2 Routine filling

Part 02 §5.2's sentence forbidding routine filling is **struck**. A writer **MAY** fill `metadata` on
every row of a table that declares it.

§2.4 measures why: an unprojected column is not read, and an optional one need not be written at
all. Part 02 §5.2's ban on `list`, `struct` and `map` stands, and so does R3 §2.1's guarantee that a
conforming reader satisfies every required column without a JSON parser. §3.3 is what keeps that
guarantee true in practice rather than only in form.

### 3.3 Content

A writer **MUST NOT** emit a `metadata` key holding a fact that a column of the logical schema
holds, unless the duplication buys access that is otherwise unavailable, and **MUST NOT** emit one
that contradicts such a column under any circumstance.

The exception is R3 §3.0's, inherited rather than invented: that clause forbids a table restating
what the data it describes declares, on the same terms, so the bag is exactly as strict as the
schema around it and no stricter. It is also what keeps the prohibition satisfiable — a writer with
a reason may keep the key and say why, where a writer that never noticed is the defect §2.3
measures three of. The second half takes no exception, since a contradiction buys nothing by
definition.

**No rule checks this and none is added.** The content is schemaless by design, so a constraint on
it is unenforceable in principle rather than merely in practice, and §2.3 measures that names carry
no signal to check against. A writer-side test can still report it, and the shape is settled: R95
§3.3 compares two columns of one table for equal values in every row, excluding a pair that is
constant, and bounds itself by row-group statistics. The same comparison over a `metadata` key and
a column is what would have caught all three of §2.3, and it belongs in Part 07 §4 beside `STATES`
rather than in a normative part. The obligation binds the writer, as R67 §2.4's prohibition on inferring
attachment from a device's name binds a consumer, and for the same reason: a named actor can comply
where no validator can observe them. Uncheckable is not unsatisfiable, and the two are distinct
defects — a requirement naming no actor binds nothing, where this one names the only party that
knows what it put in the bag.

A fact required to interpret the data therefore belongs in a column, never in a key.

**Prose belongs in a prose column where the table has one.** A `metadata` value is for a fact with
structure the standard does not model; a human-readable string has no structure to preserve, so
wrapping it in a JSON envelope costs a writer a serialisation, puts the value where no rule reads
it and no filter uses it (R66 §1.4), and buys none of the otherwise-unavailable access §3.3's
exception requires. A writer **SHOULD** put prose in the column and not in the bag.

The registry is short of such columns — three across 38 tables, `core.calibrations.description`,
`core.curation_versions.notes` and `core.sessions.session_description` — and the shortage already
shows. `sources/aind.py:417` writes a calibration's `notes` into `metadata` because `description`
carries the source's description field and there is nowhere else for the second string to go. That
argues for a prose column on `core.calibrations` rather than against the ones that exist, and
adding a column is not this part's subject.

### 3.4 The column's description and its tier

Every declaration's description is replaced by one text: what the source stated about this row that
the standard does not model, carried in the source's own vocabulary and read by no rule.

Part 09 §2's tiers place a fact in the catalog, in a core table, in an extension's tables, or in a
`docs/` sidecar, and never place a `json_string` column inside a core table. The table gains a row
for it, holding tier 3 or tier 4 content that no rule reads.

## 4. What this does not change

- **No reference and no Tier 2 rule.** `registry/rules.json` names neither `metadata` nor
  `payload` — R94 §3's check is what now keeps it so — and the 94 references and 70 rules are
  untouched.
- **No packet is invalidated.** The validator walks the registry's columns and asks whether each is
  present in the file; nothing looks for columns the registry does not declare, so striking one
  cannot fail a packet that still carries it. None does.
- **`core.intervals` keeps its `metadata`.** `interval_id` is an identifier of its own, so a new
  interval kind may record a few unmodelled facts without an extension. R90 §3.5's shared-key
  detail table stays the path for facts needing structure rather than becoming the only path.
- **The two unwritten prose columns stay, for different reasons.** `core.sessions.session_description`
  is filled in 0 of 1 rows in both packets and is nonetheless written: `sources/nwb.py` maps it and
  `session.json` carries it, so the column is empty because the source's field is. R62 strikes what
  is written by nothing *and* read by nothing, and this fails the first half.
  `core.curation_versions.notes` — 0 of 12 and 0 of 10 — meets both halves and is kept anyway:
  §3.3 makes a prose column the place prose goes, and striking the only one on that table would
  leave `metadata` as the answer, which is the trade `sources/aind.py:417` already makes for want
  of a column. Unwritten is not the same as unwanted where the alternative is worse.
- **`core.electrodes` keeps two of its four `ccf_*` keys.** R59 §2 declined to model `ccf_name` and
  `ccf_structure_id_path`, so the column is where they belong.
- **`core.events.payload` stays.** R91 §3.3 keeps it as the only home a per-event value has until an
  extension declares a mark table through `core.event_streams.detail_kind`, and forbids a writer
  putting a mark in `core.events.metadata` — so this part has nowhere to move the NWB adapter's
  `{"value": …}` object to. That leaves one table carrying two free-form columns where §3.1 requires
  one, which §6 records.

## 5. Consequence

Three columns are struck and 324 becomes **321**. None is forbidden by §3.1 — all three sit in its
**MAY** band — so each is struck on the same evidence: no adapter writes it and no consumer asks.

| struck | rows in the packets | state today |
|---|---|---|
| `core.spike_events.metadata` | 286,896,563 / 131,396,535 | omitted by the writer |
| `core.media_frames.metadata` | — / 7,570,450 | omitted |
| `core.array_channels.metadata` | 1,152 / 960 | omitted |

Three keys stop being written: `ccf_id` and `ccf_acronym` in the NWB adapter's electrode rows, and
`port` in the Open Ephys adapter's device rows. Those are writer changes and they land in the
rebuild R87 §2.1 and R88 §2 already require, forcing none of their own. After
them, `metadata` across both packets falls from 8,230 rows to **166**.

Two extension tables owe a column and declare none: `aind_opto.stimulations`, keyed on a carried
`epoch_id`, and `dynamic_foraging.blocks`, on an assigned `block_id`. Both gain one. Nothing
regenerates an extension registry, which is why §3.1's check runs against all four rather than
against core alone.

`registry/check.py` gains the §3.1 check, `build.py` emits the column from the primary key, Part 09 §2
gains a row, and twenty-one descriptions become one.

## 6. Open

- **Whether `core.events.payload` should be struck.** §4 leaves it because R91 §3.3 does, and R91
  §6 says what would settle it: an extension declaring a mark table through
  `core.event_streams.detail_kind` gives a per-event value a typed home and makes the strike free.
  Until one exists, striking `payload` removes the only place such a value may go, R91 §3.3 having
  forbidden `core.events.metadata` as its substitute. It is the one column this part would
  otherwise reach that another document has already reasoned about.
