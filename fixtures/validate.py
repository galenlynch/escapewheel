"""Validate a packet against the registry.

Four layers, in 09 §10's order: the manifest's shape, the registry it embeds, each
resource's physical schema, then the rules — Tier 1 generated from structure, Tier 2
carried inline (R2 §7).

The generator is imported from the prototype; it moves into the reference package at
Phase 1.
"""
import json
import sys
from pathlib import Path

import duckdb
import jsonschema
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prototype" / "registry-codegen"))
from generate import generate, sql_name                                    # noqa: E402

ARROW = {"string": "string", "int32": "int32", "int64": "int64", "float32": "float",
         "float64": "double", "bool": "bool", "date": "date32[day]",
         "timestamp": "timestamp[us, tz=UTC]", "json_string": "string"}


class Report:
    def __init__(self):
        self.findings = []

    def add(self, level, check, message, rows=()):
        self.findings.append({"level": level, "check": check, "message": message,
                              "rows": [list(map(str, r)) for r in list(rows)[:5]]})

    @property
    def errors(self): return sum(f["level"] == "error" for f in self.findings)

    @property
    def warnings(self): return sum(f["level"] == "warning" for f in self.findings)


def validate(packet: Path, reference_registry: dict) -> Report:
    r = Report()

    # --- 1. manifest shape (R2 §10) ---------------------------------------------------
    manifest = json.loads((packet / "nwb.packet.json").read_text())
    schema = json.loads((ROOT / "registry" / "manifest.schema.json").read_text())
    for e in jsonschema.Draft202012Validator(schema).iter_errors(manifest):
        r.add("error", "manifest.schema", f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}")

    # --- 2. the registry the packet embeds (R2 §8, §9) --------------------------------
    embedded_path = packet / "schemas" / "logical_schemas.json"
    if not embedded_path.exists():
        r.add("error", "packet.registry_absent", "schemas/logical_schemas.json is missing")
        registry = reference_registry
    else:
        registry = json.loads(embedded_path.read_text())
        meta = json.loads((ROOT / "registry" / "registry.schema.json").read_text())
        for e in jsonschema.Draft202012Validator(meta).iter_errors(registry):
            r.add("error", "registry.schema", f"{'/'.join(map(str, e.path))}: {e.message}")
        if registry["registry_version"] != manifest.get("registry_version"):
            r.add("error", "packet.registry_version_mismatch",
                  f"manifest says {manifest.get('registry_version')}, "
                  f"embedded registry says {registry['registry_version']}")

    # --- 3. physical schema per resource ----------------------------------------------
    uris = {res["resource_id"]: res["uri"] for res in manifest.get("resources", [])}
    present = {}
    for resource, spec in registry["tables"].items():
        if resource not in uris:
            continue                       # a packet need not carry every table
        path = packet / uris[resource]
        if not path.exists():
            r.add("error", "resource.missing", f"{resource}: {uris[resource]} does not resolve")
            continue
        present[resource] = path
        names = pq.read_schema(path)
        for c in spec["columns"]:
            if c["name"] not in names.names:
                if c["presence"] != "optional":
                    r.add("error", "schema.column_absent",
                          f"{resource}.{c['name']} absent (presence={c['presence']})")
                continue
            actual = str(names.field(c["name"]).type)
            if actual != ARROW[c["type"]]:
                r.add("error", "schema.column_type",
                      f"{resource}.{c['name']} is {actual}, registry declares {c['type']}")

    # --- 4. physical ordering (R10 §2) -------------------------------------------------
    # Not expressible in SQL: a query has no access to physical row order, so this is
    # checked by reading each file in the order it was written.
    for resource, path in present.items():
        keys = registry["tables"][resource].get("sort")
        if not keys:
            continue
        cols = pq.read_table(path, columns=keys).to_pydict()
        rows = list(zip(*(cols[k] for k in keys)))
        def sortable(row):
            return tuple((v is None, v) for v in row)
        out_of_order = [(i, rows[i - 1], rows[i]) for i in range(1, len(rows))
                        if sortable(rows[i]) < sortable(rows[i - 1])]
        if out_of_order:
            r.add("warning", f"{resource}.physical_order",
                  f"rows are not in declared sort order ({', '.join(keys)})",
                  [(f"row {i}", str(prev), str(cur)) for i, prev, cur in out_of_order])

    # --- 5. rules (R2 §7) --------------------------------------------------------------
    con = duckdb.connect()
    for resource, path in present.items():
        con.sql(f"CREATE VIEW {sql_name(resource)} AS SELECT * FROM '{path}'")
    sessions = manifest.get("sessions", [])
    con.sql("CREATE TABLE manifest_sessions (session_id VARCHAR)")
    for s in sessions:
        con.sql("INSERT INTO manifest_sessions VALUES (?)", params=[s])

    runnable = {r_ for r_ in present}
    for check in generate({"tables": {k: v for k, v in registry["tables"].items()
                                     if k in runnable}}):
        try:
            rows = con.sql(check["sql"]).fetchall()
        except duckdb.Error as e:
            r.add("error", check["id"], f"check could not run: {str(e).splitlines()[0][:80]}")
            continue
        if rows:
            r.add(check["level"], check["id"], check["message"], rows)
    return r


def main(packet: Path) -> int:
    registry = json.loads((ROOT / "registry" / "logical_schemas.json").read_text())
    rep = validate(packet, registry)

    for f in rep.findings:
        print(f"  {f['level']:8s} {f['check']}: {f['message']}")
        for row in f["rows"]:
            print(f"           {tuple(row)}")

    status = "failed" if rep.errors else "passed"
    print(f"\n{packet.name}: {status} — {rep.errors} error(s), {rep.warnings} warning(s)")

    # 05 Stage 5: a committed packet's manifest records the result for its current bytes.
    mpath = packet / "nwb.packet.json"
    manifest = json.loads(mpath.read_text())
    manifest["validation"]["status"] = status
    for res in manifest.get("resources", []):
        res["validation_state"] = status
    mpath.write_text(json.dumps(manifest, indent=2) + "\n")

    (packet / "validation").mkdir(exist_ok=True)
    (packet / "validation" / "validation_report.json").write_text(json.dumps({
        "packet_id": manifest["packet_id"], "status": status,
        "validator": {"name": "nwb_lake_validate", "version": "0.1.0"},
        "summary": {"errors": rep.errors, "warnings": rep.warnings},
        "findings": rep.findings}, indent=2) + "\n")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
