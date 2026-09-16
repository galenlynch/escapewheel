"""What an adapter declares, as a document a build reads instead of importing it.

A build reads `produces`, `states`, `needs`, `accepts` and `consumes` before it opens any source, and
for a class it reads them by importing the adapter -- which Part 03 §11.5 forbids requiring. So an
adapter a build cannot import publishes the same five facts as JSON, and the two forms are one
declaration: a build treats a document and an importable class alike and prefers neither.

The document is **generated** here rather than maintained, because every field is read off the class
with no judgement in it. What it does not carry is anything about the machine -- the command, the
root and the options stay in the recipe, since which interpreter is installed where is the recipe
author's fact and the resources an adapter can supply is not.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

#: Part 03 §11.1's group for `escapewheel-portable-v0.1`: the ways rows cross a process boundary.
#: A build supports every one of them, so no negotiation can fail; an adapter released
#: independently of a build supports at least one.
PROTOCOLS = ("files-v0.1", "stream-v0.1", "flight-v0.1")

#: Terms a protocol requires rather than an adapter declares (Part 03 §11.2). A build supplies one
#: because the adapter speaks that protocol and never because it asked, so an adapter declaring one
#: is refused as any undeclarable name is.
PROTOCOL_TERMS = {
    "files-v0.1": ("delivery_root",),
    "stream-v0.1": (),
    "flight-v0.1": ("socket",),
}

#: Where a report travels as a file, and so where `report_path` is supplied (Part 09 §5.8). Under
#: `flight-v0.1` the connection carries it and no file outlives the run.
REPORT_AS_FILE = ("files-v0.1", "stream-v0.1")

#: The recipe block each `states` entry resolves through, to the core table whose columns it names.
BLOCKS = {"session": "core.sessions", "subject": "core.subjects"}


def schema() -> dict[str, Any]:
    """Load the bundled JSON Schema for a declaration document (Part 03 §11.5).

    Vendored from `registry/` the way the manifest's schema is, because a wheel cannot read a file
    from another repository.
    """
    from importlib import resources

    text = resources.files(__package__).joinpath("schemas/adapter.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


def of(adapter: Any, kind: str, protocol: str) -> dict[str, Any]:
    """Return the document for one adapter class, generated from what it already declares.

    Parameters
    ----------
    adapter : type
        The adapter class, carrying `PRODUCES`, `STATES`, `NEEDS`, `ACCEPTS` and `CONSUMES`.
    kind : str
        The name a recipe's source entry uses for it.
    protocol : str
        The protocol this adapter's rows will cross by.

    Returns
    -------
    dict
        The document, ready to write. `states` is the field names alone: which attribute holds
        each is the implementation's business and no other implementation can use it.
    """
    return {
        "$schema": schema()["$id"],
        "kind": kind,
        "protocol": protocol,
        "produces": sorted(getattr(adapter, "PRODUCES", ())),
        "states": sorted(getattr(adapter, "STATES", {})),
        "needs": list(getattr(adapter, "NEEDS", ())),
        "accepts": list(getattr(adapter, "ACCEPTS", ())),
        "consumes": list(getattr(adapter, "CONSUMES", ())),
    }


def load(path: str | Path) -> dict[str, Any]:
    """Read a declaration document and check its shape against the published schema.

    Raises
    ------
    ValueError
        If the file is absent, is not JSON, or does not satisfy `registry/adapter.schema.json`.
        Shape only: what the declaration *says* is checked against the registry and the recipe by
        :func:`refusals`, which needs both and neither of which a schema can see.
    """
    where = Path(path)
    try:
        document = json.loads(where.read_text())
    except OSError as exc:
        raise ValueError(f"{where}: no adapter declaration to read ({exc.strerror})") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"{where}: not JSON ({exc})") from None
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - jsonschema is a dependency of the validator
        return dict(document)
    problems = sorted(jsonschema.Draft202012Validator(schema()).iter_errors(document), key=lambda e: list(e.path))
    if problems:
        first = problems[0]
        raise ValueError(f"{where}: {'/'.join(str(p) for p in first.path) or 'document'}: {first.message}")
    return dict(document)


def refusals(
    document: Mapping[str, Any],
    *,
    tables: Mapping[str, Any],
    options: Collection[str],
    terms: Collection[str],
) -> list[str]:
    """Return what a build refuses this declaration for, reading it, the registry and the recipe.

    Part 03 §11.5's four checks, each firing on its own and naming what is wrong. None of them
    needs the adapter opened or imported, which is the point: a declaration is checked against
    what a build holds and never against the thing it describes.

    Parameters
    ----------
    document : Mapping
        The declaration, already shape-checked by :func:`load`.
    tables : Mapping
        The loaded registries' tables, by resource ID, each carrying its columns.
    options : collection of str
        The option names the recipe's entry for this source sets.
    terms : collection of str
        Part 03 §11.2's vocabulary, which a declared name resolves against first.
    """
    found = []
    if (protocol := document.get("protocol")) not in PROTOCOLS:
        found.append(f"declares protocol {protocol!r}, which is in no group this profile names")
    for resource in document.get("produces", ()):
        if resource not in tables:
            found.append(f"produces {resource}, which no loaded registry declares")
    for field in document.get("states", ()):
        block, _, column = field.partition(".")
        if (resource := BLOCKS.get(block)) is None:
            found.append(f"states {field}, whose block is not one the recipe carries")
        elif resource not in tables:
            found.append(f"states {field}, whose block resolves to {resource}, which no registry declares")
        elif column not in {c["name"] for c in tables[resource].get("columns", ())}:
            found.append(f"states {field}, which is no column of {resource}")
    for name in document.get("needs", ()):
        if name in _protocol_terms():
            found.append(f"needs {name}, which a protocol supplies rather than an adapter declaring it")
        elif name not in terms and name not in options:
            found.append(f"needs {name}, neither a term nor an option this entry sets")
    # An accepted option is one the recipe may leave unset, so it is never checked for presence --
    # only that it is an option at all, and that it is not already mandatory (Part 03 §11.5).
    declared_needs = set(document.get("needs", ()))
    for name in document.get("accepts", ()):
        if name in terms or name in _protocol_terms():
            found.append(f"accepts {name}, which is a term a build fills rather than an option a recipe sets")
        elif name in declared_needs:
            found.append(f"accepts {name}, which it also needs, so it is both optional and required")
    return found


def _protocol_terms() -> frozenset[str]:
    """Every term a protocol supplies, which is what an adapter may not declare."""
    return frozenset(name for names in PROTOCOL_TERMS.values() for name in names) | {"report_path"}


__all__ = ["BLOCKS", "PROTOCOLS", "PROTOCOL_TERMS", "REPORT_AS_FILE", "load", "of", "refusals", "schema"]
