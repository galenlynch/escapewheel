# Design

This page explains why each adapter in this package reads its source the way it does. Its
measurements come from two sessions: `ecephys_776259_2025-04-09`, with twelve probes and 6,781
sorted units, and `ecephys_786867_2025-09-25`, with ten probes. The documents in `../inventory/`
record each measurement and the session it was taken on.

## The NWB dialect is a subclass

An AIND pipeline writes an NWB that follows the NWB schema at every path a base reader visits:
`general/subject`, `general/devices`, `general/extracellular_ephys/electrodes`, `intervals/trials`
and `acquisition`. `escapewheel_writer.adapter.NWBSource` reads all of them. The pipeline adds
seventeen columns that NWB does not define (`../inventory/nwb-adapter-base-and-dialect.md`):

| NWB table | columns the pipeline adds |
|---|---|
| electrodes | `electrode_name`, `ccf_ml`, `ccf_ap`, `ccf_dv`, `brain_region_id`, `ccf_id`, `ccf_acronym`, `ccf_name`, `ccf_structure_id_path` |
| units | `ks_unit_id`, `device_name` |
| trials | `goCue_start_time`, `reward_outcome_time`, `delay_start_time`, `animal_response`, `rewarded_historyL`, `rewarded_historyR` |

The pipeline also follows three conventions that are not columns:

- a device's `description` packs its model and serial number into one sentence, which
  `DEVICE_DESCRIPTION` matches;
- an acquired signal's description names its instrument in prose, as in "imported from HARP
  SniffDetector__32.bin", which `SIGNAL_DEVICE` matches;
- an event stream's name ends in `_time`, and its event type is the name without the suffix. The
  base adapter strips the suffix itself, because a name without one passes through unchanged.

The added columns sit in the same rows as the standard ones, and one source supplies each row
(Part 05 §3.4). A second adapter could therefore not add the pipeline's columns to rows the base
adapter supplies. `AindNWBSource` subclasses `NWBSource` instead: the base class reads the file,
and the subclass's hooks interpret the added columns. A recipe names one kind or the other.

Four of the subclass's choices rest on measurements.

- `DEVICE_DESCRIPTION` bounds the serial number explicitly. A lazy `.+?` running to `$` swallowed
  the description after it, and put "20403319544 - Description: duplicate of PRB2_1_2_0640_0" into
  the serial-number column for every probe.
- `device_identity` parses the description because the pipeline sets none of the three `Device`
  attributes that NWB core 2.9.0 declares for a model and a serial number. On the ten-probe session,
  0 of 10 devices set one.
- `local_electrode_label` treats `electrode_name` as a label and not an identifier. The column
  held 1,920 distinct values over 4,608 rows, because the shanks of a quad-base probe reuse the
  numbering.
- `unit_identity` joins on `(device_name, ks_unit_id)` because a sorter's label alone does not
  identify a unit. The twelve-probe session has 810 distinct labels across 6,781 units, sorted one
  probe per run.

Core has no column for `animal_response` or the two reward histories. `TRIAL_MAPPED` names them
anyway, which keeps them out of `core.intervals.metadata`, because they belong to the task's own
extension. `core.electrode_coordinates` has columns for `ccf_id` and `ccf_acronym` only, so
`CARRIED_ELECTRODE` sends `ccf_name` and `ccf_structure_id_path` to the row's `metadata`
(Part 02 §8.6).

## `session.json` states two facts about time

No data file in the asset records either fact.

**When each acquisition ran.** `session.json` declares a wall-clock window for each data stream.
The NWB records when events happened and never when a sensor was watching, so `session.json` is the
only source for the windows in `core.event_stream_observation_intervals`. The build pairs each
window with a stream the NWB declares, because neither source states both. The windows differ: on
the twelve-probe session the ephys stream runs 6,387 s and the behaviour stream 7,849 s, so a
reward rate computed over the wrong window is off by 23%. Ephys starts first and behaviour runs 24
minutes past it, so `SessionSource.extent` takes the union of the windows.

**Where tick zero sits.** A HARP clock free-runs from the moment its device is powered on, so that
moment is its tick zero: 1.157e7 s before the twelve-probe session, and 6.7e6 s before a session on
another rig. Nothing in the NWB locates it. The NWB's `timestamps_reference_time` equals its
`session_start_time` while its timestamps count from the HARP epoch, which places the first lick
134 days after the session. `SessionSource.epoch` locates tick zero by pairing a stream's declared
start with a tick observed at that start.

### Stored offsets are dropped

`session.json` stamps `+00:00` on Pacific wall-clock readings, a seven-hour error. Read without its
offset, the time is right in every stream checked, including the streams whose offset is right. The
adapter therefore drops the stored offset, localizes the reading to the declared zone, and reports
every disagreement.

`NWBSource` keeps a bad offset and reports it, because the defect it meets cannot be corrected. A
`+00:00` on a local reading can be, since the reading survives. The NWB's date of birth carries
`-07:53`, the offset of Pacific Local Mean Time, and a date has no time of day to localize again.

The declared zone is an IANA zone and not a fixed offset. The session ran in PDT and the HARP epoch
its ticks count from fell in PST, so one offset for the rig is wrong for half the year.

### `subject.json` is the subject's record

`general/subject` in the NWB states a species too, and on both sessions the two agree on
`Mus musculus`. `subject.json` adds two things the NWB lacks:

- a `background_strain` key, which both sessions leave unset;
- a date of birth written as a calendar date. The NWB writes `2024-09-24T00:00:00-07:53`, a
  midnight with an offset, and converting a midnight to another zone can move the day.

## Video timing is reconstructed

