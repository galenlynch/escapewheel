"""Build the Phase 0 fixture packets.

A conforming single-session packet per R1 §6, plus variants each violating exactly one
rule. Table schemas are taken from the registry rather than restated, so a fixture cannot
drift from the specification it is meant to exercise.
"""

import gzip
import hashlib
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
REGISTRY = json.loads((HERE.parent / "spec" / "artifacts" / "logical_schemas.json").read_text())
_PROFILE = json.loads(
    (HERE.parent / "spec" / "artifacts" / "physical_profiles" / "escapewheel-portable-v0.1.json").read_text()
)
#: Part 03 §5.4's overriding orders, read from the descriptor that owns them.
OVERRIDING_ORDERS = _PROFILE["interfaces"][_PROFILE["kind_interfaces"]["table"]].get("overriding_orders", {})

#: The one extension this corpus carries. Part 01 §3.10a makes an `interval_kind` naming a resource
#: the packet does not declare an error, and no core table specialises an interval -- so a packet
#: with intervals carries an extension by construction, and the corpus has to as well.
EXTENSION_ID = "dynamic_foraging"
EXTENSION = json.loads((HERE.parent / "extensions" / f"{EXTENSION_ID}.json").read_text())

#: The interval kind the fixture declares, which is the extension table that carries it.
KIND = "dynamic_foraging.trials"


def trial(label: int) -> str:
    """Name a trial as a writer does: its session and kind, then its source's label."""
    return f"s001/{KIND}/{label}"


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

START = datetime(2026, 8, 20, 14, 0, 0, tzinfo=UTC)
AP_HZ, BEH_HZ = 30_000, 1_000


class Numbering:
    """The number each name takes in one packet, among the tables its registries declare.

    R53 §2.1: an identifier is an integer. The fixture writes names and numbers them here, one
    map per column so every table agrees -- deliberately its own rather than the writer's, since
    a hand-built packet exercises the format without going through the writer at all.
    """

    def __init__(self, *registries: dict) -> None:
        #: Every table the packet may write, by resource ID.
        self.specs = {
            name: declaration["table"]
            for document in registries
            for name, declaration in document["resources"].items()
            if declaration["kind"] == "table"
        }
        #: Each identifier column's map from a name to its number.
        self.keys: dict[str, dict[str, int]] = {}

    def table(self, resource: str, rows: list[dict], readers=None) -> pa.Table:
        """Build an Arrow table for `resource` with exactly the registry's schema.

        Columns absent from `rows` are emitted as nulls unless the registry marks them
        optional, in which case they are omitted entirely — exercising all three presence
        states (Part 02 §6).
        """
        spec = self.specs[resource]
        declared = {c["name"] for c in spec["columns"]}
        if undeclared := sorted({key for row in rows for key in row} - declared):
            raise SystemExit(f"{resource}: no column declares {undeclared}, so it would be dropped")
        rows = self.number(spec, [dict(r) for r in rows], readers)
        arrays, fields = [], []
        for c in spec["columns"]:
            present = any(c["name"] in r for r in rows)
            if c["presence"] == "optional" and not present:
                continue
            typ = ARROW[c["type"]]
            arrays.append(pa.array([r.get(c["name"]) for r in rows], type=typ))
            fields.append(pa.field(c["name"], typ))
        return pa.table(arrays, schema=pa.schema(fields))

    def number(self, spec, rows, readers=None):
        """Replace an identifier's name with its number, and fill in the `*_name` that records it.

        `readers` maps an identifier paired value to a function from its row to the map it numbers in.
        """
        exported = {c for ref in spec.get("references", []) for c in ref["columns"]}
        primary = set(spec.get("primary_key") or [])
        declared = {c["name"] for c in spec["columns"]}
        # A foreign key numbers in the map of the column it points at. `parent_clock_id` and
        # `clock_id` are both clocks; numbering them apart makes the parent chain name a clock that
        # does not exist, which is what Part 01 §3.9 requires to be well-founded.
        target = {
            column: referenced
            for ref in spec.get("references", [])
            for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
        }
        identifiers = [c for c in spec["columns"] if c.get("role") == "identifier"]
        # Read before anything is numbered: a row reaches its kind through its own references.
        kinds = {name: [reader(r) for r in rows] for name, reader in (readers or {}).items()}

        def kind_of(name, index):
            return (kinds[name][index] if name in kinds else None) or target.get(name, name)

        # Collect every name before assigning any: `parent_clock_id` and `clock_id` share a map, and
        # whichever column the loop reached first would otherwise decide the numbering.
        pending = {}
        for column in identifiers:
            if column.get("identity") != "assigned":
                continue
            for index, r in enumerate(rows):
                if r.get(column["name"]) is not None:
                    pending.setdefault(kind_of(column["name"], index), set()).add(str(r[column["name"]]))
        for kind in sorted(pending):
            within = self.keys.setdefault(kind, {})
            for value in sorted(pending[kind]):
                within.setdefault(value, len(within))

        for column in identifiers:
            name = column["name"]
            assigned = column.get("identity") == "assigned"
            owns = assigned and name in primary and name not in exported
            named = f"{name.removesuffix('_id')}_name" if owns else None
            for index, row in enumerate(rows):
                if row.get(name) is None:
                    continue
                value = str(row[name])
                if named is not None and named in declared and row.get(named) is None:
                    row[named] = value
                if assigned:
                    row[name] = self.keys[kind_of(name, index)][value]
                elif column["type"] != "string":
                    row[name] = int(row[name])
        return rows

    def paired_readers(self, tables: dict[str, list[dict]], resource: str) -> dict:
        """Map each identifier paired value `resource` holds to a function from its row to its map.

        Part 02 §8.3 lets an identifier hold the key of whichever resource its row's kind names, so
        its map is that resource's one key column, chosen per row. A value on a specialised table
        reaches its kind through the reference back to the discriminator's table, by names.
        """

        def key_of(kind):
            key = (self.specs.get(kind) or {}).get("primary_key") or []
            return key[0] if len(key) == 1 else None

        readers = {}
        for owner, spec in self.specs.items():
            for column in spec["columns"]:
                if column.get("role") != "discriminator" or not column.get("discriminates"):
                    continue
                via = column.get("discriminates_via")
                if (owner if via is None else via.rsplit(".", 1)[0]) != resource:
                    continue
                name = column["name"]
                if via is None:
                    readers[column["discriminates"]] = lambda row, name=name: key_of(row.get(name))
                    continue
                back = next(r for r in self.specs[resource]["references"] if r["resource"] == owner)
                kinds = {
                    tuple(str(r.get(c)) for c in back["resource_columns"]): r.get(name) for r in tables.get(owner, [])
                }
                readers[column["discriminates"]] = lambda row, kinds=kinds, ours=back["columns"]: key_of(
                    kinds.get(tuple(str(row.get(c)) for c in ours))
                )
        return readers

    def preassign(self, tables: dict[str, list[dict]]) -> None:
        """Number every name the packet uses, before any table is built.

        Assigning as each table is built would let the order tables happen to be written in decide
        the numbers: `core.sessions` names a `reference_clock_id` and is written before
        `core.clocks`, so the clocks would be numbered by the session's mention of one of them.
        Part 05 §4.3 wants two builds of the same sources to produce the same packet, and this is what
        makes that hold across tables as well as within one.
        """
        pending: dict[str, set[str]] = {}
        for resource, rows in sorted(tables.items()):
            spec = self.specs.get(resource)
            if spec is None:
                continue
            target = {
                column: referenced
                for ref in spec.get("references", [])
                for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
            }
            readers = self.paired_readers(tables, resource)
            for column in spec["columns"]:
                name = column["name"]
                if column.get("role") != "identifier" or column.get("identity") != "assigned":
                    continue
                for r in rows:
                    if r.get(name) is not None:
                        kind = (readers[name](r) if name in readers else None) or target.get(name, name)
                        pending.setdefault(kind, set()).add(str(r[name]))
        for kind in sorted(pending):
            if kind == "interval_id":
                continue
            within = self.keys.setdefault(kind, {})
            for value in sorted(pending[kind]):
                within.setdefault(value, len(within))
        # Part 02 §12.9 numbers intervals by session, kind, clock and bounds, which only their rows
        # hold, so the rows order the names; a name no interval row carries is an orphan and follows.
        within = self.keys.setdefault("interval_id", {})
        for r in sorted(tables.get("core.intervals", []), key=self.interval_order):
            within.setdefault(str(r["interval_id"]), len(within))
        for value in sorted(pending.get("interval_id", ())):
            within.setdefault(value, len(within))

    def interval_order(self, row: dict) -> tuple:
        """Where one `core.intervals` row falls in Part 02 §12.9's numbering."""
        return (
            self.keys["session_id"][str(row["session_id"])],
            row["interval_kind"],
            self.keys["clock_id"][str(row["clock_id"])],
            row["start_tick"],
            row["stop_tick"],
            str(row["interval_id"]),
        )

    def sort_table(self, resource: str, t: pa.Table) -> pa.Table:
        """Apply the stored order (Part 03 §5.3), as a writer should: the key's, unless §5.4 overrides it.

        Sorted by number rather than by name, since Part 02 §12.9 numbers intervals by their bounds.
        """
        order = OVERRIDING_ORDERS.get(resource) or self.specs[resource].get("primary_key") or ()
        keys = [k for k in order if k in t.column_names]
        if not keys:
            return t
        return t.take(pc.sort_indices(t, sort_keys=[(k, "ascending") for k in keys], null_placement="at_end"))


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


