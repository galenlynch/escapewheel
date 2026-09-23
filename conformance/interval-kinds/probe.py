"""Does a session with several interval kinds want one base table, or one table per kind?

Part 01 §3.10 argues for a base table on the strength of a polymorphic query -- align to every
interval in a session without knowing the paradigm -- and R54 §5 records that nothing does that
yet, so the argument is unmeasured. This builds both shapes over the same rows and asks what each
costs a consumer.

Neither shape is in the registry: R54 is proposed. Both are constructed here from a copy, which is
what makes this a probe rather than an implementation.
"""

import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = json.loads(
    (HERE.parent.parent / "registry" / "logical_schemas.json").read_text()
)
SESSION, N_TRIALS, N_PULSES = "ecephys_776259", 400, 120


def col(name, type_, presence, role, **extra):
    entry = {
        "name": name,
        "type": type_,
        "presence": presence,
        "role": role,
        "description": name,
    }
    if role == "identifier":
        entry.setdefault("identity", "assigned")
    return {**entry, **extra}


def base_registry():
    """Part 01 §3.10: one `core.intervals`, keyed by (session, kind, id)."""
    registry = json.loads(json.dumps(REGISTRY))
    registry["resources"]["core.intervals"] = {
        "content_class": "core",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "producing_run": "optional",
        "table": {
            "columns": [
                col("session_id", "int32", "required", "identifier"),
                # R55 would make this `discriminator`; that role does not exist yet, so `data`.
                col("interval_kind", "string", "required", "data"),
                col(
                    "interval_id", "int32", "required", "identifier", identity="carried"
                ),
                col("clock_id", "int32", "required", "identifier"),
                col(
                    "start_tick",
                    "int64",
                    "required",
                    "coordinate",
                    clock_from="clock_id",
                ),
                col(
                    "stop_tick",
                    "int64",
                    "required",
                    "coordinate",
                    clock_from="clock_id",
                ),
            ],
            "primary_key": ["session_id", "interval_kind", "interval_id"],
            "references": [
                {
                    "columns": ["session_id"],
                    "resource": "core.sessions",
                    "resource_columns": ["session_id"],
                },
                {
                    "columns": ["clock_id"],
                    "resource": "core.clocks",
                    "resource_columns": ["clock_id"],
                },
            ],
            "sort": ["session_id", "interval_kind", "interval_id"],
            "rules": [],
        },
    }
    return registry


def detail(extension_id, table, extra, *, based):
    """One kind's detail table. Under the base shape it references `core.intervals` and carries no
    interval of its own; under the concrete shape it carries the interval too."""
    key = ["session_id", f"{'interval' if based else table[:-1]}_id"]
    columns = [
        col("session_id", "int32", "required", "identifier"),
        col(key[1], "int32", "required", "identifier", identity="carried"),
    ]
    references = [
        {
            "columns": ["session_id"],
            "resource": "core.sessions",
            "resource_columns": ["session_id"],
        }
    ]
    if based:
        # Part 02 §8.3: the named resource declares the reference back, which is what makes the
        # join mechanical rather than inferred from names matching.
        references.append(
            {
                "columns": ["session_id", "interval_id"],
                "resource": "core.intervals",
                "resource_columns": ["session_id", "interval_id"],
            }
        )
    else:
        columns += [
            col("clock_id", "int32", "required", "identifier"),
            col("start_tick", "int64", "required", "coordinate", clock_from="clock_id"),
            col("stop_tick", "int64", "required", "coordinate", clock_from="clock_id"),
        ]
        references.append(
            {
                "columns": ["clock_id"],
                "resource": "core.clocks",
                "resource_columns": ["clock_id"],
            }
        )
    return {
        "$schema": "https://escapewheel.org/schemas/registry/0.5.0",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.1",
        "extension_id": extension_id,
        "resources": {
            f"{extension_id}.{table}": {
                "content_class": "extension",
                "kind": "table",
                "instances": {"mode": "singleton", "presence": "optional"},
                "requires": [],
                "lineage": "optional",
                "producing_run": "optional",
                "table": {
                    "columns": columns + extra,
                    "primary_key": key,
                    "references": references,
                    "sort": key,
                    "rules": [],
                },
            }
        },
    }


TASK_COLUMNS = [
    col("choice", "string", "nullable", "data", enum=["left", "right", "none"]),
    col("rewarded", "bool", "nullable", "data"),
]
OPTO_COLUMNS = [
    col("wavelength_nm", "int32", "nullable", "data"),
    col("power_mw", "float64", "nullable", "data"),
]


def rows(based):
    """The same session either way: 400 task trials and 120 opto pulses, interleaved in time."""
    intervals, task, opto = [], [], []
    for i in range(N_TRIALS):
        start = i * 10_000
        if based:
            intervals.append(
                {
                    "session_id": SESSION,
                    "interval_kind": "dynamic_foraging.trials",
                    "interval_id": i,
                    "clock_id": "harp",
                    "start_tick": start,
                    "stop_tick": start + 8_000,
                }
            )
        task.append(
            {
                "session_id": SESSION,
                ("interval_id" if based else "trial_id"): i,
                "choice": ["left", "right", "none"][i % 3],
                "rewarded": i % 4 == 0,
                **(
                    {}
                    if based
                    else {
                        "clock_id": "harp",
                        "start_tick": start,
                        "stop_tick": start + 8_000,
                    }
                ),
            }
        )
    for j in range(N_PULSES):
        start = 5_000 + j * 33_000
        if based:
            intervals.append(
                {
                    "session_id": SESSION,
                    "interval_kind": "optotagging.pulses",
                    "interval_id": j,
                    "clock_id": "harp",
                    "start_tick": start,
                    "stop_tick": start + 50,
                }
            )
        opto.append(
            {
                "session_id": SESSION,
                ("interval_id" if based else "pulse_id"): j,
                "wavelength_nm": 473,
                "power_mw": 2.5 + (j % 3),
                **(
                    {}
                    if based
                    else {
                        "clock_id": "harp",
                        "start_tick": start,
                        "stop_tick": start + 50,
                    }
                ),
            }
        )
    return intervals, task, opto


