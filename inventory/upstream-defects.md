# Defects found upstream while building the importer

Found while writing the Phase 3 adapters against `ecephys_776259_2025-04-09` and
`ecephys_837772_2026-06-27`. Each is a bug in a producing pipeline rather than a gap in this
specification, and each is worked around in `escapewheel-writer` — the workarounds are noted so
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

**Workaround:** `escapewheel_writer.sources.aind.SessionSource.epoch` derives the epoch from a
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

## 10. The barcode line loses 1.6 ms of phase, twice, with nothing to restore it

Found by asking why R40's measured *maximum* extrapolation error is 1.6 ms when its p95 is
117 µs. Two earlier versions of this entry misattributed it — first to HARP time "stepping
backwards", then to the synchronizer board. Both were wrong; the evidence is below.

### What the signal does

The clock line carries a 32-bit count of whole seconds as four UART bytes at 1 kBaud, LSB
first — 39 bit-periods, 39 ms. Every frame in the session is 39.00 ms except two, which are
**59.00 ms**: six bytes instead of four.

```text
normal   burst 2234:  00 AB B0 00        -> 0x00B0AB00 = 11578112
glitched burst 2235:  01 AB B0 AB B0 00  -> bytes 1 and 2 re-sent
```

Every bit is an exact whole millisecond; nothing is stretched. The decoder reads bit-periods
31-38 for byte 3, which now hold the repeat of byte 1 (0xAB), so it decodes `0xABB0AB01` =
2880482049 — the corrupt value observed, to the bit.

### The harm is the phase, not the corrupt frame

The corrupt frame is caught: `remove_outliers` discards it. What is not caught is that the
transmitter overran by 20 ms, re-synchronised, and recovered only 18.4 ms of it:

```text
normal   burst: span 39 ms, idle 961.10 ms -> start-to-start 1000.100 ms
glitched burst: span 59 ms, idle 942.70 ms -> start-to-start 1001.700 ms
                            ^ shortened by 18.40 ms, leaving 1.60 ms lost
```

That residual is never recovered. Measured in NI-DAQ samples, the two events are +48 and +49
samples — **1617 +/- 17 µs, the same both times**, so the size is set by the frame structure
rather than by chance. Content is unaffected: repairing byte 3 gives a sequence advancing by
exactly 1 at all 6,385 steps. A sub-second phase error cannot be expressed in integer seconds,
so the message is blind to it.

Detectability: a step shows as a long barcode interval whether or not it corrupts a frame, and
the normal cadence spread is 5 samples, so **any step above ~170 µs is visible in the cadence
alone**. Exactly two occur.

### Which board, and what disciplines it

