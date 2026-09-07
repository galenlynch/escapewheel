"""The session's bounds come from the declared stream windows, and its subject is checked."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from escapewheel_writer.session import Context, _declared_start, _harvest
from escapewheel_writer.sources import SourceDefect

BEGAN = datetime(2025, 4, 10, 0, 25, 12, tzinfo=UTC)
ENDED = datetime(2025, 4, 10, 2, 38, 44, tzinfo=UTC)


class Spec:
    kind = "session"


class Stub:
    """A session source with one declared extent."""

    def __init__(self, began=BEGAN, ended=ENDED, subject_id=None):
        self.extent_value = (began, ended)
        self.subject_id = subject_id
        self.path = "session.json"
        self.notes: list[str] = []

    def extent(self):
        return self.extent_value


def _recipe(session=None, subject=None, overrides=None):
    """The parts of a Recipe `_harvest` reads, which a whole one would only pad out."""
    session = {"session_id": "s001", **(session or {})}
    subject = subject or {}
    return SimpleNamespace(
        session=session,
        subject=subject,
        overrides=overrides or {},
        declared_facts={f"session.{k}": v for k, v in session.items()}
        | {f"subject.{k}": v for k, v in subject.items()},
    )


def recipe_with(**session):
    return _recipe(session=session)


def recipe_for(subject_id, **overrides):
    """A recipe declaring one subject, which is all R87 §2.1's comparison reads."""
    return _recipe(subject={"subject_id": subject_id}, overrides=overrides or None)


def test_both_bounds_come_from_the_windows():
    context = Context(session_id="s001")
    _harvest(Spec(), Stub(), context, recipe_with())
    assert context.session_extra == {"session_start_time": BEGAN, "session_end_time": ENDED}


def test_a_recipe_that_agrees_says_nothing():
    source = Stub()
    _harvest(Spec(), source, Context(session_id="s001"), recipe_with(session_start_time="2025-04-10T00:25:12Z"))
    assert source.notes == []


def test_a_recipe_that_disagrees_is_reported_and_overridden():
    """A transcription of the same fact, differing, is worth hearing about."""
    source = Stub()
    context = Context(session_id="s001")
    _harvest(Spec(), source, context, recipe_with(session_start_time="2025-04-10T00:30:00Z"))
    assert context.session_extra["session_start_time"] == BEGAN
    assert len(source.notes) == 1 and "disagrees" in source.notes[0]


@pytest.mark.parametrize("raw", ["2025-04-10T00:25:12Z", "2025-04-10T00:25:12+00:00", "aware"])
def test_a_declared_start_is_read_however_it_is_written(raw):
    """TOML gives a datetime or a string, and either locates the same instant."""
    assert _declared_start(recipe_with(session_start_time=BEGAN if raw == "aware" else raw)) == BEGAN


def test_a_naive_declared_start_is_read_as_utc():
    """The recipe is the packet's own record, and the packet's times are UTC."""
    assert _declared_start(recipe_with(session_start_time=BEGAN.replace(tzinfo=None))) == BEGAN


def test_no_declared_start_is_not_a_disagreement():
    assert _declared_start(recipe_with()) is None


# -- the subject the recipe declares ------------------------------------------------------


def test_a_subject_the_source_contradicts_is_refused():
    """R87 §2.1. One recipe declared 786867 against a session stating 776259, and every packet
    built from it asserted 6,781 units from an animal that was never in the rig."""
    with pytest.raises(SourceDefect, match="786867"):
        _harvest(Spec(), Stub(subject_id="776259"), Context(session_id="s001"), recipe_for("786867"))


def test_a_subject_the_source_agrees_with_passes_silently():
    source = Stub(subject_id="776259")
    _harvest(Spec(), source, Context(session_id="s001"), recipe_for("776259"))
    assert [n for n in source.notes if "subject" in n] == []


def test_a_source_stating_no_subject_leaves_the_declaration_unchecked():
    """R87 §2.4: silence is a fact about the source, not a disagreement -- but it is reported,
    so a build log tells a verified subject from an asserted one."""
    source = Stub(subject_id=None)
    _harvest(Spec(), source, Context(session_id="s001"), recipe_for("776259"))
    assert any("went unchecked" in n for n in source.notes)


def test_an_override_lets_the_recipe_win_and_says_why():
    """R87 §2.5. The refusal is what an override lifts, and the reason is what it leaves behind."""
    source = Stub(subject_id="776259")
    recipe = recipe_for("786867", **{"subject.subject_id": "the session names the wrong animal"})
    _harvest(Spec(), source, Context(session_id="s001"), recipe)
    assert any("the session names the wrong animal" in n for n in source.notes)


def test_an_override_that_changes_nothing_is_reported():
    """R87 §2.5: a stale override costs a line of the log, not a build."""
    source = Stub(subject_id="776259")
    recipe = recipe_for("776259", **{"subject.subject_id": "no longer needed"})
    _harvest(Spec(), source, Context(session_id="s001"), recipe)
    assert any("states the same value" in n for n in source.notes)


def test_a_number_and_a_string_naming_one_subject_agree():
    """R87 §2.1: `session.json` states 776259 as a number; comparing what was written would refuse."""
    source = Stub(subject_id=776259)
    _harvest(Spec(), source, Context(session_id="s001"), recipe_for("776259"))
    assert source.notes == []
