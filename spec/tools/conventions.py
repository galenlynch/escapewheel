"""Authoring conventions for a registry's tables, which no packet's rows can show.

A naming convention is a property of the registry, so no Tier 2 rule can see it, and one written
anyway would pass silently. `check.py` applies these to the core registry, and a registry outside
the tree applies them to itself with exceptions of its own. Since a column declares its `role`,
seven of the tests compare a name against a declaration and flag nothing; the two comparing a name
against a type carry every exception.
"""

from collections.abc import Callable, Mapping
from typing import Any

#: SQL reserved words a column name must not be, unless declared an exception. Not exhaustive: it
#: is the words that have actually collided, since the point is to notice a new one.
RESERVED = {
    "offset",
    "order",
    "group",
    "select",
    "from",
    "where",
    "table",
    "column",
    "index",
    "key",
    "all",
    "primary",
    "case",
    "when",
    "end",
    "values",
}
INTEGERS = {"int32", "int64"}

NAMING: dict[str, Callable[[str, str, str | None], bool]] = {
    "an identifier is named _id": lambda n, t, role: (
        not (role == "identifier" and not n.endswith(("_id", "_label", "_name")))
    ),
    "an _id column is an identifier": lambda n, t, role: not (n.endswith("_id") and role != "identifier"),
    # An identifier is an integer, and a string one is the defect.
    "an _id column is an integer": lambda n, t, role: not (n.endswith("_id") and t not in INTEGERS),
    "a _name column is a string": lambda n, t, role: not (n.endswith("_name") and t != "string"),
    "a _tick column is a coordinate": lambda n, t, role: not (n.endswith("_tick") and role != "coordinate"),
    "a coordinate is named _tick": lambda n, t, role: not (role == "coordinate" and not n.endswith("_tick")),
    "an _index column is an index": lambda n, t, role: (
        not (n.endswith("_index") and role not in {"structural_index", "sequence_position"})
    ),
    "a structural index is named _index": lambda n, t, role: (
        not (role == "structural_index" and not n.endswith("_index"))
    ),
    "no column is a reserved word": lambda n, t, role: n not in RESERVED,
    # A plural integer reads as a coordinate and is a duration or a count, so it is flagged and a
    # real count says so among the exceptions.
    "no integer column is plural": lambda n, t, role: not (n.endswith("s") and t in INTEGERS),
    # Part 02 §8.3: a discriminator holds a dotted resource ID, so it is a string by construction.
    "a _kind column is a discriminator": lambda n, t, role: not (n.endswith("_kind") and role != "discriminator"),
    "a discriminator is named _kind": lambda n, t, role: not (role == "discriminator" and not n.endswith("_kind")),
    "a discriminator is a string": lambda n, t, role: not (role == "discriminator" and t != "string"),
}

#: The core registry's columns breaking a naming convention on purpose, each with the reason. An
#: exception is declared, never inferred, so removing a column here without renaming it fails.
NAMING_EXCEPTIONS = {
    "core.array_assets.resource_id": "Part 02 §2.6: packet identity is a carried string before row numbering",
    "analysis.array_assets.resource_id": "as core.array_assets.resource_id",
    "core.media_assets.resource_id": "as core.array_assets.resource_id",
    "core.sidecars.resource_id": "as core.array_assets.resource_id, and the table's whole key (Part 02 §12.10)",
    "core.sidecar_scopes.resource_id": "references core.sidecars.resource_id, which Part 02 §2.6 makes a string",
    "core.array_assets.offset": "NWB-standard name; the reserved word is handled by unconditional quoting",
    "analysis.array_assets.offset": "as core.array_assets.offset",
    "core.array_channels.offset": "as core.array_assets.offset, per channel",
    "core.units.n_spikes": "a count, not a plural duration",
    "core.source_files.size_bytes": "a quantity in bytes, not a plural of `size_byte`",
    "core.media_frames.pts": "the container's own initialism for one timestamp, not a plural (Part 01 §3.18)",
    # Part 03 §6.3: `_kind` reads as a category, and this holds the table whose rows an axis's
    # positions stand for, which its role says and its name cannot.
    "core.array_dimensions.coordinate_resource": "names the table whose rows the axis's positions stand for, "
    "not a kind of thing (Part 03 §6.3)",
    "analysis.array_dimensions.coordinate_resource": "as core.array_dimensions.coordinate_resource",
}

