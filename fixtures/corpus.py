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
    "unspecialised_interval": (
        "error",
        "core.intervals.interval_kind.dynamic_foraging_trials_is_specialised",
    ),
    "stale_summary": ("error", "core.units.spike_summary_consistent"),
    "missing_amplitude_unit": ("error", "core.units.amplitude_unit_declared"),
    "non_ucum_unit": ("error", "core.units.amplitude_unit.ucum_code"),
    "half_transform": ("error", "core.clocks.transform_pair_complete"),
    "non_finite_rate": ("error", "core.clocks.tick_rate_hz.finite"),
    "negative_slope": ("error", "core.clocks.transform_slope_positive"),
    "unsorted_spikes": ("error", "core.spike_events.physical_order"),
    "inconsistent_projection": (
        "error",
        "core.unit_quality_labels.projection_is_consistent",
    ),
    "spike_outside_window": ("warning", "core.spike_events.within_observation"),
    "orphan_manifest_session": ("error", "core.sessions.manifest_sessions_match"),
    "bad_type": ("error", "schema.column_type"),
    "extension_bad_type": ("error", "schema.column_type"),
    "missing_column": ("error", "schema.column_absent"),
    "no_reference_clock": ("error", "core.sessions.reference_clock_declared"),
    "clock_cycle": ("error", "core.clocks.parent_chain_well_founded"),
    "unreachable_clock": ("error", "core.sessions.every_clock_reaches_the_reference"),
    "unaligned_clock": ("error", "core.clocks.alignment_declared_for_conversion"),
    "wide_anchor_gap": ("warning", "core.clock_anchors.gap_within_bound"),
    "two_primaries": ("warning", "core.unit_electrodes.one_primary"),
    "unit_off_the_run": ("error", "core.unit_electrodes.electrode_is_a_run_channel"),
    "undeclared_currency": ("error", "core.processing_runs.undeclared_currency"),
    "unscoped_runs": ("error", "core.processing_runs.scope_undeclared"),
    "clock_without_window": ("error", "core.clocks.observation_declared"),
    "frame_without_axes": (
        "error",
        "core.electrode_coordinate_values."
        "session_id_coordinate_frame_axis_index_resolves",
    ),
    "coordinate_omits_an_axis": None,
    "origin_through_transform": None,
    "origin_not_earliest": ("error", "time.origin_not_earliest"),
    "origin_unmappable": ("error", "time.origin_unmappable"),
    "crc64nvme": None,
    "crc32c": None,
    "crc32": None,
    "crc64nvme_one_byte_off": ("error", "owned.digest"),
    "crc32c_one_byte_off": ("error", "owned.digest"),
    "crc32_one_byte_off": ("error", "owned.digest"),
    "owned_without_digest": ("error", "packet.resource.digest_missing"),
    "crc_prefix": None,
    "crc_prefix_disagrees": ("error", "packet.resource.member_digest"),
    "member_digest_partial": ("error", "packet.manifest.schema"),
    "member_digest_width": ("error", "packet.manifest.schema"),
    "outside_array_floor": ("info", "physical.outside_reader_floor"),
    "outside_table_floor": ("warning", "physical.outside_reader_floor"),
    "unresolved_externals": ("info", "external.physical_unassessed"),
    "padded_labels": None,
    "axis_without_form": ("error", "core.array_dimensions.one_coordinate_form"),
    "axis_with_two_forms": ("error", "core.array_dimensions.one_coordinate_form"),
    "label_naming_no_row": (
        "error",
        "core.array_dimensions.coordinate_resource.core_electrodes_resolves",
    ),
    "label_on_unlabelled_axis": (
        "error",
        "core.array_dimensions.coordinate_resource.specialised_row_has_kind",
    ),
    "label_missing": ("error", "array.label_missing"),
    "chained_dependency": ("error", "core.array_dimensions.dependency_not_chained"),
    "independent_label_off_zero": (
        "error",
        "core.array_labels.independent_depends_on_position_zero",
    ),
    "one_row_two_positions": ("error", "core.array_labels.one_position_per_row"),
    "label_beyond_axis": ("error", "array.label_position_out_of_range"),
    "dependent_axis_unlabelled": ("error", "core.array_dimensions.dependent_axis_labelled"),
    "label_outside_core": ("error", "core.array_dimensions.coordinate_resource_is_core"),
    "array_without_dimension_names": ("error", "array.dimension_names"),
    "no_extracellular": None,
    "one_clock": None,
    "sessions_only": None,
    "owned_opaque_object": None,
    "owned_opaque_prefix": None,
    "owned_opaque_singleton": None,
    "owned_opaque_encoded_name": None,
    "owned_opaque_one_byte_off": ("error", "owned.digest"),
    "opaque_name_portability": ("warning", "physical.opaque_name_portability"),
    "listing_key_spelling": ("warning", "physical.opaque_name_portability"),
    "uri_raw_space": ("error", "packet.resource.uri_form"),
    "uri_lowercase_hex": ("error", "packet.resource.uri_form"),
    "uri_encoded_unreserved": ("error", "packet.resource.uri_form"),
    "uri_dot_segment": ("error", "packet.resource.uri_form"),
}