The acquiring workflow joins the camera stream to the rig's timestamp stream with `rx:Zip`
(`dynamic-foraging-task`, `src/workflows/foraging.bonsai:8112`), which pairs by position. The host
drops frames in bursts, and every drop shifts the pairing by one. The recorded time therefore falls
behind real time by one trigger period per lost frame, which reaches 93.4 s by the end of the
session. The compensation is `video.zip_pairing_repaired`.

The camera's own chunk data survives intact. `FrameID` counts exposures and skips where one was
lost. The cameras are triggered, so exposure *k* is trigger *k*. Every recorded time is a real
trigger time written beside the wrong frame, so the repair is a lookup rather than a fit:

```text
k      = FrameID - FrameID_0
t_tick = recorded_time[k]                                         where k < rows
t_tick = recorded_time[-1] + (k - (rows - 1)) x trigger_period    past the last recorded time
```

Nothing has dropped before the first frame, so its pairing is correct. The period is measured from
the file. `inventory/upstream-defects.md §12` gives the measurements.

A recorded time out of order with both its neighbours, where those neighbours are in order, is
replaced by their midpoint before the lookup (`video.trigger_time_out_of_line`, §13). Any other
disorder is left for validation to refuse.

### The packet owns frame times, not video

Three cameras of one session are 10 GB as MP4 and 80 GB as the AVI they were encoded from, so a
packet that copied them would be mostly video (Part 04 §5.1). The packet owns one row per frame on
a declared clock instead. No player can supply that row: an MP4 knows its own presentation
timestamps and nothing about the rig's clock. A packet could own a video by declaring
`opaque_location` and delivering the file as a payload (Part 12 §5).

Each camera writes a CSV beside its video, with one line per frame and three columns:

```text
14425755.839584,1379782224,14593876902543944
```

- the frame's time in seconds on the rig clock, from which `t_tick` is derived;
- a frame counter that skips where frames were lost, from which `dropped` is derived;
- the camera's own clock in nanoseconds, against which the repair was checked.

An older workflow appends exposure and gain, which are not read.

`dropped` is true where the counter skips between a frame and the one before it, and false where
it steps by one. At the first frame it is false for a video holding every frame its CSV times. A
video holding fewer is placed by assuming its first frame is the CSV's first exposure, which a
transcode that lost the leading frames would break undetectably, so its first flag is null (Part 01
§3.18).

`pts` comes from none of the three. It is the frame's presentation timestamp in the container, on
the timeline the container presents after its edit list, an integer in the container's own time
base (Part 01 §3.18), and it locates a row in the file a consumer opens. The adapter computes it
from the MP4's `moov` box: decode times from `stts`, composition offsets from `ctts`, shifted by a
single-segment `elst`, with a sample the edit list excludes skipped as no frame of the asset. That
box is a few MB against gigabytes of media, so a published video is timed by range reads where it
lies. The result matches ffprobe's `packet=pts,flags` less its `D` packets, which is the fallback
for an MP4 the reader does not take, such as a fragmented one. The asset declares the rate those timestamps count at, so
`pts * pts_rate_den / pts_rate_num` gives seconds of video without opening the file, and `t_tick`
gives the same frame on the rig clock.

Frames are numbered in presentation order (Part 01 §3.18). Packets arrive in decode order, which
places a frame up to three positions from where it is shown, so the adapter sorts the container
index before reading it.

## Unit quality metrics come from the analyzer

`aind_unit_qc` holds the SpikeInterface metrics an AIND pipeline computes for every unit. The
adapter reads them from the `SortingAnalyzer` beside the curated sorting, as `waveforms` reads its
templates, and not from the NWB exported afterwards. The analyzer names each row by the sorter's
own unit label, so the adapter resolves a unit through the build's `units` term by
`(device_name, local_unit_label)`. The packet numbers the unit, so the adapter never needs a
committed packet to learn an integer.

Each metric keeps the pipeline's name for it, because people search by that vocabulary. The one
rename is `num_spikes`, which becomes `num_spikes_used` so that it cannot be read as core's
`n_spikes`. The synchrony metric arrives as one column per size, `sync_spike_<size>`, and becomes
one row per size, so a fourth size adds a row and leaves the schema alone.

A SpikeInterface 0.104 analyzer can leave `amplitude_median` and `amplitude_cutoff` NaN for every
unit, although the spike amplitudes they summarize are stored complete. The adapter recomputes such
a NaN from those amplitudes rather than resorting: both metrics depend on nothing else, and the
median reproduces a 0.103 analyzer's stored value exactly. The cutoff follows the 0.104 formula,
which is what the failed run would have used. A value the analyzer states is kept, so a 0.103
analyzer keeps its cutoffs, and `aind.amplitude_metrics_recomputed` records that the step ran.

Where a recipe names the session's NWB, the adapter takes a metric still NaN from the NWB's `units`
table, which may have been repaired after the analyzer was written. It fills a unit only where the
analyzer and the NWB agree on every other quality metric both state, so an NWB from another sorting
fills nothing.

## Compensations cite the inventory

A compensation records a known fault in a source and what an adapter does about it, so that the
packet states what was assumed. `escapewheel_writer.sources.compensations` defines the mechanism,
and this package's `compensations` module declares the compensations for AIND's sources. A build
finds them through the `escapewheel.compensations` entry-point group, so a compensation applied
here reaches `core.processing_runs.parameters` as a built-in adapter's does.

Each compensation's `evidence` names a document in the monorepo's `inventory/`, where the fault was
measured. Those paths do not resolve from an installed copy of this distribution. They are still
the right citation, because a packet records where the measurement lives and not a file it can
open.
