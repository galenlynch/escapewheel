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

from escapewheel_writer.recipe import RECIPE_SUPPLIES, SHARED, preferences, produces
from escapewheel_writer.scripts.cli import KINDS
from escapewheel_writer.sources import ADAPTERS, discovered


def _by_resource() -> dict[str, list[str]]:
    """Which adapters can produce each resource, over every kind a build accepts.

    Registered kinds count, because a preference may name one: a build resolves ownership over
    everything it can reach, so a check reading only the built-in table would pass a preference
    that arbitrates nothing wherever the other producer ships elsewhere.
    """
    found: dict[str, list[str]] = {}
    for kind in {**ADAPTERS, **discovered()}:
        for resource in produces(kind):
            found.setdefault(resource, []).append(kind)
    return found


@pytest.mark.parametrize("resource,winner", sorted(preferences().items()))
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
    assert set(KINDS) <= set(ADAPTERS), f"scaffolder names {sorted(set(KINDS) - set(ADAPTERS))}"


def test_every_kind_the_scaffolder_offers_can_be_opened_alone():
    """`init` and `inspect` construct a source from a root and nothing else.

    `waveforms` sat in `KINDS` and `_open` turned it away, so the argument passed validation and
    the command then failed on the next line.
    """
    from escapewheel_writer.scripts import cli

    source = Path(cli.__file__).read_text()
    opener = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == "_open")
    opens = {
        n.comparators[0].value
        for n in ast.walk(opener)
        if isinstance(n, ast.Compare)
        and isinstance(n.comparators[0], ast.Constant)
        and isinstance(n.left, ast.Name)
        and n.left.id == "kind"
    }
    assert set(KINDS) == opens, f"KINDS is {sorted(KINDS)}, _open takes {sorted(opens)}"


def test_the_build_dispatches_on_no_kind():
    """Every source is constructed from, and asked for its rows with, what it declares.

    Both used to branch per kind: `_build_source` passed a different set of extras for each, and
    the call side passed three adapters values they never declared -- a mapping of rates, a
    closure, and eight keyword arguments -- which Part 03 §11.2 forbids a build to require and
    which no protocol could carry. A branch reappearing in either is a value that belongs in the
    adapter's `NEEDS`.

    `_harvest` is not in the list: it reads what a source produced rather than supplying it, and
    what replaces its per-kind reach is a delivery rather than a declaration.
    """
    from escapewheel_writer import session

    source = Path(session.__file__).read_text()
    checked = {"_build_source", "_composed", "_add_records"}
    functions = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name in checked]
    assert {n.name for n in functions} == checked
    for function in functions:
        dispatched = {
            n.comparators[0].value
            for n in ast.walk(function)
            if isinstance(n, ast.Compare)
            and isinstance(n.comparators[0], ast.Constant)
            and isinstance(n.comparators[0].value, str)
            and isinstance(n.left, ast.Attribute)
            and n.left.attr == "kind"
        }
        assert dispatched == set(), f"{function.name} branches on {sorted(dispatched)}"


@pytest.mark.parametrize("resource", RECIPE_SUPPLIES)
def test_a_recipe_supplied_resource_is_declared(resource):
    """The recipe supplies it, so it must be a resource the registry defines."""
    import json

    registry = (
        json.loads(Path("../registry/logical_schemas.json").resolve().read_text())
        if Path("../registry/logical_schemas.json").exists()
        else None
    )
    if registry is None:
        pytest.skip("registry not reachable from this working directory")
    assert resource in registry["tables"]


#: Rows where an adapter sets a `*_name` to something other than the string its `*_id` is minted
#: from, each with why it is still here. R85 wants a name unique within its packet and the
#: numbering fills one from the identifier where a row leaves it unset, so an override that drops
#: the prefix is a name that collides once two sessions are merged under different ones — inert
#: while every packet is built at prefix "", which is why these are recorded rather than fixed.
NAME_EXCEPTIONS = {
    ("nwb.py", "device_name"): "drops the recipe's prefix, which the identifier carries",
    ("nwb.py", "probe_name"): "drops the recipe's prefix, which the identifier carries",
    ("nwb.py", "event_stream_name"): "drops the recipe's prefix, which the identifier carries",
}


def test_a_name_records_what_its_identifier_stands_for():
    """R53 §2.5: a `*_name` is the string the number was minted from, and nothing else.

    Read statically rather than by running the adapters, because what is wrong is visible in the
    row an adapter writes: `core.clocks` had a human label in `clock_name` and nothing could
    resolve a recipe's spelling back to a clock, and `core.array_assets` had a source's own label
    in `array_asset_name` and nothing could join a row to its manifest entry.
    """
    import json

    registry = json.loads((Path(__file__).resolve().parents[2] / "registry/logical_schemas.json").read_text())
    pairs = {
        column["name"]: column["name"].removesuffix("_name") + "_id"
        for table in registry["tables"].values()
        for column in table["columns"]
        if column["name"].endswith("_name")
    }
    sources = Path(__file__).resolve().parents[1] / "src/escapewheel_writer/sources"
    found = []
    for path in sorted(sources.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Dict):
                continue
            keys = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
            for name, identity in pairs.items():
                if name not in keys or identity not in keys:
                    continue
                if ast.dump(keys[name]) == ast.dump(keys[identity]):
                    continue
                if (path.name, name) in NAME_EXCEPTIONS:
                    continue
                found.append(
                    f"{path.name}:{keys[name].lineno} {name} = {ast.unparse(keys[name])} "
                    f"where {identity} = {ast.unparse(keys[identity])}"
                )
    assert found == [], "a name column holds something other than what its identifier stands for:\n" + "\n".join(found)


def test_every_name_exception_still_names_a_row_that_sets_one():
    """An exception that stops matching is one the code has outgrown, and it must not go stale."""
    sources = Path(__file__).resolve().parents[1] / "src/escapewheel_writer/sources"
    for (filename, column), reason in sorted(NAME_EXCEPTIONS.items()):
        text = (sources / filename).read_text()
        assert f'"{column}"' in text, f"{filename} no longer sets {column}; strike the exception ({reason})"
