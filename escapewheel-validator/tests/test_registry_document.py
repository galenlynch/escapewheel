"""The invariants any registry document is held to, core's and an extension's alike (Part 09 §2)."""

import json
from pathlib import Path

import pytest

from escapewheel_validator.registry_document import SCHEMA, Finding, check_extension, structural

#: The reference registry, which every extension here is checked against.
CORE = json.loads((Path(__file__).resolve().parents[2] / "registry" / "logical_schemas.json").read_text())

#: The four extensions this repository ships, each of which must stay sound.
EXTENSIONS = sorted((Path(__file__).resolve().parents[2] / "registry" / "extensions").glob("*.json"))


def _document(**tables):
    """One extension document, with the fields every table owes filled in around what a test sets."""
    return {
        "$schema": json.loads(SCHEMA.read_text())["$id"],
        "registry_version": "0.1.0",
        "logical_standard_version": "0.1",
        "extension_id": "demo",
        "extends": "escapewheel-logical-v0.1",
        "tables": {
            name: {
                "primary_key": spec.get("primary_key", ["demo_id"]),
                "columns": spec.get("columns", []),
                "references": spec.get("references", []),
                "rules": spec.get("rules", []),
                **{k: v for k, v in spec.items() if k not in ("primary_key", "columns", "references", "rules")},
            }
            for name, spec in tables.items()
        },
    }


def _column(name, **overrides):
    """A column declaring everything Part 02 §6 requires, so a test varies one thing."""
    column = {"name": name, "type": "int32", "presence": "required", "role": "identifier",
              "identity": "assigned", "description": "A demonstration column."}
    column.update(overrides)
    if column["role"] != "identifier":
        column.pop("identity", None)
    return column


def _broken(findings):
    """The labels of the invariants these findings say were broken."""
    return {f.label for f in findings if not f.passed}


def test_the_reference_registry_satisfies_its_own_invariants():
    """Core is held to exactly what an extension is, which is the point of one implementation."""
    assert _broken(structural(CORE["tables"], CORE["tables"], is_core=True)) == set()


@pytest.mark.parametrize("path", EXTENSIONS, ids=lambda p: p.stem)
def test_every_shipped_extension_is_sound(path):
    """Nothing regenerates these, so they drift; this is what notices.

    They were caught before only because they sit beside `registry/check.py` in this repository,
    which is the whole reason the invariants moved somewhere an author can reach.
    """
    findings = check_extension(json.loads(path.read_text()), CORE)
    assert _broken(findings) == set(), [str(f) for f in findings if not f.passed]


def test_every_invariant_reports_whether_it_held():
    """A caller reports which checks ran, not only which failed, so each returns a finding either way."""
    findings = structural(CORE["tables"], CORE["tables"], is_core=True)
    assert len(findings) > 25, "the invariant list shrank unexpectedly"
    assert all(isinstance(f, Finding) for f in findings)
    assert all(f.passed for f in findings)


def test_a_reference_to_a_table_no_registry_holds_is_found():
    """Part 09 §2 makes the direction one-way: an extension reaches core's tables and its own."""
    document = _document(**{"demo.rows": {
        "columns": [_column("demo_id"), _column("ghost_id")],
        "references": [{"columns": ["ghost_id"], "resource": "demo.absent", "resource_columns": ["x"]}],
    }})
    assert "reference targets exist" in _broken(check_extension(document, CORE))


def test_a_reference_across_types_is_found():
    """Part 02 §7. A join between an int32 and a string returns nothing and reports nothing."""
    document = _document(**{"demo.rows": {
        "columns": [_column("demo_id"), _column("session_id", type="string")],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]}],
    }})
    assert "a reference relates columns of the same type" in _broken(check_extension(document, CORE))


def test_a_table_outside_its_own_namespace_is_found():
    """Part 09 §2 namespaces an extension's tables, so one naming core's would collide with it."""
    document = _document(**{"core.rows": {"columns": [_column("demo_id")]}})
    assert any("namespace" in label for label in _broken(check_extension(document, CORE)))


def test_a_column_type_outside_the_vocabulary_is_found():
    """R2 §4. A spelling outside it is a column no reader can be asked to decode."""
    document = _document(**{"demo.rows": {"columns": [_column("demo_id", type="uint8")]}})
    assert "every column type is in R2 §4's vocabulary" in _broken(check_extension(document, CORE))


def test_a_table_declaring_no_primary_key_is_found():
    """R7. A table declares a key or explicitly `null` with a reason, and `null` is not omission."""
    document = _document(**{"demo.rows": {"primary_key": None, "columns": [_column("demo_id")]}})
    assert "every table declares a primary key" in _broken(check_extension(document, CORE))


def test_a_sound_document_breaks_nothing():
    """The shape an author is aiming at, so the test says what one looks like."""
    document = _document(**{"demo.rows": {
        "primary_key": ["session_id", "demo_id"],
        "columns": [
            _column("session_id", description="The session these rows belong to."),
            _column("demo_id", identity="carried", description="The source's own number for a row."),
            # Part 02 §8.6: a table keyed by an identifier of its own carries somewhere for the
            # facts core does not model, or an author has nowhere to put them but a new column.
            _column("metadata", type="json_string", presence="optional", role="data",
                    description="Source facts this table does not model."),
        ],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]}],
    }})
    findings = check_extension(document, CORE)
    assert _broken(findings) == set(), [str(f) for f in findings if not f.passed]
