"""Check the built registry against the invariants R2-R9 establish."""
import json
import re
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
# Namespaces beyond core exist from R20 §5; match any <namespace>.<table> line.
expected = {l.strip() for l in ledger.splitlines()
            if re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", l.strip())}
check("table set matches R9 §2 ledger", expected ^ set(T))
# R29 §6. A 02 table whose columns a revision amended carries `since` on those columns and
# not on itself, which is right -- so the checkable claims are the format and that every
# revision the build stamps is one the registry says it derived from.
check("every stamped revision is declared in derived_from",
      sorted({v.split(" ")[0] for n, t in T.items()
              for v in [t.get("since"), *(c.get("since") for c in t["columns"])] if v}
             - set(REG.get("derived_from", {}).get("revisions", []))))
check("a since names a revision",
      [(n, v) for n, t in T.items()
       for v in [t.get("since"), *(c.get("since") for c in t["columns"])]
       if v is not None and not re.fullmatch(r"R\d+(?: §[\d.\-]+)?", v)])
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
# R48 §2.3. A structural index may also be a foreign-key component, so a client converting one
# side and not the other would break the join. Both sides sharing a role is what makes converting
# every structural_index column join-preserving by construction.
_role = {(n, c["name"]): c["role"] for n, t in T.items() for c in t["columns"]}
check("a reference relates columns of the same role",
      [(n, a, r["resource"], b) for n, t in T.items() for r in t["references"]
       for a, b in zip(r["columns"], r["resource_columns"])
       if _role.get((n, a)) != _role.get((r["resource"], b))])
check("source labels are strings",
      [(n, c["name"], c["type"]) for n, t in T.items() for c in t["columns"]
       if c["name"].endswith("_label") and c["type"] != "string"])
check("withdrawn tables absent",
      [n for n in ("core.unit_spike_chunks", "core.provenance_entities",
                   "core.provenance_activities", "core.provenance_edges") if n in T])

# rules.json is hand-authored and merged at build time, so it can drift from the
# structure it annotates. build.py rejects unknown tables; these catch the rest.
RULES = json.loads((HERE / "rules.json").read_text())["rules"]
check("every rules.json table exists in the registry", sorted(set(RULES) - set(T)))

# Template invocations carry no id until build.py expands them (R24 §3). Expand through the
# same function rather than a second copy, so this cannot drift from what the build does.
sys.path.insert(0, str(HERE))
from build import expand  # noqa: E402

authored_rules = []
for resource, rs in RULES.items():
    for r in rs:
        if template := r.get("use"):
            authored_rules += expand(template, resource, r, T[resource]["primary_key"])
        else:
            authored_rules.append(r)

merged = {r["id"] for t_ in T.values() for r in t_["rules"]}
authored = {r["id"] for r in authored_rules}
check("every authored rule reached the registry", sorted(authored - merged))
check("the registry carries no rule rules.json does not author", sorted(merged - authored))
ids = [r["id"] for r in authored_rules]
check("rule ids are unique", sorted({i for i in ids if ids.count(i) > 1}))


# R50 §5: a naming convention is a property of the registry, not of any packet's rows, so no SQL
# rule can see it -- and one written anyway would pass silently (R12 §4). It is checked here.
#
# R48 is what makes this exact rather than heuristic. Before a column declared its `role`,
# "identifier-shaped" had to be guessed from name and type, which is why R50's three misnamed
# columns survived as long as they did. Seven of the nine tests below compare a name against a
# *declaration* and consequently flag nothing; the two that remain compare it against a type,
# and those are the two carrying every exception.

#: SQL reserved words a column name must not be, unless declared below. Not exhaustive: it is
#: the words that have actually collided, since the point is to notice a new one.
RESERVED = {"offset", "order", "group", "select", "from", "where", "table", "column",
            "index", "key", "all", "primary", "case", "when", "end", "values"}
INTEGERS = {"int32", "int64"}

#: Names that break a convention on purpose, each with the reason. An exception is declared, never
#: inferred: a baseline absorbing whatever exists today would have absorbed `step_ticks` too.
#: Removing a column here without renaming it fails the run, which is the point.
NAMING_EXCEPTIONS = {
    "core.array_assets.offset": "NWB-standard name; the reserved word is handled by unconditional quoting (R50 §4)",
    "analysis.array_assets.offset": "as core.array_assets.offset",
    "core.array_channels.offset": "as core.array_assets.offset, per channel (R19 §2)",
    "core.units.n_spikes": "a count, not a plural duration -- the shape R50 §3 renamed step_ticks for",
    "core.source_files.size_bytes": "a quantity in bytes, not a plural of `size_byte`",
}

NAMING = {
    "an identifier is named _id": lambda n, t, role: not (
        role == "identifier" and not n.endswith(("_id", "_label", "_name"))),
    "an _id column is an identifier": lambda n, t, role: not (n.endswith("_id") and role != "identifier"),
    # R53 §2.1 inverted this: an identifier is an integer, and a string one is the defect.
    "an _id column is an integer": lambda n, t, role: not (n.endswith("_id") and t not in INTEGERS),
    "a _name column is a string": lambda n, t, role: not (n.endswith("_name") and t != "string"),
    "a _tick column is a coordinate": lambda n, t, role: not (n.endswith("_tick") and role != "coordinate"),
    "a coordinate is named _tick": lambda n, t, role: not (role == "coordinate" and not n.endswith("_tick")),
    "an _index column is an index": lambda n, t, role: not (
        n.endswith("_index") and role not in {"structural_index", "sequence_position"}),
    "a structural index is named _index": lambda n, t, role: not (
        role == "structural_index" and not n.endswith("_index")),
    "no column is a reserved word": lambda n, t, role: n not in RESERVED,
    # R50 §3: `step_ticks` read as a coordinate and was a duration. A plural integer is the shape
    # that confusion takes, so it is flagged and a real count says so here.
    "no integer column is plural": lambda n, t, role: not (n.endswith("s") and t in INTEGERS),
}

flagged = {}
for label, holds in NAMING.items():
    for tid, tbl in T.items():
        for c in tbl["columns"]:
            if not holds(c["name"], c["type"], c.get("role")):
                flagged.setdefault(f"{tid}.{c['name']}", []).append(label)
check("column names follow the conventions, or say why not",
      sorted(f"{k}: {', '.join(v)}" for k, v in flagged.items() if k not in NAMING_EXCEPTIONS))
check("every declared naming exception still exists and still breaks a convention",
      sorted(k for k in NAMING_EXCEPTIONS if k not in flagged))
print(f"      {len(NAMING)} conventions over {sum(len(t['columns']) for t in T.values())} columns, "
      f"{len(NAMING_EXCEPTIONS)} declared exceptions")


# R56 §2.4: a declared unit or clock source must resolve. Structural -- decidable from the
# registry with no packet in hand, which is where this format puts a check it can make without
# data. The point is that a wrong `clock_from` converts ticks on the wrong clock silently.
def _resolves(resource, spec, value):
    """Whether a same-table column name or a one-hop `resource.column` resolves. Returns why not."""
    parts = value.split(".")
    if len(parts) == 1:
        if value not in {c["name"] for c in spec["columns"]}:
            return f"{resource} has no column {value}"
        return None
    target, column = f"{parts[0]}.{parts[1]}", parts[2]
    if target not in T:
        return f"{value} names no resource"
    if not any(ref["resource"] == target for ref in spec["references"]):
        return f"{resource} declares no reference to {target}, so the hop is not one this table can make"
    if column not in {c["name"] for c in T[target]["columns"]}:
        return f"{target} has no column {column}"
    return None


bad_context = []
for _r, _t in T.items():
    for _c in _t["columns"]:
        for _field in ("unit_from", "clock_from"):
            if _field in _c and (_why := _resolves(_r, _t, _c[_field])):
                bad_context.append(f"{_r}.{_c['name']} {_field}: {_why}")
        if "clock_from" in _c and _c.get("role") != "coordinate":
            bad_context.append(f"{_r}.{_c['name']}: clock_from on a {_c.get('role')}, not a coordinate")
        if "unit" in _c and "unit_from" in _c:
            bad_context.append(f"{_r}.{_c['name']}: declares both unit and unit_from")
check("a declared unit or clock source resolves", sorted(bad_context))

# A vendored schema is a build artifact (see `build.py`'s VENDORED), so a copy that disagrees
# means the build was not run. Checked here because this is what one runs after touching the
# registry, and because a stale copy has three times been reported as a hundred findings about
# the data rather than one about the copy.
from build import VENDORED  # noqa: E402 - after the ledger, so a broken build fails first

stale = []
for _schema, _consumer in VENDORED.items():
    if not _consumer.parent.is_dir():
        continue
    if not _consumer.exists():
        stale.append(f"{_consumer.relative_to(HERE.parent)} is absent; run build.py")
    elif _consumer.read_text() != (HERE / _schema).read_text():
        stale.append(f"{_consumer.relative_to(HERE.parent)} differs from {_schema}; run build.py")
check("every vendored schema matches its source", stale)

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
