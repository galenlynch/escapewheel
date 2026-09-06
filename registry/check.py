"""Check the built registry against the invariants R2-R9 establish."""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REG = json.loads((HERE / "logical_schemas.json").read_text())
T = REG["tables"]
# R17 §2: an extension is a registry document in R2's format, so the invariants that hold of a
# registry hold of it. They are checked here for the same reason core's are -- a naming
# convention or an unparseable rule is a property of the document, which no packet's rows can
# show and no SQL can see (R12 §4).
EXT = {f.stem: json.loads(f.read_text()) for f in sorted((HERE / "extensions").glob("*.json"))}
EXT_T = {n: t for doc in EXT.values() for n, t in doc["tables"].items()}
ALL = T | EXT_T
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
# The inverse, and the one that was actually missing: a revision may be accepted, implemented,
# and left out of the list. R54, R65 and R66 all were, for several revisions each, because the
# list was hand-maintained and only the stamped direction was checked.
_accepted = {f"R{re.match(r'R(\d+)', q.name).group(1)}" for q in (HERE.parent / "revisions").glob("R*.md")
             if "**Accepted**" in q.read_text()[:400]}
_listed = set(REG.get("derived_from", {}).get("revisions", []))
check("every accepted revision is declared in derived_from",
      sorted(_accepted - _listed, key=lambda r: int(r[1:])))
check("derived_from declares no revision that is not accepted",
      sorted(_listed - _accepted, key=lambda r: int(r[1:])))
check("every stamped revision is declared in derived_from",
      sorted({v.split(" ")[0] for n, t in T.items()
              for v in [t.get("since"), *(c.get("since") for c in t["columns"])] if v}
             - set(REG.get("derived_from", {}).get("revisions", []))))
check("a since names a revision",
      [(n, v) for n, t in T.items()
       for v in [t.get("since"), *(c.get("since") for c in t["columns"])]
       if v is not None and not re.fullmatch(r"R\d+(?: §[\d.\-]+)?", v)])
def structural(tables, universe, prefix=""):
    """The invariants that hold of any registry document, core's or an extension's.

    `universe` is what a reference may resolve against: core's own tables for core, and core's
    plus the extension's own for an extension. R17 §2 makes the direction one-way and §4 declines
    dependency resolution, so an extension reaching another extension's table is not a reference
    a packet can be relied on to satisfy.
    """
    def c_(label, bad, fmt=str):
        check(f"{prefix}{label}", bad, fmt)

    cols = {n: {c["name"]: c for c in t["columns"]} for n, t in tables.items()}
    ucols = {n: {c["name"]: c for c in t["columns"]} for n, t in universe.items()}
    c_("every table declares a primary key", [n for n, t in tables.items() if t["primary_key"] is None])
    c_("every column type is in R2 §4's vocabulary",
       [(n, c["name"], c["type"]) for n, t in tables.items() for c in t["columns"]
        if c["type"] not in VOCAB])
    c_("no required column is json_string",
       [(n, c["name"]) for n, t in tables.items() for c in t["columns"]
        if c["type"] == "json_string" and c["presence"] != "optional"])
    c_("no nested type spellings survived",
       [(n, c["name"], c["type"]) for n, t in tables.items() for c in t["columns"]
        if any(k in c["type"] for k in ("list", "struct", "map"))])
    c_("primary key columns exist",
       [(n, k) for n, t in tables.items() for k in (t["primary_key"] or []) if k not in cols[n]])
    c_("primary key columns are required",
       [(n, k) for n, t in tables.items() for k in (t["primary_key"] or [])
        if k in cols[n] and cols[n][k]["presence"] != "required"])
    # R10 §2's override names columns, and a revision that narrows a key leaves them behind:
    # `aind_unit_qc` kept sorting by two columns R81 had removed, which no packet could satisfy
    # and no rule could see, because a sort is physical and SQL cannot read it (R12 §4).
    c_("sort columns exist",
       [(n, k) for n, t in tables.items() for k in (t.get("sort") or []) if k not in cols[n]])
    c_("reference targets exist",
       [(n, r["resource"]) for n, t in tables.items() for r in t["references"]
        if r["resource"] not in universe])
    c_("reference source columns exist",
       [(n, c) for n, t in tables.items() for r in t["references"] for c in r["columns"]
        if c not in cols[n]])
    c_("reference target columns exist",
       [(n, r["resource"], c) for n, t in tables.items() for r in t["references"]
        if r["resource"] in universe for c in r["resource_columns"] if c not in ucols[r["resource"]]])
    c_("reference arity matches",
       [(n, r["resource"]) for n, t in tables.items() for r in t["references"]
        if len(r["columns"]) != len(r["resource_columns"])])
    # R48 §2.3. A structural index may also be a foreign-key component, so a client converting one
    # side and not the other would break the join. Both sides sharing a role is what makes
    # converting every structural_index column join-preserving by construction.
    role = {(n, c["name"]): c["role"] for n, t in universe.items() for c in t["columns"]}
    c_("a reference relates columns of the same role",
       [(n, a, r["resource"], b) for n, t in tables.items() for r in t["references"]
        for a, b in zip(r["columns"], r["resource_columns"])
        if role.get((n, a)) != role.get((r["resource"], b))])
    # R53 §2.3 with R48 §2.3's reasoning: `number` resolves an assigned identifier through its
    # target's map and coerces a carried one, so a reference across the two numbers each side
    # differently and resolves to nothing. Decidable here, and invisible until a packet is built.
    identity = {(n, c["name"]): c.get("identity") for n, t in universe.items() for c in t["columns"]}
    c_("a reference relates columns of the same identity",
       [(n, a, r["resource"], b) for n, t in tables.items() for r in t["references"]
        for a, b in zip(r["columns"], r["resource_columns"])
        if role.get((n, a)) == "identifier" and identity.get((n, a)) != identity.get((r["resource"], b))])
    c_("source labels are strings",
       [(n, c["name"], c["type"]) for n, t in tables.items() for c in t["columns"]
        if c["name"].endswith("_label") and c["type"] != "string"])


