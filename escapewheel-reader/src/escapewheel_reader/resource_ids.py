"""The core registry's resource IDs that code names, each spelled once.

A constant holds an ID the core registry declares under `resources`: a singleton's resource ID,
or the declaration ID the instances of a catalog share. Its name is the ID upper-cased with each
dot an underscore, so `core.units` is :data:`CORE_UNITS`.

Hand-kept, and holding only the IDs that the reader, validator, writer or an adapter refers to. An
extension's IDs belong to the package carrying that extension.
"""

from __future__ import annotations

ANALYSIS_SPIKE_EVENTS = "analysis.spike_events"
CORE_ARRAY_ASSET_INSTANCES = "core.array_asset_instances"
CORE_ARRAY_ASSETS = "core.array_assets"
CORE_ARRAY_CHANNELS = "core.array_channels"
CORE_ARRAY_DIMENSIONS = "core.array_dimensions"
CORE_ARRAY_LABELS = "core.array_labels"
CORE_CALIBRATION_DEVICES = "core.calibration_devices"
CORE_CALIBRATION_POINTS = "core.calibration_points"
CORE_CALIBRATIONS = "core.calibrations"
CORE_CLOCK_ANCHORS = "core.clock_anchors"
CORE_CLOCK_OBSERVATION_INTERVALS = "core.clock_observation_intervals"
CORE_CLOCK_PHASE_STEPS = "core.clock_phase_steps"
CORE_CLOCKS = "core.clocks"
CORE_COORDINATE_FRAME_AXES = "core.coordinate_frame_axes"
CORE_COORDINATE_FRAMES = "core.coordinate_frames"
CORE_CURATION_VERSIONS = "core.curation_versions"
CORE_DEVICES = "core.devices"
CORE_ELECTRODE_COORDINATE_VALUES = "core.electrode_coordinate_values"
CORE_ELECTRODE_COORDINATES = "core.electrode_coordinates"
CORE_ELECTRODES = "core.electrodes"
CORE_EVENT_STREAM_OBSERVATION_INTERVALS = "core.event_stream_observation_intervals"
CORE_EVENT_STREAMS = "core.event_streams"
CORE_EVENTS = "core.events"
CORE_INTERVALS = "core.intervals"
CORE_MEDIA_ASSET_INSTANCES = "core.media_asset_instances"
CORE_MEDIA_ASSETS = "core.media_assets"
CORE_MEDIA_FRAMES = "core.media_frames"
CORE_PREFERRED_RUNS = "core.preferred_runs"
CORE_PROBES = "core.probes"
CORE_PROCESSING_RUN_INPUTS = "core.processing_run_inputs"
CORE_PROCESSING_RUNS = "core.processing_runs"
CORE_SESSIONS = "core.sessions"
CORE_SORTING_RUN_CHANNELS = "core.sorting_run_channels"
CORE_SORTING_RUNS = "core.sorting_runs"
CORE_SOURCE_FILES = "core.source_files"
CORE_SPIKE_EVENTS = "core.spike_events"
CORE_SUBJECTS = "core.subjects"
CORE_UNIT_COORDINATE_VALUES = "core.unit_coordinate_values"
CORE_UNIT_COORDINATES = "core.unit_coordinates"
CORE_UNIT_ELECTRODES = "core.unit_electrodes"
CORE_UNIT_OBSERVATION_INTERVALS = "core.unit_observation_intervals"
CORE_UNIT_QUALITY_LABELS = "core.unit_quality_labels"
CORE_UNITS = "core.units"

__all__ = [
    "ANALYSIS_SPIKE_EVENTS",
    "CORE_ARRAY_ASSETS",
    "CORE_ARRAY_ASSET_INSTANCES",
    "CORE_ARRAY_CHANNELS",
    "CORE_ARRAY_DIMENSIONS",
    "CORE_ARRAY_LABELS",
    "CORE_CALIBRATIONS",
    "CORE_CALIBRATION_DEVICES",
    "CORE_CALIBRATION_POINTS",
    "CORE_CLOCKS",
    "CORE_CLOCK_ANCHORS",
    "CORE_CLOCK_OBSERVATION_INTERVALS",
    "CORE_CLOCK_PHASE_STEPS",
    "CORE_COORDINATE_FRAMES",
    "CORE_COORDINATE_FRAME_AXES",
    "CORE_CURATION_VERSIONS",
    "CORE_DEVICES",
    "CORE_ELECTRODES",
    "CORE_ELECTRODE_COORDINATES",
    "CORE_ELECTRODE_COORDINATE_VALUES",
    "CORE_EVENTS",
    "CORE_EVENT_STREAMS",
    "CORE_EVENT_STREAM_OBSERVATION_INTERVALS",
    "CORE_INTERVALS",
    "CORE_MEDIA_ASSETS",
    "CORE_MEDIA_ASSET_INSTANCES",
    "CORE_MEDIA_FRAMES",
    "CORE_PREFERRED_RUNS",
    "CORE_PROBES",
    "CORE_PROCESSING_RUNS",
    "CORE_PROCESSING_RUN_INPUTS",
    "CORE_SESSIONS",
    "CORE_SORTING_RUNS",
    "CORE_SORTING_RUN_CHANNELS",
    "CORE_SOURCE_FILES",
    "CORE_SPIKE_EVENTS",
    "CORE_SUBJECTS",
    "CORE_UNITS",
    "CORE_UNIT_COORDINATES",
    "CORE_UNIT_COORDINATE_VALUES",
    "CORE_UNIT_ELECTRODES",
    "CORE_UNIT_OBSERVATION_INTERVALS",
    "CORE_UNIT_QUALITY_LABELS",
]
