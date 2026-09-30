"""Assemble a registry document from its TOML source.

A registry's source is a directory: `registry.toml` holds the document's own fields and each
`<resource_id>.toml` declares one resource. A file uses the published format's keys (Part 02
§9) and differs from the document it produces in spelling only:

- a table's `primary_key`, `columns`, `references`, `rules` and `amendment_groups` sit at the top of its file, where
  the document nests them under `table`;
- a single-column reference is written on its column, as `references = "<resource>"` where the
  target column has the same name and `references = { resource = "...", column = "..." }`
  where it does not, with any `specialises` in that table, so a `[[references]]` entry is always
  a multi-column one;
- a rule may invoke the `interval` template (Part 02 §10.2), which is expanded into plain SQL,
  so the document a packet binds carries no vocabulary a validator would have to learn.

`canonical` fixes key and reference order, so how a file orders them changes nothing.
"""

import tomllib
from pathlib import Path
from typing import Any

from canonical import canonical, dumps

HERE = Path(__file__).resolve().parent
TREE = HERE.parent
HEADER = "registry.toml"
TABLE = ("primary_key", "columns", "references", "rules", "amendment_groups")


def sources() -> dict[Path, Path]:
    """Return the core registry's source directory and the document built from it."""
    return {TREE / "source/core": TREE / "artifacts/logical_schemas.json"}


def extension_sources(directory: Path) -> dict[Path, Path]:
    """Return each extension source under `directory` and the document beside it.

    An extension is not a member of the specification, so its registry sits outside the tree and
    is assembled there by this module.
    """
    return {
        source: directory / f"{source.name}.json"
        for source in sorted(directory.iterdir())
        if (source / HEADER).is_file()
    }


def expand(
    template: str, resource: str, call: dict, key: list[str]
) -> list[dict[str, str]]:
    """Expand one template invocation into the rules it stands for (Part 02 §10.2).

    Parameters
    ----------
    template : str
        Template name; only ``interval`` exists.
    resource : str
        The table being expanded for.
    call : dict
        The invocation, carrying the template's parameters.
    key : list of str
        The table's primary key, used to identify offending rows.

    Returns
    -------
    list of dict
        Rules in the same shape a written one has.
    """
    if template != "interval":
        raise SystemExit(f"{resource}: unknown rule template {template!r}")

    start, stop = call["start"], call["stop"]
    report = ", ".join(dict.fromkeys([*key, start, stop]))
    rules = [
        {
            "id": f"{resource}.interval_valid",
            "level": "error",
            "message": f"{stop} precedes {start}",
            "sql": f"SELECT {report}\nFROM {resource}\nWHERE {stop} < {start}",
        }
    ]

    subject = call.get("partition_of")
    if subject is None:
        return rules

    # Without an `index` the rule orders by `start`, which is what it compares against, so the
    # check is an overlap test and nothing else.
    index, op = call.get("index"), call["overlap_op"]
    by = ", ".join(subject)
    if index is not None:
        rules.append(
            {
                "id": f"{resource}.index_contiguous",
                "level": "error",
                "message": f"{index} is not contiguous from 0",
                "sql": (
                    f"SELECT {by}, COUNT(*) AS n\nFROM {resource}\nGROUP BY {by}\n"
                    f"HAVING MAX({index}) <> COUNT(*) - 1\n  OR MIN({index}) <> 0"
                ),
            }
        )
    rules.append(
        {
            "id": f"{resource}.non_overlapping",
            "level": "error",
            "message": call["overlap_message"],
            "sql": (
                f"SELECT {report}\nFROM (\n"
                f"  SELECT *, LAG({stop}) OVER (PARTITION BY {by} ORDER BY {index or start})"
                f" AS prev_stop\n  FROM {resource}\n) AS checked_interval\n"
                f"WHERE prev_stop IS NOT NULL\n  AND {start} {op} prev_stop"
            ),
        }
    )
    return rules


def _column(resource: str, column: dict[str, Any]) -> tuple[dict, dict | None]:
    """Split a column's `references` from its declaration."""
    column = dict(column)
    name = column["name"]
    target = column.pop("references", None)
    if target is None:
        return column, None
    if isinstance(target, str):
        return column, {
            "columns": [name],
            "resource": target,
            "resource_columns": [name],
        }
    if not {"resource", "column"} <= set(target) <= {"resource", "column", "specialises"}:
        raise SystemExit(
            f"{resource}.{name}: a column's references is a resource ID, or a table of "
            f"`resource`, `column` and optionally `specialises`, not {sorted(target)}"
        )
    reference = {
        "columns": [name],
        "resource": target["resource"],
        "resource_columns": [target["column"]],
    }
    if "specialises" in target:
        reference["specialises"] = target["specialises"]
    return column, reference


def _table(resource: str, source: dict[str, Any]) -> dict[str, Any]:
    """Build one table declaration from the top of its file."""
    columns, references = [], []
    for written in source["columns"]:
        column, reference = _column(resource, written)
        columns.append(column)
        if reference:
            references.append(reference)
    for reference in source.get("references", []):
        if len(reference["columns"]) < 2:
            raise SystemExit(
                f"{resource}: a single-column reference is written on its column, "
                f"not as a [[references]] entry ({reference['columns']})"
            )
        references.append(reference)
    rules = []
    for rule in source.get("rules", []):
        if template := rule.get("use"):
            rules += expand(template, resource, rule, source["primary_key"])
        else:
            rules.append(rule)
    return {
        "columns": columns,
        "primary_key": source["primary_key"],
        "references": references,
        "rules": rules,
        "amendment_groups": source["amendment_groups"],
    }


def _resource(path: Path) -> dict[str, Any]:
    """Build one resource declaration from its file."""
    source = tomllib.loads(path.read_text())
    resource = {k: v for k, v in source.items() if k not in TABLE}
    if source.get("kind") == "table":
        resource["table"] = _table(path.stem, source)
    elif written := sorted(set(source) & set(TABLE)):
        raise SystemExit(
            f"{path.name}: a {source.get('kind')} resource declares {written}"
        )
    return resource


def assemble(directory: Path) -> dict[str, Any]:
    """Return the registry document one source directory declares, in canonical form."""
    document = tomllib.loads((directory / HEADER).read_text())
    document["resources"] = {
        path.stem: _resource(path)
        for path in sorted(directory.glob("*.toml"))
        if path.name != HEADER
    }
    return canonical(document)


def main(targets: dict[Path, Path] | None = None) -> list[Path]:
    """Write each registry document from its source, by default the core registry."""
    written = []
    for directory, out in (sources() if targets is None else targets).items():
        out.write_text(dumps(assemble(directory)))
        written.append(out)
    return written


if __name__ == "__main__":
    for path in main():
        print(f"wrote {path.relative_to(TREE)}")