structural(T, T)
for _id, _doc in EXT.items():
    structural(_doc["tables"], T | _doc["tables"], prefix=f"{_id}: ")

# R17 §2's MUST, stated rather than implied: core resolving against itself above cannot see a
# reference *into* an extension, because such a target would simply be absent from core.
check("core references no extension",
      [(n, r["resource"]) for n, t in T.items() for r in t["references"]
       if r["resource"] in EXT_T])
check("an extension's tables carry its own namespace",
      [f"{_id}: {n}" for _id, _doc in EXT.items() for n in _doc["tables"]
       if not n.startswith(f"{_doc.get('extension_id', _id)}.")])
check("an extension's file name is its extension_id",
      [f"{_id}: declares {_doc.get('extension_id')!r}" for _id, _doc in EXT.items()
       if _doc.get("extension_id") != _id])
check("every extension extends the logical standard",
      [_id for _id, _doc in EXT.items() if _doc.get("extends") != "escapewheel-logical-v0.1"])
# R57 §4: the check the key exists for. A meta-schema URI resolves to nothing over the network,
# so what makes the declaration worth carrying is that it is verifiable offline against the
# schema in hand -- a document drafted against an older format says so here rather than failing
# later as findings about its tables.
META_ID = json.loads((HERE / "registry.schema.json").read_text())["$id"]
check("every registry document names this meta-schema",
      [f"{_n}: {_d.get('$schema', 'declares none')}"
       for _n, _d in {"logical_schemas": REG, **EXT}.items() if _d.get("$schema") != META_ID])

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
ids = [r["id"] for r in authored_rules] + [r["id"] for t_ in EXT_T.values() for r in t_["rules"]]
check("rule ids are unique across core and every extension",
      sorted({i for i in ids if ids.count(i) > 1}))
check("an extension's rule ids carry its table's name",
      [r["id"] for n, t_ in EXT_T.items() for r in t_["rules"] if not r["id"].startswith(f"{n}.")])


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
    "core.media_frames.pts": "the container's own initialism for one timestamp, not a plural (R68 §2.1)",
    # A metric's name is the vocabulary people search by, so renaming one makes the column match
    # nothing anyone's code expects. Unlike `sync_spike_8`, none of these is a parameter glued on.
    "aind_unit_qc.metrics.rp_violations": "the sorter's own metric name; a count of violations",
    "aind_unit_qc.waveform_metrics.num_negative_peaks": "the sorter's own metric name; a count of peaks",
    "aind_unit_qc.waveform_metrics.num_positive_peaks": "as num_negative_peaks",
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
    # R55 §2.1. A discriminator holds a dotted resource ID, so it is a string by construction,
    # and the `_kind` suffix is what R49 chose for the first one.
    "a _kind column is a discriminator": lambda n, t, role: not (
        n.endswith("_kind") and role != "discriminator"),
    "a discriminator is named _kind": lambda n, t, role: not (
        role == "discriminator" and not n.endswith("_kind")),
    "a discriminator is a string": lambda n, t, role: not (role == "discriminator" and t != "string"),
}

