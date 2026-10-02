"""Derive the registry's table set from 02 plus the accepted and proposed revisions.

Each step asserts that a removal names a table that is present and an addition names one
that is not, so a stale entry fails rather than silently miscounting. Re-run after any
revision that changes the table set.
"""

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
PARSED = HERE / "tables02.json"

# (label, removed, added)
STEPS = [
    ("R5 §3   − core.unit_spike_chunks", {"core.unit_spike_chunks"}, set()),
    ("R3 §3.1 + core.session_experimenters", set(), {"core.session_experimenters"}),
    ("R3 §3.2 + core.trial_tags", set(), {"core.trial_tags"}),
    ("R3 §3.3 + core.array_dimensions", set(), {"core.array_dimensions"}),
    ("R9 §2   − core.provenance_entities", {"core.provenance_entities"}, set()),
    ("R9 §2   − core.provenance_activities", {"core.provenance_activities"}, set()),
    ("R9 §2   − core.provenance_edges", {"core.provenance_edges"}, set()),
    ("R9 §3   + core.processing_run_inputs", set(), {"core.processing_run_inputs"}),
    ("R13 §3  + core.clock_anchors", set(), {"core.clock_anchors"}),
    ("R16 §2  + core.unit_quality_labels", set(), {"core.unit_quality_labels"}),
    (
        "R18 §2  + core.unit_observation_intervals",
        set(),
        {"core.unit_observation_intervals"},
    ),
    ("R19 §3  + core.electrode_coordinates", set(), {"core.electrode_coordinates"}),
    ("Part 00 §3.2  + analysis.array_assets", set(), {"analysis.array_assets"}),
    ("Part 00 §3.2  + analysis.array_dimensions", set(), {"analysis.array_dimensions"}),
    ("R23 §2  + core.event_streams", set(), {"core.event_streams"}),
    (
        "R25 §2  + core.event_stream_observation_intervals",
        set(),
        {"core.event_stream_observation_intervals"},
    ),
    ("R28 §2  + core.unit_electrodes", set(), {"core.unit_electrodes"}),
    ("R28 §3  + core.unit_coordinates", set(), {"core.unit_coordinates"}),
    (
        "R38 §2.1 + core.clock_observation_intervals",
        set(),
        {"core.clock_observation_intervals"},
    ),
    ("Part 01 §2.4 + core.preferred_runs", set(), {"core.preferred_runs"}),
    # R54 §2.3 withdraws the child table R3 §3.2 added: no packet ever populated it, and a
    # trial tag is a task's vocabulary, which R43 §3 sends to an extension.
    ("R54 §2.3 − core.trial_tags", {"core.trial_tags"}, set()),
    (
        "Part 01 §3.10 core.trials -> core.intervals",
        {"core.trials"},
        {"core.intervals"},
    ),
    ("06      + analysis.spike_events", set(), {"analysis.spike_events"}),
    # R83 §2.1: a channel index a source emits counts the channels its run kept, and nothing
    # held that list, so no packet could resolve one.
    ("R83 §2.1 + core.sorting_run_channels", set(), {"core.sorting_run_channels"}),
    # Part 02 §12.3: a calibration is what someone measured about an instrument so that its numbers can
    # be interpreted, and nothing in the specification recorded one. Three resources, because the
    # devices a calibration covers and the points of its curve are both repeated values (Part 02 §6).
    ("R89 §2.1 + core.calibrations", set(), {"core.calibrations"}),
    ("R89 §2.2 + core.calibration_devices", set(), {"core.calibration_devices"}),
    ("R89 §2.3 + core.calibration_points", set(), {"core.calibration_points"}),
    ("R99 §3.3 + core.clock_phase_steps", set(), {"core.clock_phase_steps"}),
    ("Part 01 §3.24 + core.coordinate_frames", set(), {"core.coordinate_frames"}),
    (
        "Part 02 §12.7 + core.coordinate_frame_axes",
        set(),
        {"core.coordinate_frame_axes"},
    ),
    (
        "Part 01 §3.8 + core.electrode_coordinate_values",
        set(),
        {"core.electrode_coordinate_values"},
    ),
    (
        "Part 01 §3.8 + core.unit_coordinate_values",
        set(),
        {"core.unit_coordinate_values"},
    ),
    ("Part 03 §6.3 + core.array_labels", set(), {"core.array_labels"}),
    ("Part 03 §6.3 + analysis.array_labels", set(), {"analysis.array_labels"}),
    ("Part 02 §12.10 + core.sidecars", set(), {"core.sidecars"}),
    ("Part 02 §12.10 + core.sidecar_scopes", set(), {"core.sidecar_scopes"}),
]

if not PARSED.exists():
    subprocess.run([sys.executable, str(HERE / "sweep.py")], check=True, stdout=subprocess.DEVNULL)

tables = set(json.loads(PARSED.read_text()))
print(f"{'02 as written':47s}{len(tables):>4d}")
for label, removed, added in STEPS:
    missing = removed - tables
    clashing = added & tables
    assert not missing, f"{label}: not present in the current set: {missing}"
    assert not clashing, f"{label}: already present: {clashing}"
    tables = (tables - removed) | added
    print(f"{label:47s}{len(tables):>4d}")
print(f"{'':47s}  --")
print(f"{'registry content':47s}{len(tables):>4d}\n")
for t in sorted(tables):
    print(f"  {t}")
