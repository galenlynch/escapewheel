"""The current core and extension registries, as typed records over their JSON documents."""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from ._record import Record
from ._root import ROOT

#: The generated core registry.
CORE = ROOT / "spec" / "artifacts" / "logical_schemas.json"
#: Where extension documents sit, each one a `*.json` file.
EXTENSION_DIRECTORIES = (ROOT / "extensions", ROOT / "escapewheel-aind" / "extensions")


@dataclass(frozen=True)
class Column(Record):
    """One declared column, with the table and registry that declare it."""

    registry: str
    table: str
    name: str
    type: str
    presence: str
    role: str | None
    identity: str | None
    unit: str | None
    description: str
    raw: Mapping[str, Any] = field(repr=False)


@dataclass(frozen=True)
class Reference(Record):
    """A foreign key: `columns` of `table` resolve to `resource_columns` of `resource`."""

    registry: str
    table: str
    columns: tuple[str, ...]
    resource: str
    resource_columns: tuple[str, ...]


@dataclass(frozen=True)
class Rule(Record):
    """One shipped Tier 2 rule, as the registry document carries it."""

    registry: str
    table: str
    id: str
    level: str
    message: str
    sql: str
    advisory: bool


@dataclass(frozen=True)
class Table(Record):
    """One table resource's declaration."""

    registry: str
    resource_id: str
    content_class: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    references: tuple[Reference, ...]
    rules: tuple[Rule, ...]
    raw: Mapping[str, Any] = field(repr=False)

    def column(self, name: str) -> Column:
        """Return the column named `name`, raising KeyError where the table declares none."""
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(f"{self.resource_id} declares no column {name!r}")


@dataclass(frozen=True)
class Registry(Record):
    """One registry document and the tables it declares."""

    registry_id: str
    version: str
    path: Path
    document: Mapping[str, Any] = field(repr=False)
    tables: Mapping[str, Table] = field(repr=False)

    @property
    def is_extension(self) -> bool:
        """Whether this is an extension rather than core."""
        return "extension_id" in self.document


def _table(registry: str, resource_id: str, declaration: Mapping[str, Any]) -> Table:
    table = declaration["table"]
    return Table(
        registry=registry,
        resource_id=resource_id,
        content_class=declaration["content_class"],
        columns=tuple(
            Column(
                registry=registry,
                table=resource_id,
                name=column["name"],
                type=column["type"],
                presence=column["presence"],
                role=column.get("role"),
                identity=column.get("identity"),
                unit=column.get("unit"),
                description=column.get("description", ""),
                raw=column,
            )
            for column in table["columns"]
        ),
        primary_key=tuple(table.get("primary_key", ())),
        references=tuple(
            Reference(
                registry=registry,
                table=resource_id,
                columns=tuple(reference["columns"]),
                resource=reference["resource"],
                resource_columns=tuple(reference["resource_columns"]),
            )
            for reference in table.get("references", ())
        ),
        rules=tuple(
            Rule(
                registry=registry,
                table=resource_id,
                id=rule["id"],
                level=rule["level"],
                message=rule["message"],
                sql=rule["sql"],
                advisory=rule.get("advisory", False),
            )
            for rule in table.get("rules", ())
        ),
        raw=declaration,
    )


def load(path: Path) -> Registry:
    """Read one registry document from `path`."""
    document = json.loads(path.read_text())
    registry_id = document["registry_id"]
    return Registry(
        registry_id=registry_id,
        version=document["registry_version"],
        path=path,
        document=document,
        tables={
            resource_id: _table(registry_id, resource_id, declaration)
            for resource_id, declaration in document["resources"].items()
            if declaration["kind"] == "table"
        },
    )


@cache
def registries() -> Mapping[str, Registry]:
    """Return core and every extension in the working tree, by registry ID, core first."""
    paths = [CORE, *(path for directory in EXTENSION_DIRECTORIES for path in sorted(directory.glob("*.json")))]
    loaded = [load(path) for path in paths]
    return {registry.registry_id: registry for registry in loaded}


def registry(registry_id: str = "core") -> Registry:
    """Return one registry by its ID.

    Parameters
    ----------
    registry_id : str
        ``core``, or an extension's registry ID as `registries` keys it.
    """
    return registries()[registry_id]


def tables(registry_id: str | None = None) -> list[Table]:
    """Return every declared table, or one registry's.

    Parameters
    ----------
    registry_id : str or None
        The registry to read, or None for every registry.
    """
    chosen = registries().values() if registry_id is None else [registry(registry_id)]
    return [table for document in chosen for table in document.tables.values()]


def table(resource_id: str) -> Table:
    """Return the table declared as `resource_id` in whichever registry declares it.

    Parameters
    ----------
    resource_id : str
        A table resource ID such as ``core.units``.
    """
    for document in registries().values():
        if resource_id in document.tables:
            return document.tables[resource_id]
    raise KeyError(f"no registry declares a table {resource_id!r}")


def columns(
    registry_id: str | None = None,
    *,
    presence: str | None = None,
    roles: tuple[str, ...] | None = None,
) -> list[Column]:
    """Return declared columns, filtered by registry, presence and role.

    Parameters
    ----------
    registry_id : str or None
        The registry to read, or None for every registry.
    presence : str or None
        Keep only columns of this presence: ``required``, ``nullable`` or ``optional``.
    roles : tuple of str or None
        Keep only columns whose role is one of these, such as ``identifier``.
    """
    return [
        column
        for declared in tables(registry_id)
        for column in declared.columns
        if (presence is None or column.presence == presence) and (roles is None or column.role in roles)
    ]


def references_to(resource_id: str) -> list[Reference]:
    """Return every foreign key, across all registries, that resolves into `resource_id`.

    Parameters
    ----------
    resource_id : str
        The referenced table resource, such as ``core.sessions``.
    """
    return [
        reference for declared in tables() for reference in declared.references if reference.resource == resource_id
    ]


def rules(registry_id: str | None = None) -> list[Rule]:
    """Return the shipped Tier 2 rules, or one registry's.

    Parameters
    ----------
    registry_id : str or None
        The registry to read, or None for every registry.
    """
    return [rule for declared in tables(registry_id) for rule in declared.rules]


def rule(rule_id: str) -> Rule:
    """Return the shipped rule with ID `rule_id`, from whichever registry ships it.

    Parameters
    ----------
    rule_id : str
        A rule ID, which begins with the resource ID of the table it is declared on.
    """
    for candidate in rules():
        if candidate.id == rule_id:
            return candidate
    raise KeyError(f"no registry ships a rule {rule_id!r}")


__all__ = [
    "CORE",
    "EXTENSION_DIRECTORIES",
    "Column",
    "Reference",
    "Registry",
    "Rule",
    "Table",
    "columns",
    "load",
    "references_to",
    "registries",
    "registry",
    "rule",
    "rules",
    "table",
    "tables",
]
