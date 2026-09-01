# Defects found upstream while building the importer

Found while writing the Phase 3 adapters against `ecephys_776259_2025-04-09` and
`ecephys_837772_2026-06-27`. Each is a bug in a producing pipeline rather than a gap in this
specification, and each is worked around in `nwb-lake-writer` — the workarounds are noted so
they can be removed once a fix lands.

Measured 2026-08-28 to 2026-09-01. Nothing here has been filed.

---

## 0. Where the ephys facts actually live

Not a defect, but the reason several below were reachable at all. Open Ephys writes its own
metadata beside the data, and it is the authority for the recording — the aind-data-schema
JSONs are derived from it and lossy:

| file | where | what it alone carries |
|---|---|---|
| `sync_messages.txt` | `Record Node N/experimentM/recordingK/` | **A real UTC instant, to the millisecond**, and every stream's counter value at that moment |
| `settings.xml` | `Record Node N/` | Signal chain, stream names and rates, probe serials; `<INFO><DATE>` stamps the same instant to the second in the machine's local zone |
| `structure.oebin` | beside `sync_messages.txt` | Channel counts, bit-volt scaling, stream layout |

`session.json` truncates the acquisition window to whole seconds, which is what makes its
ephys stream 0.88 s short of the spikes, and its stored UTC offset is wrong three ways (§5).
`sync_messages.txt` has neither problem. On `ecephys_776259_2025-04-09` its Software Time is
`1744244712090` ms — `2025-04-10T00:25:12.090Z` — against `session.json`'s
`2025-04-09T17:25:12+00:00`, which is the same instant to the second, mislabelled `+00:00`
when it is Pacific.

**Two nodes give two independent estimates.** Node 109 stamps `…712090`, node 111 `…712153`.
Mapping each node's earliest stream tick 0 onto HARP and subtracting, the two agree on HARP's
tick zero to **31 ms**. Within a node the streams reach their first sample over 36–80 ms, since
the node writes each stream's first available sample rather than a simultaneous set. So the
epoch is good to ~±50 ms, against ~±1 s for the derivation it replaces — and it is not circular,
pairing a wall clock with an instrument event rather than with the first spike.

**Caution: none of this is in a partial mirror.** A local copy synced for events and metadata
may hold only `events/` and the JSONs; these files live beside `continuous/` and come with it.
On S3 they are small and independently fetchable —
`s3://aind-open-data/<asset>/ecephys/ecephys_clipped/Record Node N/`.

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

## 4. Unaligned stubs are indistinguishable from aligned streams

**Repo:** `aind-ephys-rig-qc` / Open Ephys
**Severity:** medium — the wrong number is plausible, so it gets used

**Corrected 2026-08-28.** An earlier draft of this entry claimed rig-qc aligned `continuous/`
but not the probes' `events/*/TTL/`. That is wrong: rig-qc aligns everything a record node
owns, events included. What misled it was a stub.

A record node's directory lists every stream it *saw*, not every stream it owns. On this
session two nodes each owned six streams and carried seven local-only copies of the other's:

```text
node 109  50198, 50213, 50720-1..4          HARP-aligned, and exactly the sorter's output
node 109  46101-1..4, 46810, 50197, 50210   acquisition-local stubs
node 111  46101-1..4, 46810, 50197          HARP-aligned, and exactly the sorter's output
node 111  50198, 50213, 50720-1..4, 50210   acquisition-local stubs
```

Both nodes' NI-DAQ is aligned. `50210` is local in both, being a probe nothing sorted.

The defect is that a stub carries `timestamps.npy` in acquisition-local seconds with nothing
declaring it unaligned. The only signal is the *absence* of `original_timestamps.npy` beside
it, which is an archive rig-qc writes as a side effect rather than a marker it intends. Code
reading a stub gets seconds that look ordinary and are 17.7 million seconds from where the
same stream's aligned copy sits.

**Fix:** mark the alignment state explicitly — a `sync_status` beside the timestamps, or omit
the stub entirely rather than write an unaligned copy of another node's stream.

**Workaround:** `SyncSource` treats the archive as the ownership signal, skips every stream
without it, and reports each one.

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

---

## 6. LFP timestamps carry a negated epoch, putting LFP 268 days from the spikes

**Found:** 2026-08-29, `ecephys_776259_2025-04-09_17-25-12_nwb_2026-08-17_09-30-31`
**Repos:** the NWB export
**Severity:** high — the two are unalignable as stored, and the error is silent

