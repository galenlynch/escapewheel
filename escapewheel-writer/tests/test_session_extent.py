"""The session's bounds come from the declared stream windows, and its subject is checked."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import ClassVar

import pytest

from escapewheel_writer.errors import SourceDefect, SourceFault
from escapewheel_writer.notes import NoteCode, coded, codes
from escapewheel_writer.recipe import SourceSpec
from escapewheel_writer.session import Context, composed, harvest

BEGAN = datetime(2025, 4, 10, 0, 25, 12, tzinfo=UTC)
ENDED = datetime(2025, 4, 10, 2, 38, 44, tzinfo=UTC)


class Spec:
    kind = "session"


class Stub:
    """A session source stating both ends of its session, as the real one does.

    Part 05 §3.6: a build reads a stated fact off the source, and off the report where the source
    delivered from another process -- so a stub declaring `STATES` and the attributes behind it is
    the shape of either.
    """

    STATES: ClassVar[dict[str, str]] = {
        "session.session_start_time": "stated_session_start_time",
        "session.session_end_time": "stated_session_end_time",
        "subject.subject_id": "subject_id",
    }

    def __init__(self, began=BEGAN, ended=ENDED, subject_id=None):
        self.stated_session_start_time = began
        self.stated_session_end_time = ended
        self.subject_id = subject_id
        self.path = "session.json"
        self.notes: list[str] = []


def _recipe(session=None, subject=None, overrides=None):
    """The parts of a Recipe `harvest` reads, which a whole one would only pad out."""
    session = {"session_id": "s001", **(session or {})}
    subject = subject or {}
    return SimpleNamespace(
        session=session,
        subject=subject,
        overrides=overrides or {},
        declared_facts={f"session.{k}": v for k, v in session.items()}
        | {f"subject.{k}": v for k, v in subject.items()},
    )


#: What the packet stores each compared fact as, which `build` reads off the registry. Two
#: spellings of one instant are one fact, and without the type they compare as the text they were
#: written in.
FACT_TYPES = {"session.session_start_time": "timestamp", "session.session_end_time": "timestamp"}


def _context():
    """The build's context for a comparison, which needs the types the packet stores."""
    return Context(session_id="s001", fact_types=FACT_TYPES)


def _no_rows(resource):
    """A source that produced no rows to harvest from, which is what these stubs are about."""
    del resource
    return []


def recipe_with(**session):
    return _recipe(session=session)


def recipe_for(subject_id, **overrides):
    """A recipe declaring one subject, which is all Part 05 §3.6's comparison reads."""
    return _recipe(subject={"subject_id": subject_id}, overrides=overrides or None)


def test_both_bounds_come_from_the_windows():
    context = _context()
    harvest(Spec(), Stub(), context, recipe_with(), _no_rows)
    assert context.session_extra == {"session_start_time": BEGAN, "session_end_time": ENDED}


def test_a_recipe_that_agrees_says_nothing():
    source = Stub()
    harvest(Spec(), source, _context(), recipe_with(session_start_time="2025-04-10T00:25:12Z"), _no_rows)
    assert source.notes == []


def test_a_recipe_that_disagrees_is_reported_and_overridden():
    """A transcription of the same fact, differing, is worth hearing about."""
    source = Stub()
    context = _context()
    harvest(Spec(), source, context, recipe_with(session_start_time="2025-04-10T00:30:00Z"), _no_rows)
    assert context.session_extra["session_start_time"] == BEGAN
    assert codes(source.notes) == [NoteCode.SOURCE_VALUE_USED]


# -- the subject the recipe declares ------------------------------------------------------


def test_a_subject_the_source_contradicts_is_refused():
    """Part 05 §3.6. One recipe declared 786867 against a session stating 776259, and every packet
    built from it asserted 6,781 units from an animal that was never in the rig."""
    with pytest.raises(SourceDefect) as refused:
        harvest(Spec(), Stub(subject_id="776259"), _context(), recipe_for("786867"), _no_rows)
    assert refused.value.code is SourceFault.FACT_DIFFERS
    assert refused.value.where == "subject.subject_id"


def test_a_subject_the_source_agrees_with_passes_silently():
    source = Stub(subject_id="776259")
    harvest(Spec(), source, _context(), recipe_for("776259"), _no_rows)
    assert [n for n in source.notes if "subject" in n] == []


def test_a_source_stating_no_subject_leaves_the_declaration_unchecked():
    """Part 05 §3.6: silence is a fact about the source, not a disagreement -- but it is reported,
    so a build log tells a verified subject from an asserted one."""
    source = Stub(subject_id=None)
    harvest(Spec(), source, _context(), recipe_for("776259"), _no_rows)
    assert NoteCode.FACT_UNCHECKED in codes(source.notes)


def test_an_override_lets_the_recipe_win_and_says_why():
    """Part 05 §3.6. The refusal is what an override lifts, and the reason is what it leaves behind."""
    source = Stub(subject_id="776259")
    recipe = recipe_for("786867", **{"subject.subject_id": "the session names the wrong animal"})
    harvest(Spec(), source, _context(), recipe, _no_rows)
    (overridden,) = coded(source.notes, NoteCode.FACT_OVERRIDDEN)
    assert "the session names the wrong animal" in overridden


def test_an_override_that_changes_nothing_is_reported():
    """Part 05 §3.6: a stale override costs a line of the log, not a build."""
    source = Stub(subject_id="776259")
    recipe = recipe_for("776259", **{"subject.subject_id": "no longer needed"})
    harvest(Spec(), source, _context(), recipe, _no_rows)
    assert NoteCode.OVERRIDE_UNNEEDED in codes(source.notes)


def test_a_number_and_a_string_naming_one_subject_agree():
    """Part 05 §3.6: `session.json` states 776259 as a number; comparing what was written would refuse."""
    source = Stub(subject_id=776259)
    harvest(Spec(), source, _context(), recipe_for("776259"), _no_rows)
    assert source.notes == []


# -- the windows a build composes --------------------------------------------------------

WATCHING = SourceSpec(kind="session", root="session.json", owns=("core.event_stream_observation_intervals",))


def _watched(window, streams):
    context = Context(session_id="s1", event_streams=list(streams))
    context.windows["session"] = window
    return composed(WATCHING, context).get("core.event_stream_observation_intervals", [])


def test_every_stream_shares_the_window_its_source_declared():
    """One acquisition watched them all, so a stream of rare events gets no shorter a window."""
    rows = _watched((100, 900), ["licks", "rewards"])
    assert [(row["event_stream_id"], row["start_tick"], row["stop_tick"]) for row in rows] == [
        ("licks", 100, 900),
        ("rewards", 100, 900),
    ]


def test_no_streams_means_no_windows():
    assert _watched((100, 900), []) == []


def test_a_window_ending_before_it_starts_is_a_defect():
    with pytest.raises(SourceDefect) as refused:
        _watched((900, 100), ["licks"])
    assert refused.value.code is SourceFault.WINDOW_REVERSED
