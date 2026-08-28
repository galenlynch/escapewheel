"""Build the Phase 0 fixture packets.

A conforming single-session packet per R1 §6, plus variants each violating exactly one
rule. Table schemas are taken from the registry rather than restated, so a fixture cannot
drift from the specification it is meant to exercise.
"""
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
REGISTRY = json.loads((HERE.parent / "registry" / "logical_schemas.json").read_text())

ARROW = {"string": pa.string(), "int32": pa.int32(), "int64": pa.int64(),
         "float32": pa.float32(), "float64": pa.float64(), "bool": pa.bool_(),
         "date": pa.date32(), "timestamp": pa.timestamp("us", tz="UTC"),
         "json_string": pa.string()}

START = datetime(2026, 8, 20, 14, 0, 0, tzinfo=timezone.utc)
AP_HZ, BEH_HZ = 30_000, 1_000


def table(resource: str, rows: list[dict]) -> pa.Table:
    """Build an Arrow table for `resource` with exactly the registry's schema.

    Columns absent from `rows` are emitted as nulls unless the registry marks them
    optional, in which case they are omitted entirely — exercising all three presence
    states (R2 §5).
    """
    spec = REGISTRY["tables"][resource]
    arrays, fields = [], []
    for c in spec["columns"]:
        present = any(c["name"] in r for r in rows)
        if c["presence"] == "optional" and not present:
            continue
        typ = ARROW[c["type"]]
        arrays.append(pa.array([r.get(c["name"]) for r in rows], type=typ))
        fields.append(pa.field(c["name"], typ))
    return pa.table(arrays, schema=pa.schema(fields))


def spikes(unit, run, cur, clock, ticks):
    return [{"session_id": "s001", "unit_id": unit, "sorting_run_id": run,
             "curation_id": cur, "t_tick": int(t), "clock_id": clock,
             "amplitude": float(-80 - (i % 7) * 3)} for i, t in enumerate(ticks)]


