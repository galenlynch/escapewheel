"""The session's bounds come from the declared stream windows, not from the recipe."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from escapewheel_writer.session import Context, _declared_start, _harvest

BEGAN = datetime(2025, 4, 10, 0, 25, 12, tzinfo=UTC)
ENDED = datetime(2025, 4, 10, 2, 38, 44, tzinfo=UTC)


class Spec:
    kind = "session"


class Stub:
    """A session source with one declared extent."""

    def __init__(self, began=BEGAN, ended=ENDED):
        self.extent_value = (began, ended)
        self.notes: list[str] = []

    def extent(self):
        return self.extent_value


def recipe_with(**session):
    """Only `.session` is read here, so a whole Recipe would be scaffolding."""
    return SimpleNamespace(session={"session_id": "s001", **session})


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