def sql_name(resource):
    return resource.replace(".", "_")


def crc(polynomial: int, bits: int, data: bytes) -> int:
    """A reflected CRC with all-ones initial value and final XOR, bit by bit (Part 04 §4.3).

    Written from the polynomial rather than taken from the implementation under test, so the
    corpus pins the form a validator must reproduce.
    """
    mask = (1 << bits) - 1
    register = mask
    for byte in data:
        register ^= byte
        for _ in range(8):
            register = (register >> 1) ^ polynomial if register & 1 else register >> 1
    return register ^ mask


def digest(algorithm: str, data: bytes) -> str:
    """One object's Part 04 §4.3 value: lowercase hexadecimal of the algorithm's width."""
    if algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    if algorithm == "crc64nvme":
        return f"{crc(0x9A6C9329AC4BC9B5, 64, data):016x}"
    if algorithm == "crc32c":
        return f"{crc(0x82F63B78, 32, data):08x}"
    if algorithm == "crc32":
        return f"{crc(0xEDB88320, 32, data):08x}"
    raise ValueError(algorithm)


def write_packet(
    out: Path,
    tables: dict[str, list[dict]],
    *,
    recast: dict | None = None,
    unsorted: frozenset = frozenset(),
    algorithm: str = "sha256",
    extensions: tuple = (),
    numbers: dict[str, dict[str, int]] | None = None,
) -> Numbering:
    """Write a packet in 03's portable layout, and return the numbering of its names.

    `recast` maps a resource to a function from its Arrow table to the one written, for
    variants that must violate the registry's own schema; `unsorted` names resources
    written in insertion order, for variants that must violate Part 03 §5.3. Every resource
    records its `digest` under `algorithm`. `extensions` are registry documents bound beside
    core and `dynamic_foraging`. `numbers` replaces the numbering of each identifier it names,
    for variants that must number one otherwise."""
    if out.exists():
        shutil.rmtree(out)
    documents = (REGISTRY, EXTENSION, *extensions)
    numbering = Numbering(*documents)
    numbering.preassign(tables)
    numbering.keys.update({kind: dict(names) for kind, names in (numbers or {}).items()})
    (out / "tables" / "core").mkdir(parents=True)

    resources = []
    for resource, rows in tables.items():
        t = numbering.table(resource, rows, numbering.paired_readers(tables, resource))
        if resource not in unsorted:
            t = numbering.sort_table(resource, t)
        if resource in (recast or {}):
            t = recast[resource](t)
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
                "digest": {
                    "algorithm": algorithm,
                    "value": digest(algorithm, (out / rel).read_bytes()),
                },
            }
        )

    registries = {document["registry_id"]: bind(out, document) for document in documents}

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
                    "validator_name": "escapewheel_validator",
                    "validator_version": "0.1.0",
                },
            },
            indent=2,
        )
        + "\n"
    )
    return numbering


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


#: Writes one packet at the directory it is given.
Build = Callable[[Path], None]


@dataclass(frozen=True)
class Expected:
    """The finding a packet is built to draw."""

    level: str
    check: str
    #: How often it fires, for a finding drawn once per resource (Part 05 §5.3); at least once where None.
    count: int | None = None
    #: The extension it is filed under (Part 05 §9.5), which fails with the packet while core passes.
    registry: str | None = None
    #: The packet still passes, its finding being a warning that leaves it conformant.
    conforming: bool = False


@dataclass(frozen=True)
class Packet:
    """One packet of the corpus: how it is written, and what a validator must report of it."""

    name: str
    build: Build
    #: None for a packet that must pass without a warning.
    expected: Expected | None = None
    #: Checks it must not draw at any level.
    absent: frozenset[str] = frozenset()
    #: Validated with checksums, which establishes every packet-owned digest (Part 04 §5.3, level 2).
    checksums: bool = False
    #: Validated with advisory rules on (Part 02 §10.2), which never changes whether a packet passed.
    advisory: bool = False


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


def retyped(column: str, type_: pa.DataType):
    """Write `column` as `type_`, which its declaration does not give it."""

    def recast(t: pa.Table) -> pa.Table:
        return t.set_column(t.schema.get_field_index(column), column, t.column(column).cast(type_))

    return recast


def without_column(column: str):
    """Leave `column` out of the file."""

    def recast(t: pa.Table) -> pa.Table:
        return t.drop_columns([column])

    return recast


#: Three variants that break the physical schema, not the data.
SCHEMA_PACKETS = (
    Packet(
        "bad_type",
        variant(recast={"core.intervals": retyped("start_tick", pa.int32())}),
        Expected("error", "schema.column_type"),
    ),
    Packet(
        "extension_bad_type",
        # Part 05 §5.4: an extension's table is type-checked as core's are, and the finding is its own.
        variant(recast={KIND: retyped("trial_id", pa.float64())}),
        Expected("error", "schema.column_type", registry="dynamic_foraging"),
    ),
    Packet(
        "missing_column",
        variant(recast={"core.intervals": without_column("clock_id")}),
        Expected("error", "schema.column_absent"),
    ),
)


def without_extracellular(c):
    for resource in EXTRACELLULAR:
        del c[resource]


def behavior_clock_only(c):
    without_extracellular(c)
    c["core.clocks"] = [clock for clock in c["core.clocks"] if clock["clock_id"] == "behavior_s001"]
    for field in ("parent_clock_id", "transform_slope", "transform_offset"):
        c["core.clocks"][0][field] = None
    c["core.clock_observation_intervals"] = [
        r for r in c["core.clock_observation_intervals"] if r["clock_id"] == "behavior_s001"
    ]
    c["core.sessions"][0]["reference_clock_id"] = None


def sessions_and_subjects_only(c):
    for resource in [resource for resource in c if resource not in ("core.sessions", "core.subjects")]:
        del c[resource]
    for session in c["core.sessions"]:
        session["reference_clock_id"] = None  # a named clock would bring core.clocks


#: The valid session with tables removed.
SUBSET_PACKETS = (
    # Part 00 §1: the packet mechanism confines no packet to extracellular data, so this and
    # `sessions_only` conform.
    Packet("no_extracellular", variant(without_extracellular)),
    # Part 01 §3.3: a session declaring one clock needs no reference to name it.
    Packet("one_clock", variant(behavior_clock_only)),
    Packet("sessions_only", variant(sessions_and_subjects_only)),
)


#: A prefix's objects as a store would list them, for the manifest-only prefix variants.
FRAMES = {"frames/0.png": b"123456789", "frames/1.png": b"frame one"}