Every `processing/ecephys/LFP/ElectricalSeries*` in this file starts at a large **negative**
time, while the spikes in the same file start at the same magnitude, positive:

```text
units/spike_times                 +11575876.219 .. +11582264.099 s
ElectricalSeries45883-1-LFP       -11575876.314 .. -11569489.315 s
ElectricalSeries45883-2/3/4-LFP   identical to -1
```

Both increase, and both span 6,387 s, so the sampling is intact; it is the epoch that is
signed wrongly. Negating the LFP start gives 11,575,876.314, which agrees with the spike start
to 0.095 s. Taken at face value the two streams are 23,151,752 s -- 268 days -- apart.

The magnitude is the HARP epoch offset (see §2), so this is the same quantity the spikes use,
with its sign flipped somewhere in the LFP writer alone.

**Why it is dangerous:** nothing about the value looks wrong in isolation. It is finite,
monotonic, and correctly spaced; only comparing it against another stream in the same file
reveals it. An analysis that plots LFP against spike times gets an empty intersection rather
than an error.

**Workaround:** do not carry the stored timestamps. The sampling is regular to 1.9 ns over
200,000 samples, so R20 §2's regular form describes the axis exactly -- an origin and a step
on a declared clock -- and the origin comes from the recording's own start rather than from
this array. That is the general argument for R20 restated: a derived per-sample time array is
both 8 M values and an opportunity to be wrong, where three numbers on a clock are neither.

---

## 7. `waveform_mean` declares volts and holds microvolts

**Found:** 2026-08-29, `ecephys_776259_2025-04-09_17-25-12_nwb_2026-08-17_09-30-31`
**Repos:** the NWB export
**Severity:** medium — a factor of 10^6, silent, and the array carries no conversion to catch it

```text
units/waveform_mean  .zattrs   unit: "volts"      no conversion attribute
                      values   -1654.453 .. +1604.289
core.sorting_runs             amplitude_unit: uV  (from the analyzer's return_in_uV)
```

Read as declared these are kilovolt-scale waveforms. They are microvolts: the analyzer that
produced them was set to return microvolts, and ±1.6 mV is an ordinary extracellular spike.
Unlike an `ElectricalSeries`, which carries a `conversion` alongside `unit` and would make the
scale recoverable, this `VectorData` has only the label -- so there is nothing in the array to
reconcile against, and a consumer that trusts the attribute has no way to notice.

**Also:** the same array is `float64` while every value in it round-trips through `float32`
with **zero** error, and 93.3% of it is exactly zero -- a unit has signal on the contacts it
sits near and the rest of the 384 are padding. The stored type asserts a precision the source
never had, since the samples averaged are int16 ADC counts.

**Workaround:** take the unit from `core.sorting_runs.amplitude_unit`, which the analyzer
actually declares, and record the scale on `core.array_assets.conversion` where a reader can
find it.

---

## 8. `extremum_channel_index` names a channel the waveform is zero on

**Found:** 2026-08-29, `ecephys_776259_2025-04-09_17-25-12_nwb_2026-08-17_09-30-31`
**Repos:** the sorting pipeline's waveform export
**Severity:** medium — two fields describing one unit contradict each other, and neither is marked

`units/extremum_channel_index` names a unit's peak contact. `units/waveform_mean` is dense over
384 channels, padded with zeros outside the contacts the unit was computed on. For 609 of 6,781
units the declared peak is one of the padded channels:

```text
units disagreeing                                   609 / 6,781   (9.0%)
waveform_mean at the declared extremum, agreeing    21.9 uV       (median)
waveform_mean at the declared extremum, disagreeing 0.0 uV        (609 of 609, exactly)
```

The file states that a unit's largest waveform is on a channel where it also stores that the
waveform is identically zero.

**It is a near miss, not a wild index.** The declared extremum sits a median of **one contact**
from the unit's real support, and within four for 562 of the 609. The sparsity mask and the
extremum were computed against slightly different neighbourhoods -- a mask recomputed or
narrowed after the peak was chosen would produce exactly this.

**It is concentrated on one probe.**

