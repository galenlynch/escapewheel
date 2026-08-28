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
    ("R5 §3   − core.unit_spike_chunks",       {"core.unit_spike_chunks"}, set()),
    ("R3 §3.1 + core.session_experimenters",   set(), {"core.session_experimenters"}),
    ("R3 §3.2 + core.trial_tags",              set(), {"core.trial_tags"}),
    ("R3 §3.3 + core.array_dimensions",        set(), {"core.array_dimensions"}),
    ("R9 §2   − core.provenance_entities",     {"core.provenance_entities"}, set()),
    ("R9 §2   − core.provenance_activities",   {"core.provenance_activities"}, set()),
    ("R9 §2   − core.provenance_edges",        {"core.provenance_edges"}, set()),
    ("R9 §3   + core.processing_run_inputs",   set(), {"core.processing_run_inputs"}),
    ("R13 §3  + core.clock_anchors",           set(), {"core.clock_anchors"}),
    ("R16 §2  + core.unit_quality_labels",     set(), {"core.unit_quality_labels"}),
    ("R18 §2  + core.unit_observation_intervals", set(), {"core.unit_observation_intervals"}),
    ("R19 §3  + core.electrode_coordinates",   set(), {"core.electrode_coordinates"}),
    ("R20 §5  + analysis.array_assets",        set(), {"analysis.array_assets"}),
    ("R20 §5  + analysis.array_dimensions",    set(), {"analysis.array_dimensions"}),
    ("R23 §2  + core.event_streams",           set(), {"core.event_streams"}),
    ("R25 §2  + core.event_stream_observation_intervals", set(), {"core.event_stream_observation_intervals"}),
    ("R28 §2  + core.unit_electrodes",         set(), {"core.unit_electrodes"}),
    ("R28 §3  + core.unit_coordinates",        set(), {"core.unit_coordinates"}),
]

if not PARSED.exists():
    subprocess.run([sys.executable, str(HERE / "sweep.py")], check=True,
                   stdout=subprocess.DEVNULL)

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