def edit_manifest(out: Path, change) -> None:
    manifest = json.loads((out / "packet.json").read_text())
    change(manifest)
    (out / "packet.json").write_text(json.dumps(manifest, indent=2) + "\n")


def listing(rows) -> bytes:
    """Part 04 §4.3's listing of `(key, size_bytes, digest)` rows: sorted by the key's UTF-8, and
    RFC 8785's JSON, which `ensure_ascii=False` matches and whose keys are therefore raw UTF-8."""
    ordered = sorted((list(row) for row in rows), key=lambda row: row[0].encode())
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def prefix_entry(algorithm: str, members: list[dict]) -> dict:
    """An external image prefix recording `members`, and a `digest` of that listing (Part 04 §4.3).

    Media is declared by catalog, so the entry needs no row; nothing reads the URI.
    """
    body = listing((m["key"], m["size_bytes"], m["digest"]) for m in members if "digest" in m)
    return {
        "resource_id": "core.frames",
        "declaration_id": "core.media_asset_instances",
        "uri": "s3://example-bucket/session/frames",
        "external": True,
        "validation_state": "not_run",
        "size_bytes": sum(m["size_bytes"] for m in members),
        "digest": {
            "algorithm": algorithm,
            "value": hashlib.sha256(body).hexdigest(),
        },
        "members": members,
    }


def framed(algorithm: str) -> list[dict]:
    return [{"key": key, "size_bytes": len(body), "digest": digest(algorithm, body)} for key, body in FRAMES.items()]


def one_byte_off(algorithm: str) -> Build:
    """`valid` under `algorithm`, one table's recorded value being of its file with one byte flipped."""

    def build(out: Path) -> None:
        write_packet(out, content(), algorithm=algorithm)

        def change(manifest):
            # The file itself stays readable.
            entry = next(e for e in manifest["resources"] if e["resource_id"] == "core.intervals")
            body = bytearray((out / entry["uri"]).read_bytes())
            body[len(body) // 2] ^= 0x01
            entry["digest"]["value"] = digest(algorithm, bytes(body))

        edit_manifest(out, change)

    return build


def without_digest(manifest):
    del manifest["resources"][0]["digest"]


def crc_prefix(manifest):
    manifest["resources"].append(prefix_entry("crc32c", framed("crc32c")))


def crc_prefix_disagrees(manifest):
    entry = prefix_entry("crc32c", framed("crc32c"))
    entry["members"][0]["digest"] = digest("crc32c", b"123456780")
    manifest["resources"].append(entry)


def member_digest_partial(manifest):
    members = framed("sha256")
    entry = prefix_entry("sha256", members)
    del members[1]["digest"]
    manifest["resources"].append(entry)


def member_digest_width(manifest):
    entry = prefix_entry("crc64nvme", framed("crc64nvme"))
    entry["members"][0]["digest"] = digest("crc32c", FRAMES["frames/0.png"])
    manifest["resources"].append(entry)


#: Part 04 §4.3's digests: each admitted algorithm passing, and each way one can be wrong.
DIGEST_PACKETS = (
    Packet("crc64nvme", variant(algorithm="crc64nvme"), checksums=True),
    Packet("crc64nvme_one_byte_off", one_byte_off("crc64nvme"), Expected("error", "owned.digest"), checksums=True),
    Packet("crc32c", variant(algorithm="crc32c"), checksums=True),
    Packet("crc32c_one_byte_off", one_byte_off("crc32c"), Expected("error", "owned.digest"), checksums=True),
    Packet("crc32", variant(algorithm="crc32"), checksums=True),
    Packet("crc32_one_byte_off", one_byte_off("crc32"), Expected("error", "owned.digest"), checksums=True),
    Packet(
        "owned_without_digest",
        variant(edit=without_digest),
        Expected("error", "packet.resource.digest_missing"),
    ),
    Packet("crc_prefix", variant(edit=crc_prefix)),
    Packet(
        "crc_prefix_disagrees",
        variant(edit=crc_prefix_disagrees),
        Expected("error", "packet.resource.member_digest"),
    ),
    Packet("member_digest_partial", variant(edit=member_digest_partial), Expected("error", "packet.manifest.schema")),
    Packet("member_digest_width", variant(edit=member_digest_width), Expected("error", "packet.manifest.schema")),
)


#: The reference writer's default and sharded pipelines, both inside the v3 reader floor, and its
#: delta-filtered one, outside it (Part 03 §6.4).
BLOSC = {
    "name": "blosc",
    "configuration": {
        "typesize": 2,
        "cname": "zstd",
        "clevel": 5,
        "shuffle": "shuffle",
        "blocksize": 0,
    },
}
BYTES = {"name": "bytes", "configuration": {"endian": "little"}}
PIPELINES = {
    "default": [BYTES, BLOSC],
    "sharded": [
        {
            "name": "sharding_indexed",
            "configuration": {
                "chunk_shape": [1, 3],
                "codecs": [BYTES, BLOSC],
                "index_codecs": [BYTES, {"name": "crc32c"}],
                "index_location": "end",
            },
        }
    ],
    "delta": [
        {"name": "numcodecs.delta", "configuration": {"dtype": "int16"}},
        BYTES,
        {**BLOSC, "configuration": {**BLOSC["configuration"], "shuffle": "bitshuffle"}},
    ],
}


#: The axes every catalogued array has unless a variant says otherwise.
AXES = ("unit", "sample")

#: Part 03 §6.3's numeric form for an axis that is only an order: position k is k.
ORDER_ONLY = {"origin_value": 0.0, "step_value": 1.0, "coordinate_unit": "1"}


def zarr_metadata(codecs: list[dict], shape: tuple = (2, 3), dimension_names: tuple | None = AXES) -> bytes:
    """A Zarr v3 array with no chunk written, so every element is its fill value.

    Its metadata is all a floor assessment or an axis check reads, and the corpus needs no Zarr
    library to write it. Part 03 §6.5 has a packet-owned array name its axes.
    """
    document = {
        "zarr_format": 3,
        "node_type": "array",
        "shape": list(shape),
        "data_type": "int16",
        "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": list(shape)}},
        "chunk_key_encoding": {"name": "default", "configuration": {"separator": "/"}},
        "fill_value": 0,
        "codecs": codecs,
        "attributes": {},
    }
    if dimension_names is not None:
        document["dimension_names"] = list(dimension_names)
    return (json.dumps(document, indent=2) + "\n").encode()


def catalogue_arrays(tables: dict[str, list[dict]], names: list[str], axes: tuple = AXES) -> None:
    """Catalogue one array per name, as `core.<name>`, each axis only an order (Part 03 §6.3)."""
    tables["core.array_assets"] = [
        {"session_id": "s001", "array_asset_id": name, "resource_id": f"core.{name}"} for name in names
    ]
    tables["core.array_dimensions"] = [
        {
            "session_id": "s001",
            "array_asset_id": name,
            "axis_index": axis,
            "dimension_name": dimension,
            **ORDER_ONLY,
        }
        for name in names
        for axis, dimension in enumerate(axes)
    ]


def array_entry(out: Path | None, name: str, pipeline: str, shape: tuple = (2, 3), dimension_names=AXES) -> dict:
    """A manifest entry for `core.<name>`; packet-owned and written under `out`, or external where None."""
    entry = {
        "resource_id": f"core.{name}",
        "declaration_id": "core.array_asset_instances",
        "validation_state": "not_run",
    }
    if out is None:
        return {
            **entry,
            "uri": f"s3://example-bucket/session/{name}.zarr",
            "external": True,
        }
    uri = f"arrays/core/{name}.zarr"
    body = zarr_metadata(PIPELINES[pipeline], shape, dimension_names)
    (out / uri).mkdir(parents=True)
    (out / uri / "zarr.json").write_bytes(body)
    rows = [("zarr.json", len(body), digest("sha256", body))]
    return {
        **entry,
        "uri": uri,
        "digest": {
            "algorithm": "sha256",
            "value": hashlib.sha256(listing(rows)).hexdigest(),
        },
    }


