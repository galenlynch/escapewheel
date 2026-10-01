"""Each resource-ID constant names a declared resource, and the package spells an ID nowhere else."""

import ast
import json
from pathlib import Path

import pytest

from escapewheel_reader import resource_ids

SOURCE = Path(resource_ids.__file__).parent
REGISTRY = Path(__file__).resolve().parents[2] / "spec" / "artifacts" / "logical_schemas.json"
CONSTANTS = {name: getattr(resource_ids, name) for name in resource_ids.__all__}


def test_all_lists_every_constant_once():
    defined = {name for name, value in vars(resource_ids).items() if name.isupper() and isinstance(value, str)}
    assert sorted(defined) == sorted(resource_ids.__all__)


def test_a_constant_is_named_for_its_id():
    """The name follows from the ID, so no two constants share an ID and neither drifts from the other."""
    for name, value in CONSTANTS.items():
        assert name == value.replace(".", "_").upper()


@pytest.mark.skipif(not REGISTRY.is_file(), reason="the specification's tree is not beside this package")
def test_every_constant_names_a_resource_the_core_registry_declares():
    """A resource the registry renames or drops fails here before it fails in a packet."""
    declared = json.loads(REGISTRY.read_text())["resources"]
    assert sorted(value for value in CONSTANTS.values() if value not in declared) == []


def test_no_other_module_spells_a_named_id():
    """A string literal that is exactly a named ID is the constant's job."""
    named = set(CONSTANTS.values())
    spelled = [
        f"{path.relative_to(SOURCE)}:{node.lineno}: {node.value}"
        for path in sorted(SOURCE.rglob("*.py"))
        if path != Path(resource_ids.__file__)
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Constant) and node.value in named
    ]
    assert spelled == []