#: Packets whose expected finding is one per resource (Part 05 §5.3), and how many it must fire.
COUNTS: dict[str, int] = {
    "outside_array_floor": 1,
    "unresolved_externals": 2,
    "opaque_name_portability": 2,
    "listing_key_spelling": 3,
}

#: Packets whose expected finding is a warning that leaves them conformant, so they must still pass.
CONFORMING: set[str] = {"opaque_name_portability", "listing_key_spelling"}

#: Checks a packet must not draw at any level.
ABSENT: dict[str, set[str]] = {
    "valid": {"physical.outside_reader_floor", "external.physical_unassessed"},
    # Its digest is over keys in raw UTF-8, and a reader that escaped or encoded them would disagree.
    "listing_key_spelling": {"owned.digest", "packet.resource.member_digest"},
}

#: Packets whose expected finding belongs to an extension (Part 05 §9.5), which must fail that
#: extension and the packet and leave core passed.
EXTENSION_FINDINGS: dict[str, str] = {"extension_bad_type": "dynamic_foraging"}

#: Packets whose expected finding is advisory (Part 02 §10.2). Advisory rules are off by default --
#: enabling them must never change whether a packet passed -- so these run with them on, and
#: the `info` level they carry keeps the verdict unchanged either way.
#: R82 §2 made both mandatory errors, so nothing here needs the advisory pass any more.
ADVISORY: set[str] = set()

#: Packets run with checksums, which establishes every packet-owned digest (Part 04 §5.3, level 2).
CHECKSUMS: set[str] = {
    "valid",
    "crc64nvme",
    "crc32c",
    "crc32",
    "crc64nvme_one_byte_off",
    "crc32c_one_byte_off",
    "crc32_one_byte_off",
    "owned_opaque_object",
    "owned_opaque_prefix",
    "owned_opaque_singleton",
    "owned_opaque_encoded_name",
    "owned_opaque_one_byte_off",
    "opaque_name_portability",
    "listing_key_spelling",
}


def main() -> int:
    failures = []
    print(f"{'packet':26s} {'expected':9s} {'result':22s} findings")
    print("-" * 80)
    for name, expect in EXPECTED.items():
        report = validate(
            open_packet(HERE / "packets" / name),
            advisory=name in ADVISORY,
            checksums=name in CHECKSUMS,
        )
        absent = ABSENT.get(name, set())
        if expect is None:
            ok = report.passed and report.warnings == 0
            verdict = "clean" if ok else "UNEXPECTED FINDINGS"
        else:
            level, check = expect
            subject = EXTENSION_FINDINGS.get(name)
            fired = sum(
                f.check == check
                and f.level == level
                and (subject is None or f.registry == subject)
                for f in report.findings
            )
            ok = fired == COUNTS[name] if name in COUNTS else fired > 0
            if subject is not None:
                ok = ok and (
                    report.verdict(subject),
                    report.verdict("core"),
                    report.verdict(),
                ) == ("failed", "passed", "failed")
            if name in CONFORMING:
                ok = ok and report.passed
            verdict = "caught" if ok else f"MISSED {check}"
        if any(f.check in absent for f in report.findings):
            ok, verdict = False, "DREW AN ABSENT CHECK"
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
