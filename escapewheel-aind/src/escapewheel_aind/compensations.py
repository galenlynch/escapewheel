"""The compensations these adapters apply for known faults in their sources.

- :data:`COMPENSATIONS` -- each compensation by identifier. A build finds them through the
  `escapewheel.compensations` entry-point group.

Each `evidence` names a document in the monorepo's `inventory/`, where the fault was measured. The
path does not resolve from an installed copy of this distribution. A packet records it anyway,
because it says where the measurement lives.
"""

from __future__ import annotations

from escapewheel_writer.adapter import Compensation

#: Registered under `escapewheel.compensations`, which `compensations.registered()` merges with the
#: writer's own. An identifier here never replaces one declared there.
COMPENSATIONS: dict[str, Compensation] = {
    "aind.stored_offset_distrusted": Compensation(
        defect="aind-data-schema JSONs stamp an offset that disagrees with the reading, "
        "notably +00:00 on a Pacific wall clock -- a seven-hour error",
        action="the stored offset is dropped and the reading localised to the declared zone",
        evidence="inventory/upstream-defects.md, nwb-zarr-776259-2025-04-09.md §3.1",
    ),
    "aind.tick_zero_from_stream_start": Compensation(
        defect="a HARP clock free-runs from device power-on, so tick 0 is a power-on instant "
        "no file records; the NWB's timestamps_reference_time claims to locate it and is wrong "
        "by 134 days",
        action="tick 0 is placed by pairing the ephys stream's declared start with the first "
        "spike observed on the clock, which is accurate to about a second -- the stream's "
        "whole-second stamp plus the sub-second wait for the first of thousands of units",
        evidence="inventory/nwb-zarr-776259-2025-04-09.md §3.1, §3.3",
    ),
    "aind.amplitude_metrics_recomputed": Compensation(
        defect="a SpikeInterface 0.104 analyzer stores amplitude_median and amplitude_cutoff as NaN "
        "for every unit: the pipeline passes the 0.103 parameters, which 0.104's functions reject, "
        "while the spike_amplitudes they are computed from are complete",
        action="each NaN is recomputed from the analyzer's spike_amplitudes over the whole recording, "
        "the median as SpikeInterface takes it and the cutoff by its 0.104 formula with the recorded "
        "bin parameters; a value the analyzer states is kept",
        evidence="inventory/upstream-defects.md §11",
    ),
    "video.zip_pairing_repaired": Compensation(
        defect="the acquiring workflow joins the camera stream to the rig's timestamp stream "
        "with rx:Zip (dynamic-foraging-task, src/workflows/foraging.bonsai:8112), which pairs by "
        "position. The host drops frames in bursts, so each drop shifts every later pairing by "
        "one and the recorded time falls behind by one trigger period per lost frame -- measured "
        "at 93.4 s over one 85-minute session, from 46,723 lost frames",
        action="the time is reconstructed from the camera's own chunk data, which survived: "
        "t_tick = t0 + (FrameID - FrameID_0) x trigger period, where t0 is the one pairing still "
        "correct and the period is measured from the file. Checked against the camera's "
        "independent hardware clock, the two agree to 35-85 ms over 85 minutes",
        evidence="inventory/upstream-defects.md §video-zip-pairing",
    ),
}

__all__ = ["COMPENSATIONS"]
