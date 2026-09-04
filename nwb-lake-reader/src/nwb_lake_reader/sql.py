"""Helpers for mapping packet identifiers onto SQL identifiers.

Public because the validator emits SQL against the names this package registers, and the
two must agree exactly. One implementation, so they cannot drift apart.
"""

from __future__ import annotations


def sql_name(resource_id: str) -> str:
    """Convert a resource ID to its SQL identifier.

    Resource IDs are dotted (``core.intervals``); SQL identifiers are not, so dots become
    underscores. This is the convention the specification's own examples use.

    Parameters
    ----------
    resource_id : str
        Dotted resource ID, e.g. ``core.intervals``.

    Returns
    -------
    str
        The SQL identifier, e.g. ``core_intervals``.
    """
    return resource_id.replace(".", "_")


def quote(column: str) -> str:
    """Quote a column identifier for use in SQL.

    Quoting is unconditional. ``core.array_assets.offset`` is a reserved word in DuckDB and
    every engine reserves a different set, so relying on a word list is not portable.

    Parameters
    ----------
    column : str
        Column name.

    Returns
    -------
    str
        The quoted identifier.
    """
    return f'"{column}"'
