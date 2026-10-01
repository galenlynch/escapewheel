"""A note is text a person reads and a code a caller compares."""

from __future__ import annotations

import ast
import copy
import json
import pickle
from pathlib import Path

import pytest

import escapewheel_writer
from escapewheel_writer.notes import Note, NoteCode, coded, codes
from tests.test_adapter_columns import BUILDERS, emitted

PACKAGE = Path(escapewheel_writer.__file__).parent

#: The modules whose notes reach a build's report: every adapter, the build and a delivery.
NOTING = [*sorted((PACKAGE / "sources").glob("*.py")), PACKAGE / "session.py", PACKAGE / "delivery.py"]


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


def test_a_note_is_its_text():
    """So a list of notes prints, joins and serializes as text."""
    note = Note("probeA: skipped", NoteCode.STREAM_NOT_ALIGNED)
    assert note == "probeA: skipped"
    assert json.dumps([note]) == '["probeA: skipped"]'
    notes = [note, "plain"]
    assert "; ".join(notes) == "probeA: skipped; plain"


@pytest.mark.parametrize("copied", [copy.copy, copy.deepcopy, lambda note: pickle.loads(pickle.dumps(note))])
def test_a_copied_note_keeps_its_code(copied):
    assert copied(Note("probeA: skipped", NoteCode.STREAM_NOT_ALIGNED)).code is NoteCode.STREAM_NOT_ALIGNED


def test_plain_text_is_a_note_with_no_code():
    """An adapter released separately appends strings, and they stay valid."""
    notes = ["plain", Note("probeA: skipped", NoteCode.STREAM_NOT_ALIGNED), Note("uncoded")]
    assert codes(notes) == [None, NoteCode.STREAM_NOT_ALIGNED, None]
    assert coded(notes, NoteCode.STREAM_NOT_ALIGNED) == ["probeA: skipped"]


def test_a_code_is_its_name_in_lower_case():
    for member in NoteCode:
        assert member.value == member.name.lower(), member


@pytest.mark.parametrize("path", NOTING, ids=lambda path: path.stem)
def test_every_note_this_package_writes_carries_a_code(path):
    assert _uncoded(path) == []


@pytest.mark.parametrize("kind", sorted(BUILDERS))
def test_every_note_a_built_in_adapter_wrote_carries_a_code(kind, tmp_path):
    source = BUILDERS[kind](tmp_path)
    emitted(source)
    assert None not in codes(source.notes), [note for note in source.notes if getattr(note, "code", None) is None]
