"""Packets that edit the valid session's rows."""

from datetime import timedelta

from .record import Expected, Packet
from .registry import KIND
from .session import START, variant


def child(tables):
    """The clock that declares a parent, which is what the alignment variants are about."""
    return next(c for c in tables["core.clocks"] if c.get("parent_clock_id"))


def dup_pk(c):
    c["core.intervals"].append(dict(c["core.intervals"][0]))


def orphan_fk(c):
    c["core.intervals"][1]["clock_id"] = "no_such_clock"


def null_required(c):
    c["core.event_streams"][2]["event_type"] = None


def bad_vocabulary(c):
    # bombcell's raw label belongs in `label`; the designated column holds the
    # projection, which stays closed to sua/mua/noise (R22 5).
    c["core.units"][0]["quality_label"] = "good"


def unspecialised_interval(c):
    # Part 02 §8.3: a core interval naming a kind with no counterpart there. Every other check
    # passes -- the kind is a dotted resource ID, the packet declares it, and the detail
    # rows that exist all resolve -- which is why the reverse direction had to be generated.
    c[KIND] = c[KIND][:-1]


def bad_interval(c):
    c["core.intervals"][1]["stop_tick"] = 5999  # before its start_tick


def stale_summary(c):
    c["core.units"][0]["n_spikes"] += 5


def missing_amplitude_unit(c):
    # R96 §3.1 moved the unit of measure onto the unit that its spikes belong to.
    c["core.units"][0]["amplitude_unit"] = None


def non_ucum_unit(c):
    # Part 02 §8.4: `microvolts` names the unit whose UCUM code is `uV`, and is no code itself.
    c["core.units"][0]["amplitude_unit"] = "microvolts"


def half_transform(c):
    # By name, not position: which row is which changed when the clocks were reordered into
    # the name order R53 numbers them in, and an index silently picked the wrong clock.
    child(c)["transform_offset"] = None


def non_finite_rate(c):
    # Part 02 §5.4. NaN orders above every number, so `tick_rate_positive` passes it.
    child(c)["tick_rate_hz"] = float("nan")


def negative_slope(c):
    # Part 02 §5.4 leaves -1 to a rule: it is finite, and only its sign is wrong.
    child(c)["transform_slope"] = -1.0


def unsorted_spikes(c):
    s = c["core.spike_events"]
    s[3], s[4] = s[4], s[3]


def inconsistent_projection(c):
    # bombcell's `good` already projects to `sua` for unit_001; projecting the same
    # (source, label) pair to `mua` here is not a projection at all (R22 4).
    c["core.unit_quality_labels"].append(
        {
            "session_id": "s001",
            "unit_id": 3,
            "source": "bombcell",
            "label": "good",
            "normalized_label": "mua",
            "confidence": None,
        }
    )


def spike_outside_window(c):
    # a spike in unit_002's declared drop-out, which its windows say was not observed
    c["core.spike_events"].append(
        {
            "session_id": "s001",
            "unit_id": 2,
            "t_tick": 129_000,
            "amplitude": -80.0,
        }
    )
    c["core.units"][1]["n_spikes"] += 1


def orphan_manifest_session(c):
    c["core.sessions"][0]["session_id"] = "s999"  # manifest still says s001


# R27: the clock graph has to be usable, not merely present.
def no_reference_clock(c):
    c["core.sessions"][0]["reference_clock_id"] = None


def clock_cycle(c):
    # Each is the other's parent. Every pre-R27 rule passes; a consumer walking it hangs.
    c["core.clocks"][1]["parent_clock_id"] = "imec_ap_s001"
    c["core.clocks"][0]["parent_clock_id"] = "behavior_s001"


def unreachable_clock(c):
    # A third clock with no parent, so nothing converts it to the reference.
    c["core.clocks"].append(
        {
            "clock_id": "aux_s001",
            "session_id": "s001",
            "tick_rate_hz": 1000.0,
            "origin": "tick 0 at aux start",
        }
    )


def unaligned_clock(c):
    # Parentage known, alignment not measured -- legal under R13 4, a defect once the
    # session declares a reference (R27 4).
    child(c)["transform_slope"] = None
    child(c)["transform_offset"] = None


# R28: the unit-to-electrode links must be usable.
def two_primaries(c):
    # Two peak channels is not a peak, and the reader has no rule for choosing.
    c["core.unit_electrodes"][0]["is_primary"] = True
    c["core.unit_electrodes"][2]["is_primary"] = True


