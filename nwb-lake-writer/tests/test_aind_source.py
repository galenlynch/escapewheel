"""The JSON adapter locates tick zero and declares the windows the NWB cannot."""

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from nwb_lake_writer import Clock
from nwb_lake_writer.clock import HARP_TICK_RATE_HZ
from nwb_lake_writer.sources import SessionSource, SourceDefect

PACIFIC = ZoneInfo("America/Los_Angeles")
SESSION = "ecephys_776259_2025-04-09_17-25-12"

#: The ephys stream's start, stamped `+00:00` on a Pacific reading -- the real defect.
EPHYS_START = "2025-04-09T17:25:12+00:00"
EPHYS_STOP = "2025-04-09T19:11:39+00:00"
#: The behaviour stream's, stamped correctly.
BEHAVIOR_START = "2025-04-09T17:27:55.339024-07:00"
BEHAVIOR_STOP = "2025-04-09T19:38:44.147959-07:00"

#: The first spike, on the HARP clock. Anchors the epoch.
FIRST_SPIKE_TICK = round(11_575_876.219 * HARP_TICK_RATE_HZ)
#: The first and last behaviour event, which the declared window must contain.
FIRST_EVENT_TICK = round(11_576_039.862 * HARP_TICK_RATE_HZ)
LAST_EVENT_TICK = round(11_583_848.938 * HARP_TICK_RATE_HZ)


def build(root, *, streams=None):
    """Write a minimal `session.json` into an asset directory."""
    asset = root / SESSION
    asset.mkdir(parents=True, exist_ok=True)
    if streams is None:
        streams = [
            {
                "stream_start_time": EPHYS_START,
                "stream_end_time": EPHYS_STOP,
                "ephys_modules": [{"assembly_name": "46100"}],
            },
            {
                "stream_start_time": BEHAVIOR_START,
                "stream_end_time": BEHAVIOR_STOP,
                "ephys_modules": [],
                "stream_modalities": [{"abbreviation": "behavior-videos"}],
            },
        ]
    (asset / "session.json").write_text(
        json.dumps({"session_start_time": EPHYS_START, "subject_id": "776259", "data_streams": streams})
    )
    return asset


@pytest.fixture
def asset(tmp_path):
    return build(tmp_path)


@pytest.fixture
def source(asset):
    return SessionSource(asset, zone=PACIFIC)


@pytest.fixture
def harp(source):
    return source.clock(clock_id="harp", at_tick=FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ)


# -- reading -------------------------------------------------------------------------


def test_it_accepts_the_asset_directory_or_the_file(asset):
    assert SessionSource(asset, zone=PACIFIC).streams()
    assert SessionSource(asset / "session.json", zone=PACIFIC).streams()


def test_a_missing_session_json_is_a_defect(tmp_path):
    with pytest.raises(SourceDefect, match="holds no session.json"):
        SessionSource(tmp_path, zone=PACIFIC)


def test_a_fixed_offset_is_refused(asset):
    """PDT for the session and PST for the epoch it counts from; a constant is wrong half the year."""
    with pytest.raises(TypeError, match="fixed offset"):
        SessionSource(asset, zone=timezone(timedelta(hours=-7)))


def test_the_streams_split_on_ephys_modules(source):
    assert source.ephys().index == 0
    assert source.behavior().index == 1
    assert source.behavior().modalities == ("behavior-videos",)


def test_a_stream_missing_its_window_is_a_defect(tmp_path):
    asset = build(tmp_path, streams=[{"ephys_modules": []}])
    with pytest.raises(SourceDefect, match="has no stream_start_time"):
        SessionSource(asset, zone=PACIFIC).streams()


def test_an_ambiguous_split_is_a_defect(tmp_path):
    asset = build(
        tmp_path,
        streams=[{"stream_start_time": EPHYS_START, "stream_end_time": EPHYS_STOP, "ephys_modules": []}] * 2,
    )
    with pytest.raises(SourceDefect, match="2 non-ephys data streams"):
        SessionSource(asset, zone=PACIFIC).behavior()


# -- the offset that is not trusted --------------------------------------------------


def test_the_seven_hour_error_is_corrected_and_reported(source):
    """`+00:00` on a Pacific reading; the naive part is right, so it is re-localized."""
    assert source.ephys().start == datetime.fromisoformat("2025-04-09T17:25:12-07:00")
    assert any("+00:00 replaced with" in note and "-07:00" in note for note in source.notes)


def test_a_correct_offset_is_left_alone_and_unreported(source):
    assert source.behavior().start == datetime.fromisoformat(BEHAVIOR_START)
    assert not [note for note in source.notes if "stream_start_time" in note and "data_streams[1]" in note]


def test_the_ephys_duration_survives_the_correction(source):
    """Both ends shift together, so the span is unchanged -- it is what cross-checks the NWB."""
    assert source.ephys().duration == timedelta(seconds=6387)


