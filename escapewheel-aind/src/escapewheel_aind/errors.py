"""The codes a defect from these adapters carries.

- :class:`AindFault` -- why a source cannot supply what a build asked of it.

The package defines no exception class: an adapter raises the writer's
:exc:`~escapewheel_writer.errors.SourceDefect`, which a build already catches, with one of these as
its `code`.
"""

from __future__ import annotations

from enum import StrEnum


class AindFault(StrEnum):
    """Why an AIND source cannot supply what a build asked of it."""

    #: The root holds no ``session.json``.
    NO_SESSION_JSON = "no_session_json"
    #: A data stream lacks a field every stream states.
    STREAM_FIELD_ABSENT = "stream_field_absent"
    #: Other than one data stream is of the kind asked for.
    NO_ONE_STREAM = "no_one_stream"
    #: A data stream ends before it starts.
    STREAM_REVERSED = "stream_reversed"
    #: The session states no data stream, so it has no extent.
    NO_STREAMS = "no_streams"
    #: A calibration states a different number of inputs and outputs.
    CALIBRATION_MISALIGNED = "calibration_misaligned"
    #: The root holds no analyzer directory.
    NO_ANALYZER_DIRECTORY = "no_analyzer_directory"
    #: No analyzer belongs to the experiment.
    NO_ANALYZER = "no_analyzer"
    #: An analyzer's data frame names no unit for its rows.
    NO_UNIT_INDEX = "no_unit_index"
    #: One unit matches rows of two streams.
    UNIT_IN_TWO_STREAMS = "unit_in_two_streams"
    #: No unit the analyzer holds is in the packet's sorting.
    NO_UNIT_MATCHES = "no_unit_matches"
    #: The NWB's units table names no unit by device and sorter label.
    NO_UNIT_NAMES = "no_unit_names"
    #: The NWB's units table holds one unit twice.
    UNIT_REPEATED = "unit_repeated"


__all__ = ["AindFault"]