The aux clock line is emitted by the **Harp Behavior board**, not by the synchronizer and not by
the NI card (an earlier version of this entry said each of those in turn; both were wrong, from
over-reading `rig.json`'s sparse channel list). `harp-python`'s own docstring says so, and
`device.behavior` confirms it:

```c
void core_callback_t_new_second(void) { timestamp_tx_streaming(); }

void timestamp_tx_streaming(void) {
    timestamp_tx = core_func_read_R_TIMESTAMP_SECOND();
    timestamp_tx_index = 0;
    USARTF1.CTRLA |= USART_DREINTLVL_LO_gc;
    USARTF1_DATA = *((uint8_t*)(&timestamp_tx) + timestamp_tx_index);
}

ISR(USARTF1_DRE_vect, ISR_NAKED) {
    timestamp_tx_index++;
    USARTF1_DATA = *((uint8_t*)(&timestamp_tx) + timestamp_tx_index);
    if (timestamp_tx_index == 3)
        USARTF1.CTRLA &= ~(USART_DREINTLVL_OFF_gc | USART_DREINTLVL_gm);
    reti();
}
```

**There is a restoring force, and it is strong.** The frame is triggered by the board's
new-second event, which comes from timer TCC1 — the timer the native-bus slave logic hard-reloads
every second (`core.atxmega/Firmware/Library/hwbp_sync.c`):

```c
if (previous_timestamp + 1 == sync_timestamp) {
    if (device_lost_sync_counter >= 5) { converging = 12; TCC1_CNT = 31231 - converging; TCC1_CCA = 31233; }
    else { if (converging) converging -= 2;
           if (TCC1_CNT < TCC1_CCA) TCC1_CNT = 31231 - converging; }
    *core_timestamp_pointer = sync_timestamp;
}
```

So trigger phase is reset once per second and **cannot accumulate by design**. A merely delayed
transmission would self-correct on the next second.

**Which is why the measured step matters more, not less.** It never unwound, so the event
defeated the discipline rather than delaying a frame.

### A mechanism consistent with the evidence, not yet proven

The six bytes are `byte0, byte1, byte2, byte1, byte2, byte3`, so the write index ran
`0, 1, 2, 0, 1, 2, 3` — it was reset to zero mid-frame. The only code that zeroes it is
`timestamp_tx_streaming()` itself, and if that ran while `USARTF1_DATA` was still full its byte-0
write would be dropped, which is exactly why no extra byte 0 appears.

That points at **the new-second event firing early, mid-frame**: one mistimed TCC1 reload would
produce the byte repeat *and* leave the new-second phase permanently displaced. The reload is
conditional on two tests, and the firmware has a deliberate re-convergence ramp of
`converging = 12` steps of 32 µs = 384 µs when sync is lost for five seconds, so phase movement
is a designed behaviour on that path.

Confirming this needs the board on a bench, not the recording. Note also that `ISR_NAKED` with a
C body and no manual context save is used throughout Harp's ATxmega firmware, not just here; it
omits register and SREG save/restore, which permits exactly this class of cross-ISR corruption,
but the pattern is systemic and singling out this handler would be unfair without a test.

### The damage

Behaviour, trials, licks and rewards are Harp-native and land **exactly** on the 31,250 Hz grid
(0.000 ns departure, measured). Spikes reach Harp through the barcode. So the error is entirely
a *relative* offset between the two:

| session time | ephys offset | measured spike-event latency |
|---|---|---|
| 0 - 2235 s | 0 | correct |
| 2235 - 2237 s | ramps to -1.600 ms | — |
| 2237 - 3515 s | -1.600 ms | 1.6 ms too short |
| 3515 - 3517 s | ramps to -3.233 ms | — |
| 3517 - 6387 s | -3.233 ms | 3.2 ms too short |

The transition is a two-second ramp rather than a jump: the segment spanning a discarded barcode
maps 2 Harp seconds onto 2.0018 s of local time, so the rate is compressed by ~4e-4 for two
seconds. The map stays **strictly monotonic** throughout — smallest step 999.1684 ms over 6,388
pulses — so nothing is reordered or duplicated. `SyncSource.pulses` enforces that independently
and would refuse the source otherwise (R13 §3).

Cross-probe timing is **unaffected**: the steps land at the same Harp instants on all twelve
probe clocks, agreeing to one tick, so probe-to-probe comparisons cancel it exactly.

What it costs where it bites: 3.2 ms is 97 probe samples, about one spike width. A 30 ms PSTH
bin sees 0.1 of a bin; a 1 ms bin sees 2-3; LFP-behaviour phase sees 46 deg at 40 Hz and 116 deg
at 100 Hz.

### It is not universal

| session | barcode source | glitches |
|---|---|---|
| 776259, 2025-04-09 | NI PCIe-6363 (PC-driven) | **2** in 6,386 s |
| 837772, 2026-06-27 | `harp_white_rabbit`, whoami 1404, `DI line 5` | **0** in 5,362 s |

Same rig (`323_EPHYS2`), 14 months apart, the barcode moved from a PC-driven NI card to the
WhiteRabbit board driving the line directly. One clean session is not proof — at the 776259 rate
you would expect ~1.7 events in 5,362 s, so P(0) ~ 0.18 — but it is evidence, and it points at
the signal path rather than at any Harp board.

### The decoder's outlier test is fragile in a way that would be catastrophic

`remove_outliers` splits where consecutive values do not differ by 1 and discards runs of length
1. A single corrupt barcode is caught, which is what happened here. But the corruption is
*structured* — it keeps the low 24 bits and rewrites byte 3 with a fixed pattern — so two
consecutive glitches would decode one apart, forming a run of length 2 that the test **keeps**,
while the correct neighbours become runs of length 1 and are **discarded**:

```text
remove_outliers([good, corrupt, corrupt+1, good])  keeps  [2880482049, 2880482050]
```

That injects anchors 93.6 years out and gives the per-segment fit a negative slope. The two
glitches here were 1280 s apart; nothing prevents adjacency. The test should require a barcode's
value to agree with its *arrival time*, not merely that consecutive values differ by 1.

### What this packet does about it

Nothing, deliberately. The anchors carry the phase step faithfully — interpolation between them
reproduces the upstream timestamps to 0.1 µs (§9) — and it is permanent, so withholding the
anchors at the step would smear it rather than remove it. R37 §3.2's test is for an anchor
misplaced against its neighbours; this is a level change they all agree with.

It is also why R40 §2.2 gates on p95 rather than the maximum: the maximum reports these two
upstream events, not the quality of the estimator being bounded.

### Upstream, and one rig recommendation

1. **The Behavior board.** Its new-second phase moved permanently, twice, despite a per-second
   discipline that should prevent exactly that. The write index was reset mid-frame, which only
   `timestamp_tx_streaming()` does, so the new-second event appears to have fired early. Worth a
   bench test with the clock output on a scope against the native bus.
2. **`harp-python`.** `remove_outliers` must not be able to prefer two corrupt anchors over two
   good ones, and a frame whose span is not 39 bit-periods is malformed regardless of what it
   decodes to. Neither check exists as of `jsiegle/harp-python@decode-clock` `c73984a`.
### What the behaviour asset settles, and what it does not

The behaviour data is in the *same* asset (`behavior/.../raw.harp/`), so the Harp register
streams were checkable after all. Two results:

**No Harp device lost its second count.** `LickometerEventsLeft/Event_8.bin` and its right-hand
twin are per-second `TimestampSecond` heartbeats — 7,859 messages each, Harp seconds
11,576,034 → 11,583,892, so both glitch instants (11,578,113 and 11,579,393) are covered. Every
one of the 7,858 steps is exactly +1: no second skipped, none repeated, on either device. A
resync would very likely have disturbed that, so this is evidence against one — though not
proof, since a resync recovers the count and the phase change it makes is sub-second anyway.
The sub-second field is constant at 26,960 ticks on every message, which is self-referential and
therefore blind to a phase step by construction.

**And there is no cross-domain fiducial, demonstrated rather than assumed.**
`LickometerEventsLeft/Event_32.bin` holds 5,282 messages alternating 0/1 — exactly 2,641 rises,
matching the NWB's `left_lick_time` count. Comparing the two series directly gives **0.0 µs
difference at every one of the 2,641 events**, in all three intervals either side of the
glitches. The NWB copies the Harp device timestamps verbatim.

So every Harp-derived series in the packet traces to one clock domain and cannot witness that
domain's own phase. Confirming which side moved needs a signal that is Harp-timestamped *and*
visible in the ephys, and this rig records none.

3. **The rig.** Nothing recorded here can verify the barcode's phase against Harp's own time:
   every event stream in the packet is Harp-native and behavioural, and none is visible in the
   ephys signal, so there is no cross-domain fiducial. Routing one Harp-native digital output to
   a spare DAQ line — the NI-DAQ uses 2 of 16 — would make the ephys-to-behaviour offset a
   continuously monitored quantity rather than an unverifiable assumption.

Not filed.
