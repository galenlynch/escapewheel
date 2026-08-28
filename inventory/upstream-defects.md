# Defects found upstream while building the importer

Found while writing the Phase 3 adapters against `ecephys_776259_2025-04-09` and
`ecephys_837772_2026-06-27`. Each is a bug in a producing pipeline rather than a gap in this
specification, and each is worked around in `nwb-lake-writer` — the workarounds are noted so
they can be removed once a fix lands.

Measured 2026-08-28. Nothing here has been filed.

---

## 1. `timestamps_reference_time` is wrong by 134 days

**Repo:** `nwb-zarr-smasher` / `ecephys-behavior-nwb-smasher-capsule`
**Severity:** high — silently wrong, and the field exists precisely to prevent this

NWB defines `timestamps_reference_time` as the wall-clock instant of t = 0 for every
timestamp in the file. The smasher writes HARP-epoch timestamps and leaves the field at
NWB's default, which is `session_start_time`.

```text
session_start_time         2025-04-09T17:25:12-07:00
timestamps_reference_time  2025-04-09T17:25:12-07:00   <- identical
units/spike_times          11,575,876.219 .. 11,582,264.099 s   (HARP epoch, 134 days)
```

Taken at face value the first spike is at `17:25:12 + 11,575,876 s` = **2025-08-21**, four and
a half months after the session. Any consumer that trusts the field — which is the documented
way to convert NWB timestamps to wall clock — gets an answer wrong by 134 days.

**Fix:** write the HARP epoch into `timestamps_reference_time`. It is derivable: the ephys
stream's declared start in `session.json`, paired with the first sample's HARP time, locates
it to about a second.

**Repro:** any smashed session. Compare `timestamps_reference_time` against
`min(units/spike_times)`; if the latter is ~10⁷ the field is unset.

**Workaround:** `nwb_lake_writer.sources.aind.SessionSource.epoch` derives the epoch from a
cross-source span match and ignores the field.

---

## 2. Unit electrode regions are densified, costing ~15x on waveform arrays

**Repo:** the ecephys NWB export step (SpikeInterface `add_units_table_to_nwbfile`)
**Severity:** high — pure storage cost, no information gained

The SortingAnalyzer carries a genuine sparsity mask. The NWB export discards it and declares
every unit on every channel.

```text
sparsity_mask                (836, 382) bool   6.6% occupancy
                             channels per unit: min 14, median 26, max 26

units/electrodes             2,603,904 entries for 6781 units — all 384 channels each
units/waveform_mean          [6781, 150, 384] float64 = 3.12 GB
units/waveform_sd            [6781, 150, 384] float64 = 3.12 GB
```

At the measured sparsity those two arrays are **0.41 GB instead of 6.25 GB**, a 15.3x
reduction, and `units/electrodes` is 170,538 entries instead of 2.6 million. The `electrodes`
column as written carries no information at all: every unit's region is identical.

**Fix:** pass the analyzer's sparsity to the writer. SpikeInterface's
`add_units_table_to_nwbfile` takes `unit_electrode_indices`; when it is omitted the exporter
falls back to all channels.

**Repro:** compare `numpy.diff(units/electrodes_index)` against the analyzer's
`sparsity_mask.sum(axis=1)`. Densified files give a constant equal to the channel count.

---

## 3. Waveform arrays are `float64` where the source is `float32`

**Repo:** same as 2
**Severity:** medium — 2x on top of 1, and stacks with it

`waveform_mean` and `waveform_sd` are written `<f8`. SpikeInterface computes them in
`float32`, so the second four bytes of every value are conversion noise. Combined with 2 the
two arrays are roughly **30x larger than a sparse float32 write**: 6.25 GB against ~0.21 GB.

**Fix:** write `float32`. Worth handling in the same change as 2, since both are the same
call.

---

## 4. rig-qc aligns `continuous/` but not the probes' `events/*/TTL/`

**Repo:** `aind-ephys-rig-qc`
**Severity:** medium — the wrong number is plausible, so it is used

HARP alignment reaches every probe's continuous data and the NI-DAQ's events, but not the
probes' TTL events. Measured on `ecephys_837772_2026-06-27`:

```text
                                        timestamps.npy            archives present
NI-DAQ  continuous                   17,702,134 .. 17,707,498      yes
NI-DAQ  events/…/TTL                 17,702,134 .. 17,707,498      yes
probe   continuous                   17,702,134 .. 17,707,498      yes
probe   events/…/TTL                      1,475 ..      6,839      NO
```

The probe TTL timestamps are still acquisition-local. Nothing marks them as unaligned — there
is no `original_timestamps.npy` beside them, which is the signal that alignment ran — so code
reading a probe's sync-pulse times gets local seconds while the same probe's continuous data
is HARP, and the two silently disagree by 17.7 million seconds.

**Fix:** apply the same alignment and archive step to every stream's `events/*/TTL`, not just
the stream the HARP line was decoded on.

**Workaround:** the anchor extraction reads probe `sample_numbers.npy` and takes HARP time
from the NI-DAQ's TTL, never from a probe's `timestamps.npy`.

---

## 5. Offsets that are wrong in three different ways

**Repos:** aind-data-schema metadata generation; the NWB export
**Severity:** low individually, high in aggregate — no offset in these files can be trusted

Three wall-clock values in one session, three different errors:

| Value | Written | Should be | Error |
|---|---|---|---|
| `session.json` `session_start_time` | `2025-04-09T17:25:12+00:00` | `-07:00` | 7 h |
| NWB `general/subject/date_of_birth` | `2024-09-24T00:00:00-07:53` | `-07:00` | Pacific Local Mean Time |
| `session.json` `data_streams[1]` | `-07:00` | `-07:00` | correct |

`-07:53` is the giveaway for a timezone conversion done without a database: it is the true
solar offset of the Pacific coast, which no computer clock has used since 1883.

**Fix:** localize with an IANA zone. A fixed offset is wrong half the year regardless, since
these rigs run across the DST boundary — this session is PDT while the HARP epoch its own
ticks count from is PST.

**Workaround:** `SessionSource` discards stored offsets and re-localizes to a declared IANA
zone, reporting each disagreement; `NWBSource` keeps the stored value and reports it, because
a date has nothing to re-localize.
