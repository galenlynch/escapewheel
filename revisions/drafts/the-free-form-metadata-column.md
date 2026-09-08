# The Free-Form Metadata Column

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `02` §5.2 (the clause against filling a `json_string` routinely), `09` §2 (the tier table), the 21 registry declarations of `metadata` and their descriptions |
| **Depends on** | R48 (a column declares its role), R46 (the references that make "its own" decidable), R53 (identity), R2 §5 (three-state presence), R91 §3.3 (what `core.events.payload` is for) |
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
name is derivable from the id, and the ancestry path is a delimited list `03` forbids as a column.
One JSON object, one prefix, opposite verdicts.

### 2.4 The cost of filling one

`02` §5.2 says a writer SHOULD NOT fill a `json_string` column routinely, because "a column present
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

Both bounds are decidable from the registry with no packet in hand, as R56 §2.4's is, so
`registry/check.py` enforces them: a table owing a `metadata` column and lacking one is a build
error, and so is a relationship table carrying one. What lies between is a declaration each table
makes, which is the part that is a judgement and should be.

### 3.2 Routine filling

`02` §5.2's sentence forbidding routine filling is **struck**. A writer **MAY** fill `metadata` on
every row of a table that declares it.

§2.4 measures why: an unprojected column is not read, and an optional one need not be written at
all. `02` §5.2's ban on `list`, `struct` and `map` stands, and so does R3 §2.1's guarantee that a
conforming reader satisfies every required column without a JSON parser. §3.3 is what keeps that
guarantee true in practice rather than only in form.

### 3.3 Content

A writer **MUST NOT** emit a `metadata` key holding a fact that a column of the logical schema
holds, and **MUST NOT** emit one that contradicts such a column.

**No rule checks this and none is added.** The content is schemaless by design, so a constraint on
it is unenforceable in principle rather than merely in practice, and §2.3 measures that names carry
no signal to check against. The obligation binds the writer, as R67 §2.4's prohibition on inferring
attachment from a device's name binds a consumer, and for the same reason: a named actor can comply
where no validator can observe them.

A fact required to interpret the data therefore belongs in a column, never in a key.

### 3.4 The column's description and its tier

Every declaration's description is replaced by one text: what the source stated about this row that
the standard does not model, carried in the source's own vocabulary and read by no rule.

`09` §2's tiers place a fact in the catalog, in a core table, in an extension's tables, or in a
`docs/` sidecar, and never place a `json_string` column inside a core table. The table gains a row
for it, holding tier 3 or tier 4 content that no rule reads.

## 4. What this does not change

- **No reference and no Tier 2 rule.** `registry/rules.json` names neither `metadata` nor `payload`,
  so the 96 references and 69 rules are untouched.
- **No packet is invalidated.** The validator walks the registry's columns and asks whether each is
  present in the file; nothing looks for columns the registry does not declare, so striking one
  cannot fail a packet that still carries it. None does.
- **`core.intervals` keeps its `metadata`.** `interval_id` is an identifier of its own, so a new
  interval kind may record a few unmodelled facts without an extension. R90 §3.5's shared-key
  detail table stays the path for facts needing structure rather than becoming the only path.
- **The two unwritten prose columns stay.** `core.curation_versions.notes` is filled in 0 of 12 and
  0 of 10 rows, `core.sessions.session_description` in 0 of 1 in both. They are typed prose rather
  than free-form bags, so striking them is a decision about those two tables; §6 records it.
- **`core.electrodes` keeps two of its four `ccf_*` keys.** R59 §2 declined to model `ccf_name` and
  `ccf_structure_id_path`, so the column is where they belong.
- **`core.events.payload` stays.** R91 §3.3 keeps it as the only home a per-event value has until an
  extension declares a mark table through `core.event_streams.detail_kind`, and forbids a writer
  putting a mark in `core.events.metadata` — so this part has nowhere to move the NWB adapter's
  `{"value": …}` object to. That leaves one table carrying two free-form columns where §3.1 requires
  one, which §6 records.

## 5. Consequence

Three columns are struck and 333 becomes **330**. None is forbidden by §3.1 — all three sit in its
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

`registry/check.py` gains the §3.1 check, `build.py` emits the column from the primary key, `09` §2
gains a row, and twenty-one descriptions become one.

## 6. Open

- **Whether the two unwritten prose columns should be struck.** R62 struck a file on this evidence —
  written by nothing, read by nothing — and `core.curation_versions.notes` beside a `metadata`
  column filled on 12 of 12 rows is the same shape one level down. It is a decision about
  `core.curation_versions` and `core.sessions` rather than about free-form columns, so it is not
  taken here.
- **Whether a writer-side test should compare values rather than names.** §3.3 is unenforceable by a
  rule, but the reference implementation could compare each `metadata` value against the columns its
  table reaches and report a key agreeing on every row. It would have caught all three of §2.3 and
  would cost nothing to run, 8,230 rows holding the column at all. That belongs in `07` §4 beside
  `STATES` rather than in a normative part, and needs a guard against one constant column matching
  another by accident.
- **Whether a measurement table should be told when to declare one.** §3.1 leaves the middle band
  to each table's judgement, which is where the three struck columns came from: someone declared a
  `metadata` on `core.spike_events` because the shape allowed it, and 286,896,563 rows carried a
  column no adapter ever filled. The bound that would have caught it is evidence rather than
  structure — a column no writer fills is a column to strike (R62) — and nothing runs that check
  on its own.
- **Whether `core.events.payload` should be struck.** §4 leaves it because R91 §3.3 does, and R91
  §6 says what would settle it: an extension declaring a mark table through
  `core.event_streams.detail_kind` gives a per-event value a typed home and makes the strike free.
  Until one exists, striking `payload` removes the only place such a value may go, R91 §3.3 having
  forbidden `core.events.metadata` as its substitute. It is the one column this part would
  otherwise reach that another document has already reasoned about.
