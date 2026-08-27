"""Run every fixture packet and check each produces the findings it was built to produce.

This is the conformance corpus: expected results as data. Any implementation runs it and
must agree, which is what stops two validators drifting apart (R2 §7.4).

The validator under test is `nwb_lake_validator`. Nothing is reimplemented here;
a second copy of the checks would be the drift this corpus exists to detect.
"""

import sys
from pathlib import Path

from nwb_lake_reader import open_packet
from nwb_lake_validator import validate

HERE = Path(__file__).resolve().parent

# packet -> (expected level, the check that must fire); None means it must be clean
EXPECTED: dict[str, tuple[str, str] | None] = {
    "valid": None,
    "dup_pk": ("error", "core.trials.primary_key_unique"),
    "orphan_fk": ("error", "core.trials.clock_id_resolves"),
    "null_required": ("error", "core.events.event_type.not_null"),
    "bad_vocabulary": ("error", "core.units.quality_label.in_vocabulary"),
    "bad_interval": ("error", "core.trials.interval_valid"),
    "stale_summary": ("error", "core.units.spike_summary_consistent"),
    "missing_amplitude_unit": ("error", "core.sorting_runs.amplitude_unit_declared"),
    "half_transform": ("error", "core.clocks.transform_pair_complete"),
    "unsorted_spikes": ("warning", "core.spike_events.physical_order"),
    "inconsistent_projection": ("error", "core.unit_quality_labels.projection_is_consistent"),
    "stream_clock_mismatch": ("error", "core.events.clock_matches_stream"),
    "orphan_manifest_session": ("error", "core.sessions.manifest_sessions_match"),
    "bad_type": ("error", "schema.column_type"),
    "missing_column": ("error", "schema.column_absent"),
}


def main() -> int:
    failures = []
    print(f"{'packet':26s} {'expected':9s} {'result':22s} findings")
    print("-" * 80)
    for name, expect in EXPECTED.items():
        report = validate(open_packet(HERE / "packets" / name))
        if expect is None:
            ok = report.passed and report.warnings == 0
            verdict = "clean" if ok else "UNEXPECTED FINDINGS"
        else:
            level, check = expect
            ok = any(f.check == check and f.level == level for f in report.findings)
            verdict = "caught" if ok else f"MISSED {check}"
        if not ok:
            failures.append((name, verdict, sorted({f.check for f in report.findings})))
        expected_level = "clean" if expect is None else expect[0]
        print(
            f"{'ok ' if ok else 'FAIL'} {name:21s} {expected_level:9s} {verdict:22s} "
            f"{report.errors}e {report.warnings}w"
        )

    print("-" * 80)
    if failures:
        print(f"{len(failures)} packet(s) did not behave as specified:")
        for name, verdict, checks in failures:
            print(f"  {name}: {verdict}")
            print(f"    fired: {checks}")
    else:
        print(f"all {len(EXPECTED)} packets behaved as specified")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
