"""Build the Phase 0 fixture packets.

A conforming single-session packet per R1 §6, plus variants each violating exactly one
rule. Table schemas are taken from the registry rather than restated, so a fixture cannot
drift from the specification it is meant to exercise.
"""

import gzip
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader.ordering import stored_order

HERE = Path(__file__).resolve().parent
REGISTRY = json.loads((HERE.parent / "registry" / "logical_schemas.json").read_text())

#: The one extension this corpus carries. Part 01 §3.10a makes an `interval_kind` naming a resource
#: the packet does not declare an error, and no core table specialises an interval -- so a packet
#: with intervals carries an extension by construction, and the corpus has to as well.
EXTENSION_ID = "dynamic_foraging"
EXTENSION = json.loads(
    (HERE.parent / "registry" / "extensions" / f"{EXTENSION_ID}.json").read_text()
)

#: Every table a fixture may write, core's and the extension's alike.
SPECS = {
    name: declaration["table"]
    for document in (REGISTRY, EXTENSION)
    for name, declaration in document["resources"].items()
    if declaration["kind"] == "table"
}

#: The interval kind the fixture declares, which is the extension table that carries it.
KIND = "dynamic_foraging.trials"

ARROW = {
    "string": pa.string(),
    "int32": pa.int32(),
    "int64": pa.int64(),
    "float32": pa.float32(),
    "float64": pa.float64(),
    "bool": pa.bool_(),
    "date": pa.date32(),
    "timestamp": pa.timestamp("us", tz="UTC"),
    "json_string": pa.string(),
}

START = datetime(2026, 8, 20, 14, 0, 0, tzinfo=timezone.utc)
AP_HZ, BEH_HZ = 30_000, 1_000


def table(resource: str, rows: list[dict]) -> pa.Table:
    """Build an Arrow table for `resource` with exactly the registry's schema.

    Columns absent from `rows` are emitted as nulls unless the registry marks them
    optional, in which case they are omitted entirely — exercising all three presence
    states (Part 02 §6).
    """
    spec = SPECS[resource]
    rows = number(spec, [dict(r) for r in rows])
    arrays, fields = [], []
    for c in spec["columns"]:
        present = any(c["name"] in r for r in rows)
        if c["presence"] == "optional" and not present:
            continue
        typ = ARROW[c["type"]]
        arrays.append(pa.array([r.get(c["name"]) for r in rows], type=typ))
        fields.append(pa.field(c["name"], typ))
    return pa.table(arrays, schema=pa.schema(fields))


#: R53 §2.1: an identifier is an integer. The fixture writes names and numbers them here, one
#: map per column so every table agrees -- deliberately its own rather than the writer's, since
#: a hand-built packet exercises the format without going through the writer at all.
KEYS: dict[str, dict[str, int]] = {}


def number(spec, rows):
    """Replace an identifier's name with its number, and fill in the `*_name` that records it."""
    exported = {c for ref in spec.get("references", []) for c in ref["columns"]}
    primary = set(spec.get("primary_key") or [])
    declared = {c["name"] for c in spec["columns"]}
    # A foreign key numbers in the map of the column it points at. `parent_clock_id` and
    # `clock_id` are both clocks; numbering them apart makes the parent chain name a clock that
    # does not exist, which is what Part 01 §3.9 requires to be well-founded.
    target = {
        column: referenced
        for ref in spec.get("references", [])
        for column, referenced in zip(
            ref["columns"], ref["resource_columns"], strict=True
        )
    }
    identifiers = [c for c in spec["columns"] if c.get("role") == "identifier"]
    # Collect every name before assigning any: `parent_clock_id` and `clock_id` share a map, and
    # whichever column the loop reached first would otherwise decide the numbering.
    pending = {}
    for column in identifiers:
        if column.get("identity") != "assigned":
            continue
        kind = target.get(column["name"], column["name"])
        pending.setdefault(kind, set()).update(
            str(r[column["name"]]) for r in rows if r.get(column["name"]) is not None
        )
    for kind in sorted(pending):
        within = KEYS.setdefault(kind, {})
        for value in sorted(pending[kind]):
            within.setdefault(value, len(within))

    for column in identifiers:
        name = column["name"]
        assigned = column.get("identity") == "assigned"
        within = KEYS.setdefault(target.get(name, name), {})
        owns = assigned and name in primary and name not in exported
        named = f"{name.removesuffix('_id')}_name" if owns else None
        for row in rows:
            if row.get(name) is None:
                continue
            value = str(row[name])
            if named is not None and named in declared and row.get(named) is None:
                row[named] = value
            row[name] = within[value] if assigned else int(row[name])
    return rows


