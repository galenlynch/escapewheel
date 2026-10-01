"""The closed vocabularies a report is written in.

- :class:`Level` -- a finding's level.
- :class:`Verdict` -- the verdict of a packet or of a registry it binds.
- :class:`EvaluationStatus` -- what became of an evaluation a registry requires.
- :class:`RegistryState` -- the state of a registry document's result.

Each is a string enumeration, so a member equals the string a report's JSON carries and a caller
compares against the member wherever it holds that string.
"""

from __future__ import annotations

from enum import StrEnum


class Level(StrEnum):
    """How a finding counts against its subject (Part 05 §9.1)."""

    #: The subject does not conform.
    ERROR = "error"
    #: Conformant, but likely not intended.
    WARNING = "warning"
    #: Recorded, not judged.
    INFO = "info"


class Verdict(StrEnum):
    """A subject's verdict, declared from least to most severe (Part 05 §9.5).

    A conjunction of verdicts is the most severe among them.
    """

    PASSED = "passed"
    #: A required evaluation did not complete or was withheld.
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class EvaluationStatus(StrEnum):
    """What became of an evaluation a registry requires, kept apart from packet findings (Part 05 §9.4)."""

    COMPLETE = "complete"
    #: An input could not be read, or the engine could not finish.
    INCOMPLETE = "incomplete"
    #: A rule is outside the rule language its registry selects.
    INVALID = "invalid"
    #: The registry selects a rule language this validator does not evaluate.
    UNSUPPORTED = "unsupported"


class RegistryState(StrEnum):
    """The state of a registry document's result (Part 02 §9.4); only `VALID` directs packet checks."""

    VALID = "valid"
    INVALID = "invalid"
    UNSUPPORTED = "unsupported"
    INCOMPLETE = "incomplete"


__all__ = ["EvaluationStatus", "Level", "RegistryState", "Verdict"]
