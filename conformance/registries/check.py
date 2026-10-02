"""Check the registries against what lies outside the specification's tree.

The tree's `check.py` decides everything the tree alone can. These need something it does not
hold: the frozen v0.1 Part 02, and an engine to execute the Tier 2 rules of the core registry and
every extension in the repository.

    python conformance/registries/check.py [EXTENSION.json ...]

An extension document named on the command line is checked in place of the repository's document
with its `extension_id`, or beside them where none has it. A rule the reference validator cannot
lower is reported apart from one that is invalid or does not execute: the rule is valid, and every
packet binding it reports that rule incomplete (Part 11 §8).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import duckdb
from escapewheel_validator.errors import LoweringFailed
from escapewheel_validator.lowering import lower
from escapewheel_validator.rule_language import RuleProfileError, check_rule

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "spec/artifacts"
EXTENSIONS = (ROOT / "extensions", ROOT / "escapewheel-aind/extensions")
DDL = {
    "string": "VARCHAR",
    "int32": "INTEGER",
    "int64": "BIGINT",
    "float32": "FLOAT",
    "float64": "DOUBLE",
    "bool": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMPTZ",
    "json_string": "VARCHAR",
}
#: A valid rule the lowering cannot place a conversion in: a `USING` join of a `DECIMAL` with a
#: `DOUBLE PRECISION` column, whose join condition is made by qualification and not authored.
UNLOWERABLE = (
    "SELECT x.k FROM (SELECT CAST(tick_rate_num AS DECIMAL(38,0)) AS k FROM core.clocks) AS x "
    "INNER JOIN (SELECT transform_slope AS k FROM core.clocks) AS y USING (k)"
)
fail = []


def check(label, bad):
    bad = list(bad)
    print(f"{'FAIL' if bad else 'ok  '}  {label}" + (f"  ({len(bad)})" if bad else ""))
    for item in bad[:4]:
        print(f"          {item}")
    if bad:
        fail.append(label)


def tables(document):
    return {name: entry["table"] for name, entry in document["resources"].items() if entry["kind"] == "table"}


def evaluate(sql, document):
    """Return None for a rule the engine runs as lowered, or the kind of failure and its message."""
    try:
        check_rule(sql, document, core_resources=CORE)
        try:
            lowered, unlowered = lower(sql, ALL), None
        except LoweringFailed as failure:
            # The authored text still shows whether the rule binds and executes.
            lowered, unlowered = sql, ("unevaluable", str(failure))
        connection.sql(lowered).fetchall()
    except (RuleProfileError, duckdb.Error) as error:
        return "broken", str(error).splitlines()[0][:70]
    return unlowered


CORE = json.loads((ARTIFACTS / "logical_schemas.json").read_text())
named = [json.loads(Path(argument).read_bytes()) for argument in sys.argv[1:]]
replaced = {document["extension_id"] for document in named}
shipped = [json.loads(path.read_text()) for directory in EXTENSIONS for path in sorted(directory.glob("*.json"))]
DOCUMENTS = [CORE, *(d for d in shipped if d["extension_id"] not in replaced), *named]
ALL = {name: table for document in DOCUMENTS for name, table in tables(document).items()}

# The frozen v0.1 Part 02 and the accepted revisions derive the core table set independently.
ledger = subprocess.run(
    [sys.executable, str(ROOT / "conformance/spec-sweep/tables.py")], capture_output=True, text=True, check=False
).stdout
RESOURCE_ID = re.compile(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")
expected = {line.strip() for line in ledger.splitlines() if RESOURCE_ID.fullmatch(line.strip())}
check("the core table set matches the Part 02 ledger", expected ^ set(tables(CORE)))

# Every rule is valid SQL naming real columns: empty tables built from the registries check syntax
# and identifiers without a packet.
connection = duckdb.connect()
connection.sql("SET TimeZone = 'UTC'")
for namespace in sorted({name.split(".", 1)[0] for name in ALL}):
    connection.sql(f"CREATE SCHEMA {namespace}")
for name, table in ALL.items():
    columns = ", ".join(f'"{c["name"]}" {DDL[c["type"]]}' for c in table["columns"])
    connection.sql(f"CREATE TABLE {name} ({columns})")
outcomes = {"broken": [], "unevaluable": []}
for document in DOCUMENTS:
    for table in tables(document).values():
        for rule in table["rules"]:
            outcome = evaluate(rule["sql"], document)
            if outcome is not None:
                outcomes[outcome[0]].append((rule["id"], outcome[1]))
check("every Tier 2 rule conforms and executes against empty tables", outcomes["broken"])
check("the reference validator can evaluate every Tier 2 rule as Part 11 defines it", outcomes["unevaluable"])
outcome = evaluate(UNLOWERABLE, CORE)
check(
    "a valid rule the lowering refuses is reported as one the validator cannot evaluate",
    [] if outcome is not None and outcome[0] == "unevaluable" else [outcome],
)
print(f"      {sum(len(t['rules']) for t in ALL.values())} rules checked against {len(ALL)} empty tables")
raise SystemExit(1 if fail else 0)
