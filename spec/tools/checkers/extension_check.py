"""Check an extension registry where it sits: its document, the source it is built from, and its conventions.

An extension is not a member of the specification, so its author checks it with the same checkers
the tree checks core with. A document is held to the complete registry result under core's context
(Part 02 §9.4); beside that, where a source directory `<id>/` sits beside `<id>.json` the document
must be what it assembles to, and its tables follow the naming conventions less the exceptions a
`conventions.toml` beside it declares for its namespace.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .registry_conventions import convention_failures, declared_tables
from .registry_document import SCHEMA, CheckedRegistryContext, RegistryResult, check_registry_context_bytes
from .registry_source import HEADER, RegistrySourceError, assemble, dumps, extension_sources

#: The rule language an extension's Tier 2 SQL is written in, the one this release's validator runs.
RULE_LANGUAGE = "escapewheel-rule-sql-v0.2"
#: The file beside a registry document declaring its exceptions to the naming conventions.
CONVENTIONS = "conventions.toml"
#: The meta-schema an extension's `$schema` names, the one this release checks it against.
SCHEMA_ID: str = json.loads(SCHEMA.read_text())["$id"]


@dataclass(frozen=True)
class ExtensionCheck:
    """One extension document's complete registry result, and what else fails where it sits."""

    path: Path
    context: CheckedRegistryContext
    #: Each failure beyond the registry result: its source, its meta-schema, its conventions.
    failures: tuple[str, ...]
    #: How many table resources it declares, counted whether or not the document is valid.
    tables: int

    @property
    def sound(self) -> bool:
        """Whether the result is valid and nothing else fails."""
        return self.context.result.state == "valid" and not self.failures


def contract_failures(result: RegistryResult) -> list[str]:
    """Return each outcome of an invalid or incomplete registry result as one line; none for a valid one."""
    if result.state == "valid":
        return []
    return [
        f"{phase.phase}: {outcome.id} at {outcome.instance or '<root>'}: "
        f"{outcome.detail or outcome.reason or outcome.state}"
        for phase in result.phases
        for outcome in phase.outcomes
    ]


def source_failures(path: Path) -> list[str]:
    """Return why `path` differs from what the source directory beside it assembles to; none without one."""
    source = path.with_suffix("")
    if not (source / HEADER).is_file():
        return []
    try:
        expected = dumps(assemble(source))
    except RegistrySourceError as error:
        return [f"its source does not assemble: {error}"]
    if expected != path.read_text():
        return [f"it is not what {source.name}/ assembles to; build it"]
    return []


def _conventions(directory: Path) -> dict[str, Any]:
    """Return the conventions file in `directory`, or an empty one declaring no exceptions."""
    path = directory / CONVENTIONS
    return tomllib.loads(path.read_text()) if path.is_file() else {}


def check_extension(
    path: Path, core: CheckedRegistryContext, conventions: Mapping[str, Any] | None = None
) -> ExtensionCheck:
    """Check one extension document under core's context, with its source and conventions.

    Parameters
    ----------
    path : Path
        The extension's registry document.
    core : CheckedRegistryContext
        Core's checked context, which an extension's result depends on (Part 02 §9.4).
    conventions : Mapping or None
        The parsed conventions declaring this document's exceptions, keyed `naming_exceptions` and
        `names_a_kind`; None reads `conventions.toml` beside the document, where there is one.
    """
    context = check_registry_context_bytes(path.read_bytes(), core=core)
    document = context.document
    failures = source_failures(path)
    resources = document.get("resources") if isinstance(document, Mapping) else None
    tables = (
        sum(
            1
            for declaration in resources.values()
            if isinstance(declaration, Mapping) and declaration.get("kind") == "table"
        )
        if isinstance(resources, Mapping)
        else 0
    )
    if isinstance(document, Mapping):
        if document.get("$schema") != SCHEMA_ID:
            failures.append(f"it names {document.get('$schema', 'no meta-schema')}, not {SCHEMA_ID}")
        if document.get("rule_language") != RULE_LANGUAGE:
            failures.append(f"it selects {document.get('rule_language')}, not {RULE_LANGUAGE}")
    if context.result.state == "valid" and isinstance(document, Mapping):
        declared = _conventions(path.parent) if conventions is None else conventions
        # Exceptions are keyed `<resource>.<column>`, and an extension's resources lie in its namespace,
        # so one file serves every document in a directory.
        own = f"{document['extension_id']}."
        exceptions = {k: v for k, v in declared.get("naming_exceptions", {}).items() if k.startswith(own)}
        names_a_kind = {k: v for k, v in declared.get("names_a_kind", {}).items() if k.startswith(own)}
        for label, bad in convention_failures(declared_tables(document), exceptions, names_a_kind).items():
            failures += [f"{label}: {item}" for item in bad]
    return ExtensionCheck(path=path, context=context, failures=tuple(failures), tables=tables)


def check_directory(directory: Path, core: CheckedRegistryContext) -> tuple[list[ExtensionCheck], list[str]]:
    """Check every extension in `directory`, and say what in it no source builds.

    Returns
    -------
    checks : list of ExtensionCheck
        One per source directory's document, in name order.
    failures : list of str
        A source whose document is missing, and a document no source directory builds.
    """
    declared = _conventions(directory)
    targets = extension_sources(directory)
    checks, failures = [], []
    for source, out in targets.items():
        if out.is_file():
            checks.append(check_extension(out, core, declared))
        else:
            failures.append(f"{out.name}: {source.name}/ builds it and it is missing; build it")
    failures += [
        f"{path.name}: no source directory assembles to it"
        for path in sorted(directory.glob("*.json"))
        if path not in targets.values()
    ]
    return checks, failures


__all__ = [
    "CONVENTIONS",
    "RULE_LANGUAGE",
    "SCHEMA_ID",
    "ExtensionCheck",
    "check_directory",
    "check_extension",
    "contract_failures",
    "source_failures",
]
