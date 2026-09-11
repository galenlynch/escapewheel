"""Validate a packet against the registry.

Two layers, matching R2 §7: a schema check that SQL cannot express (does the column
exist, is its type right), then the generated SQL checks executed by DuckDB.
"""
import sys
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from generate import generate, load, sql_name

# Registry type -> the pyarrow type a conforming writer must emit (`03` §5.5).
ARROW = {"string": "string", "int32": "int32", "int64": "int64", "float32": "float",
         "float64": "double", "bool": "bool", "date": "date32[day]",
         "timestamp": "timestamp[us, tz=UTC]", "json_string": "string"}


def check_schemas(registry: dict, packet: Path) -> list[str]:
    """Column presence and physical type. Not expressible in SQL over the data."""
    findings = []
    for resource, table in registry["tables"].items():
        path = packet / f"{sql_name(resource)}.parquet"
        if not path.exists():
            findings.append(f"{resource}: resource missing")
            continue
        schema = pq.read_schema(path)
        for column in table["columns"]:
            name, expected = column["name"], ARROW[column["type"]]
            if name not in schema.names:
                if column["presence"] != "optional":
                    findings.append(f"{resource}.{name}: column absent "
                                    f"(presence={column['presence']})")
                continue
            actual = str(schema.field(name).type)
            if actual != expected:
                findings.append(f"{resource}.{name}: type is {actual}, expected {expected}")
    return findings


def run_checks(registry: dict, packet: Path):
    con = duckdb.connect()
    for resource in registry["tables"]:
        t = sql_name(resource)
        con.sql(f"CREATE VIEW {t} AS SELECT * FROM '{packet / (t + '.parquet')}'")
    results = []
    for check in generate(registry):
        rows = con.sql(check["sql"]).fetchall()
        results.append((check, rows))
    return results


def main(packet: Path) -> int:
    registry = load(Path(__file__).parent / "registry.json")

    schema_findings = check_schemas(registry, packet)
    for f in schema_findings:
        print(f"  schema   error    {f}")

    errors = len(schema_findings)
    warnings = 0
    for check, rows in run_checks(registry, packet):
        if not rows:
            continue
        errors += check["level"] == "error"
        warnings += check["level"] == "warning"
        print(f"  {check['level']:8s} {check['id']}: {check['message']}")
        for row in rows[:5]:
            print(f"                    {row}")

    print(f"\n{packet.name}: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "packets/broken"
    raise SystemExit(main(target))
