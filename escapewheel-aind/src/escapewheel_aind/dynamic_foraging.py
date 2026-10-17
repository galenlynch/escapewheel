"""The dynamic-foraging task's trials, blocks and session parameters, read from the GUI's behavior JSON.

- :class:`DynamicForagingSource` -- `core.intervals` for each trial and block, and
  `dynamic_foraging.trials`, `blocks` and `sessions`.
- :data:`ANIMAL_RESPONSE` -- the response code the GUI records, decoded.

The JSON is what the foraging GUI writes beside the raw data, `<subject>_<date>_<time>.json`
under `behavior/`. AIND's NWB trials table is converted from it by the GUI's `TransferToNWB.py`,
whose choice of field for each column this adapter follows, so reading it needs no NWB. Its `B_*`
lists are the measurements, one entry per trial, and its `TP_*` lists the task parameters in force
on each.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from escapewheel_reader.resource_ids import CORE_INTERVALS
from escapewheel_writer.adapter import (
    FILES,
    FLIGHT,
    STREAM,
    Clock,
    Note,
    SourceDefect,
    SourceFault,
    source_root,
)

from .notes import AindNote
from .resource_ids import DYNAMIC_FORAGING_BLOCKS, DYNAMIC_FORAGING_SESSIONS, DYNAMIC_FORAGING_TRIALS

#: The response code to `dynamic_foraging.trials.animal_response`'s closed vocabulary. Read from
#: the lick streams: a `0` trial has left licks and no right, a `1` trial the reverse, and a `2`
#: trial none.
ANIMAL_RESPONSE = {0: "left", 1: "right", 2: "no_response"}

#: `dynamic_foraging.sessions` column to the `TP_*` field it is read from, by type. Each is in
#: force on every trial and held once here.
SESSION_FLOATS = {
    "base_reward_probability_sum": "TP_BaseRewardSum",
    "block_beta": "TP_BlockBeta",
    "block_min": "TP_BlockMin",
    "block_max": "TP_BlockMax",
    "min_reward_each_block": "TP_BlockMinReward",
    "delay_beta": "TP_DelayBeta",
    "delay_min": "TP_DelayMin",
    "delay_max": "TP_DelayMax",
    "iti_beta": "TP_ITIBeta",
    "iti_min": "TP_ITIMin",
    "iti_max": "TP_ITIMax",
    "response_duration": "TP_ResponseTime",
    "reward_consumption_duration": "TP_RewardConsumeTime",
    "reward_delay": "TP_RewardDelay",
    "left_valve_open_time": "TP_LeftValue",
    "right_valve_open_time": "TP_RightValue",
    "reward_size_left": "TP_LeftValue_volume",
    "reward_size_right": "TP_RightValue_volume",
    "minimum_opto_interval": "TP_MinOptoInterval",
    "fraction_of_session": "TP_FractionOfSession",
}
SESSION_STRINGS = {
    "session_wide_control": "TP_SessionWideControl",
    "session_start_with": "TP_SessionStartWith",
    "session_alternation": "TP_SessionAlternating",
    "auto_train_curriculum_name": "TP_auto_train_curriculum_name",
    "auto_train_curriculum_version": "TP_auto_train_curriculum_version",
    "auto_train_curriculum_schema_version": "TP_auto_train_curriculum_schema_version",
    "auto_train_stage": "TP_auto_train_stage",
}
SESSION_BOOLS = {
    "auto_train_engaged": "TP_auto_train_engaged",
    "auto_train_stage_overridden": "TP_auto_train_stage_overridden",
}

#: What the GUI writes for a parameter it had no value for.
_UNSET = frozenset({"", "None", "none", "nan", "NaN"})


def _float(value: Any) -> float | None:
    """Read a JSON number or numeric string as a float, or None for a placeholder."""
    if value is None or (isinstance(value, str) and value.strip() in _UNSET):
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _bool(value: Any) -> bool | None:
    if value is None or (isinstance(value, str) and value.strip() in _UNSET):
        return None
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1")
    number = float(value)
    return None if not np.isfinite(number) else bool(number)


class DynamicForagingSource:
    """Trials, blocks and session parameters of one dynamic-foraging session, from its behavior JSON.

    Parameters
    ----------
    root : str or Path
        The behavior JSON, or a directory holding exactly one.
    session_id : str
        The session these trials belong to.
    reference_clock : mapping
        The `core.clocks` row of the HARP clock the JSON's `*Harp` times are on.
    prefix : str, optional
        Prepended to every interval's ID.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    """

    #: Part 12 §3: the protocols this adapter can deliver by.
    PROTOCOLS: ClassVar[tuple[str, ...]] = (STREAM, FILES, FLIGHT)

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset({DYNAMIC_FORAGING_TRIALS, DYNAMIC_FORAGING_BLOCKS, DYNAMIC_FORAGING_SESSIONS, CORE_INTERVALS})

    #: Part 05 §3.4: a session's other intervals come from other sources.
    CONTRIBUTES = frozenset({CORE_INTERVALS})

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply (Part 12 §4).
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "reference_clock")

    #: Part 05 §3.4: options this adapter reads and can run without (Part 12 §4).
    ACCEPTS: ClassVar[tuple[str, ...]] = ("prefix", "source_cache")

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        reference_clock: Mapping[str, Any],
        prefix: str = "",
        source_cache: str | None = None,
    ) -> None:
        self.root = source_root(root, cache=source_cache)
        self.session_id = session_id
        self.prefix = prefix
        self.clock = Clock(
            clock_id=str(reference_clock["clock_id"]),
            session_id=session_id,
            name=str(reference_clock["clock_id"]),
            tick_rate_num=int(reference_clock["tick_rate_num"]),
            tick_rate_den=int(reference_clock.get("tick_rate_den") or 1),
            origin=str(reference_clock.get("origin") or ""),
        )
        self.notes: list[str] = []
        self._fields: dict[str, Any] | None = None

    def path(self) -> Any:
        """Return the JSON read: `root` itself, or the one `.json` directly inside it."""
        if not self.root.is_dir():
            return self.root
        found = sorted(p for p in self.root.iterdir() if p.suffix == ".json" and p.name[:1].isdigit())
        if len(found) != 1:
            raise SourceDefect(
                f"{self.root} holds {len(found)} behavior JSON files; name the one to read",
                code=SourceFault.STREAM_FILE_ABSENT,
                where=str(self.root),
            )
        return found[0]

    def fields(self) -> dict[str, Any]:
        """Return the JSON's top-level fields, refused where they carry no HARP trial times."""
        if self._fields is None:
            path = self.path()
            self._fields = json.loads(path.read_text())
            # The GUI's own clock is the computer's; only the `*Harp` times are on the reference.
            for required in ("B_TrialStartTimeHarp", "B_TrialEndTimeHarp", "B_RewardProHistory"):
                if not self._fields.get(required):
                    raise SourceDefect(
                        f"{path}: no {required}, so its trials are on no clock this packet holds",
                        code=SourceFault.TRIAL_COLUMN_ABSENT,
                        where=f"{path}#{required}",
                    )
        return self._fields

    @property
    def n(self) -> int:
        """How many trials completed; a list one longer holds the trial in progress at the stop."""
        return len(self.fields()["B_TrialEndTimeHarp"])

    def _list(self, name: str) -> list[Any]:
        """Return a per-trial field cut to the completed trials, or None per trial where it is absent."""
        values = self.fields().get(name)
        return [None] * self.n if not values else list(values[: self.n])

    def _pair(self, name: str, side: int) -> list[Any]:
        """One side of a field the GUI nests as `[left trials, right trials]`.

        A flat list is one value per trial for both sides, as older files record auto water.
        """
        values = self.fields().get(name)
        if not values:
            return [None] * self.n
        return list((values[side] if isinstance(values[0], list) else values)[: self.n])

    def _per_trial_pair(self, name: str, side: int) -> list[Any]:
        """One side of a field the GUI nests as one `[left, right]` per trial."""
        return [None if v is None else v[side] for v in self._list(name)]

    def _ticks(self, name: str) -> list[int | None]:
        """Convert a field of seconds on the reference clock to ticks, a missing or NaN entry as None."""
        seconds = np.array([np.nan if v is None else float(v) for v in self._list(name)], dtype=np.float64)
        out: list[int | None] = [None] * self.n
        finite = np.flatnonzero(np.isfinite(seconds))
        for index, tick in zip(finite, self.clock.ticks(seconds[finite]), strict=True):
            out[index] = int(tick)
        return out

    def _interval(self, kind: str, label: int) -> str:
        return f"{self.prefix}{self.session_id}/{kind}/{label}"

    def _blocks(self) -> tuple[list[int], list[int]]:
        """Each trial's block, and where each block starts and the last ends.

        The GUI records no boundary, so a block is a run of trials sharing a probability pair.
        """
        left, right = self._pair("B_RewardProHistory", 0), self._pair("B_RewardProHistory", 1)
        starts = [i for i in range(self.n) if i == 0 or (left[i], right[i]) != (left[i - 1], right[i - 1])]
        block_of = [int(np.searchsorted(starts, i, side="right")) - 1 for i in range(self.n)]
        return block_of, [*starts, self.n]

    def trial_intervals(self) -> list[dict[str, Any]]:
        """`core.intervals`, one row per completed trial."""
        start, stop = self._ticks("B_TrialStartTimeHarp"), self._ticks("B_TrialEndTimeHarp")
        return [
            {
                "session_id": self.session_id,
                "interval_id": self._interval(DYNAMIC_FORAGING_TRIALS, i),
                "interval_kind": DYNAMIC_FORAGING_TRIALS,
                "local_interval_label": str(i),
                "clock_id": self.clock.clock_id,
                "start_tick": start[i],
                "stop_tick": stop[i],
            }
            for i in range(self.n)
        ]

    def block_intervals(self) -> list[dict[str, Any]]:
        """`core.intervals`, one row per block, from its first trial's start to its last trial's stop."""
        _, edges = self._blocks()
        start, stop = self._ticks("B_TrialStartTimeHarp"), self._ticks("B_TrialEndTimeHarp")
        return [
            {
                "session_id": self.session_id,
                "interval_id": self._interval(DYNAMIC_FORAGING_BLOCKS, i),
                "interval_kind": DYNAMIC_FORAGING_BLOCKS,
                "local_interval_label": str(i),
                "clock_id": self.clock.clock_id,
                "start_tick": start[edges[i]],
                "stop_tick": stop[edges[i + 1] - 1],
            }
            for i in range(len(edges) - 1)
        ]

    def trials(self) -> list[dict[str, Any]]:
        """`dynamic_foraging.trials`, one row per completed trial."""
        block_of, _ = self._blocks()
        # The go cue as the sound card played it; older files name the same stamp `B_GoCueTimeHarp`.
        go_cue = "B_GoCueTimeHarp" if self.fields().get("B_GoCueTimeHarp") else "B_GoCueTimeSoundCard"
        stage = self._list("B_StagePositions")
        columns: dict[str, list[Any]] = {
            "animal_response": [
                None if (code := _float(v)) is None else ANIMAL_RESPONSE.get(int(code))
                for v in self._list("B_AnimalResponseHistory")
            ],
            "rewarded_history_left": [_bool(v) for v in self._pair("B_RewardedHistory", 0)],
            "rewarded_history_right": [_bool(v) for v in self._pair("B_RewardedHistory", 1)],
            "bait_left": [_bool(v) for v in self._pair("B_BaitHistory", 0)],
            "bait_right": [_bool(v) for v in self._pair("B_BaitHistory", 1)],
            "reward_probability_left": [_float(v) for v in self._pair("B_RewardProHistory", 0)],
            "reward_probability_right": [_float(v) for v in self._pair("B_RewardProHistory", 1)],
            "reward_random_number_left": [
                _float(v) for v in self._per_trial_pair("B_CurrentRewardProbRandomNumber", 0)
            ],
            "reward_random_number_right": [
                _float(v) for v in self._per_trial_pair("B_CurrentRewardProbRandomNumber", 1)
            ],
            "delay_start_tick": self._ticks("B_DelayStartTimeHarp"),
            "go_cue_start_tick": self._ticks(go_cue),
            # The GUI stamps the outcome once, on the HARP clock, under the unsuffixed name.
            "reward_outcome_tick": self._ticks("B_RewardOutcomeTime"),
            "delay_duration": [_float(v) for v in self._list("B_DelayHistory")],
            "iti_duration": [_float(v) for v in self._list("B_ITIHistory")],
            "auto_water_left": [_bool(v) for v in self._pair("B_AutoWaterTrial", 0)],
            "auto_water_right": [_bool(v) for v in self._pair("B_AutoWaterTrial", 1)],
            **{
                f"lickspout_position_{axis}": [_float(p.get(axis)) if isinstance(p, dict) else None for p in stage]
                for axis in ("x", "y", "z")
            },
        }
        return [
            {
                "session_id": self.session_id,
                "trial_id": self._interval(DYNAMIC_FORAGING_TRIALS, i),
                "block_id": self._interval(DYNAMIC_FORAGING_BLOCKS, block_of[i]),
                **{column: values[i] for column, values in columns.items()},
            }
            for i in range(self.n)
        ]

    def blocks(self) -> list[dict[str, Any]]:
        """`dynamic_foraging.blocks`, one row per block."""
        _, edges = self._blocks()
        left, right = self._pair("B_RewardProHistory", 0), self._pair("B_RewardProHistory", 1)
        return [
            {
                "session_id": self.session_id,
                "block_id": self._interval(DYNAMIC_FORAGING_BLOCKS, i),
                "reward_probability_left": _float(left[edges[i]]),
                "reward_probability_right": _float(right[edges[i]]),
            }
            for i in range(len(edges) - 1)
        ]

    def _one(self, name: str, cast: Any) -> Any:
        """Return the one value a parameter held on every completed trial, or None where it held none or several."""
        distinct = {value for v in self._list(name) if (value := cast(v)) is not None}
        if len(distinct) > 1:
            self.notes.append(
                Note(
                    f"{name} takes {len(distinct)} values across the trials, so dynamic_foraging.sessions "
                    "leaves it unset",
                    AindNote.PARAMETER_VARIES,
                )
            )
            return None
        return next(iter(distinct), None)

    def sessions(self) -> list[dict[str, Any]]:
        """`dynamic_foraging.sessions`, one row."""
        row: dict[str, Any] = {"session_id": self.session_id}
        row.update({column: self._one(name, _float) for column, name in SESSION_FLOATS.items()})
        row.update(
            {
                column: self._one(name, lambda v: None if v is None or str(v) in _UNSET else str(v))
                for column, name in SESSION_STRINGS.items()
            }
        )
        row.update({column: self._one(name, _bool) for column, name in SESSION_BOOLS.items()})
        return [row]

    def offers(self) -> dict[str, int]:
        """Part 05 §4.1: how many rows of each resource this root holds."""
        return {resource: len(rows) for resource, rows in self.records().items()}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID."""
        return {
            CORE_INTERVALS: self.trial_intervals() + self.block_intervals(),
            DYNAMIC_FORAGING_TRIALS: self.trials(),
            DYNAMIC_FORAGING_BLOCKS: self.blocks(),
            DYNAMIC_FORAGING_SESSIONS: self.sessions(),
        }


__all__ = ["ANIMAL_RESPONSE", "DynamicForagingSource"]
