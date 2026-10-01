"""The valid session's rows, and a packet built from them once they are edited."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from .record import Build, Packet
from .registry import KIND
from .writing import edit_manifest, write_packet


def trial(label: int) -> str:
    """Name a trial as a writer does: its session and kind, then its source's label."""
    return f"s001/{KIND}/{label}"


START = datetime(2026, 8, 20, 14, 0, 0, tzinfo=UTC)
AP_HZ, BEH_HZ = 30_000, 1_000


def spikes(unit, run, cur, clock, ticks):
    # R96 §3.4: the tick reaches its clock through the unit, so the spike carries none.
    return [
        {
            "session_id": "s001",
            "unit_id": unit,
            "t_tick": int(t),
            "amplitude": float(-80 - (i % 7) * 3),
        }
        for i, t in enumerate(ticks)
    ]


def content() -> dict[str, list[dict]]:
    u1 = list(range(30_000, 300_000, 9_000))  # unit_001, ~3.3 Hz on the AP clock
    # unit_002 drops out between 120k and 150k, so it has no spikes there: the windows
    # declared below and these spikes must agree (core.spike_events.within_observation).
    u2 = [t for t in range(45_000, 300_000, 21_000) if not 120_000 < t < 150_000]
    # Part 01 §3.8: a position is one row per axis of its frame, so each is written once here and
    # split below into the coordinate row and its values. The `probe` frame has two axes and the
    # `ccf` frame three, which is the arity the frame declares rather than a column count.
    unit_positions = [
        (unit, frame, values, region, label)
        for unit, depth in ((1, 22.0), (2, 58.0))
        for frame, values, region, label in (
            ("probe", (8.0, depth), None, None),
            ("ccf", (-1960.0, 8770.0 + depth, -5140.0), 385, "VISp"),
        )
    ]
    electrode_positions = [
        (f"elec_{i:03d}", frame, values, region, label)
        for i in range(4)
        for frame, values, region, label in (
            ("probe", (0.0 + (i % 2) * 16.0, 20.0 * (i // 2)), None, None),
            ("ccf", (-1968.4 + i, 8768.5 + i, -5142.2 + i), 385, "VISp"),
        )
    ]
    return {
        "core.sessions": [
            {
                "session_id": "s001",
                "subject_id": "m001",
                "session_start_time": START,
                "session_end_time": START + timedelta(hours=1),
                "session_description": "Two-trial synthetic fixture session.",
                "institution": "Example Institute",
                "task_name": "two_choice",
                # R27 2: the behavior clock hangs off this one, so it is the root.
                "reference_clock_id": "imec_ap_s001",
            }
        ],
        "core.subjects": [
            {
                "subject_id": "m001",
                "species": "Mus musculus",
                "sex": "male",
                "date_of_birth": (START - timedelta(days=120)).date(),
                "genotype": "wt",
                "strain": "C57BL/6J",
            }
        ],
        "core.session_experimenters": [
            {"session_id": "s001", "experimenter": "A. Researcher"},
            {"session_id": "s001", "experimenter": "B. Technician"},
        ],
        "core.devices": [
            {
                "device_id": "imec0",
                "session_id": "s001",
                "manufacturer": "imec",
                "model": "Neuropixels 1.0",
            }
        ],
        "core.probes": [
            {
                "probe_id": "probe0",
                "session_id": "s001",
                "device_id": "imec0",
                "probe_type": "Neuropixels 1.0",
                "manufacturer": "imec",
                "target_region": "VISp",
            }
        ],
        "core.electrodes": [
            {
                "electrode_id": f"elec_{i:03d}",
                "session_id": "s001",
                "probe_id": "probe0",
                "local_electrode_label": str(i),
                "local_channel_label": f"AP{i}",
            }
            for i in range(4)
        ],
        # R83 2.1: the channels the sorting ran on, in its own order. `elec_002` was dropped,
        # so a channel index and a contact position part company at position 2 -- which is the
        # whole reason the list has to be written down.
        "core.sorting_run_channels": [
            {
                "session_id": "s001",
                "sorting_run_id": "sort_ks4_001",
                "channel_index": k,
                "electrode_id": f"elec_{e:03d}",
            }
            for k, e in enumerate((0, 1, 3))
        ],
        # R28: a unit sits on several electrodes and somewhere, in more than one frame.
        # Each unit's set contains its own default_electrode_id, which R28 2.1 requires.
        "core.unit_electrodes": [
            {
                "session_id": "s001",
                "unit_id": unit,
                "electrode_id": f"elec_{e:03d}",
                "is_primary": f"elec_{e:03d}" == primary,
            }
            # Contacts drawn from the run's channel list only, which R83 2.4 requires:
            # `elec_002` is a real electrode the sorting dropped, so no unit can sit on it.
            for unit, primary, contacts in (
                (1, "elec_001", (0, 1, 3)),
                (2, "elec_003", (1, 3)),
            )
            for e in contacts
        ],
        # Part 01 §3.24: which space a frame name means is a declared row. `ccf` names the atlas and
        # its version; `probe` is nobody's published atlas, so both are null and the description
        # is what a reader without one has.
        "core.coordinate_frames": [
            {
                "session_id": "s001",
                "coordinate_frame": "ccf",
                "atlas": "Allen Mouse Brain Common Coordinate Framework",
                "atlas_version": "CCFv3",
                "description": None,
            },
            {
                "session_id": "s001",
                "coordinate_frame": "probe",
                "atlas": None,
                "atlas_version": None,
                "description": "contact positions on the shank, as the probe file states them",
            },
        ],
        # Part 02 §12.7: `axis_name` is the source's own word for the field, and `axis_direction` is
        # null on the shank because no source of a probe geometry says which way `rel_x` runs.
        "core.coordinate_frame_axes": [
            {
                "session_id": "s001",
                "coordinate_frame": frame,
                "axis_index": i,
                "axis_name": name,
                "axis_direction": direction,
                "unit": "um",
            }
            for frame, axes in (
                (
                    "ccf",
                    (
                        ("ccf_ml", "right"),
                        ("ccf_ap", "posterior"),
                        ("ccf_dv", "inferior"),
                    ),
                ),
                ("probe", (("rel_x", None), ("rel_y", None))),
            )
            for i, (name, direction) in enumerate(axes)
        ],
        "core.unit_coordinates": [
            {
                "session_id": "s001",
                "unit_id": unit,
                "coordinate_frame": frame,
                "coordinate_basis": "measured",
                "region_id": region,
                "region_label": label,
            }
            for unit, frame, _values, region, label in unit_positions
        ],
        "core.unit_coordinate_values": [
            {
                "session_id": "s001",
                "unit_id": unit,
                "coordinate_frame": frame,
                "coordinate_basis": "measured",
                "axis_index": i,
                "axis_value": value,
            }
            for unit, frame, values, _region, _label in unit_positions
            for i, value in enumerate(values)
        ],
        "core.electrode_coordinates": [
            {
                "session_id": "s001",
                "electrode_id": electrode,
                "coordinate_frame": frame,
                "coordinate_basis": "measured",
                "region_id": region,
                "region_label": label,
            }
            for electrode, frame, _values, region, label in electrode_positions
        ],
        "core.electrode_coordinate_values": [
            {
                "session_id": "s001",
                "electrode_id": electrode,
                "coordinate_frame": frame,
                "coordinate_basis": "measured",
                "axis_index": i,
                "axis_value": value,
            }
            for electrode, frame, values, _region, _label in electrode_positions
            for i, value in enumerate(values)
        ],
        # In name order, because R53 numbers a name to its rank and Part 03 §5.3 sorts by the key --
        # so the file's order is the names' order, and the child now precedes its parent.
        "core.clocks": [
            {
                "clock_id": "behavior_s001",
                "session_id": "s001",
                "tick_rate_hz": float(BEH_HZ),
                "origin": "tick 0 at behavior start",
                "parent_clock_id": "imec_ap_s001",
                "transform_slope": float(AP_HZ / BEH_HZ),
                "transform_offset": 0.0,
                "tick_zero_utc": START,
            },
            {
                "clock_id": "imec_ap_s001",
                "session_id": "s001",
                "tick_rate_hz": float(AP_HZ),
                "origin": "sample 0 at acquisition start",
                "tick_zero_utc": START,
            },
        ],
        # Part 01 §3.10: the kind is a dotted resource ID naming the table that says what the
        # interval was, and §2.4a makes naming one the packet does not carry an error.
        "core.intervals": [
            {
                "session_id": "s001",
                "interval_kind": KIND,
                "interval_id": trial(1),
                "local_interval_label": "1",
                "start_tick": 1000,
                "stop_tick": 5000,
                "clock_id": "behavior_s001",
            },
            {
                "session_id": "s001",
                "interval_kind": KIND,
                "interval_id": trial(2),
                "local_interval_label": "2",
                "start_tick": 6000,
                "stop_tick": 10000,
                "clock_id": "behavior_s001",
            },
        ],
        KIND: [
            {
                "session_id": "s001",
                "trial_id": trial(1),
                "animal_response": "left",
                "rewarded_history_left": True,
                "rewarded_history_right": False,
            },
            {
                "session_id": "s001",
                "trial_id": trial(2),
                "animal_response": "right",
                "rewarded_history_left": False,
                "rewarded_history_right": False,
            },
        ],
        # Three streams: one hardware-detected, one with a processing run behind it, and
        # one emitting two event types -- which is why R23 4.1 keeps event_type on the row.
        # R91 §3.1: a stream emits one kind of event, so the trigger's onset and offset are two.
        "core.event_streams": [
            {
                "event_stream_id": "stim",
                "session_id": "s001",
                "event_type": "stimulus_onset",
                "clock_id": "behavior_s001",
                "device_id": None,
                "processing_run_id": None,
            },
            {
                "event_stream_id": "stim_off",
                "session_id": "s001",
                "event_type": "stimulus_offset",
                "clock_id": "behavior_s001",
                "device_id": None,
                "processing_run_id": None,
            },
            {
                "event_stream_id": "reward",
                "session_id": "s001",
                "event_type": "reward",
                "clock_id": "behavior_s001",
                "device_id": "imec0",
                "processing_run_id": None,
            },
            {
                "event_stream_id": "lick",
                "session_id": "s001",
                "event_type": "lick",
                "clock_id": "behavior_s001",
                "device_id": "imec0",
                "processing_run_id": "run_import_001",
            },
        ],
        "core.event_stream_observation_intervals": [
            {
                "session_id": "s001",
                "event_stream_id": "stim",
                "start_tick": 0,
                "stop_tick": 12000,
            },
            {
                "session_id": "s001",
                "event_stream_id": "reward",
                "start_tick": 0,
                "stop_tick": 5000,
            },
            # the sensor dropped out mid-session, which is why one window is not enough
            {
                "session_id": "s001",
                "event_stream_id": "reward",
                "start_tick": 6000,
                "stop_tick": 12000,
            },
        ],
        # R91 §3.2: an event is a tick on a stream, keyed (session_id, stream_id, t_tick).
        "core.events": [
            {"session_id": "s001", "stream_id": "lick", "t_tick": 6900},
            {"session_id": "s001", "stream_id": "reward", "t_tick": 4200},
            {"session_id": "s001", "stream_id": "stim", "t_tick": 1200},
            {"session_id": "s001", "stream_id": "stim_off", "t_tick": 6200},
        ],
        "core.sorting_runs": [
            {
                "sorting_run_id": "sort_ks4_001",
                "session_id": "s001",
                "probe_id": "probe0",
                # R96 §3: the clock and the unit of measure moved to the units this run produced.
                "sorter_name": "kilosort4",
                "sorter_version": "4.0.16",
                "started_at": START + timedelta(hours=2),
                "ended_at": START + timedelta(hours=3),
            }
        ],
        "core.curation_versions": [
            {
                "curation_id": "curation_001",
                "sorting_run_id": "sort_ks4_001",
                "session_id": "s001",
                "curator": "A. Researcher",
                "curation_tool": "phy",
                "curation_tool_version": "2.0.0",
                "created_at": START + timedelta(hours=4),
            }
        ],
        "core.units": [
            {
                "session_id": "s001",
                "unit_id": 1,
                "probe_id": "probe0",
                "sorting_run_id": "sort_ks4_001",
                "curation_id": "curation_001",
                "local_unit_label": "17",
                "quality_label": "sua",
                "quality_label_source": "decoder",
                "clock_id": "imec_ap_s001",
                "amplitude_unit": "uV",
                "firing_rate_hz": len(u1) / (300_000 / AP_HZ),
                "n_spikes": len(u1),
                "first_spike_tick": u1[0],
                "last_spike_tick": u1[-1],
            },
            {
                "session_id": "s001",
                "unit_id": 2,
                "probe_id": "probe0",
                "sorting_run_id": "sort_ks4_001",
                "curation_id": "curation_001",
                "local_unit_label": "42",
                "quality_label": "mua",
                "quality_label_source": "decoder",
                "clock_id": "imec_ap_s001",
                "amplitude_unit": "uV",
                "firing_rate_hz": len(u2) / (300_000 / AP_HZ),
                "n_spikes": len(u2),
                "first_spike_tick": u2[0],
                "last_spike_tick": u2[-1],
            },
        ],
        "core.unit_quality_labels": [
            {
                "session_id": "s001",
                "unit_id": u,
                "source": src,
                "label": lab,
                "normalized_label": norm,
                "confidence": conf,
            }
            for u, src, lab, norm, conf in (
                (1, "decoder", "sua", "sua", 0.94),
                (1, "bombcell", "good", "sua", None),
                (2, "decoder", "mua", "mua", 0.71),
                # non_soma has no honest projection, so it is null rather than forced (R22 3).
                (2, "bombcell", "non_soma", None, None),
            )
        ],
        # Part 02 §12.5: a clock anything is timestamped on says when it was observing. Each window
        # contains the per-thing windows below, which Part 01 §2.2 narrows it with rather than adding to.
        "core.clock_observation_intervals": [
            {
                "session_id": "s001",
                "clock_id": "imec_ap_s001",
                "start_tick": 0,
                "stop_tick": 300_000,
            },
            {
                "session_id": "s001",
                "clock_id": "behavior_s001",
                "start_tick": 0,
                "stop_tick": 12_000,
            },
        ],
        "core.unit_observation_intervals": [
            {
                "session_id": "s001",
                "unit_id": u,
                "start_tick": lo,
                "stop_tick": hi,
            }
            for u, windows in (
                (1, [(0, 300_000)]),
                (2, [(0, 120_000), (150_000, 300_000)]),
            )
            for i, (lo, hi) in enumerate(windows)
        ],
        "core.spike_events": spikes(1, "sort_ks4_001", "curation_001", "imec_ap_s001", u1)
        + spikes(2, "sort_ks4_001", "curation_001", "imec_ap_s001", u2),
        "core.source_files": [
            {
                "source_file_id": "src_0001",
                "uri": "raw/s001_imec0_ap.bin",
                "format": "spikeglx_bin",
                "size_bytes": 1234567890,
                "modified_at": START + timedelta(hours=1),
            }
        ],
        "core.processing_runs": [
            {
                "processing_run_id": "run_import_001",
                "session_id": "s001",
                "activity_type": "import",
                "software_name": "escapewheel",
                "software_version": "0.1.0",
                "status": "succeeded",
                "started_at": START + timedelta(hours=5),
                "ended_at": START + timedelta(hours=5, minutes=10),
            }
        ],
        "core.processing_run_inputs": [
            {
                "session_id": "s001",
                "processing_run_id": "run_import_001",
                "source_file_id": "src_0001",
            }
        ],
    }


def variant(mutate=None, *, edit=None, **options) -> Build:
    """A build of the valid session once `mutate` has edited its rows.

    `options` are `write_packet`'s, and `edit` then changes the manifest.
    """

    def build(out: Path) -> None:
        c = content()
        if mutate is not None:
            mutate(c)
        write_packet(out, c, **options)
        if edit is not None:
            edit_manifest(out, edit)

    return build


VALID = Packet(
    "valid",
    variant(),
    absent=frozenset({"physical.outside_reader_floor", "external.physical_unassessed"}),
    checksums=True,
)


#: The valid packet's core tables specific to extracellular electrophysiology.
EXTRACELLULAR = (
    "core.probes",
    "core.electrodes",
    "core.electrode_coordinates",
    "core.electrode_coordinate_values",
    "core.sorting_runs",
    "core.sorting_run_channels",
    "core.curation_versions",
    "core.units",
    "core.spike_events",
    "core.unit_quality_labels",
    "core.unit_electrodes",
    "core.unit_coordinates",
    "core.unit_coordinate_values",
    "core.unit_observation_intervals",
)