#: Part 02 §8.2: the core registry's name columns naming a kind of thing rather than one assigned
#: identifier's value, and so expected to repeat. Declared for the reason the naming exceptions
#: are: a set absorbing whatever has no `*_id` sibling would absorb the next one added without it.
NAMES_A_KIND = {
    "core.array_dimensions.dimension_name": "an axis's name, repeated across every array",
    "analysis.array_dimensions.dimension_name": "as core.array_dimensions.dimension_name",
    "core.probes.insertion_name": "the trajectory the probe was inserted along, not the probe",
    "core.processing_runs.software_name": "what ran, so every run of one tool repeats it",
    "core.sessions.task_name": "which task, so every session running it repeats the name",
    "core.sorting_runs.sorter_name": "as software_name, per sorting",
    "core.coordinate_frame_axes.axis_name": "what the source called the field, repeated across "
    "every frame that read the same one (Part 01 §3.24)",
}

Tables = Mapping[str, Mapping[str, Any]]


def column_order(tables: Tables) -> dict[str, list[str]]:
    """Return the tables breaking each column-order convention, by convention.

    Column order is a convention of these registries rather than a conformance requirement.
    """
    return {
        "a table carrying session_id leads with it": [
            name
            for name, table in tables.items()
            if any(c["name"] == "session_id" for c in table["columns"]) and table["columns"][0]["name"] != "session_id"
        ],
        "a table carrying metadata ends with it": [
            name
            for name, table in tables.items()
            if any(c["name"] == "metadata" for c in table["columns"]) and table["columns"][-1]["name"] != "metadata"
        ],
    }


def naming(tables: Tables) -> dict[str, list[str]]:
    """Return each column breaking a naming convention and the conventions it breaks."""
    flagged: dict[str, list[str]] = {}
    for label, holds in NAMING.items():
        for resource, table in tables.items():
            for column in table["columns"]:
                if not holds(column["name"], column["type"], column.get("role")):
                    flagged.setdefault(f"{resource}.{column['name']}", []).append(label)
    return flagged


def name_columns(tables: Tables) -> dict[str, bool]:
    """Return each `*_name` column and whether it names an assigned identifier of its own table.

    Part 02 §8.2 puts the uniqueness obligation on the columns that do, and a generated check reports
    two rows sharing one; none sees two things a writer numbering per distinct name merged into one row.
    """
    named = {}
    for resource, table in tables.items():
        owned = {c["name"]: c for c in table["columns"]}
        for column in table["columns"]:
            if column["name"].endswith("_name"):
                identifier = owned.get(f"{column['name'][: -len('_name')]}_id") or {}
                named[f"{resource}.{column['name']}"] = identifier.get("identity") == "assigned"
    return named


def convention_failures(
    tables: Tables, exceptions: Mapping[str, str], names_a_kind: Mapping[str, str]
) -> dict[str, list[str]]:
    """Return every convention check over `tables` with what fails it, allowing the declared exceptions."""
    flagged = naming(tables)
    named = name_columns(tables)
    return {
        **column_order(tables),
        "column names follow the conventions, or say why not": sorted(
            f"{k}: {', '.join(v)}" for k, v in flagged.items() if k not in exceptions
        ),
        "every declared naming exception still exists and still breaks a convention": sorted(
            k for k in exceptions if k not in flagged
        ),
        "a name column names an assigned identifier, or is declared to name a kind of thing": sorted(
            n for n, paired in named.items() if not paired and n not in names_a_kind
        ),
        "every column declared to name a kind of thing still exists and still names one": sorted(
            n for n in names_a_kind if named.get(n, True)
        ),
    }
