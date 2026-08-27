"""Run every fixture packet and check each produces the findings it was built to produce.

This is the conformance corpus: expected results as data. Any implementation runs it and
must agree, which is what stops two validators drifting apart (R2 §7.4).
"""
import json
import sys
from pathlib import Path

from validate import validate

HERE = Path(__file__).resolve().parent
REGISTRY = json.loads((HERE.parent / "registry" / "logical_schemas.json").read_text())

# packet -> (expected level, the check that must fire)
EXPECTED = {
    "valid":                   None,
    "dup_pk":                  ("error",   "core.trials.primary_key_unique"),
    "orphan_fk":               ("error",   "core.trials.clock_id_resolves"),
    "null_required":           ("error",   "core.events.event_type.not_null"),
    "bad_vocabulary":          ("error",   "core.units.quality_label.in_vocabulary"),
    "bad_interval":            ("error",   "core.trials.interval_valid"),
    "stale_summary":           ("error",   "core.units.spike_summary_consistent"),
    "missing_amplitude_unit":  ("error",   "core.sorting_runs.amplitude_unit_declared"),
    "half_transform":          ("error",   "core.clocks.transform_pair_complete"),
    "unsorted_spikes":         ("warning", "core.spike_events.physical_order"),
    "orphan_manifest_session": ("error",   "core.sessions.manifest_sessions_match"),
    "bad_type":                ("error",   "schema.column_type"),
    "missing_column":          ("error",   "schema.column_absent"),
}


def main() -> int:
    failures = []
    print(f"{'packet':26s} {'expected':9s} {'result':22s} findings")
    print("-" * 84)
    for name, expect in EXPECTED.items():
        packet = HERE / "packets" / name
        rep = validate(packet, REGISTRY)
        checks = {f["check"] for f in rep.findings}

        if expect is None:
            ok = rep.errors == 0 and rep.warnings == 0
            verdict = "clean" if ok else "UNEXPECTED FINDINGS"
        else:
            level, check = expect
            fired = any(f["check"] == check and f["level"] == level for f in rep.findings)
            ok = fired
            verdict = "caught" if fired else f"MISSED {check}"

        if not ok:
            failures.append((name, verdict, sorted(checks)))
        exp = "clean" if expect is None else expect[0]
        print(f"{'ok ' if ok else 'FAIL'} {name:21s} {exp:9s} {verdict:22s} "
              f"{rep.errors}e {rep.warnings}w")

    print("-" * 84)
    if failures:
        print(f"{len(failures)} packet(s) did not behave as specified:")
        for name, verdict, checks in failures:
            print(f"  {name}: {verdict}")
            print(f"    fired: {checks}")
    else:
        print(f"all {len(EXPECTED)} packets behaved as specified")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
