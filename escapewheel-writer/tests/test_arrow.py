"""Records become typed columns: instants localized, metadata serialized, dates parsed."""

import json

import pytest
from escapewheel_reader import open_packet

from escapewheel_writer.errors import (
    FixedOffsetZone,
)
from tests.builders import commit_tables


def test_localize_resolves_dst_per_date():
    """A rig's zone is an IANA zone; its offset depends on the date (`inventory/` §3.1)."""
    from zoneinfo import ZoneInfo

    from escapewheel_writer.arrow import localize

    la = ZoneInfo("America/Los_Angeles")
    assert localize("2025-04-09T17:25:12", la).utcoffset().total_seconds() == -7 * 3600  # PDT
    assert localize("2024-11-26T16:51:12", la).utcoffset().total_seconds() == -8 * 3600  # PST


def test_localize_refuses_a_fixed_offset():
    """A fixed offset is wrong for half the year, silently."""
    from datetime import timedelta, timezone

    from escapewheel_writer.arrow import localize

    with pytest.raises(FixedOffsetZone):
        localize("2025-04-09T17:25:12", timezone(timedelta(hours=-7)))


def test_localize_leaves_an_aware_value_alone():
    from zoneinfo import ZoneInfo

    from escapewheel_writer.arrow import localize

    aware = localize("2025-04-09T17:25:12+00:00", ZoneInfo("America/Los_Angeles"))
    assert aware.utcoffset().total_seconds() == 0


def test_metadata_is_serialized_to_canonical_json(tmp_path, registry, minimal):
    """Adapters build metadata as dictionaries; JSON encoding belongs to the profile."""
    clock = {**minimal["core.clocks"][0], "metadata": {"source": "harp", "board": 1}}
    root = tmp_path / "s001"
    commit_tables(root, registry, {**minimal, "core.clocks": [clock]})
    written = open_packet(root).table("core.clocks").column("metadata").to_pylist()[0]
    assert written == '{"board":1,"source":"harp"}'  # keys sorted, no spaces


def test_metadata_drops_non_finite_numbers_rather_than_emitting_invalid_json(tmp_path, registry, minimal):
    """JSON has no NaN, and source data is full of it -- 384 electrodes' worth in one file."""
    clock = {**minimal["core.clocks"][0], "metadata": {"drift_ppm": float("nan"), "rate": 31250.0}}
    root = tmp_path / "s001"
    commit_tables(root, registry, {**minimal, "core.clocks": [clock]})
    written = open_packet(root).table("core.clocks").column("metadata").to_pylist()[0]
    assert json.loads(written) == {"drift_ppm": None, "rate": 31250.0}


def test_a_metadata_string_is_left_alone(tmp_path, registry, minimal):
    """A caller that serialized its own JSON keeps its bytes."""
    clock = {**minimal["core.clocks"][0], "metadata": '{"already": "json"}'}
    root = tmp_path / "s001"
    commit_tables(root, registry, {**minimal, "core.clocks": [clock]})
    assert open_packet(root).table("core.clocks").column("metadata").to_pylist()[0] == '{"already": "json"}'


def test_metadata_carries_sequences_and_arrays(tmp_path, registry, minimal):
    import numpy as np

    clock = {**minimal["core.clocks"][0], "metadata": {"anchors": [1, 2], "gains": np.array([0.5, 1.5])}}
    root = tmp_path / "s001"
    commit_tables(root, registry, {**minimal, "core.clocks": [clock]})
    written = json.loads(open_packet(root).table("core.clocks").column("metadata").to_pylist()[0])
    assert written == {"anchors": [1, 2], "gains": [0.5, 1.5]}


def test_a_date_written_as_a_string_becomes_a_date(tmp_path, registry, minimal):
    subject = {**minimal["core.subjects"][0], "date_of_birth": "2024-09-24"}
    root = tmp_path / "s001"
    commit_tables(root, registry, {**minimal, "core.subjects": [subject]})
    written = open_packet(root).table("core.subjects").column("date_of_birth").to_pylist()[0]
    assert (written.year, written.month, written.day) == (2024, 9, 24)