#: One array per pipeline, by the name it is catalogued under.
FLOOR_ARRAYS = {
    "default_array": "default",
    "sharded_array": "sharded",
    "delta_array": "delta",
}


def outside_array_floor(out: Path) -> None:
    c = content()
    catalogue_arrays(c, list(FLOOR_ARRAYS))
    write_packet(out, c)
    edit_manifest(
        out,
        lambda m: m["resources"].extend(array_entry(out, name, pipeline) for name, pipeline in FLOOR_ARRAYS.items()),
    )


def outside_table_floor(out: Path) -> None:
    # Parquet format version 1.0 writes dictionary pages as PLAIN_DICTIONARY, valid upstream and
    # outside the writer floor (Part 03 §5.5).
    write_packet(out, content())
    entry_uri = "tables/core/intervals.parquet"
    pq.write_table(
        pq.read_table(out / entry_uri),
        out / entry_uri,
        compression="zstd",
        version="1.0",
    )

    def redigest(manifest):
        entry = next(e for e in manifest["resources"] if e["uri"] == entry_uri)
        entry["digest"]["value"] = digest("sha256", (out / entry_uri).read_bytes())

    edit_manifest(out, redigest)


def unresolved_externals(out: Path) -> None:
    names = ["lfp_probe_a", "lfp_probe_b"]
    c = content()
    catalogue_arrays(c, names)
    write_packet(out, c)
    edit_manifest(out, lambda m: m["resources"].extend(array_entry(None, name, "default") for name in names))


#: Part 05 §5.3's outside-floor and unassessed findings, one resource at a time.
FLOOR_PACKETS = (
    Packet("outside_array_floor", outside_array_floor, Expected("info", "physical.outside_reader_floor", count=1)),
    Packet("outside_table_floor", outside_table_floor, Expected("warning", "physical.outside_reader_floor")),
    Packet("unresolved_externals", unresolved_externals, Expected("info", "external.physical_unassessed", count=2)),
)


#: A waveform-shaped array: two units, a channel axis four positions long, and three samples.
LABELLED_SHAPE = (2, 4, 3)
LABELLED_AXES = ("unit", "channel", "sample")

#: Each unit's contacts along the channel axis. The second unit has two, so its last two
#: positions are padding, which is what the one positive variant holds (Part 03 §6.3).
LABELLED_CONTACTS = {
    1: ("elec_000", "elec_001", "elec_003", None),
    2: ("elec_001", "elec_003", None, None),
}


def labelled_array(tables: dict[str, list[dict]]) -> None:
    """Catalogue `core.waveform_mean` with a unit axis and a channel axis that depends on it."""
    catalogue_arrays(tables, ["waveform_mean"], LABELLED_AXES)
    unit_axis, channel_axis, _ = tables["core.array_dimensions"]
    for axis, kind in ((unit_axis, "core.units"), (channel_axis, "core.electrodes")):
        for field in ORDER_ONLY:
            del axis[field]
        axis["coordinate_resource"] = kind
    channel_axis["depends_on_axis_index"] = 0
    common = {"session_id": "s001", "array_asset_id": "waveform_mean"}
    tables["core.array_labels"] = [
        {**common, "axis_index": 0, "depends_on_position_index": 0, "position_index": k, "label_id": unit}
        for k, unit in enumerate(LABELLED_CONTACTS)
    ] + [
        {**common, "axis_index": 1, "depends_on_position_index": k, "position_index": j, "label_id": contact}
        for k, contacts in enumerate(LABELLED_CONTACTS.values())
        for j, contact in enumerate(contacts)
    ]


def with_waveform(mutate=None, dimension_names: tuple | None = LABELLED_AXES) -> Build:
    """A build of the valid session holding `core.waveform_mean`, once `mutate` has edited its rows."""

    def build(out: Path) -> None:
        c = content()
        labelled_array(c)
        if mutate is not None:
            mutate(c)
        write_packet(out, c)
        entry = array_entry(out, "waveform_mean", "default", LABELLED_SHAPE, dimension_names)
        edit_manifest(out, lambda m: m["resources"].append(entry))

    return build


def labels(c, axis, outer):
    return [r for r in c["core.array_labels"] if (r["axis_index"], r["depends_on_position_index"]) == (axis, outer)]


def axis_without_form(c):
    for field in ORDER_ONLY:
        del c["core.array_dimensions"][2][field]


def axis_with_two_forms(c):
    c["core.array_dimensions"][2] |= {"clock_id": "imec_ap_s001", "origin_tick": 0, "step_tick_num": 1}


def label_naming_no_row(c):
    # A real name, numbered like any other, so only the per-kind anti-join sees it names nothing.
    labels(c, 1, 0)[0]["label_id"] = "elec_009"


def label_on_unlabelled_axis(c):
    c["core.array_labels"].append({**labels(c, 1, 0)[0], "axis_index": 2})


def label_missing(c):
    # The padding row goes, not the label: a null label still declares its position.
    c["core.array_labels"].remove(labels(c, 1, 1)[-1])


def chained_dependency(c):
    # Its labels repeat at each of the sample axis's positions, so completeness still holds.
    c["core.array_dimensions"][0]["depends_on_axis_index"] = 2
    units = labels(c, 0, 0)
    c["core.array_labels"] += [
        {**r, "depends_on_position_index": k} for k in range(1, LABELLED_SHAPE[2]) for r in units
    ]


def independent_label_off_zero(c):
    c["core.array_labels"].append({**labels(c, 0, 0)[0], "depends_on_position_index": 1})


def one_row_two_positions(c):
    first, second, *_ = labels(c, 1, 0)
    second["label_id"] = first["label_id"]


def label_beyond_axis(c):
    c["core.array_labels"].append({**labels(c, 1, 1)[-1], "position_index": LABELLED_SHAPE[1]})


def dependent_axis_unlabelled(c):
    c["core.array_dimensions"][2]["depends_on_axis_index"] = 0


def label_outside_core(c):
    # Null labels name no row, so nothing but the resource's class is wrong.
    c["core.array_dimensions"][0]["coordinate_resource"] = "analysis.array_assets"
    for r in labels(c, 0, 0):
        r["label_id"] = None


#: Part 03 §6.3's labelled axes: one packet that pads, and one per rule a label or axis breaks.
AXIS_PACKETS = (
    Packet("padded_labels", with_waveform()),
    Packet(
        "axis_without_form",
        with_waveform(axis_without_form),
        Expected("error", "core.array_dimensions.one_coordinate_form"),
    ),
    Packet(
        "axis_with_two_forms",
        with_waveform(axis_with_two_forms),
        Expected("error", "core.array_dimensions.one_coordinate_form"),
    ),
    Packet(
        "label_naming_no_row",
        with_waveform(label_naming_no_row),
        Expected("error", "core.array_dimensions.coordinate_resource.core_electrodes_resolves"),
    ),
    Packet(
        "label_on_unlabelled_axis",
        with_waveform(label_on_unlabelled_axis),
        Expected("error", "core.array_dimensions.coordinate_resource.specialised_row_has_kind"),
    ),
    Packet("label_missing", with_waveform(label_missing), Expected("error", "array.label_missing")),
    Packet(
        "chained_dependency",
        with_waveform(chained_dependency),
        Expected("error", "core.array_dimensions.dependency_not_chained"),
    ),
    Packet(
        "independent_label_off_zero",
        with_waveform(independent_label_off_zero),
        Expected("error", "core.array_labels.independent_depends_on_position_zero"),
    ),
    Packet(
        "one_row_two_positions",
        with_waveform(one_row_two_positions),
        Expected("error", "core.array_labels.one_position_per_row"),
    ),
    Packet(
        "label_beyond_axis",
        with_waveform(label_beyond_axis),
        Expected("error", "array.label_position_out_of_range"),
    ),
    Packet(
        "dependent_axis_unlabelled",
        with_waveform(dependent_axis_unlabelled),
        Expected("error", "core.array_dimensions.dependent_axis_labelled"),
    ),
    Packet(
        "label_outside_core",
        with_waveform(label_outside_core),
        Expected("error", "core.array_dimensions.coordinate_resource_is_core"),
    ),
    Packet(
        "array_without_dimension_names",
        with_waveform(dimension_names=None),
        Expected("error", "array.dimension_names"),
    ),
)


