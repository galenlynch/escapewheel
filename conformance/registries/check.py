"""Check the registries against what lies outside the specification's tree.

The tree's `check.py` decides everything the tree alone can. These need something it does not
hold: the frozen v0.1 Part 02, and an engine to execute the Tier 2 rules of the core registry and
every extension in the repository.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import duckdb
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


CORE = json.loads((ARTIFACTS / "logical_schemas.json").read_text())
EXTENSION_PATHS = [path for directory in EXTENSIONS for path in sorted(directory.glob("*.json"))]
DOCUMENTS = [CORE, *(json.loads(path.read_text()) for path in EXTENSION_PATHS)]
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
broken = []
for document in DOCUMENTS:
    for table in tables(document).values():
        for rule in table["rules"]:
            try:
                check_rule(rule["sql"], document, core_resources=CORE)
                connection.sql(lower(rule["sql"])).fetchall()
            except (RuleProfileError, duckdb.Error) as error:
                broken.append((rule["id"], str(error).splitlines()[0][:70]))
check("every Tier 2 rule conforms and executes against empty tables", broken)
print(f"      {sum(len(t['rules']) for t in ALL.values())} rules checked against {len(ALL)} empty tables")
raise SystemExit(1 if fail else 0)
