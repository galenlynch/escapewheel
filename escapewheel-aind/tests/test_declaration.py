"""What these adapters declare about themselves, checked as the writer checks its own.

`escapewheel-writer` sweeps its built-in table for these properties, so a kind leaving that table
leaves the sweep with it. The checks travel with the kinds rather than narrowing silently, which is
the whole cost of registering a source instead of shipping it: nothing upstream can see these two.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from escapewheel_writer import declaration
from escapewheel_writer.recipe import TERMS, Recipe
from escapewheel_writer.sources import discovered

#: The kinds this distribution registers, read back through the same discovery a build uses rather
#: than named here, so a kind added to `pyproject.toml` is swept without editing this file.
KINDS = {name: adapter for name, adapter in discovered().items() if adapter.__module__.startswith("escapewheel_aind")}


def test_this_distribution_registers_the_kinds_it_ships():
    """A guard on the sweep below: an empty discovery would make every test here vacuously pass."""
    assert set(KINDS) == {"session", "video", "aind_nwb"}


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_every_registered_adapter_generates_a_valid_document(kind):
    """Generated rather than maintained (Part 03 §11.5), so this is what an author starts from."""
    jsonschema = pytest.importorskip("jsonschema")
    document = declaration.of(KINDS[kind], kind, "stream-v0.1")
    assert not list(jsonschema.Draft202012Validator(declaration.schema()).iter_errors(document))
    assert document["kind"] == kind


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_every_option_an_adapter_reads_is_declared(kind):
    """The declared list is checked against the constructor, so it cannot go stale.

    A parameter holding a default is an option a recipe may set, and one a recipe may set and no
    declaration names is refused (Part 03 §11.2) -- so an option added here without being declared
    would refuse every recipe setting it. `store` is the exception: a handle a recipe cannot
    carry, supplied where the class accepts one rather than declared (Part 03 §11.2).
    """
    adapter = KINDS[kind]
    parameters = list(inspect.signature(adapter.__init__).parameters.values())[1:]
    optional = {
        p.name
        for p in parameters
        if p.default is not inspect.Parameter.empty
        and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
        and p.name not in adapter.NEEDS
        and p.name not in TERMS
        and p.name != "store"
    }
    assert optional == set(getattr(adapter, "ACCEPTS", ()))


def test_ownership_from_the_documents_is_ownership_from_the_classes():
    """The two forms are one declaration, so what a build settles from them cannot differ."""
    from_document = {
        resource: kind
        for kind in sorted(KINDS)
        for resource in declaration.of(KINDS[kind], kind, "stream-v0.1")["produces"]
    }
    from_class = {resource: kind for kind in sorted(KINDS) for resource in sorted(KINDS[kind].PRODUCES)}
    assert from_document == from_class


#: A session whose acquisition metadata and NWB both describe the subject: the contest a recipe
#: settles for these kinds, since `session` and `aind_nwb` or `nwb` each produce `core.subjects`.
CONTESTED = """
[packet]
id = "p"

[session]
session_id = "s"

[[source]]
kind = "session"
root = "."
in_process = true

[[source]]
kind = "nwb"
root = "."
zone = "UTC"
"""

#: `subject.json` is the record `general/subject` projects, carrying a `background_strain` key the
#: projection lacks, which is the reason a recipe gives for preferring it.
PREFER_SESSION = """
[preference."core.subjects"]
source = "session"
reason = "subject.json is the record the NWB's subject group projects"
"""


def _checked(tmp_path, text):
    registry = json.loads((Path(__file__).parents[2] / "registry/logical_schemas.json").read_text())
    path = tmp_path / "recipe.toml"
    path.write_text(text)
    recipe = Recipe.load(path)
    return recipe, [p.message for p in recipe.check(registry) if p.level == "error"]


def test_a_subject_both_sources_describe_is_refused_until_the_recipe_prefers_one(tmp_path):
    """No distribution holds a preference for a build (Part 05 §3.3), so the recipe must name one."""
    _, errors = _checked(tmp_path, CONTESTED)
    assert any(e.startswith("core.subjects is owned by 2 sources (nwb, session)") for e in errors), errors


def test_a_recipe_preferring_the_session_source_gives_it_the_subject(tmp_path):
    recipe, errors = _checked(tmp_path, CONTESTED + PREFER_SESSION)
    owners = {spec.kind: set(spec.owns) for spec in recipe.sources}
    assert "core.subjects" in owners["session"]
    assert "core.subjects" not in owners["nwb"]
    assert not [e for e in errors if "core.subjects" in e], errors
