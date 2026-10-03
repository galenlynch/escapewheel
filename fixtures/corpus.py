"""Run every fixture packet and check each produces the findings it was built to produce.

This is the conformance corpus: expected results as data. Any implementation runs it and
must agree, which is what stops two validators drifting apart (R2 §7.4).

The validator under test is `escapewheel_validator`. Nothing is reimplemented here;
a second copy of the checks would be the drift this corpus exists to detect.
"""

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

from corpus_packets import PACKETS
from escapewheel_reader import open_packet
from escapewheel_validator import Verdict, Verification, validate

HERE = Path(__file__).resolve().parent

#: Packets validated at once. Each validation is independent and takes a fraction of a second.
WORKERS = 8

#: packet -> (expected level, the check that must fire); None means it must be clean. `PACKETS`
#: declares each packet, and this restates that much of it as a literal, because
#: `revisions/evidence.py` and `tools/facts.py` read it from this file's syntax tree. `main` judges
#: nothing while the two disagree.
EXPECTED: dict[str, tuple[str, str] | None] = {
    "valid": None,
    "dup_pk": ("error", "core.intervals.primary_key_unique"),
    "shared_name": ("error", "core.intervals.interval_name.unique"),
    "names_differ_in_case": None,
    "names_differ_in_form": None,
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
    "undeclared_column": ("error", "schema.column_undeclared"),
    "extension_undeclared_column": ("error", "schema.column_undeclared"),
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
        "core.electrode_coordinate_values.session_id_coordinate_frame_axis_index_resolves",
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
    "two_kinds_one_label": None,
    "trial_names_a_tone": ("error", "dynamic_foraging.trials.trial_id.names_a_row_of_its_kind"),
    "tone_names_a_trial": ("error", "cue.tones.tone_id.names_a_row_of_its_kind"),
    "tone_in_place_of_its_own": ("error", "cue.tones.tone_id.names_a_row_of_its_kind"),
    "interval_of_a_session": ("error", "core.intervals.interval_kind.core_sessions_is_specialised"),
    "device_detail": None,
    "device_detail_unkinded": ("error", "rig.neuropixels.device_id.names_a_row_of_its_kind"),
    "device_detail_other_kind": ("error", "rig.neuropixels.device_id.names_a_row_of_its_kind"),
    "media_frames": None,
    "frames_timed_in_decode_order": ("error", "core.media_frames.t_tick_nondecreasing_with_frame_index"),
    "frames_fall_behind_another_clock": ("error", "core.media_frames.t_tick_nondecreasing_with_frame_index"),
    "frames_pts_out_of_order": ("error", "core.media_frames.pts_increases_with_frame_index"),
    "frames_index_skips": ("error", "core.media_frames.frame_index_contiguous"),
    "kinds_out_of_unicode_order": None,
    "equal_bounds": None,
    "equal_bounds_swapped": None,
    "trial_labelled_axis": None,
    "trials_numbered_from_one": ("error", "core.intervals.numbered_in_order"),
    "trials_misordered": ("error", "core.intervals.numbered_in_order"),
    "trials_numbered_by_tick": ("error", "core.intervals.numbered_in_order"),
    "interval_numbering_gap": ("error", "core.intervals.numbered_in_order"),
    "repeated_interval_label": ("error", "core.intervals.label_unique_within_kind"),
    "orphan_trial": ("error", "dynamic_foraging.trials.trial_id_resolves"),
    "units_numbered_by_scalar": ("error", "core.units.numbered_in_order"),
    "units_numbered_from_one": ("error", "core.units.numbered_in_order"),
    "unit_labels_by_length": None,
    "null_unit_labels": None,
    "null_unit_labels_swapped": None,
    "later_run_numbered_first": None,
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
    "amended_intervals": None,
    "amended_curation": None,
    "amended_preference": None,
    "amended_trial": ("error", "amendment.group_grown"),
    "amended_trial_bounds": ("error", "amendment.row_changed"),
    "amended_unit_window": ("error", "amendment.group_grown"),
    "amended_packet_id": ("error", "amendment.identity_changed"),
    "amended_replacement": None,
    "amended_replacement_unlinked": ("error", "amendment.identity_changed"),
    "amended_replacement_major": ("error", "amendment.identity_changed"),
    "replaces_own_packet": None,
    "replaces_another_packet": None,
    "replaces_same_major": ("error", "packet.replaces.major_version"),
    "replaces_item_with_location": ("error", "packet.manifest.schema"),
    "replaces_item_without_digest": ("error", "packet.manifest.schema"),
    "two_imports": None,
    "preference_of_another_scope": ("error", "core.preferred_runs.scope_matches_run"),
    "spikes_on_reference_clock": None,
    "spikes_off_reference_clock": ("error", "analysis.spike_events.on_reference_clock"),
    "spikes_without_reference_clock": ("error", "analysis.spike_events.on_reference_clock"),
    "sidecars": None,
    "sidecars_without_scopes": None,
    "sidecar_row_unbound": ("error", "packet.resource.catalog_row_binding"),
    "sidecar_entry_unbound": ("error", "packet.resource.catalog_row_binding"),
    "sidecar_listed_twice": ("error", "core.sidecars.primary_key_unique"),
    "sidecar_scope_unlisted": ("error", "core.sidecar_scopes.resource_id_resolves"),
    "sidecar_scope_undeclared_table": ("error", "core.sidecar_scopes.scope_kind.kind_declared"),
    "sidecar_scope_uncarried_table": ("error", "core.sidecar_scopes.scope_kind.kind_declared"),
    "sidecar_scope_composite_key": ("error", "core.sidecar_scopes.scope_kind.key_fits_paired_value"),
    "sidecar_scope_absent_row": ("error", "core.sidecar_scopes.scope_kind.core_subjects_resolves"),
    "sidecar_scope_null": ("error", "core.sidecar_scopes.scope.not_null"),
    "sidecar_with_lineage": ("error", "packet.resource.derived_from_forbidden"),
}

