"""The codes a note from these adapters carries.

- :class:`AindNote` -- what an adapter here worked around.

An adapter appends the writer's :class:`~escapewheel_writer.notes.Note` with one of these as its
`code`.
"""

from __future__ import annotations

from enum import StrEnum


class AindNote(StrEnum):
    """What an AIND adapter worked around."""

    #: A timestamp's stored UTC offset was replaced with the declared zone's.
    OFFSET_REPLACED = "offset_replaced"
    #: Tick zero was derived from a stream's start, no source declaring it.
    TICK_ZERO_DERIVED = "tick_zero_derived"
    #: The reference clock has no tick zero, so no observation interval is emitted.
    NO_OBSERVATION_INTERVAL = "no_observation_interval"
    #: An analyzer holds no metrics of one kind.
    NO_METRIC_GROUP = "no_metric_group"
    #: A unit the source holds is not in the packet's sorting and is skipped.
    UNIT_UNMATCHED = "unit_unmatched"
    #: How many metric values the analyzer left NaN were filled from the NWB.
    NAN_FILLED = "nan_filled"
    #: How many metric values the analyzer left NaN were recomputed from its spike amplitudes.
    NAN_RECOMPUTED = "nan_recomputed"
    #: How many units the NWB and the analyzer disagree on, which are not filled.
    NAN_DISAGREED = "nan_disagreed"
    #: Units with a NaN to fill are absent from the NWB.
    NAN_UNSTATED = "nan_unstated"
    #: A video has no timing file and is referenced without frames.
    NO_TIMING = "no_timing"
    #: Frames index past the timing file and are dropped.
    FRAME_PAST_TIMING = "frame_past_timing"
    #: Timed frames are absent from the video.
    FRAME_ABSENT = "frame_absent"
    #: Frames past the last recorded trigger were given extrapolated times.
    FRAME_EXTRAPOLATED = "frame_extrapolated"
    #: Trigger times outside the span of their two neighbours were replaced by its midpoint.
    TRIGGER_REPAIRED = "trigger_repaired"
    #: A video's MP4 index could not be read, so ffprobe listed every packet.
    INDEX_UNREAD = "index_unread"
    #: The units table names no unit by device and sorter label, so no coordinate is emitted.
    NO_UNIT_NAMES = "no_unit_names"
    #: A task parameter varies across trials, so the session row leaves it unset.
    PARAMETER_VARIES = "parameter_varies"


__all__ = ["AindNote"]
