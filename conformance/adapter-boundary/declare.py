"""An adapter's declarations as a document, read before anything is launched.

`PRODUCES`, `STATES` and `NEEDS` are class attributes, so a build reads them by importing the
adapter -- the one thing an adapter in another language cannot offer. This writes the same four
facts as a JSON document, settles ownership from the documents alone, and checks what a build must
refuse. The values behind `STATES` are the part no document can carry, since they need the source
read, so they come back in the run's report.

    uv run --project ../../escapewheel-writer python declare.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# The NWB fixture the writer's and aind's suites share.
sys.path.insert(0, str(HERE.parent.parent / "fixtures/shared"))

import build_side
import nwbfixture
import serve_nwb
from escapewheel_writer.adapter import ADAPTERS

REGISTRY_DOCUMENT = json.loads((HERE.parent.parent / "spec" / "artifacts" / "logical_schemas.json").read_text())
REGISTRY = {
    name: declaration["table"]
    for name, declaration in REGISTRY_DOCUMENT["resources"].items()
    if declaration["kind"] == "table"
}

#: Which core table each recipe block supplies, so a `states` entry resolves to a column and a
#: build can refuse one that names no field the recipe has.
BLOCKS = {"session": "core.sessions", "subject": "core.subjects"}

#: The protocols `escapewheel-portable-v0.1` names, for checking a declared one.
GROUP = ("files-v0.1", "stream-v0.1", "flight-v0.1")


def declaration(kind: str, protocol: str, needs: tuple[str, ...] | None = None) -> dict:
    """One adapter's own properties, as the document a build reads instead of importing it.

    Every field is read off the class, which is what makes generating the document rather than
    maintaining it possible; `needs` is overridable so a refusal can be exercised against a name
    no adapter declares.
    """
    cls = ADAPTERS[kind]
    return {
        "$schema": "https://escapewheel.org/schemas/adapter/0.1.0",
        "kind": kind,
        "protocol": protocol,
        "produces": sorted(getattr(cls, "PRODUCES", ())),
        "states": sorted(getattr(cls, "STATES", {})),
        "needs": list(getattr(cls, "NEEDS", ()) if needs is None else needs),
        "consumes": list(getattr(cls, "CONSUMES", ())),
    }


def refusals(doc: dict, options: dict) -> list[str]:
    """What a build refuses a declaration for, reading it and the registry and nothing else."""
    out = []
    if doc["protocol"] not in GROUP:
        out.append(f"protocol {doc['protocol']} is in no group of this profile")
    for resource in doc["produces"]:
        if resource not in REGISTRY:
            out.append(f"produces {resource}, which no loaded registry declares")
    for field in doc["states"]:
        block, _, name = field.partition(".")
        resource = BLOCKS.get(block)
        if resource is None:
            out.append(f"states {field}, whose block is not one the recipe carries")
        elif name not in {c["name"] for c in REGISTRY[resource]["columns"]}:
            out.append(f"states {field}, which is no column of {resource}")
    for term in doc["needs"]:
        if term not in build_side.SUPPLIABLE and term not in options:
            out.append(f"needs {term}, neither a term nor an option this recipe sets")
    return out


def owners(docs: list[dict]) -> dict[str, str]:
    """Part 05 §3.4's default ownership, settled from the documents and no adapter."""
    claims: dict[str, list[str]] = {}
    for doc in docs:
        for resource in doc["produces"]:
            claims.setdefault(resource, []).append(doc["kind"])
    return {r: kinds[0] for r, kinds in claims.items() if len(kinds) == 1}


def main() -> int:
    options = {"zone": "America/Los_Angeles", "interval_kind": "task.trials"}
    docs = [declaration(kind, "stream-v0.1", serve_nwb.NEEDS if kind == "nwb" else ()) for kind in sorted(ADAPTERS)]

    print("1. one document per shipped adapter\n")
    for doc in docs:
        text = json.dumps(doc, indent=2)
        print(
            f"   {doc['kind']:11s} {len(text):>5} bytes  "
            f"{len(doc['produces']):>2} produces, {len(doc['states'])} states, "
            f"{len(doc['needs'])} needs, {len(doc['consumes'])} consumes"
        )
    print(f"\n   the NWB adapter's, in full:\n{json.dumps(docs[2], indent=2)}\n")

    print("2. ownership settled from the documents, with nothing imported\n")
    from_docs = owners(docs)
    contested = sorted({r for doc in docs for r in doc["produces"]} - set(from_docs))
    print(f"   {len(from_docs)} resources have one producer, {len(contested)} more than one")
    from_classes = owners(
        [{"kind": k, "produces": sorted(getattr(c, "PRODUCES", ()))} for k, c in sorted(ADAPTERS.items())]
    )
    print(f"   same as reading the classes: {from_docs == from_classes}")

    print("\n3. what a build refuses, per broken declaration\n")
    good = declaration("nwb", "stream-v0.1", serve_nwb.NEEDS)
    print(f"   the sound one: {refusals(good, options) or 'nothing'}")
    for label, broken in (
        ("a protocol no group names", {**good, "protocol": "carrier-pigeon-v1"}),
        (
            "a resource the registry lacks",
            {**good, "produces": [*good["produces"], "core.tirals"]},
        ),
        (
            "a field no block has",
            {**good, "states": [*good["states"], "subject.sbuject_id"]},
        ),
        ("a term nothing resolves", {**good, "needs": [*good["needs"], "open_store"]}),
    ):
        print(f"   {label:32s} {refusals(broken, options)}")

    print("\n4. the values behind `states`, which no document can carry\n")
    with tempfile.TemporaryDirectory(dir="/mnt/Data") as tmp:
        root = nwbfixture.build(Path(tmp))
        report = Path(tmp) / "report.json"
        held = {
            "root": str(root),
            "session_id": build_side.SESSION,
            "reference_clock": {
                "clock_id": "harp",
                "session_id": build_side.SESSION,
                "origin": "HARP epoch",
                "tick_rate_num": 31_250,
                "tick_rate_den": 1,
                "metadata": {"label": "HARP"},
            },
            "wanted": ["core.sessions"],
        }
        supplied = build_side.supply(serve_nwb.NEEDS, held, options)
        child = subprocess.run(
            [sys.executable, str(HERE / "serve_stream.py")],
            input=json.dumps({**supplied, "report_path": str(report)}).encode(),
            stdout=subprocess.DEVNULL,
            env={**os.environ, "PYTHONPATH": str(HERE)},
            check=True,
        )
        stated = json.loads(report.read_text())["stated"]
        print(f"   the report is {report.stat().st_size} bytes, exit {child.returncode}")
        for field, value in stated.items():
            print(f"     {field:28s} {value!r}")
        declared = {"subject.subject_id": "786867"}
        for field, value in declared.items():
            verdict = "agrees" if stated.get(field) == value else "DIFFERS"
            print(f"\n   the recipe declares {field} = {value!r}: {verdict}")
            if verdict == "DIFFERS":
                print(f"   the source states {stated.get(field)!r}, which Part 05 §3.6 refuses on")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