#: A fixture-local extension declaring a second kind of interval, whose resource ID sorts before
#: `KIND` so a numbering by kind puts its intervals first.
CUE_EXTENSION = {
    "$schema": EXTENSION["$schema"],
    "registry_id": "cue",
    "registry_version": "0.1.0",
    "logical_standard_version": EXTENSION["logical_standard_version"],
    "rule_language": EXTENSION["rule_language"],
    "extension_id": "cue",
    "resources": {
        "cue.tones": {
            "content_class": "extension",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {
                "columns": [
                    {
                        "name": "session_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "Session ID.",
                    },
                    {
                        "name": "tone_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "The tone, and the interval it occupies in core.",
                    },
                ],
                "primary_key": ["tone_id"],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                    {
                        "columns": ["tone_id"],
                        "resource": "core.intervals",
                        "resource_columns": ["interval_id"],
                        "specialises": "core.intervals.interval_kind",
                    },
                ],
                "rules": [],
                "amendment_groups": [["tone_id"]],
            },
        }
    },
}


#: A fixture-local extension declaring a detail table of `core.devices.device_kind`, which core
#: may not declare (Part 02 §8.3).
RIG_EXTENSION = {
    "$schema": EXTENSION["$schema"],
    "registry_id": "rig",
    "registry_version": "0.1.0",
    "logical_standard_version": EXTENSION["logical_standard_version"],
    "rule_language": EXTENSION["rule_language"],
    "extension_id": "rig",
    "resources": {
        "rig.neuropixels": {
            "content_class": "extension",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {
                "columns": [
                    {
                        "name": "session_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "Session ID.",
                    },
                    {
                        "name": "device_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "The probe this row describes.",
                    },
                ],
                "primary_key": ["device_id"],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                    {
                        "columns": ["device_id"],
                        "resource": "core.devices",
                        "resource_columns": ["device_id"],
                        "specialises": "core.devices.device_kind",
                    },
                ],
                "rules": [],
                "amendment_groups": [["device_id"]],
            },
        }
    },
}


def probe_of_kind(kind: str | None):
    """Name `kind` as the probe's `device_kind`, and describe the probe in `rig.neuropixels`."""

    def mutate(c):
        c["core.devices"][0]["device_kind"] = kind
        c["rig.neuropixels"] = [{"session_id": "s001", "device_id": "imec0"}]

    return mutate


RIG = (RIG_EXTENSION,)

#: Part 02 §8.3's kind check on a detail table whose discriminator resolves `optional`.
DEVICE_PACKETS = (
    Packet("device_detail", variant(probe_of_kind("rig.neuropixels"), extensions=RIG)),
    Packet(
        "device_detail_unkinded",
        variant(probe_of_kind(None), extensions=RIG),
        Expected("error", "rig.neuropixels.device_id.names_a_row_of_its_kind", registry="rig"),
    ),
    Packet(
        "device_detail_other_kind",
        variant(probe_of_kind("core.probes"), extensions=RIG),
        Expected("error", "rig.neuropixels.device_id.names_a_row_of_its_kind", registry="rig"),
    ),
)


#: The names of the tone `with_tone` adds and of the two trials.
TONE, FIRST, SECOND = "s001/cue.tones/1", trial(1), trial(2)


def with_tone(c):
    # A tone the cue source labels "1", as the task source labels the first trial.
    c["core.intervals"].append(
        {
            "session_id": "s001",
            "interval_kind": "cue.tones",
            "interval_id": "s001/cue.tones/1",
            "local_interval_label": "1",
            "start_tick": 500,
            "stop_tick": 900,
            "clock_id": "behavior_s001",
        }
    )
    c["cue.tones"] = [{"session_id": "s001", "tone_id": "s001/cue.tones/1"}]


def trial_names_a_tone(c):
    # Part 02 §8.3: a detail row whose interval is of another kind; the reverse check passes,
    # since every interval still has a row of its own kind.
    with_tone(c)
    c[KIND].append({**c[KIND][1], "trial_id": TONE})


def tone_names_a_trial(c):
    with_tone(c)
    c["cue.tones"].append({"session_id": "s001", "tone_id": FIRST})


def tone_in_place_of_its_own(c):
    with_tone(c)
    c["cue.tones"][0]["tone_id"] = FIRST


def interval_of_a_session(c):
    # `core.sessions` is declared, so the kind resolves, but it specialises no interval.
    c["core.intervals"].append(
        {
            "session_id": "s001",
            "interval_kind": "core.sessions",
            "interval_id": "s001/core.sessions/1",
            "local_interval_label": "1",
            "start_tick": 500,
            "stop_tick": 900,
            "clock_id": "behavior_s001",
        }
    )


def equal_bounds(c):
    c["core.intervals"][1] |= {"start_tick": 1000, "stop_tick": 5000}


def second_trial_on_the_probe_clock(c):
    # Earlier in ticks than the first trial, on the clock numbered after the behavior clock.
    c["core.intervals"][1] |= {"clock_id": "imec_ap_s001", "start_tick": 500, "stop_tick": 900}


def repeated_label(c):
    c["core.intervals"][1]["local_interval_label"] = "1"


def orphan_trial(c):
    c[KIND].append({**c[KIND][1], "trial_id": trial(3)})


def trial_labelled_axis(c):
    axis = c["core.array_dimensions"][0]
    axis["coordinate_resource"] = "core.intervals"
    for r, name in zip((r for r in c["core.array_labels"] if r["axis_index"] == 0), (trial(1), trial(2)), strict=True):
        r["label_id"] = name


CUE = (CUE_EXTENSION,)

#: Part 02 §12.9's numbering: packets numbering intervals in each admitted order, and one per defect.
INTERVAL_PACKETS = (
    Packet("two_kinds_one_label", variant(with_tone, extensions=CUE)),
    Packet(
        "trial_names_a_tone",
        variant(trial_names_a_tone, extensions=CUE),
        Expected(
            "error",
            "dynamic_foraging.trials.trial_id.names_a_row_of_its_kind",
            registry="dynamic_foraging",
        ),
    ),
    Packet(
        "tone_names_a_trial",
        variant(tone_names_a_trial, extensions=CUE),
        Expected("error", "cue.tones.tone_id.names_a_row_of_its_kind", registry="cue"),
    ),
    Packet(
        "tone_in_place_of_its_own",
        variant(tone_in_place_of_its_own, extensions=CUE),
        Expected("error", "cue.tones.tone_id.names_a_row_of_its_kind"),
    ),
    Packet(
        "interval_of_a_session",
        variant(interval_of_a_session),
        Expected("error", "core.intervals.interval_kind.core_sessions_is_specialised"),
    ),
    Packet(
        "kinds_out_of_unicode_order",
        variant(with_tone, extensions=CUE, numbers={"interval_id": {FIRST: 0, SECOND: 1, TONE: 2}}),
    ),
    Packet("equal_bounds", variant(equal_bounds)),
    Packet("equal_bounds_swapped", variant(equal_bounds, numbers={"interval_id": {SECOND: 0, FIRST: 1}})),
    Packet("trial_labelled_axis", with_waveform(trial_labelled_axis)),
    Packet(
        "trials_numbered_from_one",
        variant(numbers={"interval_id": {FIRST: 1, SECOND: 2}}),
        Expected("error", "core.intervals.numbered_in_order"),
    ),
    Packet(
        "trials_misordered",
        variant(numbers={"interval_id": {SECOND: 0, FIRST: 1}}),
        Expected("error", "core.intervals.numbered_in_order"),
    ),
    Packet(
        "trials_numbered_by_tick",
        variant(second_trial_on_the_probe_clock, numbers={"interval_id": {SECOND: 0, FIRST: 1}}),
        Expected("error", "core.intervals.numbered_in_order"),
    ),
    Packet(
        "interval_numbering_gap",
        variant(numbers={"interval_id": {FIRST: 0, SECOND: 2}}),
        Expected("error", "core.intervals.numbered_in_order"),
    ),
    Packet(
        "repeated_interval_label",
        variant(repeated_label),
        Expected("error", "core.intervals.label_unique_within_kind"),
    ),
    Packet(
        "orphan_trial",
        variant(orphan_trial),
        Expected("error", "dynamic_foraging.trials.trial_id_resolves", registry="dynamic_foraging"),
    ),
)