flagged = {}
for label, holds in NAMING.items():
    for tid, tbl in ALL.items():
        for c in tbl["columns"]:
            if not holds(c["name"], c["type"], c.get("role")):
                flagged.setdefault(f"{tid}.{c['name']}", []).append(label)
check("column names follow the conventions, or say why not",
      sorted(f"{k}: {', '.join(v)}" for k, v in flagged.items() if k not in NAMING_EXCEPTIONS))
check("every declared naming exception still exists and still breaks a convention",
      sorted(k for k in NAMING_EXCEPTIONS if k not in flagged))
print(f"      {len(NAMING)} conventions over {sum(len(t['columns']) for t in ALL.values())} columns "
      f"in core and {len(EXT)} extensions, "
      f"{len(NAMING_EXCEPTIONS)} declared exceptions")


# R55 §2.2, §2.3.2. What a discriminator declares, checked where the meta-schema cannot: the
# enum constrains the value but not that a discriminator has one, and `resolves` on anything else
# is a declaration that decides nothing.
_disc = []
for _r, _t in ALL.items():
    _names = {_c["name"] for _c in _t["columns"]}
    for _c in _t["columns"]:
        _is = _c.get("role") == "discriminator"
        if _is and "resolves" not in _c:
            _disc.append(f"{_r}.{_c['name']}: a discriminator declares no resolves")
        for _field in ("resolves", "discriminates"):
            if _field in _c and not _is:
                _disc.append(f"{_r}.{_c['name']}: {_field} on a {_c.get('role')}, not a discriminator")
        # A paired value lives in the named table's key space, so it is an identifier here too.
        if (_paired := _c.get("discriminates")) is not None:
            if _paired not in _names:
                _disc.append(f"{_r}.{_c['name']}: discriminates {_paired}, which is not a column here")
check("a discriminator declares what it resolves to", sorted(_disc))

# R55 §2.3.3. A paired value is a string, and not by accident: one column resolves against
# several kinds, and an assigned key is matched by its `*_name` where a carried one is matched by
# the number itself, so the union it joins mixes types by construction.
check("a paired value is a string",
      sorted(f"{_r}.{_c['discriminates']} is declared "
             f"{next(x for x in _t['columns'] if x['name'] == _c['discriminates'])['type']}"
             for _r, _t in ALL.items() for _c in _t["columns"]
             if _c.get("discriminates") and any(
                 x["name"] == _c["discriminates"] and x["type"] != "string" for x in _t["columns"])))

# R55 §2.3.1: a paired value holds one identifier, so it can only name a resource whose key is one
# column. Reported rather than enforced -- the kind vocabulary is open (R49 §2.4), so what this can
# say is which resources are namable at all, which is otherwise found by a check quietly matching
# no branch.
NAMABLE = {_r: _t["primary_key"][0] for _r, _t in ALL.items()
           if _t.get("primary_key") and len(_t["primary_key"]) == 1}
# R55 §2.3.3: which column a paired value matches follows from the key's identity, so the split
# is a property of the registry and is reported rather than rediscovered per consumer.
_by_name = {_r for _r, _k in NAMABLE.items()
            if next(c for c in ALL[_r]["columns"] if c["name"] == _k).get("identity") == "assigned"
            and any(c["name"] == _k.removesuffix("_id") + "_name" for c in ALL[_r]["columns"])}
_core = {_r for _r in NAMABLE if _r in T}
print(f"      {len(_core)} of {len(T)} core resources have a single-column key "
      f"({len(NAMABLE)} of {len(ALL)} with extensions); "
      f"{len(_by_name & _core)} of those resolve by name, {len(_core - _by_name)} by key")