def preassign(tables: dict[str, list[dict]]) -> None:
    """Number every name the packet uses, before any table is built.

    Assigning as each table is built would let the order tables happen to be written in decide
    the numbers: `core.sessions` names a `reference_clock_id` and is written before
    `core.clocks`, so the clocks would be numbered by the session's mention of one of them.
    Part 05 §8 wants two builds of the same sources to produce the same packet, and this is what
    makes that hold across tables as well as within one.
    """
    pending: dict[str, set[str]] = {}
    for resource, rows in sorted(tables.items()):
        spec = SPECS.get(resource)
        if spec is None:
            continue
        target = {
            column: referenced
            for ref in spec.get("references", [])
            for column, referenced in zip(
                ref["columns"], ref["resource_columns"], strict=True
            )
        }
        for column in spec["columns"]:
            if (
                column.get("role") != "identifier"
                or column.get("identity") != "assigned"
            ):
                continue
            kind = target.get(column["name"], column["name"])
            pending.setdefault(kind, set()).update(
                str(r[column["name"]])
                for r in rows
                if r.get(column["name"]) is not None
            )
    for kind in sorted(pending):
        within = KEYS.setdefault(kind, {})
        for value in sorted(pending[kind]):
            within.setdefault(value, len(within))


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
                "name": "Neuropixels headstage",
                "manufacturer": "imec",
                "model": "Neuropixels 1.0",
            }
        ],
        "core.probes": [
            {
                "probe_id": "probe0",
                "session_id": "s001",
                "device_id": "imec0",
                "name": "probe0",
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
                "sorting_run_id": "sort_ks4_001",
                "curation_id": "curation_001",
                "electrode_id": f"elec_{e:03d}",
                "channel_index": k,
                "is_primary": f"elec_{e:03d}" == primary,
                "amplitude": -80.0 + k,
            }
            # Contacts drawn from the run's channel list only, which R83 2.4 requires:
            # `elec_002` is a real electrode the sorting dropped, so no unit can sit on it.
            for unit, primary, contacts in (
                (1, "elec_001", (0, 1, 3)),
                (2, "elec_003", (1, 3)),
            )
            for k, e in enumerate(contacts)
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
                "name": "behavior acquisition clock",
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
                "name": "Neuropixels AP sample clock",
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
                "interval_id": 1,
                "start_tick": 1000,
                "stop_tick": 5000,
                "clock_id": "behavior_s001",
            },
            {
                "session_id": "s001",
                "interval_kind": KIND,
                "interval_id": 2,
                "start_tick": 6000,
                "stop_tick": 10000,
                "clock_id": "behavior_s001",
            },
        ],
        KIND: [
            {
                "session_id": "s001",
                "interval_kind": KIND,
                "trial_id": 1,
                "animal_response": "left",
                "rewarded_history_left": True,
                "rewarded_history_right": False,
            },
            {
                "session_id": "s001",
                "interval_kind": KIND,
                "trial_id": 2,
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
                "name": "stimulus_trigger",
                "event_type": "stimulus_onset",
                "clock_id": "behavior_s001",
                "device_id": None,
                "processing_run_id": None,
            },
            {
                "event_stream_id": "stim_off",
                "session_id": "s001",
                "name": "stimulus_trigger_off",
                "event_type": "stimulus_offset",
                "clock_id": "behavior_s001",
                "device_id": None,
                "processing_run_id": None,
            },
            {
                "event_stream_id": "reward",
                "session_id": "s001",
                "name": "reward_valve",
                "event_type": "reward",
                "clock_id": "behavior_s001",
                "device_id": "imec0",
                "processing_run_id": None,
            },
            {
                "event_stream_id": "lick",
                "session_id": "s001",
                "name": "lick_sensor",
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
                "clock_id": "imec_ap_s001",
            }
            for u, windows in (
                (1, [(0, 300_000)]),
                (2, [(0, 120_000), (150_000, 300_000)]),
            )
            for i, (lo, hi) in enumerate(windows)
        ],
        "core.spike_events": spikes(
            1, "sort_ks4_001", "curation_001", "imec_ap_s001", u1
        )
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


