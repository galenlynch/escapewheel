"""The dynamic-foraging tables, read from the foraging GUI's behavior JSON."""

import json

import pytest
from escapewheel_writer.adapter import SourceDefect

from escapewheel_aind.dynamic_foraging import DynamicForagingSource
from escapewheel_aind.notes import AindNote

HARP = {"clock_id": "harp", "session_id": "s001", "tick_rate_num": 31250}

#: Three completed trials and the one in progress at the stop, which every list the GUI extends
#: before a trial ends holds one more of. Times are whole multiples of 32 µs, as HARP stamps are.
BEHAVIOR = {
    "B_TrialStartTimeHarp": [10.0, 12.0, 14.0],
    "B_TrialEndTimeHarp": [11.5, 13.5, 15.5],
    "B_DelayStartTimeHarp": [10.5, 12.5, 14.5],
    "B_GoCueTimeSoundCard": [11.0, 13.0, 15.0],
    "B_RewardOutcomeTime": [11.264, 13.264, None],
    "B_AnimalResponseHistory": [0.0, 1.0, 2.0],
    "B_RewardedHistory": [[True, False, False], [False, True, False]],
    "B_BaitHistory": [[True, True, False], [False, True, True]],
    "B_RewardProHistory": [[0.4, 0.4, 0.1, 0.1], [0.1, 0.1, 0.4, 0.4]],
    "B_CurrentRewardProbRandomNumber": [[0.2, 0.9], [0.5, 0.05], [0.3, 0.3]],
    "B_DelayHistory": [1.0, 1.0, 1.0, 1.0],
    "B_ITIHistory": [2.0, 3.0, 4.0, 5.0],
    "B_AutoWaterTrial": [[0, 0, 1], [0, 0, 1]],
    "B_StagePositions": [{"x": 1.0, "y": 2.0, "z": 3.0}] * 4,
    "TP_BlockBeta": ["20", "20", "20", "20"],
    "TP_LeftValue": ["0.03", "0.03", "0.04", "0.04"],
    "TP_SessionWideControl": ["off", "off", "off", "off"],
    "TP_auto_train_engaged": [False, False, False, False],
}


def behavior(root, fields=BEHAVIOR):
    """Write the JSON where the GUI does, and return the folder holding it."""
    folder = root / "behavior"
    folder.mkdir(parents=True)
    (folder / "786867_2025-09-25_12-44-05.json").write_text(json.dumps(fields))
    return folder


def source(root, **options):
    return DynamicForagingSource(behavior(root), session_id="s001", reference_clock=HARP, **options)


def test_completed_trials_are_intervals_on_the_reference_clock(tmp_path):
    """10 s is tick 312,500; the trial in progress at the stop is not one."""
    trials = [r for r in source(tmp_path).trial_intervals()]
    assert [(r["start_tick"], r["stop_tick"]) for r in trials] == [
        (312_500, 359_375),
        (375_000, 421_875),
        (437_500, 484_375),
    ]
    assert trials[0]["interval_id"] == "s001/dynamic_foraging.trials/0"


def test_a_block_is_a_run_of_one_probability_pair(tmp_path):
    adapter = source(tmp_path)
    assert [(b["reward_probability_left"], b["reward_probability_right"]) for b in adapter.blocks()] == [
        (0.4, 0.1),
        (0.1, 0.4),
    ]
    assert [r["block_id"] for r in adapter.trials()] == ["s001/dynamic_foraging.blocks/0"] * 2 + [
        "s001/dynamic_foraging.blocks/1"
    ]
    (_, second) = adapter.block_intervals()
    assert (second["start_tick"], second["stop_tick"]) == (437_500, 484_375)


def test_a_trial_decodes_its_codes_and_splits_its_sides(tmp_path):
    first, _, last = source(tmp_path).trials()
    assert (first["animal_response"], last["animal_response"]) == ("left", "no_response")
    assert (first["rewarded_history_left"], first["bait_right"]) == (True, False)
    assert (first["reward_random_number_left"], first["reward_random_number_right"]) == (0.2, 0.9)
    assert (last["auto_water_left"], last["reward_outcome_tick"]) == (True, None)
    assert (first["go_cue_start_tick"], first["iti_duration"], first["lickspout_position_y"]) == (343_750, 2.0, 2.0)


def test_a_parameter_held_on_every_trial_is_the_sessions(tmp_path):
    adapter = source(tmp_path)
    (row,) = adapter.sessions()
    assert (row["block_beta"], row["session_wide_control"], row["auto_train_engaged"]) == (20.0, "off", False)
    assert row["left_valve_open_time"] is None
    assert [note.code for note in adapter.notes] == [AindNote.PARAMETER_VARIES]


def test_a_file_without_harp_times_is_refused(tmp_path):
    fields = {k: v for k, v in BEHAVIOR.items() if k != "B_TrialEndTimeHarp"}
    with pytest.raises(SourceDefect):
        DynamicForagingSource(behavior(tmp_path, fields), session_id="s001", reference_clock=HARP).trials()