| Probe | Disagreeing | Rate |
|---|---|---|
| 46116-2 | 219 / 570 | 38.4% |
| 46116-1 | 114 / 409 | 27.9% |
| 46116-3 | 166 / 767 | 21.6% |
| 46116-4 | 44 / 567 | 7.8% |
| 45883-1 .. 45883-4 | 64 / 2,806 | 0.5-3.8% |
| 46122 | 2 / 503 | 0.4% |
| 46110, 46113, 50209 | 0 / 1,159 | 0.0% |

All four shanks of 46116 account for 543 of the 609, and three probes are clean. A systematic
indexing error would hit every probe alike, so this is a per-probe difference in how the two
fields were produced.

**Workaround:** none, deliberately. `core.unit_electrodes.is_primary` is left unset for those
units, so 609 of 6,781 have no primary row and R28 §2.1's *"where is this unit"* cannot be
answered for them from that table alone. The array's own peak within the support would be a
plausible substitute -- at a median distance of one contact it is probably even right -- but it
manufactures a fact the source contradicts itself about and hides the defect behind a
believable number. The gap is left visible.

**Not currently load-bearing, by luck.** `core.units.default_electrode_id` is null for every
unit in the packet, so the corpus's `undetected_default` check has nothing to catch. Had the
adapter filled it from `extremum_channel_index`, all 609 would be validation errors.

---

## 9. `harp-python` maps out-of-range timestamps with the global fit, displacing every stream's first sync pulse

`harp.clock.align_timestamps_to_anchor_points` builds one linear model per barcode segment and,
at index 0, a least-squares fit over every barcode. It then selects a model per timestamp:

```python
nearest = np.searchsorted(start_times, timestamps_to_align, side="left")
nearest[nearest == N] = 0
aligned = timestamps_to_align * slopes[nearest] + offsets[nearest]
```

`searchsorted` yields 0 before the first anchor and `N` after the last, and the second line
folds `N` onto 0. Both out-of-range regions are therefore mapped by the global fit while every
interior point uses its own segment.

It predicts the measurement exactly. On `ecephys_776259_2025-04-09` the barcode anchors span
11,575,877.001 → 11,582,264.039 s; the sync pulses span 11,575,876.947 → 11,582,263.930. The
first pulse falls 54 ms **before** the first barcode and comes out displaced; the last falls
109 ms **inside** the last barcode and is clean.

Measured against each clock's own interior spread — predict an anchor from a one-sided fit over
its thirty neighbours, and compare the residual against the same statistic taken at 600 interior
positions:

| | median | p99 | first anchor | last anchor |
|---|---:|---:|---:|---:|
| interior residual | 2.5–30 µs | 126–140 µs | | |
| ten of twelve probe clocks | | | 156–288 µs | 4–33 µs |
| 46110 and 46122 | | | 4–10 µs | 4–10 µs |

Only the first anchor of a stream is affected, and only where the first pulse preceded the first
barcode. Nothing below this layer is implicated: Open Ephys's `sample_numbers` are exact and its
`original_timestamps` carry no terminal anomaly, only ±1.2 ms of software jitter throughout,
which the alignment otherwise removes to a single sample.

**Workaround:** `SyncSource` applies R37 §3.2's test and withholds a terminal anchor whose
residual exceeds its own clock's interior 99th percentile — ten of twelve first anchors on this
session, no last anchors. What it withheld goes in `core.processing_runs.parameters`. Because
that moves the first usable anchor from 0.66 s to 1.66 s, the build then measures the
extrapolation error at the distance it needs (R37 §3.3) and maps at two median anchor intervals,
which costs 0.96 parent ticks at the median — inside R37's one-tick tolerance.

**Confirmed against an independent implementation, 2026-09-01.** `aind-ephys-export-nwb`
solves the same problem a different way: it loads `continuous/<stream>/timestamps.npy` — a dense
float64 per sample, which `aind-ephys-rig-qc` has rewritten to HARP — calls
`recording.set_times(sync_times)` and `sorting.register_recording(recording)`, so a spike time is
a lookup into that array at the spike's frame. No interpolation, no anchors, and no way to say
"undefined".

Comparing that array's element 0 — the HARP time of the recording's sample 0 — against the same
quantity reconstructed from our anchors:

| stream | first anchor | theirs − ours | its own residual, §3.2 |
|---|---|---:|---:|
| 46110 | kept | **+0.1 µs** | +10.3 µs |
| 46122 | kept | **+0.8 µs** | +4.2 µs |
| 45883-1 | withheld | +135.0 µs | +156.5 µs |
| 46113 | withheld | −157.2 µs | −163.4 µs |
| 46116-1 | withheld | −260.8 µs | −258.2 µs |
| 50209 | withheld | +305.9 µs | +287.5 µs |