def sql_name(resource):
    return resource.replace(".", "_")


def sort_rows(resource: str, rows: list[dict]) -> list[dict]:
    """Apply the registry's declared physical ordering (Part 03 §5.3), as a writer should.

    A resource declaring no sort takes its primary key's order, which Part 03 §5.3 requires of it:
    before that rule the thirteen tables with `sort: null` were written in insertion order and
    the validator scanned none of them.
    """
    keys = stored_order(resource, SPECS[resource])
    if not keys:
        return rows
    return sorted(rows, key=lambda r: tuple((r.get(k) is None, r.get(k)) for k in keys))


def write_packet(
    out: Path,
    tables: dict[str, list[dict]],
    *,
    raw: dict = None,
    unsorted: frozenset = frozenset(),
):
    """Write a packet in 03's portable layout. `raw` supplies pre-built Arrow tables for
    variants that must violate the registry's own schema; `unsorted` names resources
    written in insertion order, for variants that must violate Part 03 §5.3."""
    if out.exists():
        shutil.rmtree(out)
    KEYS.clear()
    preassign(tables)
    (out / "tables" / "core").mkdir(parents=True)

    resources = []
    for resource, rows in tables.items():
        ordered = rows if resource in unsorted else sort_rows(resource, rows)
        t = (raw or {}).get(resource) or table(resource, ordered)
        namespace, name = resource.split(".", 1)
        rel = f"tables/{namespace}/{name}.parquet"
        (out / "tables" / namespace).mkdir(exist_ok=True)
        pq.write_table(t, out / rel, compression="zstd")
        resources.append(
            {
                "resource_id": resource,
                "declaration_id": resource,
                "uri": rel,
                "validation_state": "not_run",
            }
        )

    registries = {
        document["registry_id"]: bind(out, document) for document in (REGISTRY, EXTENSION)
    }

    sessions = sorted({r["session_id"] for r in tables["core.sessions"]})
    (out / "packet.json").write_text(
        json.dumps(
            {
                "packet_id": out.name,
                "packet_version": "0.1.0",
                "profile_id": "escapewheel-portable-v0.1",
                "semantic_standard_version": REGISTRY["semantic_standard_version"],
                "logical_standard_version": REGISTRY["logical_standard_version"],
                "registries": registries,
                "created_at": "2026-08-26T00:00:00Z",
                "description": "Phase 0 synthetic fixture, single session (R1 §6).",
                "sessions": sessions,
                "resources": resources,
                "validation": {
                    "status": "not_run",
                    "validated_at": "2026-08-26T00:00:00Z",
                    "validator_name": "escapewheel_validate",
                    "validator_version": "0.1.0",
                },
            },
            indent=2,
        )
        + "\n"
    )


def bind(out, document):
    """Store a registry as Part 03 §3.3 requires and return its manifest descriptor."""
    body = (json.dumps(document, indent=2) + "\n").encode()
    relative = f"registries/{document['registry_id']}/{document['registry_version']}.json.gz"
    (out / relative).parent.mkdir(parents=True, exist_ok=True)
    (out / relative).write_bytes(gzip.compress(body, mtime=0))
    return {
        "role": "extension" if "extension_id" in document else "core",
        "version": document["registry_version"],
        "path": relative,
        "sha256": hashlib.sha256(body).hexdigest(),
    }


# Each variant violates exactly one rule, so the corpus demonstrates that each check fires.
def child(tables):
    """The clock that declares a parent, which is what the alignment variants are about."""
    return next(c for c in tables["core.clocks"] if c.get("parent_clock_id"))