# -- tick zero -----------------------------------------------------------------------


def test_the_epoch_lands_on_the_measured_instant(source):
    """Derived from the ephys start and the first spike; verified against the real asset."""
    assert source.epoch(FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ) == datetime(
        2024, 11, 27, 0, 53, 55, 780992, tzinfo=timezone.utc
    )


def test_the_epoch_crosses_the_dst_boundary_correctly(source):
    """The session is PDT and the epoch 134 days earlier is PST; naive subtraction loses an hour."""
    assert source.epoch(FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ).astimezone(PACIFIC).hour == 16


def test_the_epoch_says_it_was_derived(source):
    source.epoch(FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ)
    assert any("derived from data_streams[0]" in note and "uncertain" in note for note in source.notes)


def test_the_clock_carries_the_epoch_and_the_session(harp):
    assert harp.tick_zero_utc == datetime(2024, 11, 27, 0, 53, 55, 780992, tzinfo=timezone.utc)
    assert (harp.clock_id, harp.session_id, harp.tick_rate_num) == ("harp", SESSION, HARP_TICK_RATE_HZ)


def test_the_clock_round_trips_its_own_anchor(harp):
    """tick_at inverts epoch: the ephys start maps back to the tick it was derived from."""
    assert harp.tick_at(datetime.fromisoformat("2025-04-09T17:25:12-07:00")) == FIRST_SPIKE_TICK


def test_a_clock_without_an_epoch_locates_nothing():
    bare = Clock("harp", session_id=SESSION, name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="epoch")
    with pytest.raises(ValueError, match="no tick_zero_utc"):
        bare.tick_at(datetime.now(timezone.utc))


def test_a_naive_instant_locates_nothing(harp):
    with pytest.raises(ValueError, match="carries no offset"):
        harp.tick_at(datetime(2025, 4, 9, 17, 25, 12))  # noqa: DTZ001 -- the point


# -- observation intervals -----------------------------------------------------------


def test_every_stream_shares_the_declared_window(source, harp):
    rows = source.observation_intervals(harp, ["left_lick_time", "right_reward_delivery_time"])
    assert {(r["start_tick"], r["stop_tick"]) for r in rows} == {(361_751_236_188, 361_996_511_468)}
    assert [r["interval_index"] for r in rows] == [0, 0]


def test_the_window_contains_the_events_it_declares(source, harp):
    """The independent check on the epoch: the events must fall inside the declared window."""
    row = source.observation_intervals(harp, ["left_lick_time"])[0]
    assert row["start_tick"] <= FIRST_EVENT_TICK
    assert row["stop_tick"] >= LAST_EVENT_TICK


def test_the_window_is_wider_than_the_events(source, harp):
    """Deriving it from the events instead would lose this slack and bias every rate upward."""
    row = source.observation_intervals(harp, ["left_lick_time"])[0]
    leading = (FIRST_EVENT_TICK - row["start_tick"]) / HARP_TICK_RATE_HZ
    trailing = (row["stop_tick"] - LAST_EVENT_TICK) / HARP_TICK_RATE_HZ
    assert 0 < leading < 1
    assert 39 < trailing < 40


def test_it_uses_the_behaviour_window_not_the_ephys_one(source, harp):
    row = source.observation_intervals(harp, ["left_lick_time"])[0]
    assert (row["stop_tick"] - row["start_tick"]) / HARP_TICK_RATE_HZ == pytest.approx(7848.8, abs=0.1)


def test_the_ephys_window_can_be_asked_for(source, harp):
    row = source.observation_intervals(harp, ["probe_sync"], stream=source.ephys())[0]
    assert (row["stop_tick"] - row["start_tick"]) / HARP_TICK_RATE_HZ == pytest.approx(6387.0, abs=0.1)


def test_no_streams_means_no_intervals(source, harp):
    assert source.observation_intervals(harp, []) == []


def test_an_inverted_window_is_a_defect(tmp_path, harp):
    asset = build(
        tmp_path,
        streams=[{"stream_start_time": EPHYS_STOP, "stream_end_time": EPHYS_START, "ephys_modules": []}],
    )
    with pytest.raises(SourceDefect, match="ends before it starts"):
        SessionSource(asset, zone=PACIFIC).observation_intervals(harp, ["left_lick_time"])


def test_notes_do_not_grow_when_the_file_is_read_twice(source):
    """Deriving a clock and then asking for a window must not report the offset twice."""
    source.clock(clock_id="harp", at_tick=FIRST_SPIKE_TICK, tick_rate_num=HARP_TICK_RATE_HZ)
    offsets = [n for n in source.notes if "replaced with" in n]
    source.behavior()
    assert [n for n in source.notes if "replaced with" in n] == offsets