def labelled(first, second):
    def mutate(c):
        c["core.units"][0]["local_unit_label"] = first
        c["core.units"][1]["local_unit_label"] = second

    return mutate


def later_run(c):
    # A second run of the same probe, whose one curation holds the second unit.
    run, curation = c["core.sorting_runs"][0], c["core.curation_versions"][0]
    c["core.sorting_runs"].append(
        run
        | {
            "sorting_run_id": "sort_ks4_002",
            "started_at": run["ended_at"],
            "ended_at": run["ended_at"] + timedelta(hours=1),
        }
    )
    c["core.sorting_run_channels"] += [r | {"sorting_run_id": "sort_ks4_002"} for r in c["core.sorting_run_channels"]]
    c["core.curation_versions"].append(
        curation
        | {
            "curation_id": "curation_002",
            "sorting_run_id": "sort_ks4_002",
            "created_at": curation["created_at"] + timedelta(hours=2),
        }
    )
    c["core.units"][1] |= {"sorting_run_id": "sort_ks4_002", "curation_id": "curation_002"}


#: Part 02 §12.1's numbering: packets numbering units in each admitted order, and one per defect.
#: The two units are named "1" and "2" and numbered in that order unless a variant says otherwise.
UNIT_PACKETS = (
    Packet(
        "units_numbered_by_scalar",
        variant(labelled("10", "2")),
        Expected("error", "core.units.numbered_in_order"),
    ),
    Packet(
        "units_numbered_from_one",
        variant(numbers={"unit_id": {"1": 1, "2": 2}}),
        Expected("error", "core.units.numbered_in_order"),
    ),
    Packet("unit_labels_by_length", variant(labelled("7", "007"))),
    Packet("null_unit_labels", variant(labelled(None, None))),
    Packet("null_unit_labels_swapped", variant(labelled(None, None), numbers={"unit_id": {"2": 0, "1": 1}})),
    Packet("later_run_numbered_first", variant(later_run, numbers={"unit_id": {"2": 0, "1": 1}})),
)


#: A fixture-local extension declaring an opaque singleton, which core does not.
QC_EXTENSION = {
    "$schema": EXTENSION["$schema"],
    "registry_id": "qc_documents",
    "registry_version": "0.1.0",
    "logical_standard_version": EXTENSION["logical_standard_version"],
    "rule_language": EXTENSION["rule_language"],
    "extension_id": "qc_documents",
    "resources": {
        "qc_documents.report": {
            "content_class": "extension",
            "kind": "opaque",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
        }
    },
}

#: The keys of `listing_key_spelling`'s payload: each character RFC 8785 escapes differently from
#: a percent-encoder or from `ensure_ascii`, and one below a directory.
SPELLED_KEYS = ['"', "\\", "\n", "\x7f", "\u00e9", "more/\U0001f600"]

#: That payload's listing, written out by hand: RFC 8785's `\"`, `\\`, and `\n`; U+007F, `é`, and
#: U+1F600 as their UTF-8; each digest the CRC32C of the key's own UTF-8.
SPELLED_LISTING = (
    b'[["\\n",1,"399f7b69"],'
    b'["\\"",1,"93fbad78"],'
    b'["\\\\",1,"4e1b4652"],'
    b'["more/\xf0\x9f\x98\x80",9,"bd6a29c1"],'
    b'["\x7f",1,"7df63b78"],'
    b'["\xc3\xa9",2,"1bab8ddc"]]'
)


def owned_opaque(
    out: Path,
    resource_id: str,
    name: str,
    payload,
    *,
    algorithm: str = "sha256",
    declaration_id: str = "core.media_asset_instances",
) -> dict:
    """Publish a payload at `opaque/<resource_id>/<name>` as a build does (Part 03 §11), and
    return its entry.

    `payload` is the bytes of a payload that is one file, or a mapping from each file's path
    within it to its bytes. The `uri` percent-encodes every octet but the unreserved ones in
    uppercase (Part 03 §4), which is what `quote` does with nothing marked safe.
    """
    where = out / "opaque" / resource_id / name
    if isinstance(payload, bytes):
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_bytes(payload)
        value, size = digest(algorithm, payload), len(payload)
    else:
        for key, body in payload.items():
            (where / key).parent.mkdir(parents=True, exist_ok=True)
            (where / key).write_bytes(body)
        rows = [(key, len(body), digest(algorithm, body)) for key, body in payload.items()]
        value = hashlib.sha256(listing(rows)).hexdigest()
        size = sum(len(body) for body in payload.values())
    return {
        "resource_id": resource_id,
        "declaration_id": declaration_id,
        "uri": "/".join(("opaque", quote(resource_id, safe=""), quote(name, safe=""))),
        "validation_state": "not_run",
        "size_bytes": size,
        "digest": {"algorithm": algorithm, "value": value},
    }


def publish(out: Path, *payloads, extensions=()) -> list[dict]:
    """Write `valid` plus each `(resource_id, name, payload, options)` payload, and return their entries."""
    write_packet(out, content(), extensions=extensions)
    entries = [owned_opaque(out, rid, file, body, **options) for rid, file, body, options in payloads]
    edit_manifest(out, lambda m: m["resources"].extend(entries))
    return entries


def owning(*payloads, extensions=()) -> Build:
    """A build of `publish`."""

    def build(out: Path) -> None:
        publish(out, *payloads, extensions=extensions)

    return build


def owned_opaque_encoded_name(out: Path) -> None:
    (entry,) = publish(out, ("core.qc_report", "QC report \u00e9.pdf", b"%PDF-1.7", {}))
    assert entry["uri"] == "opaque/core.qc_report/QC%20report%20%C3%A9.pdf", entry["uri"]


def owned_opaque_one_byte_off(out: Path) -> None:
    publish(out, ("core.clip", "clip.mp4", b"\x00\x00\x00\x18ftypmp42", {}))
    edit_manifest(
        out,
        lambda m: m["resources"][-1]["digest"].update(value=digest("sha256", b"\x00\x00\x00\x18ftypmp43")),
    )


def listing_key_spelling(out: Path) -> None:
    spelled = {key: key.encode("utf-8") for key in SPELLED_KEYS}
    publish(out, ("core.keys", "keys", spelled, {"algorithm": "crc32c"}))
    rows = [(key, len(body), digest("crc32c", body)) for key, body in spelled.items()]
    assert listing(rows) == SPELLED_LISTING, listing(rows)


def misspelt_uri(file: str, uri: str) -> Build:
    """Part 03 §4's one form, broken one way; the file is where the `uri` decodes to, if anywhere."""

    def build(out: Path) -> None:
        publish(out, ("core.clip", file, b"clip", {}))
        edit_manifest(out, lambda m: m["resources"][-1].update(uri=uri))

    return build


#: `é` in NFC and `É` in NFD are one name folded; `12:00:00.png` is one Windows refuses.
PORTABILITY = {"\u00e9.png": b"a", "E\u0301.png": b"b", "12:00:00.png": b"c"}

