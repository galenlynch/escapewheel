"""Draft an extension registry document from tables that already exist.

**This invents no format.** Part 09 §2 makes an extension a registry document in R2's format, so
there is nothing here to design — only typing to avoid. The relationship is `escapewheel init`'s to a
recipe: draft what can be read off the data, name what cannot, and let a human finish it.

What can be read off a Parquet file: column names, their Arrow types mapped to R2 §4's vocabulary,
and whether a column is ever null. What cannot: everything that decides meaning. R48 §3 measured
that a column's `role` is not derivable from its name (`step_ticks` was a duration), its type (all
110 identifiers are strings, and so are many non-identifiers) or its key membership. R53 §2.3 adds
that `identity` is not derivable either -- a source may supply an integer the writer replaces.

So a draft is **incomplete on purpose**. It carries a guess for what a guess is cheap for, and the
report says which. R48 §2.2's reason applies to a scaffolder more than to anything else: a default
makes a forgotten classification look deliberate, and a generated file is exactly where a
forgotten one hides.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from escapewheel_validator.validator import registry_meta_schema

#: R2 §4's vocabulary, keyed by what pyarrow reports. A type outside this is a defect in the
#: source rather than a gap here: Part 03 §5.5 bans nested types so a native reader stays viable.
ARROW_TO_REGISTRY = {
    "string": "string",
    "large_string": "string",
    "int8": "int32",
    "int16": "int32",
    "int32": "int32",
    "int64": "int64",
    "uint8": "int32",
    "uint16": "int32",
    "uint32": "int64",
    "float": "float32",
    "double": "float64",
    "bool": "bool",
    "date32[day]": "date",
}

#: What a name suggests, which R48 §3 established is a hint and not an answer. Every application
#: of this is reported, because the whole point of R48 is that this guess is wrong often enough
#: to have needed three renames (R50).
NAME_HINTS = (("_tick", "coordinate"), ("_index", "structural_index"), ("_id", "identifier"))

#: Up to how many distinct values a string column's report lists, as candidates for a closed enum.
SHOWN_VALUES = 10


@dataclass
class Draft:
    """A drafted extension registry, and what a human still has to decide."""

    document: dict[str, Any]
    decisions: list[str] = field(default_factory=list)

    def write(self, path: Path) -> Path:
        """Write the document, finished or not.

        An unfinished one fails the meta-schema, because no column carries a role — which is the
        intended way to notice, and the only one that survives someone not reading the report.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.document, indent=2) + "\n")
        return path


def _timestamp(kind: pa.DataType) -> str | None:
    return "timestamp" if pa.types.is_timestamp(kind) else None


def _registry_type(kind: pa.DataType) -> str | None:
    return ARROW_TO_REGISTRY.get(str(kind)) or _timestamp(kind)


def _column(table: pa.Table, name: str, resource: str, decisions: list[str]) -> dict[str, Any]:
    field_ = table.schema.field(name)
    declared = _registry_type(field_.type)
    if declared is None:
        decisions.append(f"{resource}.{name}: {field_.type} is outside R2 §4's vocabulary; map it by hand")
        declared = "string"
    entry: dict[str, Any] = {
        "name": name,
        "type": declared,
        # Read off the data, and only true of *this* data: a column with no null here may be
        # nullable in the next session, which is why this is reported rather than trusted.
        "presence": "required" if table.column(name).null_count == 0 else "nullable",
        "description": "",
    }
    if declared in ("float32", "float64"):
        # Part 02 §5.4 gives `finite` no default. `false` claims nothing, as the null key does: a
        # column free of NaN in one session need not be in the next, and `true` is enforced.
        entry["finite"] = False
        values = table.column(name)
        non_finite = pc.count(values.filter(pc.invert(pc.is_finite(values)))).as_py()
        decisions.append(
            f"{resource}.{name}: finite is false, admitting NaN and infinities; declare true if it never "
            f"holds one (Part 02 §5.4); this data holds {non_finite} non-finite value(s)"
        )
    if declared == "string":
        # Part 02 §9.3 gives `vocabulary` no default either, and the meta-schema requires one as
        # soon as the column has a role, so a draft finished by its reported decisions alone fails.
        distinct = pc.unique(table.column(name).drop_null())
        listed = f": {', '.join(sorted(distinct.to_pylist()))}" if len(distinct) <= SHOWN_VALUES else ""
        decisions.append(
            f"{resource}.{name}: needs a vocabulary, closed with an enum, open, or free, unless its role is "
            f"discriminator (Part 02 §9.3); this data holds {len(distinct)} distinct value(s){listed}"
        )
    # No role is written, deliberately. R48 §2.2 refuses a default because a forgotten
    # classification would look deliberate, and a *generated* file is where a forgotten one
    # hides best: a draft that validated is a draft nobody finishes. So the hint is reported and
    # the document stays invalid until a human supplies the answer.
    hint = next((role for suffix, role in NAME_HINTS if name.endswith(suffix)), None)
    decisions.append(
        f"{resource}.{name}: needs a role"
        + (f" — the name suggests {hint!r}, which R48 §3 measured is a hint and not an answer" if hint else "")
        + ("; then `identity`, carried or assigned (R53 §2.3)" if hint == "identifier" else "")
    )
    decisions.append(f"{resource}.{name}: needs a description")
    return entry


def draft(
    extension_id: str,
    tables: dict[str, Path],
    *,
    logical_standard_version: str = "escapewheel-logical-v0.1",
) -> Draft:
    """Draft a registry document covering `tables`, mapping resource name to a Parquet file.

    Parameters
    ----------
    extension_id : str
        Namespace for every table, which Part 09 §2 requires each to be prefixed by.
    tables : dict
        Bare table name to the Parquet file whose schema it takes.
    """
    decisions: list[str] = []
    drafted: dict[str, Any] = {}
    for name, path in sorted(tables.items()):
        resource = f"{extension_id}.{name}"
        table = pq.read_table(path)
        drafted[resource] = {
            "columns": [_column(table, column, resource, decisions) for column in table.column_names],
            # R7: every table declares a key or explicitly null with a reason. Neither is
            # guessable -- a column unique in one session need not be unique in the next.
            "primary_key": None,
            # Part 09 §2 lets an extension reference core, and Part 02 §8.3 needs it to where a
            # discriminator names this table. Nothing here can know which.
            "references": [],
            "rules": [],
        }
        decisions.append(f"{resource}: primary_key is null; declare it or say why not (R7)")
        decisions.append(f"{resource}: no references; an extension may reference core (Part 09 §2)")
    return Draft(
        {
            # Part 02 §9.2. Taken from the meta-schema the validator vendors rather than written
            # here, because a second copy of a URI is a second thing to go stale.
            "$schema": registry_meta_schema()["$id"],
            "registry_id": extension_id,
            "registry_version": "0.1.0",
            "logical_standard_version": logical_standard_version,
            "rule_language": "escapewheel-rule-sql-v0.2",
            "extension_id": extension_id,
            "resources": {
                resource_id: {
                    "content_class": "extension",
                    "kind": "table",
                    "instances": {"mode": "singleton", "presence": "optional"},
                    "requires": [],
                    "lineage": "optional",
                    "table": table,
                }
                for resource_id, table in drafted.items()
            },
        },
        decisions,
    )


__all__ = ["ARROW_TO_REGISTRY", "Draft", "draft"]
