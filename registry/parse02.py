"""Parse 02's markdown table definitions into structured form.

Extracts columns, primary keys, and references. This is the input to build.py, which
applies the accepted revisions on top.
"""

import re
from pathlib import Path

SPEC = (
    Path(__file__).resolve().parent.parent
    / "nwb_lake_poc_docs"
    / "02_core_logical_schemas.md"
)

COL = re.compile(
    r"^\|\s*`([a-z_0-9]+)`\s*\|\s*([^|]+?)\s*\|\s*([a-z]+)\s*\|\s*([^|]*?)\s*\|"
)
PK = re.compile(r"^Primary key:\s*(.+?)\.?\s*$", re.M)
REF = re.compile(r"^-\s*`([^`]+)`\s*->\s*`([^`]+)`(,\s*when present)?", re.M)


def _cols(names):
    return [c.strip(" `()") for c in names.split(",")]


def parse() -> dict:
    text = SPEC.read_text()
    tables = {}
    for m in re.finditer(
        r"^#{2,3} `(core\.[a-z_]+)`\n(.*?)(?=\n#{2,3} |\Z)", text, re.S | re.M
    ):
        name, body = m.group(1), m.group(2)
        columns = [
            {
                "name": c.group(1),
                "type": c.group(2),
                "required": c.group(3),
                "description": c.group(4),
            }
            for line in body.splitlines()
            if (c := COL.match(line))
        ]
        pk = PK.search(body)
        refs = []
        for r in REF.finditer(body):
            target = r.group(2).split(".")
            resource = ".".join(target[:2])
            tcols = [target[2]] if len(target) > 2 else None
            refs.append(
                {
                    "columns": _cols(r.group(1)),
                    "resource": resource,
                    "resource_columns": tcols,
                    "conditional": bool(r.group(3)),
                }
            )
        tables[name] = {
            "columns": columns,
            "primary_key": _cols(pk.group(1)) if pk else None,
            "references": refs,
        }
    return tables


if __name__ == "__main__":
    t = parse()
    print(
        f"{len(t)} tables, {sum(len(v['columns']) for v in t.values())} columns, "
        f"{sum(1 for v in t.values() if v['primary_key'])} keys, "
        f"{sum(len(v['references']) for v in t.values())} references\n"
    )
    for n in ("core.trials", "core.spike_events", "core.units"):
        v = t[n]
        print(f"{n}\n  pk: {v['primary_key']}")
        for r in v["references"]:
            print(
                f"  ref: {r['columns']} -> {r['resource']}{r['resource_columns'] or ''}"
                f"{'  (conditional)' if r['conditional'] else ''}"
            )
