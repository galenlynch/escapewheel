"""The adapter's rows, read with nothing but the adapter: no build, no packet."""

import json

import numpy as np
import pytest
from escapewheel_writer.adapter import SourceDefect, document_of, shape_problems
from lick_wheel import DECLARATION, LickWheelSource

from session import EVENTS, START_TICK, STOP_TICK, WHEEL_SAMPLES, wheel_ticks, write

HARP = {"clock_id": "harp", "session_id": "s001", "tick_rate_num": 31250, "tick_rate_den": 1, "origin": "harp_epoch"}


def opened(root):
    return LickWheelSource(root, session_id="s001", reference_clock=HARP)


def test_the_declaration_document_is_the_one_the_class_generates():
    """`escapewheel declare lick_wheel --out src/lick_wheel/declaration.json` writes it."""
    generated = document_of(LickWheelSource, "lick_wheel", [])
    assert shape_problems(generated) == []
    assert json.loads(DECLARATION.read_text()) == generated


def test_each_event_lands_on_its_tick_with_its_payload(tmp_path):
    events = opened(write(tmp_path / "s001")).records()["core.events"]
    assert [(e["stream_id"], e["t_tick"]) for e in events] == [(kind, tick) for tick, kind, _ in EVENTS]
    assert [json.loads(e["payload"]) for e in events if "payload" in e] == [{"volume_ul": 2.5}, {"volume_ul": 3.0}]


def test_each_stream_is_observed_over_the_recording(tmp_path):
    windows = opened(write(tmp_path / "s001")).records()["core.event_stream_observation_intervals"]
    assert {(w["event_stream_id"], w["start_tick"], w["stop_tick"]) for w in windows} == {
        ("lick", START_TICK, STOP_TICK),
        ("reward", START_TICK, STOP_TICK),
    }


def test_the_wheel_is_regular_on_its_own_clock_and_anchored_to_harp(tmp_path):
    source = opened(write(tmp_path / "s001"))
    rows = source.records()
    (array,) = source.staged_arrays()
    assert array.values.shape == (WHEEL_SAMPLES,)
    wheel = next(c for c in rows["core.clocks"] if c["clock_id"] == "wheel")
    assert (wheel["tick_rate_num"], wheel["parent_clock_id"]) == (250, "harp")
    anchors = rows["core.clock_anchors"]
    assert [a["anchor_index"] for a in anchors] == list(range(len(anchors)))
    assert anchors[-1]["t_tick"] == WHEEL_SAMPLES - 1
    assert all(a["parent_tick"] == wheel_ticks()[a["t_tick"]] for a in anchors)


def test_a_session_without_a_wheel_says_so_and_delivers_none(tmp_path):
    source = opened(write(tmp_path / "s001", wheel=False))
    assert source.staged_arrays() == []
    assert "core.array_assets" not in source.records()
    assert [note for note in source.notes if "wheel.csv" in note]


def test_the_source_states_its_subject(tmp_path):
    assert opened(write(tmp_path / "s001", subject_id="m002")).subject_id == "m002"


def test_a_missing_file_is_a_source_defect(tmp_path):
    (tmp_path / "s001").mkdir()
    with pytest.raises(SourceDefect, match="events.csv"):
        opened(tmp_path / "s001").records()


def test_a_harp_time_off_the_grid_is_refused(tmp_path):
    root = write(tmp_path / "s001")
    (root / "events.csv").write_text("harp_seconds,event,volume_ul\n3600.0000001,lick,\n")
    with pytest.raises(ValueError, match="grid"):
        opened(root).records()


def test_a_store_root_is_read_as_a_disk_is():
    """`memory://` stands in for `s3://`: the adapter reads through the root it is handed."""
    from upath import UPath

    root = write(UPath("memory://lick-wheel/s001"))
    assert np.array_equal(
        opened("memory://lick-wheel/s001").staged_arrays()[0].values, opened(root).staged_arrays()[0].values
    )
