"""Every note these adapters write carries a code."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from escapewheel_writer.notes import codes

import escapewheel_aind
from escapewheel_aind.notes import AindNote
from tests.test_adapter_columns import BUILDERS, emitted

NOTING = sorted(Path(escapewheel_aind.__file__).parent.glob("*.py"))


def _uncoded(path: Path) -> list[str]:
    """Where a module appends a note that is neither a `Note` nor a name bound to one."""
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append"):
            continue
        target = node.func.value
        if getattr(target, "attr", getattr(target, "id", None)) != "notes":
            continue
        (written,) = node.args
        if not (isinstance(written, ast.Name) or getattr(getattr(written, "func", None), "id", None) == "Note"):
            found.append(f"{path.name}:{node.lineno}")
    return found


def test_a_code_is_its_name_in_lower_case():
    for member in AindNote:
        assert member.value == member.name.lower(), member


@pytest.mark.parametrize("path", NOTING, ids=lambda path: path.stem)
def test_every_note_this_package_writes_carries_a_code(path):
    assert _uncoded(path) == []


@pytest.mark.parametrize("kind", sorted(BUILDERS))
def test_every_note_an_adapter_wrote_carries_a_code(kind, tmp_path, monkeypatch):
    source = BUILDERS[kind](tmp_path, monkeypatch)
    emitted(source)
    assert None not in codes(source.notes), [note for note in source.notes if getattr(note, "code", None) is None]
