"""What the arbitration tables imply about each other, asserted rather than assumed.

`PREFERRED`, `SHARED`, `RECIPE_SUPPLIES` and each adapter's `PRODUCES` are four lists consulted in
one order by `recipe._resolve_ownership`, in another by `session`, and in a third by the
scaffolder. Nothing compared them, so an entry could stop arbitrating and say nothing: R108 §2.2
measured that class and R108 §3.4 struck one entry, leaving three.

These are the shape `registry/check.py` applies to `NAMING_EXCEPTIONS` — an exception is declared
with a reason and is checked to still be needed — turned on the writer's own tables.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from escapewheel_writer.recipe import PREFERRED, RECIPE_SUPPLIES, SHARED, produces
from escapewheel_writer.scripts.cli import KINDS
from escapewheel_writer.session import _KINDS


def _by_resource() -> dict[str, list[str]]:
    """Which adapters can produce each resource, over every kind a build accepts."""
    found: dict[str, list[str]] = {}
    for kind in _KINDS:
        for resource in produces(kind):
            found.setdefault(resource, []).append(kind)
    return found


@pytest.mark.parametrize("resource,winner", sorted(PREFERRED.items()))
def test_a_preference_arbitrates_something(resource, winner):
    """A preference names the winner among several producers, so there must be several.

    `_resolve_ownership` checks `SHARED` first and returns, so a preference for a shared resource
    is never read: three sat there unnoticed until this test.
    """
    producers = _by_resource().get(resource, [])
    assert resource not in SHARED, f"{resource} is SHARED, so its preference is never consulted"
    assert len(producers) > 1, f"{resource} is produced only by {producers}, so nothing is contested"
    assert winner in producers, f"{resource} prefers {winner}, which does not produce it"


@pytest.mark.parametrize("resource", sorted(SHARED))
def test_a_shared_resource_has_several_contributors(resource):
    """Sharing is for a resource several sources each supply part of (R98 §2.1)."""
    producers = _by_resource().get(resource, [])
    assert len(producers) > 1, f"{resource} is SHARED but only {producers} produces it"


def test_the_scaffolder_names_only_kinds_a_build_knows():
    """A draft and a build resolve alike only if they agree about what a kind is.

    `PREFERRED`'s docstring gives that as the reason it is held in `recipe` rather than in the
    scaffolder, and the two lists had drifted to 5 kinds against 10.
    """
    assert set(KINDS) <= set(_KINDS), f"scaffolder names {sorted(set(KINDS) - set(_KINDS))}"


def test_every_kind_the_scaffolder_offers_can_be_opened_alone():
    """`init` and `inspect` construct a source from a root and nothing else.

    `waveforms` sat in `KINDS` and `_open` turned it away, so the argument passed validation and
    the command then failed on the next line.
    """
    from escapewheel_writer.scripts import cli

    source = Path(cli.__file__).read_text()
    opener = next(n for n in ast.walk(ast.parse(source))
                  if isinstance(n, ast.FunctionDef) and n.name == "_open")
    opens = {n.comparators[0].value for n in ast.walk(opener)
             if isinstance(n, ast.Compare)
             and isinstance(n.comparators[0], ast.Constant)
             and isinstance(n.left, ast.Name) and n.left.id == "kind"}
    assert set(KINDS) == opens, f"KINDS is {sorted(KINDS)}, _open takes {sorted(opens)}"


def test_the_build_knows_every_kind_it_dispatches_on():
    """`_KINDS` is what an unknown kind is reported against, and it had gone stale by three."""
    from escapewheel_writer import session

    source = Path(session.__file__).read_text()
    builder = next(n for n in ast.walk(ast.parse(source))
                   if isinstance(n, ast.FunctionDef) and n.name == "_build_source")
    dispatched = {n.comparators[0].value for n in ast.walk(builder)
                  if isinstance(n, ast.Compare)
                  and isinstance(n.comparators[0], ast.Constant)
                  and isinstance(n.comparators[0].value, str)
                  and isinstance(n.left, ast.Attribute) and n.left.attr == "kind"}
    assert dispatched <= set(_KINDS), f"_build_source handles {sorted(dispatched - set(_KINDS))}"


@pytest.mark.parametrize("resource", RECIPE_SUPPLIES)
def test_a_recipe_supplied_resource_is_declared(resource):
    """The recipe supplies it, so it must be a resource the registry defines."""
    import json

    registry = json.loads(Path("../registry/logical_schemas.json").resolve().read_text()) \
        if Path("../registry/logical_schemas.json").exists() else None
    if registry is None:
        pytest.skip("registry not reachable from this working directory")
    assert resource in registry["tables"]