#: Packet-owned opaque payloads (Part 03 §11): kept names, their `uri`, and their digest.
OPAQUE_PACKETS = (
    Packet(
        "owned_opaque_object",
        owning(("core.clip", "clip.mp4", b"\x00\x00\x00\x18ftypmp42", {})),
        checksums=True,
    ),
    Packet(
        "owned_opaque_prefix",
        owning(
            (
                "core.frames",
                "frames",
                {k.removeprefix("frames/"): v for k, v in FRAMES.items()},
                {},
            )
        ),
        checksums=True,
    ),
    Packet(
        "owned_opaque_singleton",
        owning(
            (
                "qc_documents.report",
                "QC.pdf",
                b"%PDF-1.7",
                {"declaration_id": "qc_documents.report"},
            ),
            extensions=(QC_EXTENSION,),
        ),
        checksums=True,
    ),
    Packet("owned_opaque_encoded_name", owned_opaque_encoded_name, checksums=True),
    Packet("owned_opaque_one_byte_off", owned_opaque_one_byte_off, Expected("error", "owned.digest"), checksums=True),
    Packet(
        "opaque_name_portability",
        owning(("core.frames", "frames", PORTABILITY, {})),
        Expected("warning", "physical.opaque_name_portability", count=2, conforming=True),
        checksums=True,
    ),
    Packet(
        "listing_key_spelling",
        listing_key_spelling,
        Expected("warning", "physical.opaque_name_portability", count=3, conforming=True),
        # Its digest is over keys in raw UTF-8, and a reader that escaped or encoded them would disagree.
        absent=frozenset({"owned.digest", "packet.resource.member_digest"}),
        checksums=True,
    ),
    Packet(
        "uri_raw_space",
        misspelt_uri("cam 1.mp4", "opaque/core.clip/cam 1.mp4"),
        Expected("error", "packet.resource.uri_form"),
    ),
    Packet(
        "uri_lowercase_hex",
        misspelt_uri("QC report \u00e9.pdf", "opaque/core.clip/QC%20report%20%c3%a9.pdf"),
        Expected("error", "packet.resource.uri_form"),
    ),
    Packet(
        "uri_encoded_unreserved",
        misspelt_uri("A.mp4", "opaque/core.clip/%41.mp4"),
        Expected("error", "packet.resource.uri_form"),
    ),
    Packet(
        "uri_dot_segment",
        misspelt_uri("clip.mp4", "opaque/core.clip/../core.clip/clip.mp4"),
        Expected("error", "packet.resource.uri_form"),
    ),
)


def amend(
    out: Path,
    make,
    change,
    *,
    extensions: tuple = (),
    identity: dict | None = None,
    superseded_identity: dict | None = None,
    dropped: tuple = (),
) -> None:
    """Write `make()`, then `change`'s edit of it over it at the next patch version (Part 05 §15.1).

    A table whose bytes the edit changes is written at a new uri beside the held file; every other
    entry is kept, and the superseded manifest's exact bytes are retained under `manifests/`
    (Part 03 §9). A name the packet holds keeps its number and a new one is numbered after them, as
    Part 05 §4.3 has an amending build number. `superseded_identity` sets packet-level fields of
    the first version; `identity` overrides, and `dropped` removes, those of the amended one.
    """
    held = write_packet(out, make(), extensions=extensions).keys
    if superseded_identity:
        edit_manifest(out, lambda manifest: manifest.update(superseded_identity))
    edited = make()
    change(edited)
    unheld = Numbering(REGISTRY, EXTENSION, *extensions)
    unheld.preassign(edited)
    numbers = {}
    for kind, names in unheld.keys.items():
        kept = held.get(kind, {})
        added = sorted((name for name in names if name not in kept), key=names.get)
        start = max(kept.values(), default=-1) + 1
        numbers[kind] = {**kept, **{name: start + i for i, name in enumerate(added)}}
    scratch = out.with_name(out.name + ".next")
    write_packet(scratch, edited, extensions=extensions, numbers=numbers)

    superseded = json.loads((out / "packet.json").read_text())
    major, minor, patch = superseded["packet_version"].split(".")
    following = f"{major}.{minor}.{int(patch) + 1}"
    manifest = json.loads((scratch / "packet.json").read_text())
    assert manifest["registries"] == superseded["registries"], out.name
    before = {e["resource_id"]: e for e in superseded["resources"]}
    resources = []
    for entry in manifest["resources"]:
        kept = before.get(entry["resource_id"])
        if kept is not None and (out / kept["uri"]).read_bytes() == (scratch / entry["uri"]).read_bytes():
            resources.append(kept)
            continue
        uri = entry["uri"] if kept is None else entry["uri"].replace(".parquet", f".{following}.parquet")
        (out / uri).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(scratch / entry["uri"], out / uri)
        resources.append({**entry, "uri": uri})
    shutil.rmtree(scratch)
    (out / "manifests").mkdir()
    retained = out / "manifests" / f"{superseded['packet_version']}.json"
    retained.write_bytes((out / "packet.json").read_bytes())
    amended = {**superseded, "packet_version": following, "resources": resources, **(identity or {})}
    for member in dropped:
        del amended[member]
    (out / "packet.json").write_text(json.dumps(amended, indent=2) + "\n")


def replaced(packet_id: str, packet_version: str = "0.1.0", **extra) -> dict:
    """A `replaces` item naming a version whose manifest bytes are the id and version (Part 04 §3)."""
    body = f"{packet_id} {packet_version}".encode()
    digest = hashlib.sha256(body).hexdigest()
    return {"packet_id": packet_id, "packet_version": packet_version, "sha256": digest, **extra}


def replaces(version: str, items: list[dict]) -> Build:
    """`valid` at `version`, naming `items` as the packets it replaces."""
    return variant(edit=lambda manifest: manifest.update(packet_version=version, replaces=items))


#: Part 04 §3's `replaces`: a packet naming the packets it replaces, and each way an item is wrong.
REPLACEMENT_PACKETS = (
    Packet("replaces_own_packet", replaces("1.0.0", [replaced("replaces_own_packet")])),
    Packet("replaces_another_packet", replaces("0.1.0", [replaced("session_000", "3.0.0")])),
    Packet(
        "replaces_same_major",
        replaces("0.1.0", [replaced("replaces_same_major")]),
        Expected("error", "packet.replaces.major_version"),
    ),
    Packet(
        "replaces_item_with_location",
        replaces("1.0.0", [replaced("replaces_item_with_location", uri="../old")]),
        Expected("error", "packet.manifest.schema"),
    ),
    Packet(
        "replaces_item_without_digest",
        replaces("1.0.0", [{"packet_id": "replaces_item_without_digest", "packet_version": "0.1.0"}]),
        Expected("error", "packet.manifest.schema"),
    ),
)


def materialize(c, clock):
    c["analysis.spike_events"] = [
        {
            "session_id": s["session_id"],
            "unit_id": s["unit_id"],
            "t_tick": s["t_tick"],
            "clock_id": clock,
            "time_bucket_tick": s["t_tick"] // SPIKE_BUCKET_TICKS * SPIKE_BUCKET_TICKS,
        }
        for s in c["core.spike_events"]
    ]


def ap_clock_only(c):
    # The AP clock alone, so the units keep theirs and only the missing reference is wrong.
    c["core.clocks"] = [clock for clock in c["core.clocks"] if clock["clock_id"] == "imec_ap_s001"]
    c["core.clock_observation_intervals"] = [
        r for r in c["core.clock_observation_intervals"] if r["clock_id"] == "imec_ap_s001"
    ]
    c.pop("core.clock_anchors", None)
    for rows in c.values():
        for row in rows:
            if row.get("clock_id") == "behavior_s001":
                row["clock_id"] = "imec_ap_s001"
    c["core.sessions"][0]["reference_clock_id"] = None


def derive_spikes(manifest: dict) -> None:
    for entry in manifest["resources"]:
        if entry["resource_id"] == "analysis.spike_events":
            entry["derived_from"] = ["core.spike_events"]


#: The width of a materialized spike's time bucket, in ticks of its clock.
SPIKE_BUCKET_TICKS = 100_000


def materialized(clock: str, mutate=None) -> Build:
    """A build of the valid session with its spikes materialized on `clock`, once `mutate` has edited its rows."""

    def build(out: Path) -> None:
        c = content()
        if mutate is not None:
            mutate(c)
        materialize(c, clock)
        write_packet(out, c)
        edit_manifest(out, derive_spikes)

    return build


