"""What an adapter or a build worked around, as text a person reads and a code a caller compares.

- :class:`Note` -- one note: its text, carrying the code that says which note it is.
- :class:`NoteCode` -- the notes this package's adapters and its build write.
- :func:`codes` -- the codes of a list of notes.
- :func:`coded` -- the notes of a list that carry one code.

`notes` stays a list of strings: a :class:`Note` is one, so an adapter that appends plain text is
as valid as it was, and its notes carry no code. Nor does a code cross an out-of-process delivery,
whose report carries a note's text alone (Part 12 §9).
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Self


class Note(str):
    """A note's text, carrying which note it is.

    Attributes
    ----------
    code : str or None
        Which note it is, whatever the names in its text: a :class:`NoteCode` from this package, and
        a code of its own from an adapter released separately. None where the writer gave none.
    """

    code: str | None

    def __new__(cls, text: str, code: str | None = None) -> Self:
        """Return `text` as a note of the given code."""
        note = super().__new__(cls, text)
        note.code = code
        return note


def codes(notes: Iterable[str]) -> list[str | None]:
    """Return each note's code in order, None for a note that is plain text."""
    return [getattr(note, "code", None) for note in notes]


def coded(notes: Iterable[str], code: str) -> list[str]:
    """Return the notes carrying `code`, in order."""
    return [note for note in notes if getattr(note, "code", None) == code]


class NoteCode(StrEnum):
    """Which note a built-in adapter or the build wrote."""

    # -- the built-in adapters

    #: A device schema declares no device name, so the device is skipped.
    DEVICE_UNNAMED = "device_unnamed"
    #: The file holds no LFP series, so none is referenced.
    NO_LFP_SERIES = "no_lfp_series"
    #: A referenced array's store could not be reached, so nothing about it is recorded.
    NOT_VERIFIED = "not_verified"
    #: The store offered no digest for a referenced array's members.
    NO_STORE_DIGEST = "no_store_digest"
    #: The electrode table has no `channel_name`, so a contact is named by its group and row.
    NO_CHANNEL_NAMES = "no_channel_names"
    #: The electrode table has no `inter_sample_shift`, so no channel carries an offset.
    NO_SAMPLE_SHIFT = "no_sample_shift"
    #: The electrode table's `inter_sample_shift` has no array channel to go on.
    SAMPLE_SHIFT_NOT_EMITTED = "sample_shift_not_emitted"
    #: A column is in an encoding the adapter does not decode, and is not read.
    COLUMN_NOT_READ = "column_not_read"
    #: A timestamp stores no UTC offset and is read in the declared zone.
    OFFSET_ASSUMED = "offset_assumed"
    #: A timestamp's stored UTC offset disagrees with the declared zone and is kept.
    OFFSET_KEPT = "offset_kept"
    #: Timestamps that are not finite were dropped.
    TIMESTAMPS_DROPPED = "timestamps_dropped"
    #: Devices sharing a serial number are recorded as one.
    DEVICES_MERGED = "devices_merged"
    #: A settings file is not XML and is skipped.
    SETTINGS_UNPARSEABLE = "settings_unparseable"
    #: The sorter stamped its run with no UTC offset.
    SORT_TIME_NAIVE = "sort_time_naive"
    #: A recording has several segments, so no observation window is written.
    SEVERAL_SEGMENTS = "several_segments"
    #: An analyzer states no channel list, so none is written.
    NO_CHANNEL_LIST = "no_channel_list"
    #: An analyzer does not say what its values are in.
    UNIT_UNSTATED = "unit_unstated"
    #: An analyzer carries no spike amplitudes.
    NO_AMPLITUDES = "no_amplitudes"
    #: A label has no declared projection and is kept verbatim.
    LABEL_UNPROJECTED = "label_unprojected"
    #: The curation removed units that carry no manual label saying so.
    REMOVAL_UNRECORDED = "removal_unrecorded"
    #: A curated stream records no curation, so nothing removed, merged or labelled is known.
    CURATION_UNRECORDED = "curation_unrecorded"
    #: A manual label names a unit the sorting does not have.
    LABEL_NAMES_NO_UNIT = "label_names_no_unit"
    #: A unit has several labels in one category, and they are left unprojected.
    SEVERAL_LABELS = "several_labels"
    #: A stream has no aligned timestamps and is skipped.
    STREAM_NOT_ALIGNED = "stream_not_aligned"
    #: Two record nodes hold the same events, and one is kept.
    NODE_DUPLICATE = "node_duplicate"
    #: A record node states no start instant.
    NO_START_INSTANT = "no_start_instant"
    #: How far apart the record nodes put tick zero.
    TICK_ZERO_SPREAD = "tick_zero_spread"
    #: A stream has no declared clock and is anchored to nothing.
    NO_CLOCK_DECLARED = "no_clock_declared"
    #: A terminal anchor was withheld.
    ANCHOR_WITHHELD = "anchor_withheld"
    #: A clock has too few anchors for the terminal-anchor test.
    ANCHOR_TEST_SKIPPED = "anchor_test_skipped"
    #: The anchors a stream was given.
    ANCHORS_WRITTEN = "anchors_written"
    #: The reference alignment steps in phase.
    PHASE_DISCONTINUITY = "phase_discontinuity"
    #: A unit the source holds is not in the packet's sorting and is skipped.
    UNIT_UNMATCHED = "unit_unmatched"
    #: A unit is sparse on no contact and is stored with no channels.
    UNIT_NO_CONTACT = "unit_no_contact"
    #: A unit of the packet's sorting has no template and is stored with no channels.
    UNIT_NO_TEMPLATE = "unit_no_template"

    # -- the build

    #: A declared fact went unchecked, since the source states none.
    FACT_UNCHECKED = "fact_unchecked"
    #: A fact declares an override and the source states the same value.
    OVERRIDE_UNNEEDED = "override_unneeded"
    #: A declared fact overrides what the source states.
    FACT_OVERRIDDEN = "fact_overridden"
    #: Information: a column override released a value a passed-over source stated.
    VALUE_RELEASED = "value_released"
    #: A warning: a column override released no value.
    COLUMN_OVERRIDE_IDLE = "column_override_idle"
    #: A declared fact differs from what the source derives, and the source's is used.
    SOURCE_VALUE_USED = "source_value_used"
    #: A declared fact differs from what the source states, and the recipe's is used.
    RECIPE_VALUE_USED = "recipe_value_used"
    #: A source states a fact the amended packet holds otherwise, and the packet's is kept.
    PACKET_VALUE_KEPT = "packet_value_kept"
    #: The configured source cache cannot be used, so no adapter is supplied one.
    NO_SOURCE_CACHE = "no_source_cache"
    #: A source produced rows no source claims, and they are discarded.
    UNCLAIMED_DISCARDED = "unclaimed_discarded"
    #: The terminal-anchor test ran in a delivered source, so its result is not recorded.
    ANCHOR_TEST_UNRECORDED = "anchor_test_unrecorded"
    #: The terminal-anchor test examined clocks that are not staged.
    ANCHOR_TEST_PARTIAL = "anchor_test_partial"
    #: A delivery's report is not JSON.
    REPORT_NOT_JSON = "report_not_json"
    #: A problem a delivered adapter reported.
    REPORTED = "reported"
    #: The inputs a delivered adapter says it read.
    INPUTS_READ = "inputs_read"


__all__ = ["Note", "NoteCode", "coded", "codes"]
