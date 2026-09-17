# Is the NWB a faithful carrier?

Measured on `ecephys_786867_2025-09-25_12-43-56`, against the raw asset it was exported from.
The question is whether a packet may read the NWB for a resource, or must read past it: an export
that re-encodes a measurement is a fine source, and one that recomputes or discards is not.

## 1. Event times are the native HARP ticks, exactly

A HARP timestamp is `seconds * 31250 + ticks`. The NWB stores float seconds. Recovering the tick
is `round(seconds * 31250)`, and the error is zero:

| stream | samples | `max abs(tick - round(tick))` |
|---|---:|---:|
| `left_lick_time` | 2,203 | **0** |
| `right_reward_delivery_time` | 62 | **0** |
| `sniff_detector` | 200,000 | **0** |

So the float is a lossless encoding of an integer tick, and `core.events` built from the NWB
carries the measurement rather than a reconstruction of it. This is what makes reading the NWB
admissible under the tick invariant.

## 2. The sniff signal is byte-identical to the raw register

`acquisition/sniff_detector` declares itself *"imported from HARP SniffDetector__32.bin"*.
`SniffDetector__32.bin` is 82,343,688 bytes: 5,881,692 HARP messages of 14 bytes, register 32
(`RawVoltage`, U16, access `Event`). Parsed and compared against the NWB:

```
                       raw register            NWB
first tick             450,783,938,993         450,783,938,993
last tick              451,243,445,179         451,243,445,179
tick steps             78 x 5,033,638          78 x 5,033,638
                       79 x   773,567          79 x   773,567
values                 2,397 distinct 846..4095  2,397 distinct 846..4095
```

Identical. Reading the raw buys nothing here in fidelity; it buys independence from the exporter
continuing to be faithful, which is a different argument.

### 2.1 The axis is natively irregular

The device emits a periodic event at ~400 Hz on a 31250 Hz counter, so each interval lands on 78
or 79 ticks: mean 78.1248, against `625/8 = 78.125`. Deviation from a strict rational grid reaches
924 ticks (30 ms) over the session, with **no gaps**. That is dispatch jitter and not clock drift
-- these are harp ticks, and HARP devices are hardware-synchronised, so there is no second clock
to drift against.

R20 §2.1's compact form therefore does not apply, and R33's rational step would cost 30 ms of
error. The axis needs explicit tick coordinates. They are monotonic with a near-constant step, so
they delta-encode to a small fraction of their 47 MB.

### 2.2 The firmware says why, and R20 §2.1 already anticipated it

`AllenNeuralDynamics/harp.device.sniff-detector`, `firmware/src/main.cpp`:

```c
dispatch_interval_us = div_u32u32(1'000'000, app_regs.voltage_dispatch_frequency_hz);
if (int32_t(curr_time_us - next_msg_dispatch_time_us) >= dispatch_interval_us)
    next_msg_dispatch_time_us += dispatch_interval_us;   // accumulates, so no drift
```

Register 33 (`RawVoltageDispatchRate`) reads **400**, so the interval is 2500 µs exactly. The
device schedules on `time_us_32()`, the RP2040's own microsecond timer, accumulating rather than
re-basing -- so the samples are **evenly spaced on that counter**. The HARP timestamp stamped on
each message counts a different oscillator, 2.0 ppm away, which is why the intervals land on 78 or
79 ticks and reach 924 ticks of deviation over 14,704 s.

R20 §2.1 argued exactly this from LFP `times_seg0`: *"after HARP alignment the times are not
regular in seconds. On the array's own clock they remain perfectly regular -- one tick per sample
-- and R13's `core.clock_anchors` carries the mapping."* This is the same argument from a
different device, with firmware as evidence rather than inference. So the axis is R20 §2.1's
regular form on a dispatch clock, three integers, and the 2 ppm lives in the anchors -- of which
every one is a measured `(sample_index, harp_tick)` pair, since each message carries its own.

## 3. The trials table drops configuration, not measurement

The behaviour GUI writes `<session>.json` beside the raw: **264 per-trial arrays**, 27 `B_*`
(measurements) and 237 `TP_*` (task parameters). `TransferToNWB.py` reads 45 of them -- 16 of the
27 measurements and 29 of the 237 parameters -- and the NWB's trials table carries 67 columns.

Of the 219 it does not read, **only 10 vary within the session**, and of those:

| | |
|---|---|
| `TP_PositionX/Y/Z` | the lickspout position, which the NWB **does** carry |
| `TP_TotalWater` | a running cumulative total, derivable from the rewards |
| `B_Bias`, `B_Bias_CI` | the GUI's online bias estimate, a derived analysis |
| `B_*Complete` | the untruncated series behind fields already taken |
| `B_GoCueTimeBehaviorBoard` | **a second hardware timestamp of the go cue**, 17 ms before the one taken |

The remaining 209 are constant across all 450 trials: settings written per trial so a mid-session
change would be visible, and none changed.

### 3.1 The converter prefers hardware time

```python
if Harp == "":
    goCue_start_time_t = obj.B_GoCueTime[i]  # CPU time, old sessions only
elif hasattr(obj, "B_GoCueTimeHarp"):
    goCue_start_time_t = obj.B_GoCueTimeHarp[i]  # Harp time, old format
else:
    goCue_start_time_t = obj.B_GoCueTimeSoundCard[i]  # Harp time, new format
```

`B_GoCueTime` is the software's own clock and the export drops it deliberately, taking the
hardware timestamp. The 17 ms between `B_GoCueTimeBehaviorBoard` and `B_GoCueTimeSoundCard` is
latency down the chain -- software issues, board acts, speaker emits -- on one clock, not
disagreement between clocks.

## 4. Verdict

| resource | read the NWB? | why |
|---|---|---|
| `core.events` | **yes** | ticks recovered exactly; the export takes hardware time |
| the sniff signal | **yes** | byte-identical to the raw register |
| `core.trials` and `dynamic_foraging.*` | **yes** | what it drops is configuration and derived values |
| `core.spike_events`, `core.units` | **no** | the sorting is the primitive record; the NWB's units are a projection of it |
| `core.clock_anchors` | **no** | the TTLs are in the raw and nowhere else |

The one measured loss is `B_GoCueTimeBehaviorBoard`, and whether it is worth carrying is a
scientific judgement rather than a fidelity failure.