def content() -> dict[str, list[dict]]:
    u1 = list(range(30_000, 300_000, 9_000))     # unit_001, ~3.3 Hz on the AP clock
    # unit_002 drops out between 120k and 150k, so it has no spikes there: the windows
    # declared below and these spikes must agree (core.spike_events.within_observation).
    u2 = [t for t in range(45_000, 300_000, 21_000) if not 120_000 < t < 150_000]
    return {
        "core.sessions": [{"session_id": "s001", "subject_id": "m001",
                           "session_start_time": START,
                           "session_end_time": START + timedelta(hours=1),
                           "session_description": "Two-trial synthetic fixture session.",
                           "institution": "Example Institute", "task_name": "two_choice",
                           # R27 2: the behavior clock hangs off this one, so it is the root.
                           "reference_clock_id": "imec_ap_s001"}],
        "core.subjects": [{"subject_id": "m001", "species": "Mus musculus", "sex": "M",
                           "date_of_birth": (START - timedelta(days=120)).date(),
                           "genotype": "wt", "strain": "C57BL/6J"}],
        "core.session_experimenters": [
            {"session_id": "s001", "experimenter": "A. Researcher"},
            {"session_id": "s001", "experimenter": "B. Technician"}],
        "core.devices": [{"device_id": "imec0", "session_id": "s001",
                          "name": "Neuropixels headstage", "manufacturer": "imec",
                          "model": "Neuropixels 1.0"}],
        "core.probes": [{"probe_id": "probe0", "session_id": "s001", "device_id": "imec0",
                         "name": "probe0", "probe_type": "Neuropixels 1.0",
                         "manufacturer": "imec", "target_region": "VISp"}],
        "core.electrodes": [
            {"electrode_id": f"elec_{i:03d}", "session_id": "s001", "probe_id": "probe0",
             "local_electrode_label": str(i), "local_channel_label": f"AP{i}",
             "brain_region": "VISp"} for i in range(4)],
        # R28: a unit sits on several electrodes and somewhere, in more than one frame.
        # R28: a unit sits on several electrodes and somewhere, in more than one frame.
        # Each unit's set contains its own default_electrode_id, which R28 2.1 requires.
        "core.unit_electrodes": [
            {"session_id": "s001", "unit_id": unit, "sorting_run_id": "sort_ks4_001",
             "curation_id": "curation_001", "electrode_id": f"elec_{e:03d}",
             "channel_ordinal": k, "is_primary": f"elec_{e:03d}" == primary,
             "amplitude": -80.0 + k}
            for unit, primary, contacts in (
                ("unit_001", "elec_001", (0, 1, 2)),
                ("unit_002", "elec_003", (2, 3)))
            for k, e in enumerate(contacts)],
        "core.unit_coordinates": [
            {"session_id": "s001", "unit_id": unit, "sorting_run_id": "sort_ks4_001",
             "curation_id": "curation_001", "coordinate_frame": frame,
             "x_um": x, "y_um": y, "z_um": z}
            for unit, depth in (("unit_001", 22.0), ("unit_002", 58.0))
            for frame, x, y, z in (("probe", 8.0, depth, None),
                                   ("ccf", -1960.0, 8770.0 + depth, -5140.0))],
        "core.electrode_coordinates": [
            {"electrode_id": f"elec_{i:03d}", "coordinate_frame": frame,
             "x_um": x, "y_um": y, "z_um": z}
            for i in range(4)
            for frame, x, y, z in (
                ("probe", 0.0 + (i % 2) * 16.0, 20.0 * (i // 2), None),
                ("ccf", -1968.4 + i, 8768.5 + i, -5142.2 + i))],
        "core.clocks": [
            {"clock_id": "imec_ap_s001", "session_id": "s001",
             "name": "Neuropixels AP sample clock", "tick_rate_hz": float(AP_HZ),
             "origin": "sample 0 at acquisition start", "tick_zero_utc": START},
            {"clock_id": "behavior_s001", "session_id": "s001",
             "name": "behavior acquisition clock", "tick_rate_hz": float(BEH_HZ),
             "origin": "tick 0 at behavior start", "parent_clock_id": "imec_ap_s001",
             "transform_slope": float(AP_HZ / BEH_HZ), "transform_offset": 0.0,
             "tick_zero_utc": START}],
        "core.trials": [
            {"session_id": "s001", "trial_id": "trial_0001", "start_tick": 1000,
             "stop_tick": 5000, "clock_id": "behavior_s001", "condition_id": "A_high",
             "stimulus_id": "grating_45", "choice": "left", "rewarded": True},
            {"session_id": "s001", "trial_id": "trial_0002", "start_tick": 6000,
             "stop_tick": 10000, "clock_id": "behavior_s001", "condition_id": "A_high",
             "stimulus_id": "grating_45", "choice": "right", "rewarded": False}],
        "core.trial_tags": [
            {"session_id": "s001", "trial_id": "trial_0001", "tag": "hit"},
            {"session_id": "s001", "trial_id": "trial_0002", "tag": "miss"},
            {"session_id": "s001", "trial_id": "trial_0002", "tag": "review"}],
        # Three streams: one hardware-detected, one with a processing run behind it, and
        # one emitting two event types -- which is why R23 4.1 keeps event_type on the row.
        "core.event_streams": [
            {"event_stream_id": "stim", "session_id": "s001", "name": "stimulus_trigger",
             "clock_id": "behavior_s001", "device_id": None, "processing_run_id": None},
            {"event_stream_id": "reward", "session_id": "s001", "name": "reward_valve",
             "clock_id": "behavior_s001", "device_id": "imec0", "processing_run_id": None},
            {"event_stream_id": "lick", "session_id": "s001", "name": "lick_sensor",
             "clock_id": "behavior_s001", "device_id": "imec0",
             "processing_run_id": "run_import_001"}],
        "core.event_stream_observation_intervals": [
            {"event_stream_id": "stim", "interval_index": 0, "start_tick": 0, "stop_tick": 12000},
            {"event_stream_id": "reward", "interval_index": 0, "start_tick": 0, "stop_tick": 5000},
            # the sensor dropped out mid-session, which is why one window is not enough
            {"event_stream_id": "reward", "interval_index": 1, "start_tick": 6000, "stop_tick": 12000}],
        "core.events": [
            {"session_id": "s001", "event_id": "ev_0001", "stream_id": "stim",
             "event_type": "stimulus_onset", "t_tick": 1200, "clock_id": "behavior_s001"},
            {"session_id": "s001", "event_id": "ev_0002", "stream_id": "reward",
             "event_type": "reward", "t_tick": 4200, "clock_id": "behavior_s001"},
            {"session_id": "s001", "event_id": "ev_0003", "stream_id": "stim",
             "event_type": "stimulus_offset", "t_tick": 6200, "clock_id": "behavior_s001"},
            {"session_id": "s001", "event_id": "ev_0004", "stream_id": "lick",
             "event_type": "lick", "t_tick": 6900, "clock_id": "behavior_s001"}],
        "core.sorting_runs": [
            {"sorting_run_id": "sort_ks4_001", "session_id": "s001", "probe_id": "probe0",
             "sorter_name": "kilosort4", "sorter_version": "4.0.16",
             "amplitude_unit": "uV", "started_at": START + timedelta(hours=2),
             "ended_at": START + timedelta(hours=3)}],
        "core.curation_versions": [
            {"curation_id": "curation_001", "sorting_run_id": "sort_ks4_001",
             "session_id": "s001", "curator": "A. Researcher", "curation_tool": "phy",
             "curation_tool_version": "2.0.0",
             "created_at": START + timedelta(hours=4)}],
        "core.units": [
            {"session_id": "s001", "unit_id": "unit_001", "probe_id": "probe0",
             "sorting_run_id": "sort_ks4_001", "curation_id": "curation_001",
             "local_unit_label": "17", "quality_label": "sua",
             "quality_label_source": "decoder",
             "default_electrode_id": "elec_001",
             "firing_rate_hz": len(u1) / (300_000 / AP_HZ),
             "n_spikes": len(u1), "first_spike_tick": u1[0], "last_spike_tick": u1[-1]},
            {"session_id": "s001", "unit_id": "unit_002", "probe_id": "probe0",
             "sorting_run_id": "sort_ks4_001", "curation_id": "curation_001",
             "local_unit_label": "42", "quality_label": "mua",
             "quality_label_source": "decoder",
             "default_electrode_id": "elec_003",
             "firing_rate_hz": len(u2) / (300_000 / AP_HZ),
             "n_spikes": len(u2), "first_spike_tick": u2[0], "last_spike_tick": u2[-1]}],
        "core.unit_quality_labels": [
            {"session_id": "s001", "unit_id": u, "sorting_run_id": "sort_ks4_001",
             "curation_id": "curation_001", "source": src, "label": lab,
             "normalized_label": norm, "confidence": conf}
            for u, src, lab, norm, conf in (
                ("unit_001", "decoder", "sua", "sua", 0.94),
                ("unit_001", "bombcell", "good", "sua", None),
                ("unit_002", "decoder", "mua", "mua", 0.71),
                # non_soma has no honest projection, so it is null rather than forced (R22 3).
                ("unit_002", "bombcell", "non_soma", None, None))],
        "core.unit_observation_intervals": [
            {"session_id": "s001", "unit_id": u, "sorting_run_id": "sort_ks4_001",
             "curation_id": "curation_001", "interval_index": i,
             "start_tick": lo, "stop_tick": hi, "clock_id": "imec_ap_s001"}
            for u, windows in (("unit_001", [(0, 300_000)]),
                               ("unit_002", [(0, 120_000), (150_000, 300_000)]))
            for i, (lo, hi) in enumerate(windows)],
        "core.spike_events":
            spikes("unit_001", "sort_ks4_001", "curation_001", "imec_ap_s001", u1) +
            spikes("unit_002", "sort_ks4_001", "curation_001", "imec_ap_s001", u2),
        "core.source_files": [
            {"source_file_id": "src_0001", "uri": "raw/s001_imec0_ap.bin",
             "format": "spikeglx_bin", "size_bytes": 1234567890,
             "modified_at": START + timedelta(hours=1)}],
        "core.processing_runs": [
            {"processing_run_id": "run_import_001", "session_id": "s001",
             "activity_type": "import", "software_name": "nwb_lake",
             "software_version": "0.1.0", "status": "succeeded",
             "started_at": START + timedelta(hours=5),
             "ended_at": START + timedelta(hours=5, minutes=10)}],
        "core.processing_run_inputs": [
            {"processing_run_id": "run_import_001", "source_file_id": "src_0001"}],
    }


def sql_name(resource): return resource.replace(".", "_")


def sort_rows(resource: str, rows: list[dict]) -> list[dict]:
    """Apply the registry's declared physical ordering (R10 §2), as a writer should."""
    keys = REGISTRY["tables"][resource].get("sort")
    if not keys:
        return rows
    return sorted(rows, key=lambda r: tuple((r.get(k) is None, r.get(k)) for k in keys))


def write_packet(out: Path, tables: dict[str, list[dict]], *, raw: dict = None,
                 unsorted: frozenset = frozenset()):
    """Write a packet in 03's portable layout. `raw` supplies pre-built Arrow tables for
    variants that must violate the registry's own schema; `unsorted` names resources
    written in insertion order, for variants that must violate R10 §2."""
    if out.exists():
        shutil.rmtree(out)
    (out / "tables" / "core").mkdir(parents=True)
    (out / "schemas").mkdir()

    resources = []
    for resource, rows in tables.items():
        ordered = rows if resource in unsorted else sort_rows(resource, rows)
        t = (raw or {}).get(resource) or table(resource, ordered)
        rel = f"tables/core/{resource.split('.')[1]}.parquet"
        pq.write_table(t, out / rel, compression="zstd")
        resources.append({
            "resource_id": resource, "layer": "core", "kind": "table",
            "schema_id": f"{resource}.v0.1", "physical_profile": "parquet",
            "uri": rel, "canonical": True, "validation_state": "not_run"})

    (out / "schemas" / "logical_schemas.json").write_text(
        json.dumps(REGISTRY, indent=2) + "\n")
    (out / "schemas" / "semantic_version.txt").write_text(
        REGISTRY["semantic_standard_version"] + "\n")

    sessions = sorted({r["session_id"] for r in tables["core.sessions"]})
    (out / "nwb.packet.json").write_text(json.dumps({
        "packet_id": out.name,
        "packet_version": "0.1.0",
        "profile_id": "nwb-lake-portable-v0.1",
        "semantic_standard_version": REGISTRY["semantic_standard_version"],
        "logical_standard_version": REGISTRY["logical_standard_version"],
        "registry_version": REGISTRY["registry_version"],
        "created_at": "2026-08-26T00:00:00Z",
        "dataset_id": "nwb_lake_phase0",
        "description": "Phase 0 synthetic fixture, single session (R1 §6).",
        "sessions": sessions,
        "required_codecs": [],
        "resources": resources,
        "validation": {"status": "not_run", "validated_at": "2026-08-26T00:00:00Z",
                       "validator_name": "nwb_lake_validate", "validator_version": "0.1.0"},
        "provenance": {"import_processing_run_id": "run_import_001"},
    }, indent=2) + "\n")


# Each variant violates exactly one rule, so the corpus demonstrates that each check fires.
def variants():
    def dup_pk(c):
        c["core.trials"].append(dict(c["core.trials"][0]))
    def orphan_fk(c):
        c["core.trials"][1]["clock_id"] = "no_such_clock"
    def null_required(c):
        c["core.events"][2]["event_type"] = None
    def bad_vocabulary(c):
        # bombcell's raw label belongs in `label`; the designated column holds the
        # projection, which stays closed to sua/mua/noise (R22 5).
        c["core.units"][0]["quality_label"] = "good"
    def bad_interval(c):
        c["core.trials"][1]["stop_tick"] = 5999             # before its start_tick
    def stale_summary(c):
        c["core.units"][0]["n_spikes"] += 5
    def missing_amplitude_unit(c):
        c["core.sorting_runs"][0]["amplitude_unit"] = None
    def half_transform(c):
        c["core.clocks"][1]["transform_offset"] = None
    def unsorted_spikes(c):
        s = c["core.spike_events"]
        s[3], s[4] = s[4], s[3]
    def inconsistent_projection(c):
        # bombcell's `good` already projects to `sua` for unit_001; projecting the same
        # (source, label) pair to `mua` here is not a projection at all (R22 4).
        c["core.unit_quality_labels"].append(
            {"session_id": "s001", "unit_id": "unit_003", "sorting_run_id": "sort_ks4_001",
             "curation_id": "curation_001", "source": "bombcell", "label": "good",
             "normalized_label": "mua", "confidence": None})
    def spike_outside_window(c):
        # a spike in unit_002's declared drop-out, which its windows say was not observed
        c["core.spike_events"].append(
            {"session_id": "s001", "unit_id": "unit_002", "sorting_run_id": "sort_ks4_001",
             "curation_id": "curation_001", "t_tick": 129_000, "clock_id": "imec_ap_s001",
             "amplitude": -80.0})
        c["core.units"][1]["n_spikes"] += 1
    def stream_clock_mismatch(c):
        # An event on a clock its own stream does not declare (R23 4.2).
        c["core.events"][0]["clock_id"] = "imec_ap_s001"
    def orphan_manifest_session(c):
        c["core.sessions"][0]["session_id"] = "s999"        # manifest still says s001

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
            {"clock_id": "aux_s001", "session_id": "s001", "name": "unparented aux clock",
             "tick_rate_hz": 1000.0, "origin": "tick 0 at aux start"})
    def unaligned_clock(c):
        # Parentage known, alignment not measured -- legal under R13 4, a defect once the
        # session declares a reference (R27 4).
        c["core.clocks"][1]["transform_slope"] = None
        c["core.clocks"][1]["transform_offset"] = None
    # R28: the unit-to-electrode links must be usable.
    def two_primaries(c):
        # Two peak channels is not a peak, and the reader has no rule for choosing.
        c["core.unit_electrodes"][0]["is_primary"] = True
        c["core.unit_electrodes"][2]["is_primary"] = True
    def gapped_ordinal(c):
        # A dense waveform axis indexed by this addresses a row that is not there (R20 2).
        c["core.unit_electrodes"][2]["channel_ordinal"] = 7
    def undetected_default(c):
        # The designated electrode is not one the unit was detected on.
        c["core.units"][0]["default_electrode_id"] = "elec_003"
    def wide_anchor_gap(c):
        # 1 kHz anchors with one 20x hole: inside the span, outside the bound (R27 5.3).
        c["core.clocks"][1]["transform_slope"] = None
        c["core.clocks"][1]["transform_offset"] = None
        c["core.clock_anchors"] = [
            {"clock_id": "behavior_s001", "anchor_index": i, "t_tick": t,
             "parent_tick": t * 30}
            for i, t in enumerate([0, 1000, 2000, 3000, 23_000, 24_000, 25_000])]
    return {"dup_pk": dup_pk, "orphan_fk": orphan_fk, "null_required": null_required,
            "bad_vocabulary": bad_vocabulary, "bad_interval": bad_interval,
            "stale_summary": stale_summary,
            "missing_amplitude_unit": missing_amplitude_unit,
            "half_transform": half_transform, "unsorted_spikes": unsorted_spikes,
            "inconsistent_projection": inconsistent_projection,
            "spike_outside_window": spike_outside_window,
            "stream_clock_mismatch": stream_clock_mismatch,
            "orphan_manifest_session": orphan_manifest_session,
            "no_reference_clock": no_reference_clock, "clock_cycle": clock_cycle,
            "unreachable_clock": unreachable_clock, "unaligned_clock": unaligned_clock,
            "wide_anchor_gap": wide_anchor_gap, "two_primaries": two_primaries,
            "gapped_ordinal": gapped_ordinal, "undetected_default": undetected_default}


def main():
    root = HERE / "packets"
    write_packet(root / "valid", content())
    print(f"valid                     {sum(len(v) for v in content().values()):>5d} rows")

    for name, mutate in variants().items():
        c = content()
        mutate(c)
        if name == "unsorted_spikes":               # must defeat the writer's sort
            write_packet(root / name, c, unsorted=frozenset({"core.spike_events"}))
        elif name == "orphan_manifest_session":     # manifest must keep the original id
            write_packet(root / name, c)
            m = json.loads((root / name / "nwb.packet.json").read_text())
            m["sessions"] = ["s001"]
            (root / name / "nwb.packet.json").write_text(json.dumps(m, indent=2) + "\n")
        else:
            write_packet(root / name, c)
        print(f"{name:26s}written")

    # Two variants must break the physical schema, not the data.
    c = content()
    t = table("core.trials", c["core.trials"])
    wrong = t.set_column(t.schema.get_field_index("start_tick"), "start_tick",
                         t.column("start_tick").cast(pa.int32()))
    write_packet(root / "bad_type", c, raw={"core.trials": wrong})
    print(f"{'bad_type':26s}written")

    c = content()
    t = table("core.trials", c["core.trials"])
    write_packet(root / "missing_column", c,
                 raw={"core.trials": t.drop_columns(["condition_id"])})
    print(f"{'missing_column':26s}written")


if __name__ == "__main__":
    main()
