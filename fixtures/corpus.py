"""Run every fixture packet and check each produces the findings it was built to produce.

This is the conformance corpus: expected results as data. Any implementation runs it and
must agree, which is what stops two validators drifting apart (R2 §7.4).

The validator under test is `escapewheel_validator`. Nothing is reimplemented here;
a second copy of the checks would be the drift this corpus exists to detect.
"""

import sys
from pathlib import Path

from escapewheel_reader import open_packet
from escapewheel_validator import validate

HERE = Path(__file__).resolve().parent

# packet -> (expected level, the check that must fire); None means it must be clean
EXPECTED: dict[str, tuple[str, str] | None] = {
    "valid": None,
    "dup_pk": ("error", "core.intervals.primary_key_unique"),
    "orphan_fk": ("error", "core.intervals.clock_id_resolves"),
    "null_required": ("error", "core.event_streams.event_type.not_null"),
    "bad_vocabulary": ("error", "core.units.quality_label.in_vocabulary"),
    "bad_interval": ("error", "core.intervals.interval_valid"),
    "unspecialised_interval": ("error", "core.intervals.interval_kind.dynamic_foraging_trials_is_specialised"),
    "stale_summary": ("error", "core.units.spike_summary_consistent"),
    "missing_amplitude_unit": ("error", "core.sorting_runs.amplitude_unit_declared"),
    "half_transform": ("error", "core.clocks.transform_pair_complete"),
    "unsorted_spikes": ("error", "core.spike_events.physical_order"),
    "inconsistent_projection": ("error", "core.unit_quality_labels.projection_is_consistent"),
    "spike_outside_window": ("warning", "core.spike_events.within_observation"),
    "orphan_manifest_session": ("error", "core.sessions.manifest_sessions_match"),
    "bad_type": ("error", "schema.column_type"),
    "missing_column": ("error", "schema.column_absent"),
    "no_reference_clock": ("error", "core.sessions.reference_clock_declared"),
    "clock_cycle": ("error", "core.clocks.parent_chain_well_founded"),
    "unreachable_clock": ("error", "core.sessions.every_clock_reaches_the_reference"),
    "unaligned_clock": ("error", "core.clocks.alignment_declared_for_conversion"),
    "wide_anchor_gap": ("warning", "core.clock_anchors.gap_within_bound"),
    "two_primaries": ("warning", "core.unit_electrodes.one_primary"),
    "gapped_ordinal": ("error", "core.unit_electrodes.channel_index_contiguous"),
    "unit_off_the_run": ("error", "core.unit_electrodes.electrode_is_a_run_channel"),
    "undeclared_currency": ("error", "core.processing_runs.undeclared_currency"),
    "unscoped_runs": ("error", "core.processing_runs.scope_undeclared"),
}

#: Packets whose expected finding is advisory (R26 §3). Advisory rules are off by default --
#: enabling them must never change whether a packet passed -- so these run with them on, and
#: the `info` level they carry keeps the verdict unchanged either way.
#: R82 §2 made both mandatory errors, so nothing here needs the advisory pass any more.
ADVISORY: set[str] = set()


def main() -> int:
    failures = []
    print(f"{'packet':26s} {'expected':9s} {'result':22s} findings")
    print("-" * 80)
    for name, expect in EXPECTED.items():
        report = validate(open_packet(HERE / "packets" / name), advisory=name in ADVISORY)
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
