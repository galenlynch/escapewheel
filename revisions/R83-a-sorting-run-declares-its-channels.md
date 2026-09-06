# R83 — A Sorting Run Declares Its Channels

| | |
|---|---|
| **Status** | **Accepted** 2026-09-05 |
| **Amends** | `02` (adds `core.sorting_run_channels`), R28 §2 (what `core.unit_electrodes` may name), R3 §6 (a structural index's coordinate system) |
| **Depends on** | R28 (a unit sits on many electrodes), R38 (a sorting run names its clock), R46 (a reference is declared), R48 (a column declares its role), R53 (an identifier is an integer) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

Measured on the two AIND Neuropixels sessions this project has packaged: **`ecephys_776259`**,
twelve probes and 6,781 sorted units, and **`ecephys_786867`**, ten probes and 4,559. Both were
sorted by Kilosort 4 under SpikeInterface 0.104.7, so what §1.3 finds them disagreeing about is
not a difference of version.

## 1. Motivation

### 1.1 `extremum_channel_index` indexes a channel list the NWB never writes down

The NWB records which electrode a unit peaks on in `extremum_channel_index`. Both adapters in this
project read it as a position in the probe's contact list; it is a position in the list of channels
the sorting kept, and the two lists differ by however many channels that sorting dropped. The
analyzer that produced the value holds that list; the file carrying it does not. Read the first way
it names the wrong electrode for **5,071 of 6,781 units** on `ecephys_776259`, one contact off for
each channel dropped below it.

`ecephys_776259` bears that out probe by probe: the largest value a probe's units carry, plus one,
equals the channel count its analyzer states, on **11 of the 12 probes**. Those counts run from
366 to 384. The twelfth probe is one short, no unit having peaked on its last channel.

Nothing caught the error until it produced a unit with no primary electrode at all. The index
lands outside its own unit's channel support for 609 of the 6,781, so those rows went missing
entirely while the other 4,462 kept a row naming the wrong contact.

The convention is invisible on a run that dropped nothing. `ecephys_786867`'s analyzer kept every
contact, its largest index reaching 384 on four probes and its units carrying signal on all 384 of
five — two of those probes ones whose preprocessing had flagged channels bad — so an index into
the kept channels and a contact number are the same number there. What distinguishes the two cases
is the channel count, which neither packet carries.

### 1.2 The packet cannot state which channels a sorting used

`core.electrodes` holds every contact and `core.unit_electrodes` names the contacts some unit had
signal on. Neither is the set a sorting ran on. Measured on `ecephys_776259`:

| | contacts | kept by the sorting | named by some unit |
|---|---:|---:|---:|
| twelve probes | 4,608 | 4,510 | 4,508 |

What a unit had signal on is a **lower bound**, and a loose one. Probe 46122 kept 383 channels of
which two carried no unit, so the packet's best answer is 381; on `ecephys_786867` the gap reaches
**50 of 384** on probe 50213-4, where units cover 334 contacts of a run that kept every one. The
bound lands exactly right on the other probes by luck, and nothing marks which those are.

The bound errs in the direction that matters. Units per contact divides by 384 where the
denominator is 366 on two of these probes — 4.7%, concentrated rather than spread, because a dead
channel usually belongs to a run of them at the end of a shank.

Resolving an index also needs the kept channels **in order**, which membership does not give.
Index 348 on probe 46122 means contact CH365, and finding that out means counting through the 383
channels that sorting kept.

### 1.3 Only one session records the channels it sorted on

`ecephys_776259` records its channel list directly, as `channel_ids` under
`postprocessed/<stream>.zarr/recording_info` — 383 names for probe 46122, with `CH2` absent.

`ecephys_786867` records no channel list anywhere. Its curated output carries `unit_ids` alone, and
its only channel statement is the preprocessing's `bad_channel_ids` — 27 contacts over ten probes,
labelled 24 `dead` and 3 `out`. That list is not the complement of what the sorting used, though
its class name says the channels were removed: the templates carry signal on **727 (unit, channel)
cells** among them, so a writer taking it for the kept set would exclude channels the run had.

Core exists to carry exactly this: a fact one export records, another records elsewhere, and
neither makes derivable. R59 found the same shape for the atlas annotation and R66 for the
firmware version.

## 2. Decision

### 2.1 A new table names a run's channels in order

`core.sorting_run_channels` is added to `02`, one row per channel of one sorting run:

| column | type | presence | role | description |
|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | The session. |
| `sorting_run_id` | `int32` | required | identifier | The run these channels belong to. |
| `channel_index` | `int64` | required | structural_index | Position in the run's own channel order, 0-based. |
| `electrode_id` | `int32` | required | identifier | The contact at that position. |

Primary key `(session_id, sorting_run_id, channel_index)`, sorted by it, with references to
`core.sorting_runs` and `core.electrodes` declared (R46 §2). `channel_index` is `int64` because
every structural index in the registry is, `core.array_channels.channel_index` included, and two
columns of one name and one meaning may not differ in type. A contact **MUST NOT** appear twice
in one run, which the key does not settle and a Tier 2 rule checks; both measured sessions have
0 such rows.

The shape is `core.array_channels` one level over: a labelled axis whose positions name
electrodes, which is what an axis no range can describe requires (R20 §2). `channel_index` takes
R48's `structural_index` role rather than `data`, because it is exactly the offset R3 §6 makes a
1-based client convert at the boundary.

### 2.2 A writer records the channel list rather than inferring it

A writer that can read a sorting's channel list SHOULD emit this table. A writer that cannot
SHOULD emit nothing, as R36 §2.4 requires of a resource it cannot reach, leaving the run's
coordinate system undeclared rather than guessed.

A writer **MUST NOT** derive the list from `core.unit_electrodes`, nor from a bad-channel list.
§1.2 and §1.3 measure both inferences wrong — by 50 channels of 384 and by 727 cells respectively
— and wrong in the way that costs most: usually right, never marked.

### 2.3 A consumer resolves a channel index through the new table

A consumer holding an index into a sorting's channels **MUST** resolve it through
`core.sorting_run_channels` and **MUST NOT** read it as a position in `core.electrodes`. Where the
run declares no channels, the index is unresolvable and the consumer **MUST** report that rather
than resolve it against the contact list.

An unresolvable index is a fact about what the packet carries rather than a defect in it, as R55
§2 has it for a discriminator and R80 §2.4 for an unresolved source. A packet whose runs declare
no channels is conforming, so a consumer reports the gap to its caller and does not fail the
packet.

### 2.4 A unit's electrode must be one the run used

Where a run declares its channels, every `core.unit_electrodes` row for a unit of that run
**MUST** name an electrode among them, at level `error`:

```sql
SELECT ue.unit_id, ue.electrode_id
FROM core_unit_electrodes ue
JOIN core_units u ON ue.unit_id = u.unit_id
JOIN (SELECT DISTINCT session_id, sorting_run_id FROM core_sorting_run_channels) d
  ON d.session_id = u.session_id AND d.sorting_run_id = u.sorting_run_id
LEFT JOIN core_sorting_run_channels c
  ON c.session_id = u.session_id AND c.sorting_run_id = u.sorting_run_id
 AND c.electrode_id = ue.electrode_id
WHERE c.electrode_id IS NULL
```

Run against `ecephys_776259` with the table built from its recorded channel list, it returns **0
of 171,280 rows**. It returns 0 on `ecephys_786867` too, whose runs kept every contact. The `d` join
keeps it silent for a run that declares nothing, which is every run of that session until its
channel list is recovered.

## 3. What this does not change

- **No column is added to `core.electrodes`.** Which channels a run used is a fact about the
  `(run, electrode)` pair, since a probe sorted twice may drop different sets, so a column on the
  contact cannot hold it.
- **`extremum_channel_index` is still not carried.** `core.unit_electrodes.is_primary` carries the
  peak since R81 §2.7, taken from the template's own negative peak, which reproduces the source's
  index in 6,781 of 6,781 and 4,559 of 4,559 units. This revision makes the coordinate system
  nameable and restores no column.
- **No packet becomes invalid.** §2.2 is SHOULD and §2.4 fires only where a run declares its
  channels, so both measured packets pass unchanged until rebuilt.
- **No change to `core.array_channels`.** An acquired series declares its channel axis from the
  electrode region the file writes down, which is a different pipeline stage and already resolves.

## 4. Consequence

One table, four columns, two references and two rules: core goes from 34 tables to 35. The rows
cost 4,510 on `ecephys_776259` and none on `ecephys_786867`, which records no list — 8 KB written,
one varying integer column beside three that hold one value per run.

The writer gains one read per stream, of an artifact the sorter adapter already opens.

Migration is a rebuild, which re-reads no external resource (R61 §5).

## 5. Open

- **Whether a dropped channel's reason should be carried.** `ecephys_786867` labels every contact
  `good`, `dead` or `out`, and `out` means outside the brain — anatomy rather than hardware, and a
  different fact from a dead channel. Carrying it needs the complement rather than the kept list,
  so it is a second table or a per-run column on the contact, and §1.3 measures those labels as
  describing a preprocessing step the sorting did not inherit. A reason for an exclusion that did
  not happen is not the fact this revision is about.
- **Whether a run with no declared channels should be reported.** §2.3 makes an index against such
  a run unresolvable, and nothing says so at validation: a packet whose runs declare no channels is
  silent rather than marked. R44 §2.3 faced this and added a third state, **undeterminable**, which
  would apply here unchanged.
- **Whether the table should be required where `core.units` exists.** MUST would refuse every
  packet built before this revision until rebuilt, and one of the two measured sessions could not
  satisfy it at all. Tightening later costs one revision and no migration, which is the order R82
  §5 chose for the same reason.
