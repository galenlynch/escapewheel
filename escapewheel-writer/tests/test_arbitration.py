"""What the ownership declarations imply about each other, asserted rather than assumed.

Each adapter's `PRODUCES` and `CONTRIBUTES` and the writer's `RECIPE_SUPPLIES` are consulted in one
order by `recipe._resolve_ownership`, in another by `session`, and in a third by the scaffolder, so
an entry could stop meaning anything and say nothing. These are the shape `spec/tools/conventions.py`
applies to `NAMING_EXCEPTIONS` -- a declaration is checked to still be needed -- turned on the
adapters' own.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from escapewheel_writer import recipe
from escapewheel_writer.recipe import RECIPE_SUPPLIES, contributes, produces
from escapewheel_writer.scripts.cli import KINDS
from escapewheel_writer.sources import ADAPTERS, discovered

#: Every kind a build accepts. Registered kinds count, because a build resolves ownership over
#: everything it can reach, and a check reading only the built-in table would pass a declaration
#: that another distribution's adapter contradicts.
EVERY_KIND = sorted({**ADAPTERS, **discovered()})


def _by_resource() -> dict[str, list[str]]:
    """Which adapters can produce each resource, over every kind a build accepts."""
    found: dict[str, list[str]] = {}
    for kind in EVERY_KIND:
        for resource in produces(kind):
            found.setdefault(resource, []).append(kind)
    return found


@pytest.mark.parametrize("kind", EVERY_KIND)
def test_an_adapter_contributes_only_what_it_produces(kind):
    """Part 12 §7: a resource supplied in part is still one the adapter declares it can supply."""
    assert contributes(kind) <= produces(kind), f"{kind} contributes {sorted(contributes(kind) - produces(kind))}"


@pytest.mark.parametrize("resource", sorted({r for kind in EVERY_KIND for r in contributes(kind)}))
def test_a_partly_supplied_resource_is_partly_supplied_by_every_producer(resource):
    """Sharing is for a resource several sources each supply part of (Part 05 §3.3).

    One producer contributing and another owning by default is a recipe refused for a resource
    "owned by one source but also supplied by another", which no author asked for.
    """
    producers = _by_resource()[resource]
    assert len(producers) > 1, f"{resource} is contributed but only {producers} produces it"
    owning = [kind for kind in producers if resource not in contributes(kind)]
    assert owning == [], f"{resource} is contributed by some producers and owned by default by {owning}"


def test_the_writer_holds_no_preference_of_its_own():
    """Part 05 §3.3: a build applies the recipe's preferences and holds none of its own."""
    for name in ("PREFERRED", "PREFERENCE_GROUP", "SHARED", "preferences", "arbitrated"):
        assert not hasattr(recipe, name), f"recipe.{name} is a winner no recipe can see"
    sources = Path(recipe.__file__).parent
    for path in sorted(sources.rglob("*.py")):
        assert "escapewheel.preferences" not in path.read_text(), f"{path.name} reads a registered preference"


def test_the_scaffolder_names_only_kinds_a_build_knows():
    """A draft and a build resolve alike only if they agree about what a kind is."""
    assert set(KINDS) <= set(ADAPTERS), f"scaffolder names {sorted(set(KINDS) - set(ADAPTERS))}"


def test_every_kind_the_scaffolder_offers_can_be_opened_alone():
    """`init` and `inspect` construct a source from a root and nothing else.

    `waveforms` sat in `KINDS` and `open_for_inspection` turned it away, so the argument passed validation and
    the command then failed on the next line.
    """
    from escapewheel_writer.scripts import cli

    source = Path(cli.__file__).read_text()
    opener = next(
        n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == "open_for_inspection"
    )
    opens = {
        n.comparators[0].value
        for n in ast.walk(opener)
        if isinstance(n, ast.Compare)
        and isinstance(n.comparators[0], ast.Constant)
        and isinstance(n.left, ast.Name)
        and n.left.id == "kind"
    }
    assert set(KINDS) == opens, f"KINDS is {sorted(KINDS)}, open_for_inspection takes {sorted(opens)}"


def test_the_build_dispatches_on_no_kind():
    """Every source is constructed from, and asked for its rows with, what it declares.

    Both used to branch per kind: `build_source` passed a different set of extras for each, and
    the call side passed three adapters values they never declared -- a mapping of rates, a
    closure, and eight keyword arguments -- which Part 12 §4 forbids a build to require and
    which no protocol could carry. A branch reappearing in either is a value that belongs in the
    adapter's `NEEDS`.

    `harvest` is not in the list: it reads what a source produced rather than supplying it, and
    what replaces its per-kind reach is a delivery rather than a declaration.
    """
    from escapewheel_writer import session, sourcing

    checked = {"build_source", "composed", "_add_records"}
    functions = [
        n
        for module in (session, sourcing)
        for n in ast.walk(ast.parse(Path(module.__file__).read_text()))
        if isinstance(n, ast.FunctionDef) and n.name in checked
    ]
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

    registry = json.loads((Path(__file__).resolve().parents[2] / "spec/artifacts/logical_schemas.json").read_text())
    assert resource in registry["resources"]


def test_a_name_records_what_its_identifier_stands_for():
    """R53 §2.5: a `*_name` is the string the number was minted from, and nothing else.

    No exception: R85 wants a name unique within its packet, and one that drops the recipe's prefix
    its identifier carries collides once two sessions share a packet under different prefixes.

    Read statically rather than by running the adapters, because what is wrong is visible in the
    row an adapter writes: `core.clocks` had a human label in `clock_name` and nothing could
    resolve a recipe's spelling back to a clock, and `core.array_assets` had a source's own label
    in `array_asset_name` and nothing could join a row to its manifest entry.
    """
    import json

    registry = json.loads((Path(__file__).resolve().parents[2] / "spec/artifacts/logical_schemas.json").read_text())
    pairs = {
        column["name"]: column["name"].removesuffix("_name") + "_id"
        for declaration in registry["resources"].values()
        if declaration["kind"] == "table"
        for table in [declaration["table"]]
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
                found.append(
                    f"{path.name}:{keys[name].lineno} {name} = {ast.unparse(keys[name])} "
                    f"where {identity} = {ast.unparse(keys[identity])}"
                )
    assert found == [], "a name column holds something other than what its identifier stands for:\n" + "\n".join(found)