_BY_NAME = {packet.name: packet for packet in PACKETS}


def _judge(name: str) -> tuple[bool, str, list[str], int, int]:
    """Validate one packet and return whether it behaved, the verdict, its checks and counts."""
    packet = _BY_NAME[name]
    report = validate(
        open_packet(HERE / "packets" / name),
        # Off for every packet: R82 §2 made mandatory errors of the two rules that needed it.
        advisory=packet.advisory,
        # Packet-owned digests alone: the corpus resolves no external resource.
        verification=Verification(checksums=packet.checksums, external=False),
    )
    expected = packet.expected
    if expected is None:
        ok = report.passed and report.warnings == 0
        verdict = "clean" if ok else "UNEXPECTED FINDINGS"
    else:
        fired = sum(
            f.check == expected.check
            and f.level == expected.level
            and (expected.registry is None or f.registry == expected.registry)
            for f in report.findings
        )
        ok = fired > 0 if expected.count is None else fired == expected.count
        if expected.registry is not None:
            ok = ok and (
                report.verdict(expected.registry),
                report.verdict("core"),
                report.verdict(),
            ) == (Verdict.FAILED, Verdict.PASSED, Verdict.FAILED)
        if expected.conforming:
            ok = ok and report.passed
        verdict = "caught" if ok else f"MISSED {expected.check}"
    if any(f.check in packet.absent for f in report.findings):
        ok, verdict = False, "DREW AN ABSENT CHECK"
    return ok, verdict, sorted({f.check for f in report.findings}), report.errors, report.warnings


def _restated() -> list[str]:
    """Each packet `EXPECTED` and `PACKETS` state differently, or only one of them names."""
    declared = {
        name: None if packet.expected is None else (packet.expected.level, packet.expected.check)
        for name, packet in _BY_NAME.items()
    }
    return sorted(
        name
        for name in declared.keys() | EXPECTED.keys()
        if name not in declared or name not in EXPECTED or declared[name] != EXPECTED[name]
    )


def main() -> int:
    if differing := _restated():
        print(f"EXPECTED and the packet records disagree about: {', '.join(differing)}")
        return 1
    failures = []
    print(f"{'packet':26s} {'expected':9s} {'result':22s} findings")
    print("-" * 80)
    # Spawned, since a forked worker inherits the thread pools the imports above may have started.
    with ProcessPoolExecutor(min(WORKERS, os.cpu_count() or 1), mp_context=get_context("spawn")) as pool:
        judged = pool.map(_judge, EXPECTED, chunksize=4)
        for (name, expect), (ok, verdict, checks, errors, warnings) in zip(EXPECTED.items(), judged, strict=True):
            if not ok:
                failures.append((name, verdict, checks))
            expected_level = "clean" if expect is None else expect[0]
            print(f"{'ok ' if ok else 'FAIL'} {name:21s} {expected_level:9s} {verdict:22s} {errors}e {warnings}w")

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
