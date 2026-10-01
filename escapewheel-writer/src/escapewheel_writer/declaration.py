"""An adapter's declarations as a document a build reads without importing the adapter (Part 12 §7).

- :func:`of` -- the document for one adapter class, generated from what the class declares.
- :func:`load` -- a declaration document read from a file, with its shape checked.
- :func:`shape_problems` -- where a declaration fails the published schema.
- :func:`refusals` -- the reasons a build refuses a declaration, given the registry and the recipe.
- :func:`schema` -- the bundled JSON Schema for a declaration document.
- :data:`PROTOCOLS`, :data:`FILES`, :data:`STREAM`, :data:`FLIGHT` -- Part 12 §3's protocol group
  and its members.
- :data:`PROTOCOL_TERMS`, :data:`REPORT_AS_FILE` -- the terms each protocol requires, and the
  protocols whose report travels as a file.
- :data:`SOURCE_CACHE` -- the one term a declaration names in `accepts`.

A class and a document declaring the same facts are one declaration: a build checks a class as
the document the class would generate, and prefers neither.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import RecipeFault

#: Part 12 §3's group for `escapewheel-portable-v0.1`: the ways rows cross a process boundary.
#: A build supports every one of them, so no negotiation can fail; an adapter released
#: independently of a build declares at least one, as a class's `PROTOCOLS` or a document's
#: `protocols`.
FILES = "files-v0.1"
STREAM = "stream-v0.1"
FLIGHT = "flight-v0.1"
PROTOCOLS = (FILES, STREAM, FLIGHT)

#: Terms a protocol requires rather than an adapter declares (Part 12 §4). A build supplies one
#: because it reaches the adapter by that protocol and never because the adapter asked, so an
#: adapter declaring one is refused as any undeclarable name is.
PROTOCOL_TERMS = {
    FILES: ("delivery_root",),
    STREAM: (),
    FLIGHT: ("socket",),
}

#: The one term a declaration names in `accepts`, since a build supplies it only where it has a
#: source-cache location, and never in `needs` (Part 12 §4).
SOURCE_CACHE = "source_cache"

#: Where a report travels as a file, and so where `report_path` is supplied (Part 12 §9). Under
#: `flight-v0.1` the connection carries it and no file outlives the run.
REPORT_AS_FILE = (FILES, STREAM)

#: The recipe block each `states` entry resolves through, to the core table whose columns it names.
BLOCKS = {"session": "core.sessions", "subject": "core.subjects"}


def schema() -> dict[str, Any]:
    """Load the bundled JSON Schema for a declaration document (Part 12 §7).

    Copied from the specification's tree the way the manifest's schema is, because a wheel cannot
    read a file outside its package.
    """
    from importlib import resources

    text = resources.files(__package__).joinpath("schemas/adapter.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


def of(adapter: Any, kind: str, protocols: Sequence[str] = ()) -> dict[str, Any]:
    """Return the document for one adapter class, generated from what it already declares.

    Parameters
    ----------
    adapter : type
        The adapter class, carrying `PROTOCOLS`, `PRODUCES`, `CONTRIBUTES`, `STATES`, `NEEDS`,
        `ACCEPTS` and `CONSUMES`.
    kind : str
        The name a recipe's source entry uses for it.
    protocols : sequence of str, optional
        What to declare for a class stating no `PROTOCOLS`, as an adapter a build ships does not
        (Part 12 §3). A class stating its own keeps them.

    Returns
    -------
    dict
        The document, ready to write. `states` is the field names alone: which attribute holds
        each is the implementation's business and no other implementation can use it. Without
        `protocols` where neither states any, which only a shipped adapter's class may be.
    """
    stated = list(getattr(adapter, "PROTOCOLS", ()) or protocols)
    return {
        "$schema": schema()["$id"],
        "kind": kind,
        **({"protocols": stated} if stated else {}),
        "produces": sorted(getattr(adapter, "PRODUCES", ())),
        "contributes": sorted(getattr(adapter, "CONTRIBUTES", ())),
        "states": sorted(getattr(adapter, "STATES", {})),
        "needs": list(getattr(adapter, "NEEDS", ())),
        "accepts": list(getattr(adapter, "ACCEPTS", ())),
        "consumes": list(getattr(adapter, "CONSUMES", ())),
    }


def shape_problems(document: Any, *, shipped: bool = False) -> list[str]:
    """Where a declaration fails the schema Part 12 §7 incorporates, each as `where: message`.

    One check for a document and for the document a class would generate, so the two are refused
    for the same defects. `shipped` lifts the one difference: an adapter a build ships may declare
    no protocol (Part 12 §3).
    """
    import jsonschema

    shape = schema()
    if shipped:
        shape = {**shape, "required": [member for member in shape["required"] if member != "protocols"]}
    return [
        f"{'/'.join(str(p) for p in error.absolute_path) or 'declaration'}: {error.message}"
        for error in sorted(
            jsonschema.Draft202012Validator(shape).iter_errors(document),
            key=lambda e: [str(p) for p in e.absolute_path],
        )
    ]


def load(path: str | Path) -> dict[str, Any]:
    """Read a declaration document and check its shape against the published schema.

    Raises
    ------
    ValueError
        If the file is absent, is not JSON, or does not satisfy `adapter.schema.json`,
        naming every place it fails. Shape only: what the declaration *says* is checked against
        the registry and the recipe by :func:`refusals`, which needs both.
    """
    where = Path(path)
    try:
        document = json.loads(where.read_text())
    except OSError as exc:
        raise ValueError(f"{where}: no adapter declaration to read ({exc.strerror})") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"{where}: not JSON ({exc})") from None
    if problems := shape_problems(document):
        raise ValueError(f"{where}: " + "; ".join(problems))
    return dict(document)


def refusals(
    document: Mapping[str, Any],
    *,
    tables: Mapping[str, Any],
    options: Collection[str],
    terms: Collection[str],
    payloads: Collection[str] = (),
) -> list[tuple[RecipeFault, str]]:
    """Return what a build refuses this declaration for, reading it, the registry and the recipe.

    Part 12 §7's checks, each firing on its own and naming what is wrong. None of them
    needs the adapter opened or imported, which is the point: a declaration is checked against
    what a build holds and never against the thing it describes.

    Parameters
    ----------
    document : Mapping
        The declaration, already shape-checked by :func:`shape_problems`.
    tables : Mapping
        The loaded registries' tables, by resource ID, each carrying its columns.
    options : collection of str
        The option names the recipe's entry for this source sets.
    terms : collection of str
        Part 12 §4's vocabulary, which a declared name resolves against first.
    payloads : collection of str
        The loaded registries' opaque singleton declarations, which an adapter may produce as a
        payload rather than as rows (Part 12 §5).

    Returns
    -------
    list of (RecipeFault, str)
        Each refusal as its code and the message that reports it.
    """
    found = [
        (RecipeFault.PROTOCOL_UNKNOWN, f"declares protocol {protocol!r}, which is in no group this profile names")
        for protocol in document.get("protocols", ())
        if protocol not in PROTOCOLS
    ]
    for resource in document.get("produces", ()):
        if resource not in tables and resource not in payloads:
            found.append((RecipeFault.PRODUCES_UNDECLARED, f"produces {resource}, which no loaded registry declares"))
    produced = set(document.get("produces", ()))
    found += [
        (RecipeFault.CONTRIBUTES_UNPRODUCED, f"contributes {resource}, which its produces does not name")
        for resource in document.get("contributes", ())
        if resource not in produced
    ]
    for field in document.get("states", ()):
        block, _, column = field.partition(".")
        unresolved = None
        if (resource := BLOCKS.get(block)) is None:
            unresolved = f"states {field}, whose block is not one the recipe carries"
        elif resource not in tables:
            unresolved = f"states {field}, whose block resolves to {resource}, which no registry declares"
        elif column not in {c["name"] for c in tables[resource].get("columns", ())}:
            unresolved = f"states {field}, which is no column of {resource}"
        if unresolved is not None:
            found.append((RecipeFault.STATES_UNRESOLVED, unresolved))
    return found + _name_refusals(document, options=options, terms=terms)


def _name_refusals(
    document: Mapping[str, Any], *, options: Collection[str], terms: Collection[str]
) -> list[tuple[RecipeFault, str]]:
    """Return what `needs` and `accepts` name that Part 12 §4 does not let them."""
    found: list[tuple[RecipeFault, str]] = []
    for name in document.get("needs", ()):
        if name == SOURCE_CACHE:
            found.append(
                (
                    RecipeFault.NEEDS_SOURCE_CACHE,
                    f"needs {name}, which a build supplies only where it has a location, so it is accepted",
                )
            )
        elif name in _protocol_terms():
            found.append(
                (
                    RecipeFault.NEEDS_PROTOCOL_TERM,
                    f"needs {name}, which a protocol supplies rather than an adapter declaring it",
                )
            )
        elif name not in terms and name not in options:
            found.append((RecipeFault.NEEDS_UNFILLED, f"needs {name}, neither a term nor an option this entry sets"))
    # An accepted option is one the recipe may leave unset, so it is never checked for presence --
    # only that it is an option at all, and that it is not already mandatory (Part 12 §7).
    declared_needs = set(document.get("needs", ()))
    for name in document.get("accepts", ()):
        if name == SOURCE_CACHE:
            continue
        if name in terms or name in _protocol_terms():
            found.append(
                (
                    RecipeFault.ACCEPTS_TERM,
                    f"accepts {name}, which is a term a build fills rather than an option a recipe sets",
                )
            )
        elif name in declared_needs:
            found.append(
                (
                    RecipeFault.ACCEPTS_NEEDED,
                    f"accepts {name}, which it also needs, so it is both optional and required",
                )
            )
    return found


def _protocol_terms() -> frozenset[str]:
    """Every term a protocol supplies, which is what an adapter may not declare."""
    return frozenset(name for names in PROTOCOL_TERMS.values() for name in names) | {"report_path"}


__all__ = [
    "BLOCKS",
    "FILES",
    "FLIGHT",
    "PROTOCOLS",
    "PROTOCOL_TERMS",
    "REPORT_AS_FILE",
    "SOURCE_CACHE",
    "STREAM",
    "load",
    "of",
    "refusals",
    "schema",
    "shape_problems",
]