def unit_off_the_run(c):
    # A unit sitting on a contact its run never used (R83 2.4). `elec_002` is a real
    # electrode, so only the run's channel list can tell this from a valid row.
    c["core.unit_electrodes"][0]["electrode_id"] = "elec_002"


def wide_anchor_gap(c):
    # 1 kHz anchors with one 20x hole: inside the span, outside the bound (R27 5.3).
    child(c)["transform_slope"] = None
    child(c)["transform_offset"] = None
    c["core.clock_anchors"] = [
        {
            "session_id": "s001",
            "clock_id": "behavior_s001",
            "anchor_index": i,
            "t_tick": t,
            "parent_tick": t * 30,
        }
        for i, t in enumerate([0, 1000, 2000, 3000, 23_000, 24_000, 25_000])
    ]


def clock_without_window(c):
    # Part 02 §12.5: the reference clock declares no observation interval, so nothing timestamped
    # on it has a window to inherit and the session's origin has nothing to be a minimum over.
    c["core.clock_observation_intervals"] = [
        r for r in c["core.clock_observation_intervals"] if r["clock_id"] != "imec_ap_s001"
    ]


# Part 05 §5.3: a declared origin is the session's earliest observation start on its reference.
def origin_through_transform(c):
    # Behavior started 3000 reference ticks before the probe, so its start, carried through
    # the transform, is the minimum and the origin sits before the reference's own start.
    child(c)["transform_offset"] = -3000.0
    c["core.sessions"][0]["t_zero_tick"] = -3000


def origin_not_earliest(c):
    # The reference's own start, which is what an origin read without the transform gives.
    child(c)["transform_offset"] = -3000.0
    c["core.sessions"][0]["t_zero_tick"] = 0


def origin_unmappable(c):
    # Anchors that begin twenty intervals after the behavior clock's start, so the start
    # has no reference tick to be compared at.
    child(c)["transform_slope"] = None
    child(c)["transform_offset"] = None
    c["core.clock_anchors"] = [
        {
            "session_id": "s001",
            "clock_id": "behavior_s001",
            "anchor_index": i,
            "t_tick": t,
            "parent_tick": t * 30,
        }
        for i, t in enumerate(range(20_000, 25_000, 1000))
    ]
    c["core.sessions"][0]["t_zero_tick"] = 0


def frame_without_axes(c):
    # Part 01 §3.8: the frame declares two axes where its coordinates carry three, so every
    # `ccf_dv` value names an axis no frame declares and Tier 1's anti-join returns it.
    c["core.coordinate_frame_axes"] = [
        r for r in c["core.coordinate_frame_axes"] if not (r["coordinate_frame"] == "ccf" and r["axis_index"] == 2)
    ]


def coordinate_omits_an_axis(c):
    # Part 01 §3.8: a coordinate carries values only on the axes its source states, so a unit
    # whose `ccf_dv` value is absent conforms; nothing requires a value on every axis.
    c["core.unit_coordinate_values"] = [
        r
        for r in c["core.unit_coordinate_values"]
        if not (r["unit_id"] == 1 and r["coordinate_frame"] == "ccf" and r["axis_index"] == 2)
    ]


def undeclared_currency(c):
    # One probe sorted twice with nothing saying which to read (Part 01 §2.6). Both runs carry
    # a scope, so the packet says enough to know they compete -- which is what separates
    # this from `unscoped_runs` below.
    c["core.processing_runs"][0]["scope_kind"] = "core.sessions"
    c["core.processing_runs"][0]["scope"] = "s001"
    for suffix in ("a", "b"):
        c["core.processing_runs"].append(
            {
                "processing_run_id": f"run_sort_{suffix}",
                "session_id": "s001",
                "activity_type": "spike_sorting",
                # R49 §2.1: the pair, so the only finding is the missing preference.
                "scope_kind": "core.probes",
                "scope": "probe0",
                "software_name": "kilosort4",
                "software_version": "4.0.0",
                "status": "succeeded",
                "started_at": START + timedelta(hours=6),
                "ended_at": START + timedelta(hours=7),
            }
        )


def unscoped_runs(c):
    # Two runs of one activity, neither saying what it is about, so whether they compete
    # cannot be determined (Part 01 §2.6). The fix is to record the scopes, not to choose.
    for suffix in ("a", "b"):
        c["core.processing_runs"].append(
            {
                "processing_run_id": f"run_pose_{suffix}",
                "session_id": "s001",
                "activity_type": "pose_estimation",
                "software_name": "sleap",
                "software_version": "1.3.0",
                "status": "succeeded",
                "started_at": START + timedelta(hours=6),
                "ended_at": START + timedelta(hours=7),
            }
        )


