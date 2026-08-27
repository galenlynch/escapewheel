"""Check the built registry against the invariants R2-R9 establish."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REG = json.loads((HERE / "logical_schemas.json").read_text())
T = REG["tables"]
VOCAB = {"string", "int32", "int64", "float32", "float64", "bool", "date",
         "timestamp", "json_string"}

fail = []


def check(label, bad, fmt=str):
    bad = list(bad)
    print(f"{'FAIL' if bad else 'ok  '}  {label}" + (f"  ({len(bad)})" if bad else ""))
    for b in bad[:4]:
        print(f"          {fmt(b)}")
    if bad:
        fail.append(label)


ledger = subprocess.run([sys.executable, str(HERE.parent / "conformance/spec-sweep/tables.py")],
                        capture_output=True, text=True).stdout
expected = {l.strip() for l in ledger.splitlines() if l.strip().startswith("core.")}
check("table set matches R9 §2 ledger", expected ^ set(T))
check("every table declares a primary key", [n for n, t in T.items() if t["primary_key"] is None])
check("every column type is in R2 §4's vocabulary",
      [(n, c["name"], c["type"]) for n, t in T.items() for c in t["columns"]
       if c["type"] not in VOCAB])
check("no required column is json_string",
      [(n, c["name"]) for n, t in T.items() for c in t["columns"]
       if c["type"] == "json_string" and c["presence"] != "optional"])
check("no nested type spellings survived",
      [(n, c["name"], c["type"]) for n, t in T.items() for c in t["columns"]
       if any(k in c["type"] for k in ("list", "struct", "map"))])

cols = {n: {c["name"]: c for c in t["columns"]} for n, t in T.items()}
check("primary key columns exist",
      [(n, k) for n, t in T.items() for k in (t["primary_key"] or []) if k not in cols[n]])
check("primary key columns are required",
      [(n, k) for n, t in T.items() for k in (t["primary_key"] or [])
       if k in cols[n] and cols[n][k]["presence"] != "required"])
check("reference targets exist",
      [(n, r["resource"]) for n, t in T.items() for r in t["references"] if r["resource"] not in T])
check("reference source columns exist",
      [(n, c) for n, t in T.items() for r in t["references"] for c in r["columns"]
       if c not in cols[n]])
check("reference target columns exist",
      [(n, r["resource"], c) for n, t in T.items() for r in t["references"]
       if r["resource"] in T for c in r["resource_columns"] if c not in cols[r["resource"]]])
check("reference arity matches",
      [(n, r["resource"]) for n, t in T.items() for r in t["references"]
       if len(r["columns"]) != len(r["resource_columns"])])
check("source labels are strings",
      [(n, c["name"], c["type"]) for n, t in T.items() for c in t["columns"]
       if c["name"].endswith("_label") and c["type"] != "string"])
check("withdrawn tables absent",
      [n for n in ("core.unit_spike_chunks", "core.provenance_entities",
                   "core.provenance_activities", "core.provenance_edges") if n in T])

# R2 §9: the registry validates against its published meta-schema.
try:
    import jsonschema
    meta = json.loads((HERE / "registry.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(meta)
    errs = list(jsonschema.Draft202012Validator(meta).iter_errors(REG))
    check("registry validates against its meta-schema",
          [f"{list(e.path)[:4]}: {e.message[:60]}" for e in errs])
    manifest = json.loads((HERE / "manifest.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(manifest)
    check("manifest schema is valid JSON Schema", [])
except ImportError:
    print("skip  schema validation (jsonschema not available)")

# Every rule must be valid SQL naming real columns. Empty tables built from the registry
# validate syntax and identifiers without needing a packet.
DDL = {"string": "VARCHAR", "int32": "INTEGER", "int64": "BIGINT", "float32": "FLOAT",
       "float64": "DOUBLE", "bool": "BOOLEAN", "date": "DATE",
       "timestamp": "TIMESTAMPTZ", "json_string": "VARCHAR"}
try:
    import duckdb
    con = duckdb.connect()
    for n, t_ in T.items():
        cols = ", ".join(f'"{c["name"]}" {DDL[c["type"]]}' for c in t_["columns"])
        con.sql(f"CREATE TABLE {n.replace('.', '_')} ({cols})")
    con.sql("CREATE TABLE manifest_sessions (session_id VARCHAR)")   # supplied by the shim
    broken = []
    for n, t_ in T.items():
        for r in t_["rules"]:
            try:
                con.sql(r["sql"]).fetchall()
            except Exception as e:
                broken.append((r["id"], str(e).splitlines()[0][:70]))
    check("every Tier 2 rule is executable SQL", broken)
    print(f"      {sum(len(t_['rules']) for t_ in T.values())} rules executed against "
          f"{len(T)} empty tables")
except ImportError:
    print("skip  rule execution (duckdb not available)")

print(f"\n{len(T)} tables, {sum(len(t['columns']) for t in T.values())} columns, "
      f"{sum(len(t['references']) for t in T.values())} references")
raise SystemExit(1 if fail else 0)
