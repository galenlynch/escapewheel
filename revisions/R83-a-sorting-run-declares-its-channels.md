# R83 — A Sorting Run Declares Its Channels

| | |
|---|---|
| **Status** | **Accepted** 2026-09-05 |
| **Amends** | `02` (adds `core.sorting_run_channels`), R28 §2 (what `core.unit_electrodes` may name), R3 §6 (a structural index's coordinate system) |
| **Depends on** | R28 (a unit sits on many electrodes), R38 (a sorting run names its clock), R46 (a reference is declared), R48 (a column declares its role), R53 (an identifier is an integer) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

Measured on the two AIND Neuropixels sessions this project has packaged: **`ecephys_776259`**,
twelve probes and 6,781 sorted units, and **`ecephys_786867`**, ten probes and 4,505. Both were
sorted by Kilosort 4 under SpikeInterface 0.104.7, and each is read from the sorted asset its NWB
was built from.

## 1. Motivation

### 1.1 `extremum_channel_index` indexes a channel list the NWB never writes down

The NWB records which electrode a unit peaks on in `extremum_channel_index`. Both adapters in this
project read it as a position in the probe's contact list; it is a position in the list of channels
the sorting kept, and the two lists differ by however many channels that sorting dropped. The
analyzer that produced the value holds that list; the file carrying it does not. Read the first way
it names the wrong electrode for **5,071 of 6,781 units** on `ecephys_776259` and **1,862 of
4,505** on `ecephys_786867`, one contact off for each channel dropped below it.

Both sessions bear that out probe by probe: the largest value a probe's units carry, plus one,
equals the channel count its analyzer states, on **11 of `ecephys_776259`'s 12 probes** and **5 of
`ecephys_786867`'s 10**. The rest fall one or a few short, no unit having peaked on the last
channels. Kept counts run from 366 to 384 and from 373 to 384.

Nothing caught the error until it produced a unit with no primary electrode at all. The index
lands outside its own unit's channel support for 609 of the 6,781, so those rows went missing
entirely while the other 4,462 kept a row naming the wrong contact.

The convention is invisible on a run that dropped nothing, which is why it went unnoticed. A run
that kept every contact makes an index into the kept channels and a contact number the same
number, and the misreading costs nothing until a channel goes. What distinguishes the two cases is
the channel count, which neither packet carried.

### 1.2 The packet cannot state which channels a sorting used

`core.electrodes` holds every contact and `core.unit_electrodes` names the contacts some unit had
signal on. Neither is the set a sorting ran on. Measured on `ecephys_776259`:

| | contacts | kept by the sorting | named by some unit |
|---|---:|---:|---:|
| twelve probes | 4,608 | 4,510 | 4,508 |

What a unit had signal on is a **lower bound**, and a loose one. Probe 46122 kept 383 channels of
which two carried no unit, so the packet's best answer is 381. The bound lands exactly right on
other probes by luck, and nothing marks which those are.

The bound errs in the direction that matters. Units per contact divides by 384 where the
denominator is 366 on two of these probes — 4.7%, concentrated rather than spread, because a dead
channel usually belongs to a run of them at the end of a shank.

Resolving an index also needs the kept channels **in order**, which membership does not give.
Index 348 on probe 46122 means contact CH365, and finding that out means counting through the 383
channels that sorting kept.

### 1.3 Both sessions record it, in a place the packet does not reach

Each session's analyzer states its channel list, as `channel_ids` under
`postprocessed/<stream>.zarr/recording_info`: 4,510 of 4,608 contacts on `ecephys_776259` and
3,813 of 3,840 on `ecephys_786867`. Every stream of both carries one.

That is not where a consumer of the packet can look. The list lives in the sorted asset, which a
packet references at most and more often does not mention, while the NWB the packet is built from
carries the index and not what it counts. A fact both producers record and no consumer can reach
is what core exists to carry.

The place it is recorded also moves. An earlier staging of `ecephys_786867` had no
`postprocessed/` at all, and its only channel statement was a preprocessing `bad_channel_ids` —
which for the current asset happens to match the analyzer's drops exactly, per probe, and for that
older one did not. A writer reading whichever file a given export happens to have is the reason
§2.2 forbids inferring the list rather than reading it.

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
§1.2 measures the first as a lower bound that is exact only by luck, and §1.3 the second as a file
that agrees with the analyzer in one export of a session and not in another — both wrong in the
way that costs most: usually right, never marked.

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

It returns **0 rows on both packets** — 171,280 `core.unit_electrodes` rows on `ecephys_776259`
and 114,945 on `ecephys_786867`, each against a run that now declares its channels. The `d` join
keeps it silent for a run that declares none, which is what a writer that could not read the list
leaves behind.

## 3. What this does not change

- **No column is added to `core.electrodes`.** Which channels a run used is a fact about the
  `(run, electrode)` pair, since a probe sorted twice may drop different sets, so a column on the
  contact cannot hold it.
- **`extremum_channel_index` is still not carried.** `core.unit_electrodes.is_primary` carries the
  peak since R81 §2.7, taken from the template's own negative peak, which reproduces the source's
  index in 6,781 of 6,781 and 4,505 of 4,505 units. This revision makes the coordinate system
  nameable and restores no column.
- **No packet becomes invalid.** §2.2 is SHOULD and §2.4 fires only where a run declares its
  channels, so both measured packets pass unchanged until rebuilt.
- **No change to `core.array_channels`.** An acquired series declares its channel axis from the
  electrode region the file writes down, which is a different pipeline stage and already resolves.

## 4. Consequence

One table, four columns, two references and two rules: core goes from 34 tables to 35. The rows
cost **4,510 on `ecephys_776259` and 3,813 on `ecephys_786867`** — 8 KB and 7 KB written, one
varying integer column beside three that hold one value per run.

The writer gains one read per stream, of an artifact the sorter adapter already opens.

Migration is a rebuild, which re-reads no external resource (R61 §3).

## 5. Open

- **Whether a dropped channel's reason should be carried.** `ecephys_786867`'s preprocessing
  labels every contact `good`, `dead` or `out`, and `out` means outside the brain — anatomy rather
  than hardware, and a different fact from a dead channel. Carrying it needs the complement rather
  than the kept list, so it is a second table or a per-run column on the contact, and §2.2 forbids
  reading that file for the kept set at all. Recording a reason from a source a writer may not
  trust for membership wants its own argument.
- **Whether a run with no declared channels should be reported.** §2.3 makes an index against such
  a run unresolvable, and nothing says so at validation: a packet whose runs declare no channels is
  silent rather than marked. R44 §2.3 faced this and added a third state, **undeterminable**, which
  would apply here unchanged.
- **Why §1.3 changed after acceptance.** The evidence first written here came from a staging of
  `ecephys_786867` that had no `postprocessed/`, so the session appeared to record no channel list
  and to have kept every contact. Read from the sorted asset its NWB was built from, it records
  one and drops 27 contacts. No clause of §2 depended on the difference, and the corrected reading
  is the stronger one: two sessions showing the convention rather than one.
- **Whether the table should be required where `core.units` exists.** MUST would refuse every
  packet built before this revision until rebuilt, and a writer that cannot reach the list has
  nothing to satisfy it with. Tightening later costs one revision and no migration, which is the
  order R82 §5 chose for the same reason.