def manifest_keeps_s001(manifest):
    manifest["sessions"] = ["s001"]


#: The valid session with its rows edited, each to violate exactly one rule or to conform where a
#: rule might be thought to apply, so the corpus demonstrates that each check fires.
ROW_PACKETS = (
    Packet("dup_pk", variant(dup_pk), Expected("error", "core.intervals.primary_key_unique")),
    Packet("orphan_fk", variant(orphan_fk), Expected("error", "core.intervals.clock_id_resolves")),
    Packet("null_required", variant(null_required), Expected("error", "core.event_streams.event_type.not_null")),
    Packet("bad_vocabulary", variant(bad_vocabulary), Expected("error", "core.units.quality_label.in_vocabulary")),
    Packet("bad_interval", variant(bad_interval), Expected("error", "core.intervals.interval_valid")),
    Packet(
        "unspecialised_interval",
        variant(unspecialised_interval),
        Expected("error", "core.intervals.interval_kind.dynamic_foraging_trials_is_specialised"),
    ),
    Packet("stale_summary", variant(stale_summary), Expected("error", "core.units.spike_summary_consistent")),
    Packet(
        "missing_amplitude_unit",
        variant(missing_amplitude_unit),
        Expected("error", "core.units.amplitude_unit_declared"),
    ),
    Packet("non_ucum_unit", variant(non_ucum_unit), Expected("error", "core.units.amplitude_unit.ucum_code")),
    Packet("half_transform", variant(half_transform), Expected("error", "core.clocks.transform_pair_complete")),
    Packet("non_finite_rate", variant(non_finite_rate), Expected("error", "core.clocks.tick_rate_hz.finite")),
    Packet("negative_slope", variant(negative_slope), Expected("error", "core.clocks.transform_slope_positive")),
    Packet(
        "unsorted_spikes",
        # Written in insertion order, which must defeat the writer's sort.
        variant(unsorted_spikes, unsorted=frozenset({"core.spike_events"})),
        Expected("error", "core.spike_events.physical_order"),
    ),
    Packet(
        "inconsistent_projection",
        variant(inconsistent_projection),
        Expected("error", "core.unit_quality_labels.projection_is_consistent"),
    ),
    Packet(
        "spike_outside_window",
        variant(spike_outside_window),
        Expected("warning", "core.spike_events.within_observation"),
    ),
    Packet(
        "orphan_manifest_session",
        variant(orphan_manifest_session, edit=manifest_keeps_s001),
        Expected("error", "core.sessions.manifest_sessions_match"),
    ),
    Packet(
        "no_reference_clock",
        variant(no_reference_clock),
        Expected("error", "core.sessions.reference_clock_declared"),
    ),
    Packet("clock_cycle", variant(clock_cycle), Expected("error", "core.clocks.parent_chain_well_founded")),
    Packet(
        "unreachable_clock",
        variant(unreachable_clock),
        Expected("error", "core.sessions.every_clock_reaches_the_reference"),
    ),
    Packet(
        "unaligned_clock",
        variant(unaligned_clock),
        Expected("error", "core.clocks.alignment_declared_for_conversion"),
    ),
    Packet("wide_anchor_gap", variant(wide_anchor_gap), Expected("warning", "core.clock_anchors.gap_within_bound")),
    Packet("two_primaries", variant(two_primaries), Expected("warning", "core.unit_electrodes.one_primary")),
    Packet(
        "unit_off_the_run",
        variant(unit_off_the_run),
        Expected("error", "core.unit_electrodes.electrode_is_a_run_channel"),
    ),
    Packet(
        "undeclared_currency",
        variant(undeclared_currency),
        Expected("error", "core.processing_runs.undeclared_currency"),
    ),
    Packet("unscoped_runs", variant(unscoped_runs), Expected("error", "core.processing_runs.scope_undeclared")),
    Packet(
        "clock_without_window",
        variant(clock_without_window),
        Expected("error", "core.clocks.observation_declared"),
    ),
    Packet(
        "frame_without_axes",
        variant(frame_without_axes),
        Expected("error", "core.electrode_coordinate_values.session_id_coordinate_frame_axis_index_resolves"),
    ),
    Packet("coordinate_omits_an_axis", variant(coordinate_omits_an_axis)),
    Packet("origin_through_transform", variant(origin_through_transform)),
    Packet("origin_not_earliest", variant(origin_not_earliest), Expected("error", "time.origin_not_earliest")),
    Packet("origin_unmappable", variant(origin_unmappable), Expected("error", "time.origin_unmappable")),
)
