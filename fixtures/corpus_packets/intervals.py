"""Packets about how intervals are numbered and specialised."""

from .arrays import with_waveform
from .record import Expected, Packet
from .registry import EXTENSION, KIND
from .session import trial, variant

#: A fixture-local extension declaring a second kind of interval, whose resource ID sorts before
#: `KIND` so a numbering by kind puts its intervals first.
CUE_EXTENSION = {
    "$schema": EXTENSION["$schema"],
    "registry_id": "cue",
    "registry_version": "0.1.0",
    "logical_standard_version": EXTENSION["logical_standard_version"],
    "rule_language": EXTENSION["rule_language"],
    "extension_id": "cue",
    "resources": {
        "cue.tones": {
            "content_class": "extension",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {
                "columns": [
                    {
                        "name": "session_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "Session ID.",
                    },
                    {
                        "name": "tone_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "The tone, and the interval it occupies in core.",
                    },
                ],
                "primary_key": ["tone_id"],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                    {
                        "columns": ["tone_id"],
                        "resource": "core.intervals",
                        "resource_columns": ["interval_id"],
                        "specialises": "core.intervals.interval_kind",
                    },
                ],
                "rules": [],
                "amendment_groups": [["tone_id"]],
            },
        }
    },
}


#: The names of the tone `with_tone` adds and of the two trials.
TONE, FIRST, SECOND = "s001/cue.tones/1", trial(1), trial(2)


def with_tone(c):
    # A tone the cue source labels "1", as the task source labels the first trial.
    c["core.intervals"].append(
        {
            "session_id": "s001",
            "interval_kind": "cue.tones",
            "interval_id": "s001/cue.tones/1",
            "local_interval_label": "1",
            "start_tick": 500,
            "stop_tick": 900,
            "clock_id": "behavior_s001",
        }
    )
    c["cue.tones"] = [{"session_id": "s001", "tone_id": "s001/cue.tones/1"}]


def trial_names_a_tone(c):
    # Part 02 §8.3: a detail row whose interval is of another kind; the reverse check passes,
    # since every interval still has a row of its own kind.
    with_tone(c)
    c[KIND].append({**c[KIND][1], "trial_id": TONE})


def tone_names_a_trial(c):
    with_tone(c)
    c["cue.tones"].append({"session_id": "s001", "tone_id": FIRST})


def tone_in_place_of_its_own(c):
    with_tone(c)
    c["cue.tones"][0]["tone_id"] = FIRST


def interval_of_a_session(c):
    # `core.sessions` is declared, so the kind resolves, but it specialises no interval.
    c["core.intervals"].append(
        {
            "session_id": "s001",
            "interval_kind": "core.sessions",
            "interval_id": "s001/core.sessions/1",
            "local_interval_label": "1",
            "start_tick": 500,
            "stop_tick": 900,
            "clock_id": "behavior_s001",
        }
    )


def equal_bounds(c):
    c["core.intervals"][1] |= {"start_tick": 1000, "stop_tick": 5000}


def second_trial_on_the_probe_clock(c):
    # Earlier in ticks than the first trial, on the clock numbered after the behavior clock.
    c["core.intervals"][1] |= {"clock_id": "imec_ap_s001", "start_tick": 500, "stop_tick": 900}


def repeated_label(c):
    c["core.intervals"][1]["local_interval_label"] = "1"


def orphan_trial(c):
    c[KIND].append({**c[KIND][1], "trial_id": trial(3)})


def trial_labelled_axis(c):
    axis = c["core.array_dimensions"][0]
    axis["coordinate_resource"] = "core.intervals"
    for r, name in zip((r for r in c["core.array_labels"] if r["axis_index"] == 0), (trial(1), trial(2)), strict=True):
        r["label_id"] = name


CUE = (CUE_EXTENSION,)

#: Part 02 §12.9's numbering: packets numbering intervals in each admitted order, and one per defect.
INTERVAL_PACKETS = (
    Packet("two_kinds_one_label", variant(with_tone, extensions=CUE)),
    Packet(
        "trial_names_a_tone",
        variant(trial_names_a_tone, extensions=CUE),
        Expected(
            "error",
            "dynamic_foraging.trials.trial_id.names_a_row_of_its_kind",
            registry="dynamic_foraging",
        ),
    ),
    Packet(
        "tone_names_a_trial",
        variant(tone_names_a_trial, extensions=CUE),
        Expected("error", "cue.tones.tone_id.names_a_row_of_its_kind", registry="cue"),
    ),
    Packet(
        "tone_in_place_of_its_own",
        variant(tone_in_place_of_its_own, extensions=CUE),
        Expected("error", "cue.tones.tone_id.names_a_row_of_its_kind"),
    ),
    Packet(
        "interval_of_a_session",
        variant(interval_of_a_session),
        Expected("error", "core.intervals.interval_kind.core_sessions_is_specialised"),
    ),
    Packet(
        "kinds_out_of_unicode_order",
        variant(with_tone, extensions=CUE, numbers={"interval_id": {FIRST: 0, SECOND: 1, TONE: 2}}),
    ),
    Packet("equal_bounds", variant(equal_bounds)),
    Packet("equal_bounds_swapped", variant(equal_bounds, numbers={"interval_id": {SECOND: 0, FIRST: 1}})),
    Packet("trial_labelled_axis", with_waveform(trial_labelled_axis)),
    Packet(
        "trials_numbered_from_one",
        variant(numbers={"interval_id": {FIRST: 1, SECOND: 2}}),
        Expected("error", "core.intervals.numbered_in_order"),
    ),
    Packet(
        "trials_misordered",
        variant(numbers={"interval_id": {SECOND: 0, FIRST: 1}}),
        Expected("error", "core.intervals.numbered_in_order"),
    ),
    Packet(
        "trials_numbered_by_tick",
        variant(second_trial_on_the_probe_clock, numbers={"interval_id": {SECOND: 0, FIRST: 1}}),
        Expected("error", "core.intervals.numbered_in_order"),
    ),
    Packet(
        "interval_numbering_gap",
        variant(numbers={"interval_id": {FIRST: 0, SECOND: 2}}),
        Expected("error", "core.intervals.numbered_in_order"),
    ),
    Packet(
        "repeated_interval_label",
        variant(repeated_label),
        Expected("error", "core.intervals.label_unique_within_kind"),
    ),
    Packet(
        "orphan_trial",
        variant(orphan_trial),
        Expected("error", "dynamic_foraging.trials.trial_id_resolves", registry="dynamic_foraging"),
    ),
)