def build(root, *, based):
    from escapewheel_writer import PacketWriter

    registry = base_registry() if based else json.loads(json.dumps(REGISTRY))
    extensions = [
        detail("dynamic_foraging", "trials", TASK_COLUMNS, based=based),
        detail("optotagging", "pulses", OPTO_COLUMNS, based=based),
    ]
    writer = PacketWriter(registry, packet_id=root.name, extensions=extensions)
    writer.add(
        "core.subjects",
        [{"subject_id": "m776259", "species": "Mus musculus", "sex": "male"}],
    )
    writer.add(
        "core.sessions",
        [
            {
                "session_id": SESSION,
                "subject_id": "m776259",
                "session_start_time": "2026-04-09T17:25:12Z",
                "reference_clock_id": "harp",
            }
        ],
    )
    writer.add(
        "core.clocks",
        [
            {
                "clock_id": "harp",
                "session_id": SESSION,
                "name": "HARP",
                "tick_rate_hz": 31250.0,
                "origin": "HARP epoch",
            }
        ],
    )
    intervals, task, opto = rows(based)
    if based:
        writer.add("core.intervals", intervals)
    writer.add("dynamic_foraging.trials", task)
    writer.add("optotagging.pulses", opto)
    report = writer.commit(root)
    return report


def ask(root, *, based):
    """The two questions Part 01 §3.10 claims the base table answers, and what each costs."""
    from escapewheel_reader import open_packet

    packet = open_packet(root)
    out = {}

    # Generic on purpose: a consumer that has never heard of either extension. Naming them would
    # answer a different question -- Part 01 §3.10's claim is about not having to.
    t = time.perf_counter()
    if based:
        every = packet.table("core.intervals")
        out["every interval"] = (
            every.num_rows,
            "1 scan of one known name",
            time.perf_counter() - t,
        )
    else:
        # Nothing declares "this is an alignable interval set", so the only way to find one is to
        # guess from its columns -- and the guess is wrong: it also matches every observation
        # interval table in core, which R54 §3 says is a different thing entirely.
        found, wrong = [], []
        for document in packet.extensions().values():
            for resource, declaration in document["resources"].items():
                if declaration["kind"] != "table":
                    continue
                spec = declaration["table"]
                names = {c["name"] for c in spec["columns"]}
                if {"start_tick", "stop_tick"} <= names:
                    found.append(resource)
        for resource, declaration in (
            (packet.registry or {}).get("resources", {}).items()
        ):
            if declaration["kind"] != "table":
                continue
            spec = declaration["table"]
            names = {c["name"] for c in spec["columns"]}
            if {"start_tick", "stop_tick"} <= names:
                wrong.append(resource)
        total = sum(packet.table(r).num_rows for r in found)
        out["every interval"] = (
            total,
            f"{len(found)} found by guessing at columns",
            time.perf_counter() - t,
        )
        out["  ...and wrongly"] = (
            len(wrong),
            f"core tables the guess also matches: {', '.join(sorted(wrong))}",
            0.0,
        )

    t = time.perf_counter()
    if based:
        import pyarrow.compute as pc

        every = packet.table("core.intervals")
        kind = "optotagging.pulses"
        chosen = every.filter(pc.equal(every["interval_kind"], kind))
        # The kind IS the resource id, and the registry gives the join. No extension named here.
        registry = packet.extensions()[kind.split(".")[0]]
        reference = next(
            r
            for r in registry["resources"][kind]["table"]["references"]
            if r["resource"] == "core.intervals"
        )
        detail_table = packet.table(kind)
        joined = chosen.join(
            detail_table,
            keys=reference["resource_columns"],
            right_keys=reference["columns"],
        )
        out["one kind, with detail"] = (
            joined.num_rows,
            "filter + declared join",
            time.perf_counter() - t,
        )
    else:
        detail_table = packet.table("optotagging.pulses")
        out["one kind, with detail"] = (
            detail_table.num_rows,
            "1 scan, name known ahead",
            time.perf_counter() - t,
        )
    return out


def main():
    scratch = Path("/mnt/Data/escapewheel/scratch/interval-kinds")
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    for based in (True, False):
        shape = "base table (R54)" if based else "concrete tables"
        root = scratch / ("based" if based else "concrete")
        report = build(root, based=based)
        print(
            f"\n{shape}: committed={report.passed}"
            + (
                ""
                if report.passed
                else f" — {[f.check for f in report.findings if f.level == 'error'][:3]}"
            )
        )
        if not report.passed:
            continue
        for question, (rows_, how, seconds) in ask(root, based=based).items():
            print(
                f"  {question:24s} {rows_:>5} rows   {how:28s} {seconds * 1e3:6.2f} ms"
            )


if __name__ == "__main__":
    sys.exit(main())