# A single-column key is necessary and not sufficient. An assigned identifier a table does not
# *own* -- it is exported through a reference, so R53 §2.3.1 puts the name on the owner -- has no
# column a value written before the build could match, so the resource is simply not namable.
# vr_foraging.sessions is the instance: its session_id belongs to core.sessions.
_unnamable = sorted(_r for _r, _k in NAMABLE.items() if _r not in _by_name
                    and next(c for c in ALL[_r]["columns"] if c["name"] == _k).get("identity") == "assigned")
for _r in _unnamable:
    print(f"      note  {_r} has a single-column key but no name to match, so a scope cannot name it")

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
    if target not in ALL:
        return f"{value} names no resource"
    if not any(ref["resource"] == target for ref in spec["references"]):
        return f"{resource} declares no reference to {target}, so the hop is not one this table can make"
    if column not in {c["name"] for c in ALL[target]["columns"]}:
        return f"{target} has no column {column}"
    return None


bad_context = []
for _r, _t in ALL.items():
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

# The same argument one level up: a count restated in prose goes stale, and this one did --
# 33 tables against 34, 51 rules against 61, and two rules revisions had removed.
import render  # noqa: E402 - after the ledger, so a broken build fails first

_readme = (HERE / "README.md").read_text()
check("README's generated regions are current",
      [] if render.fill(_readme, render.regions(REG)) == _readme else ["README.md is stale; run build.py"])

# R2 §9: the registry validates against its published meta-schema.
try:
    import jsonschema
    meta = json.loads((HERE / "registry.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(meta)
    errs = list(jsonschema.Draft202012Validator(meta).iter_errors(REG))
    check("registry validates against its meta-schema",
          [f"{list(e.path)[:4]}: {e.message[:60]}" for e in errs])
    validator = jsonschema.Draft202012Validator(meta)
    check("every extension validates against the same meta-schema",
          [f"{_id}: {list(e.path)[:4]} {e.message[:50]}"
           for _id, _doc in EXT.items() for e in validator.iter_errors(_doc)])
    manifest = json.loads((HERE / "manifest.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(manifest)
    check("manifest schema is valid JSON Schema", [])
    # R80 §2.2's sidecar is specified the way the manifest is, so it is checked the way the
    # manifest is: valid JSON Schema here, vendored by build.py, compared by the loop above.
    _sources = json.loads((HERE / "sources.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(_sources)
    check("source resolution schema is valid JSON Schema", [])
    _example = HERE / "sources.example.json"
    check("the example resolution document validates against it",
          [f"{list(e.path)[:4]} {e.message[:60]}"
           for e in jsonschema.Draft202012Validator(_sources).iter_errors(
               json.loads(_example.read_text()))] if _example.exists() else [])
    # The prototype argues that the format drives the tooling, which is worth nothing if its
    # own input is a document the format rejects. It drifted 16 errors out of conformance
    # unnoticed -- 13 columns with no `role` after R48, two tables with no `rules`.
    _proto = HERE.parent / "prototype/registry-codegen/registry.json"
    check("the registry-codegen prototype's document validates against the meta-schema",
          [f"{list(e.path)[:4]} {e.message[:60]}"
           for e in validator.iter_errors(json.loads(_proto.read_text()))] if _proto.exists() else [])
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
    for n, t_ in ALL.items():
        cols = ", ".join(f'"{c["name"]}" {DDL[c["type"]]}' for c in t_["columns"])
        con.sql(f"CREATE TABLE {n.replace('.', '_')} ({cols})")
    con.sql("CREATE TABLE manifest_sessions (session_id VARCHAR)")   # supplied by the shim
    broken = []
    for n, t_ in ALL.items():
        for r in t_["rules"]:
            try:
                con.sql(r["sql"]).fetchall()
            except Exception as e:
                broken.append((r["id"], str(e).splitlines()[0][:70]))
    check("every Tier 2 rule is executable SQL", broken)
    print(f"      {sum(len(t_['rules']) for t_ in ALL.values())} rules executed against "
          f"{len(ALL)} empty tables")
except ImportError:
    print("skip  rule execution (duckdb not available)")

print(f"\n{len(T)} tables, {sum(len(t['columns']) for t in T.values())} columns, "
      f"{sum(len(t['references']) for t in T.values())} references")
print(f"{len(EXT)} extensions: {len(EXT_T)} tables, "
      f"{sum(len(t['columns']) for t in EXT_T.values())} columns, "
      f"{sum(len(t['references']) for t in EXT_T.values())} references")
raise SystemExit(1 if fail else 0)