#: Part 06 §4's materialized spikes: on the reference clock, off it, and in a session naming none.
SPIKE_PACKETS = (
    Packet("spikes_on_reference_clock", materialized("imec_ap_s001")),
    Packet(
        "spikes_off_reference_clock",
        materialized("behavior_s001"),
        Expected("error", "analysis.spike_events.on_reference_clock"),
    ),
    Packet(
        "spikes_without_reference_clock",
        materialized("imec_ap_s001", ap_clock_only),
        Expected("error", "analysis.spike_events.on_reference_clock"),
    ),
)


def processing_run(run_id, activity, scope_kind, scope, hours):
    return {
        "processing_run_id": run_id,
        "session_id": "s001",
        "activity_type": activity,
        "scope_kind": scope_kind,
        "scope": scope,
        "software_name": "escapewheel",
        "software_version": "0.1.0",
        "status": "succeeded",
        "started_at": START + timedelta(hours=hours),
        "ended_at": START + timedelta(hours=hours, minutes=10),
    }


def scoped():
    # An import's scope is its session, so two imports of one session share a scope.
    c = content()
    c["core.processing_runs"][0] |= {"scope_kind": "core.sessions", "scope": "s001"}
    return c


def reimported(c):
    c["core.processing_runs"].append(processing_run("run_import_002", "import", "core.sessions", "s001", 30))


def curated(preferred=None):
    def make():
        c = scoped()
        c["core.processing_runs"].append(
            processing_run("run_curation_001", "curation", "core.sorting_runs", "sort_ks4_001", 4)
        )
        if preferred is not None:
            add_curation(c)
            c["core.preferred_runs"] = [preference(preferred)]
        return c

    return make


def preference(run_id):
    return {
        "session_id": "s001",
        "activity_type": "curation",
        "scope_kind": "core.sorting_runs",
        "scope": "sort_ks4_001",
        "processing_run_id": run_id,
        "reason": "the later curation",
        "chosen_at": START + timedelta(hours=31),
    }


def add_curation(c):
    """A second curation of the sorting run: new units, their spikes, contacts, windows and labels."""
    c["core.curation_versions"].append(
        {**c["core.curation_versions"][0], "curation_id": "curation_002", "created_at": START + timedelta(hours=29)}
    )
    held = [u for u in c["core.units"] if u["curation_id"] == "curation_001"]
    by_unit = {}
    for unit in held:
        name = f"recurated.{unit['unit_id']}"  # sorts after the held units, as the build numbers them
        by_unit[unit["unit_id"]] = name
        c["core.units"].append({**unit, "unit_id": name, "curation_id": "curation_002"})
    for table in (
        "core.spike_events",
        "core.unit_electrodes",
        "core.unit_observation_intervals",
        "core.unit_quality_labels",
    ):
        c[table] += [{**r, "unit_id": by_unit[r["unit_id"]]} for r in c[table] if r["unit_id"] in by_unit]
    c["core.processing_runs"].append(
        processing_run("run_curation_002", "curation", "core.sorting_runs", "sort_ks4_001", 29)
    )


def with_curation(c):
    add_curation(c)
    c["core.preferred_runs"] = [preference("run_curation_002")]
    reimported(c)


def tones(c):
    # 120 tones of a kind sorting before the trials, numbered after every interval the packet holds.
    for i in range(120):
        name = f"s001/cue.tones/{i + 1}"
        c["core.intervals"].append(
            {
                "session_id": "s001",
                "interval_kind": "cue.tones",
                "interval_id": name,
                "local_interval_label": str(i + 1),
                "start_tick": 100 + 90 * i,
                "stop_tick": 140 + 90 * i,
                "clock_id": "behavior_s001",
            }
        )
        c.setdefault("cue.tones", []).append({"session_id": "s001", "tone_id": name})
    reimported(c)


def another_trial(c):
    c["core.intervals"].append(
        {
            **c["core.intervals"][1],
            "interval_id": trial(3),
            "local_interval_label": "3",
            "start_tick": 10500,
            "stop_tick": 11500,
        }
    )
    c[KIND].append({**c[KIND][1], "trial_id": trial(3)})
    reimported(c)


def moved_trial(c):
    c["core.intervals"][0]["stop_tick"] = 5500
    reimported(c)


def held_unit_observed_again(c):
    # Unit 2's dropout, observed after all: its windows are one group the packet holds.
    c["core.unit_observation_intervals"].append(
        {"session_id": "s001", "unit_id": 2, "start_tick": 125_000, "stop_tick": 145_000}
    )
    reimported(c)


def replacing(packet_id):
    # The first version replaces version 0.1.0 of its own packet_id, so it is at 1.0.0.
    return {"packet_version": "1.0.0", "replaces": [replaced(packet_id)]}


def repreferred(c):
    c["core.preferred_runs"] = [preference("run_curation_001")]
    reimported(c)


def amended(make, change, **options) -> Build:
    """A build of `amend`."""

    def build(out: Path) -> None:
        amend(out, make, change, **options)

    return build


def two_imports(out: Path) -> None:
    c = scoped()
    reimported(c)
    write_packet(out, c)


def preference_of_another_scope(out: Path) -> None:
    # A preference whose run curated the probe, not the sorting run the preference names.
    c = curated()()
    c["core.processing_runs"].append(processing_run("run_curation_002", "curation", "core.probes", "probe0", 29))
    c["core.preferred_runs"] = [preference("run_curation_002")]
    write_packet(out, c)


#: Part 05 §15.2's amendments: each adds groups a packet lacks, or breaks one rule of adding.
AMENDMENT_PACKETS = (
    Packet("amended_intervals", amended(scoped, tones, extensions=(CUE_EXTENSION,))),
    Packet("amended_curation", amended(curated(), with_curation)),
    Packet("amended_preference", amended(curated("run_curation_002"), repreferred)),
    Packet("amended_trial", amended(scoped, another_trial), Expected("error", "amendment.group_grown")),
    Packet("amended_trial_bounds", amended(scoped, moved_trial), Expected("error", "amendment.row_changed")),
    Packet(
        "amended_unit_window",
        amended(scoped, held_unit_observed_again),
        Expected("error", "amendment.group_grown"),
    ),
    Packet(
        "amended_packet_id",
        amended(scoped, reimported, identity={"packet_id": "another_packet"}),
        Expected("error", "amendment.identity_changed"),
    ),
    Packet(
        "amended_replacement",
        amended(scoped, reimported, superseded_identity=replacing("amended_replacement")),
    ),
    Packet(
        "amended_replacement_unlinked",
        amended(
            scoped,
            reimported,
            superseded_identity=replacing("amended_replacement_unlinked"),
            dropped=("replaces",),
        ),
        Expected("error", "amendment.identity_changed"),
    ),
    Packet(
        "amended_replacement_major",
        amended(
            scoped,
            reimported,
            superseded_identity=replacing("amended_replacement_major"),
            identity={"packet_version": "2.0.0"},
        ),
        Expected("error", "amendment.identity_changed"),
    ),
    Packet("two_imports", two_imports),
    Packet(
        "preference_of_another_scope",
        preference_of_another_scope,
        Expected("error", "core.preferred_runs.scope_matches_run"),
    ),
)


#: Every packet of the corpus, in the order it is written.
PACKETS: tuple[Packet, ...] = (
    VALID,
    *ROW_PACKETS,
    *SCHEMA_PACKETS,
    *SUBSET_PACKETS,
    *DIGEST_PACKETS,
    *FLOOR_PACKETS,
    *AXIS_PACKETS,
    *INTERVAL_PACKETS,
    *DEVICE_PACKETS,
    *UNIT_PACKETS,
    *OPAQUE_PACKETS,
    *AMENDMENT_PACKETS,
    *REPLACEMENT_PACKETS,
    *SPIKE_PACKETS,
)
if len({packet.name for packet in PACKETS}) != len(PACKETS):
    raise SystemExit("two packets of the corpus share a name")


def main():
    root = HERE / "packets"
    # A packet dropped from the table would otherwise leave its last build behind.
    if root.exists():
        shutil.rmtree(root)
    for packet in PACKETS:
        packet.build(root / packet.name)
        written = f"{sum(len(v) for v in content().values()):>5d} rows" if packet is VALID else "written"
        print(f"{packet.name:26s}{written}")


if __name__ == "__main__":
    main()
