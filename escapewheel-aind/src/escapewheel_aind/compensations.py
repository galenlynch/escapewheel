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
        action="every recorded time is a real trigger time written beside the wrong frame, so "
        "exposure k, counted by the camera's FrameID from the first frame, takes the k-th recorded "
        "time; an exposure past the last recorded time extrapolates at the period the file measures",
        evidence="inventory/upstream-defects.md §12",
    ),
    "video.trigger_time_out_of_line": Compensation(
        defect="a camera's recorded trigger times can break order at a HARP second boundary, one "
        "sitting a second early or two adjacent ones out of order by 0.2 ms, so frames are no longer "
        "timed in order",
        action="each time outside the span of its two neighbours, where those are themselves in order, "
        "is replaced by their recorded midpoint, within a trigger period of the true time; any other "
        "disorder is left for validation to refuse",
        evidence="inventory/upstream-defects.md §13",
    ),
}

__all__ = ["COMPENSATIONS"]
