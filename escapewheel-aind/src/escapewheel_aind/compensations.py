"""What these adapters do about faults in their sources, recorded rather than assumed.

The writer's `escapewheel_writer.sources.compensations` carries the discipline and the reason for
it; this module is the half belonging to one institution's sources. It reaches a build through the
`escapewheel.compensations` entry-point group, so a compensation an adapter here applies lands in
`core.processing_runs.parameters` exactly as a built-in adapter's does.

Each `evidence` names a document in the monorepo's `inventory/`, which is where the fault was
measured. Those paths do not resolve from an installed copy of this distribution alone, and they
are still the right citation: what a packet records is where the measurement lives, not a file it
can open.
"""

from __future__ import annotations

from escapewheel_writer.sources.compensations import Compensation

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