The separation is total. On the two streams whose first anchor the test *kept*, six thousand
anchors and a piecewise map reproduce a 191.6 M-element array to **under a microsecond** — so the
sparse representation loses nothing. On the four it *withheld*, the difference is that stream's
own displacement, in sign and magnitude. Sample 0 lies before the first barcode, so the dense
array computes it with the global fit; the defect is baked into every sample of the out-of-range
region and cannot be removed downstream, because by then it is data rather than a model.

Over whole spike trains the two agree to **9 µs median, 24 µs p95** across 263,094 spikes — a
quarter of a probe sample, and consistent with our rounding to integer HARP ticks being the whole
of the residual.

**Upstream:** drafted against `jsiegle/harp-python@decode-clock` commit `c73984a`; not filed.
The fix is to give the out-of-range regions their own terminal-anchored models rather than
folding them onto index 0, which is the same correction R37 §3.1 makes to this specification.
Because `aind-ephys-rig-qc` materializes the result per sample, every consumer of a session's
`timestamps.npy` inherits it, and re-running the alignment is the only way to clear it.


---

## 10. HARP time steps back ~1.5 ms twice a session

Found while asking why R40's measured *maximum* extrapolation error is 1.6 ms when its p95 is
117 µs. It is not a bad sync pulse, and R37 §3.2's terminal-anchor test cannot reach it.

Taking each sync-pulse interval's departure from the probe's own sample counter, two intervals
per session are short — and the deficit is permanent, not a spike that recovers:

```text
   i       t_tick           parent        Δt    Δparent   implied ratio
3514    105471714     361855998090     30000      31250      1.0416667
3515    105501714     361856029316     30000      31226      1.0408667   ← −768 µs
3516    105531714     361856060540     30000      31224      1.0408000   ← −832 µs
3517    105561714     361856091790     30000      31250      1.0416667   ← resumes, 1.6 ms behind
```

**It is HARP, not the probes.** The two steps fall at the *same HARP instants* —
11,578,111.942 s and 11,579,391.939 s — on all twelve probe streams, which are twelve
independent sample counters in two record nodes:

| | step 1 | step 2 | net |
|---|---:|---:|---:|
| every stream | −1471 to −1504 µs | −1567 to −1600 µs | −3.1 ms |

The spread across streams is one HARP tick, which is quantization. Each probe's own Δt is a
regular 30,000 throughout.

**It is not a missing barcode.** The barcode line carries 6,388 barcodes, one per second, nine
pulses each, with no irregular interval anywhere in the session.

**The alignment is otherwise doing its job.** Per sync-pulse interval, against the probe clock:

| | p50 | p95 | max |
|---|---:|---:|---:|
| before alignment (Open Ephys software time) | 7.2 µs | 525.7 µs | 1813.6 µs |
| after alignment (rig-qc, HARP) | 16.2 µs | 58.9 µs | 831.6 µs |

p95 improves ninefold and the residual median of 16.2 µs is half a HARP tick — the quantization
floor, so the alignment is at its own resolution everywhere except these two points.

**Cause not established.** Either HARP's counter genuinely stepped, or one barcode in each pair
decoded to a value ~1.5 ms low. The pre-alignment timestamps carry ±1.8 ms of software jitter,
which is larger than the step, so the step cannot be isolated in them. Distinguishing the two
needs the decoded barcode values, which the packet does not carry.

**Workaround:** none, and deliberately. The anchors represent the shift faithfully —
interpolation between them reproduces the upstream timestamps to 0.1 µs (§9) — and the shift is
*permanent*, so withholding the anchors at the step would not remove it, only smear it across a
wider interpolation. R37 §3.2's test is for anchors that are individually misplaced against
their neighbours; this is a level change that every subsequent anchor agrees with.

**What it means for a consumer.** Times either side of a step are internally consistent and
offset from each other by 1.5 ms. Nothing within a trial is affected. A measurement comparing
the first third of a session against the last carries up to 3.1 ms of offset, which matters for
a 1 ms cross-correlogram bin and for nothing coarser.

It is also why R40 §2.2 gates on p95 rather than on the maximum: the maximum here reports two
upstream events, not the quality of the estimator being bounded.