def variants():
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
                "clock_id": "imec_ap_s001",
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
                "name": "unparented aux clock",
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

    def gapped_ordinal(c):
        # A dense waveform axis indexed by this addresses a row that is not there (R20 2).
        c["core.unit_electrodes"][2]["channel_index"] = 7

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
            r
            for r in c["core.clock_observation_intervals"]
            if r["clock_id"] != "imec_ap_s001"
        ]

    def frame_without_axes(c):
        # Part 01 §3.8: the frame declares two axes where its coordinates carry three, so every
        # `ccf_dv` value names an axis no frame declares and Tier 1's anti-join returns it.
        c["core.coordinate_frame_axes"] = [
            r
            for r in c["core.coordinate_frame_axes"]
            if not (r["coordinate_frame"] == "ccf" and r["axis_index"] == 2)
        ]

    def undeclared_currency(c):
        # One probe sorted twice with nothing saying which to read (Part 01 §2.4). Both runs carry
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
        # cannot be determined (Part 01 §2.4). The fix is to record the scopes, not to choose.
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

    return {
        "dup_pk": dup_pk,
        "orphan_fk": orphan_fk,
        "null_required": null_required,
        "bad_vocabulary": bad_vocabulary,
        "bad_interval": bad_interval,
        "unspecialised_interval": unspecialised_interval,
        "stale_summary": stale_summary,
        "missing_amplitude_unit": missing_amplitude_unit,
        "non_ucum_unit": non_ucum_unit,
        "half_transform": half_transform,
        "unsorted_spikes": unsorted_spikes,
        "inconsistent_projection": inconsistent_projection,
        "spike_outside_window": spike_outside_window,
        "orphan_manifest_session": orphan_manifest_session,
        "no_reference_clock": no_reference_clock,
        "clock_cycle": clock_cycle,
        "unreachable_clock": unreachable_clock,
        "unaligned_clock": unaligned_clock,
        "wide_anchor_gap": wide_anchor_gap,
        "two_primaries": two_primaries,
        "gapped_ordinal": gapped_ordinal,
        "unit_off_the_run": unit_off_the_run,
        "undeclared_currency": undeclared_currency,
        "unscoped_runs": unscoped_runs,
        "clock_without_window": clock_without_window,
        "frame_without_axes": frame_without_axes,
    }


def main():
    root = HERE / "packets"
    write_packet(root / "valid", content())
    print(
        f"valid                     {sum(len(v) for v in content().values()):>5d} rows"
    )

    for name, mutate in variants().items():
        c = content()
        mutate(c)
        if name == "unsorted_spikes":  # must defeat the writer's sort
            write_packet(root / name, c, unsorted=frozenset({"core.spike_events"}))
        elif name == "orphan_manifest_session":  # manifest must keep the original id
            write_packet(root / name, c)
            m = json.loads((root / name / "packet.json").read_text())
            m["sessions"] = ["s001"]
            (root / name / "packet.json").write_text(json.dumps(m, indent=2) + "\n")
        else:
            write_packet(root / name, c)
        print(f"{name:26s}written")

    # Three variants must break the physical schema, not the data.
    c = content()
    t = table("core.intervals", c["core.intervals"])
    wrong = t.set_column(
        t.schema.get_field_index("start_tick"),
        "start_tick",
        t.column("start_tick").cast(pa.int32()),
    )
    write_packet(root / "bad_type", c, raw={"core.intervals": wrong})
    print(f"{'bad_type':26s}written")

    # Part 05 §5.4: an extension's table is type-checked as core's are, and the finding is its own.
    c = content()
    t = table(KIND, c[KIND])
    wrong = t.set_column(
        t.schema.get_field_index("trial_id"),
        "trial_id",
        t.column("trial_id").cast(pa.float64()),
    )
    write_packet(root / "extension_bad_type", c, raw={KIND: wrong})
    print(f"{'extension_bad_type':26s}written")

    c = content()
    t = table("core.intervals", c["core.intervals"])
    write_packet(
        root / "missing_column", c, raw={"core.intervals": t.drop_columns(["clock_id"])}
    )
    print(f"{'missing_column':26s}written")


if __name__ == "__main__":
    main()
