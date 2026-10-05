import json
import shutil

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from packet_fixture import (
    CLOCK_BEHAVIOUR,
    CLOCK_PROBE,
    CURATION,
    SESSION,
    SESSION_NAME,
    SORTING_RUN,
    STREAMS,
    SUBJECT,
    TS,
    UNITS,
    column,
    install_registry,
    read_registry,
    resource_entry,
    write_packet,
    write_table,
)

from escapewheel_reader import open_packet

#: What the fixture packet declares of core: each table's key and the columns a test reads.
COLUMNS = {
    "core.sessions": ("session_id", "session_name", "subject_id", "session_start_time"),
    "core.clocks": ("session_id", "clock_id"),
    "core.processing_runs": ("session_id", "processing_run_id"),
    "core.intervals": (
        "session_id",
        "interval_id",
        "interval_name",
        "interval_kind",
        "local_interval_label",
        "start_tick",
        "stop_tick",
        "clock_id",
    ),
    "core.units": ("session_id", "unit_id", "unit_name", "sorting_run_id", "curation_id", "quality_label", "clock_id"),
    "core.event_streams": ("event_stream_id", "session_id", "event_stream_name", "event_type", "clock_id"),
    "core.events": ("session_id", "stream_id", "t_tick"),
    "core.spike_events": ("session_id", "unit_id", "t_tick"),
    "analysis.spike_events": ("session_id", "unit_id", "t_tick"),
}


@pytest.fixture
def packet_root(tmp_path):
    """The shared packet with `core.clocks` declared and absent, so a test supplies the clocks it needs."""
    return write_packet(tmp_path / "session_001", COLUMNS, unwritten=("core.clocks",))


@pytest.fixture
def two_clock_packet(tmp_path, packet_root):
    """A packet whose spikes are on a probe clock and whose session reports on another.

    The realistic shape: anchors relate the two, and only a mapped tick is comparable with a
    behavioural event. Anchor pairs are exact multiples so the expected ticks are exact.
    """
    root = tmp_path / "two_clock"
    shutil.copytree(packet_root, root)
    manifest = json.loads((root / "packet.json").read_text())
    by_id = {r["resource_id"]: r for r in manifest["resources"]}

    i32 = pa.int32()
    sessions = pa.table(
        {
            "session_id": pa.array([SESSION], type=i32),
            "session_name": pa.array([SESSION_NAME]),
            "subject_id": pa.array([SUBJECT], type=i32),
            "session_start_time": pa.array([1_756_000_000_000_000], type=TS),
            "reference_clock_id": pa.array([CLOCK_BEHAVIOUR], type=i32),
            # Probe tick 0, which is where the probe clock's observation window begins and so
            # what Part 01 §2.2 makes the origin. It lands on a whole harp second by construction,
            # so a derived second is exact and a test can say what it should be.
            "t_zero_tick": pa.array([1_000_000], type=pa.int64()),
        }
    )
    clocks = pa.table(
        {
            "clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], type=i32),
            "session_id": pa.array([SESSION] * 2, type=i32),
            "tick_rate_num": pa.array([31_250, 30_000], type=pa.int64()),
            "tick_rate_den": pa.array([1, 1], type=pa.int64()),
            "parent_clock_id": pa.array([None, CLOCK_BEHAVIOUR], type=i32),
        }
    )
    units = pa.table(
        {
            "session_id": pa.array([SESSION] * 3, type=i32),
            "unit_id": pa.array(list(UNITS), type=i32),
            "unit_name": pa.array([str(unit) for unit in UNITS]),
            "sorting_run_id": pa.array([SORTING_RUN] * 3, type=i32),
            "curation_id": pa.array([CURATION] * 3, type=i32),
            "quality_label": pa.array(["sua", "mua", "noise"]),
            "clock_id": pa.array([CLOCK_PROBE, CLOCK_PROBE, CLOCK_BEHAVIOUR], type=i32),
        }
    )
    # Probe tick 0 is harp tick 1,000,000, and the probe runs at 30 kHz against harp's 31,250.
    n = 8
    anchors = pa.table(
        {
            "clock_id": pa.array([CLOCK_PROBE] * n, type=i32),
            "anchor_index": pa.array(list(range(n)), type=pa.int64()),
            "t_tick": pa.array([i * 30_000 for i in range(n)], type=pa.int64()),
            "parent_tick": pa.array([1_000_000 + i * 31_250 for i in range(n)], type=pa.int64()),
        }
    )
    spikes = pa.table(
        {
            "session_id": pa.array([SESSION] * 3, type=i32),
            "unit_id": pa.array([UNITS[0], UNITS[0], UNITS[2]], type=i32),
            "t_tick": pa.array([30_000, 60_000, 90_000], type=pa.int64()),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array([SESSION], type=i32),
            "stream_id": pa.array([STREAMS[0]], type=i32),
            "t_tick": pa.array([1_200_000], type=pa.int64()),
        }
    )
    # The kind lives on the stream, so the fixture declares the one it emits.
    event_streams = pa.table(
        {
            "event_stream_id": pa.array([STREAMS[0]], type=i32),
            "session_id": pa.array([SESSION], type=i32),
            "event_stream_name": pa.array(["go_cue"]),
            "event_type": pa.array(["go_cue"]),
            "clock_id": pa.array([CLOCK_BEHAVIOUR], type=i32),
        }
    )
    for resource_id, name, table in (
        ("core.sessions", "sessions", sessions),
        ("core.units", "units", units),
        ("core.spike_events", "spike_events", spikes),
        ("core.event_streams", "event_streams", event_streams),
        ("core.events", "events", events),
    ):
        by_id[resource_id]["uri"] = write_table(root, name, table)
    manifest["resources"].append(resource_entry("core.clock_anchors", write_table(root, "clock_anchors", anchors)))
    manifest["resources"].append(resource_entry("core.clocks", write_table(root, "clocks", clocks)))
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return root


@pytest.fixture
def dense_root(two_clock_packet):
    """`two_clock_packet` with spikes and events on every 7th tick across and past the probe's anchors.

    The first two units and the second stream are on the probe, the third unit and the first stream
    on the reference clock, and intervals sit on both, so a range selects differently on each clock.
    """
    i32 = pa.int32()
    ticks = np.arange(-60_000, 300_000, 7, dtype=np.int64)
    spikes = pa.table(
        {
            "session_id": pa.array([SESSION] * (3 * ticks.size), i32),
            "unit_id": pa.array(np.repeat(np.array(UNITS, np.int32), ticks.size)),
            "t_tick": pa.array(np.tile(ticks, 3) + np.repeat([0, 1_000_000, 1_000_000], ticks.size)),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array([SESSION] * (2 * ticks.size), i32),
            "stream_id": pa.array(np.repeat(np.array(STREAMS, np.int32), ticks.size)),
            "t_tick": pa.array(np.concatenate([ticks + 1_000_000, ticks])),
        }
    )
    event_streams = pa.table(
        {
            "event_stream_id": pa.array(list(STREAMS), i32),
            "session_id": pa.array([SESSION] * 2, i32),
            "event_stream_name": pa.array(["go_cue", "lick"]),
            "event_type": pa.array(["go_cue", "lick"]),
            "clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], i32),
        }
    )
    intervals = pa.table(
        {
            "session_id": pa.array([SESSION] * 4, i32),
            "interval_id": pa.array([1, 2, 3, 4], i32),
            "interval_name": pa.array(["a", "b", "c", "d"]),
            "interval_kind": pa.array(["trial"] * 4),
            "local_interval_label": pa.array(["a", "b", "c", "d"]),
            "start_tick": pa.array([0, 90_000, 1_010_000, 1_100_000], pa.int64()),
            "stop_tick": pa.array([30_000, 400_000, 1_040_000, 1_200_000], pa.int64()),
            "clock_id": pa.array([CLOCK_PROBE, CLOCK_PROBE, CLOCK_BEHAVIOUR, CLOCK_BEHAVIOUR], i32),
        }
    )
    manifest = json.loads((two_clock_packet / "packet.json").read_text())
    by_id = {r["resource_id"]: r for r in manifest["resources"]}
    for resource_id, name, table in (
        ("core.spike_events", "spike_events", spikes),
        ("core.events", "events", events),
        ("core.event_streams", "event_streams", event_streams),
        ("core.intervals", "intervals", intervals),
    ):
        by_id[resource_id]["uri"] = write_table(two_clock_packet, name, table)
    (two_clock_packet / "packet.json").write_text(json.dumps(manifest, indent=2))
    return two_clock_packet


# -- arrays ---------------------------------------------------------------------------------

#: Two core arrays and an analysis one. The analysis array shares the LFP's number, since each
#: catalog numbers its own, so a read not scoped to its own tables finds the other's rows.
WAVE, LFP, RATES = 30, 31, 31
ELECTRODES = (100, 101, 102, 103)

TYPES = {"int32": pa.int32(), "int64": pa.int64(), "string": pa.string(), "float64": pa.float64()}


def _index(name, presence="required"):
    return column(name, "int64", presence, role="structural_index")


def _axes_columns(namespace):
    return [
        column("session_id", "int32", "required"),
        column("array_asset_id", "int32", "required"),
        _index("axis_index"),
        column("dimension_name", "string", "required"),
        column(
            "coordinate_resource",
            "string",
            "nullable",
            role="discriminator",
            resolves="required",
            discriminates_via=f"{namespace}.array_labels.axis_index",
            discriminates="label_id",
        ),
        _index("depends_on_axis_index", "nullable"),
        column("coordinate_array_asset_id", "int32", "nullable"),
        column("coordinate_unit", "string", "nullable"),
        column("step_value", "float64", "nullable"),
        column("origin_value", "float64", "nullable"),
        column("step_tick_num", "int64", "nullable"),
        column("step_tick_den", "int64", "nullable"),
        column("origin_tick", "int64", "nullable"),
        column("clock_id", "int32", "nullable"),
    ]


def _label_columns():
    return [
        column("session_id", "int32", "required"),
        column("array_asset_id", "int32", "required"),
        _index("axis_index"),
        _index("depends_on_position_index"),
        _index("position_index"),
        column("label_id", "int32", "nullable"),
    ]


def _asset_columns():
    return [
        column("session_id", "int32", "required"),
        column("array_asset_id", "int32", "required"),
        column("resource_id", "string", "required"),
        column("unit", "string", "nullable"),
        column("conversion", "float64", "nullable"),
        column("offset", "float64", "nullable"),
    ]


def _to_axes(namespace):
    return [
        {
            "columns": ["array_asset_id", "axis_index"],
            "resource": f"{namespace}.array_dimensions",
            "resource_columns": ["array_asset_id", "axis_index"],
        }
    ]


#: Each table this module reads, as (columns, primary key, references). The rows below and the
#: registry both come from it, so the two cannot disagree about a column.
DECLARED = {
    "core.electrodes": (
        [
            column("session_id", "int32", "required"),
            column("electrode_id", "int32", "required"),
            column("electrode_name", "string", "required"),
        ],
        ["electrode_id"],
        [],
    ),
    "core.array_assets": (_asset_columns(), ["array_asset_id"], []),
    "core.array_dimensions": (_axes_columns("core"), ["array_asset_id", "axis_index"], []),
    "core.array_labels": (
        _label_columns(),
        ["array_asset_id", "axis_index", "depends_on_position_index", "position_index"],
        _to_axes("core"),
    ),
    "core.array_channels": (
        [
            column("session_id", "int32", "required"),
            column("array_asset_id", "int32", "required"),
            _index("axis_index"),
            _index("channel_index"),
            column("unit", "string", "nullable"),
            column("offset", "float64", "nullable"),
            column("conversion", "float64", "nullable"),
        ],
        ["array_asset_id", "channel_index"],
        _to_axes("core"),
    ),
    "analysis.array_assets": (_asset_columns(), ["array_asset_id"], []),
    "analysis.array_dimensions": (_axes_columns("analysis"), ["array_asset_id", "axis_index"], []),
    "analysis.array_labels": (
        _label_columns(),
        ["array_asset_id", "axis_index", "depends_on_position_index", "position_index"],
        _to_axes("analysis"),
    ),
}

#: Each array's catalog, and the shape its `zarr.json` declares.
ARRAYS = {
    "core.waveform_mean": ("core", (2, 3, 4)),
    "core.lfp": ("core", (4, 3)),
    "analysis.unit_rates": ("analysis", (2, 5)),
}


def _rows():
    """The waveform labels two units, and each unit's contacts along its channel axis.

    The first unit has three contacts, 102, 100 and 103 in that order; the second has 101 and
    103, so its third channel position is padding. Label rows are stored in reverse, so a read
    that forgets to sort gets every axis backwards.
    """
    session = {"session_id": SESSION}
    wave, lfp, rates = ({**session, "array_asset_id": a} for a in (WAVE, LFP, RATES))

    def labels(of, axis, grid):
        return [
            {**of, "axis_index": axis, "depends_on_position_index": d, "position_index": p, "label_id": label}
            for d, row in enumerate(grid)
            for p, label in enumerate(row)
        ]

    core_labels = [
        *labels(wave, 0, [[11, 12]]),
        *labels(wave, 1, [[102, 100, 103], [101, 103, None]]),
        *labels(lfp, 1, [[100, 101, 102]]),
    ]
    return {
        "core.electrodes": [{**session, "electrode_id": e, "electrode_name": f"e{e}"} for e in ELECTRODES],
        "core.array_assets": [
            {**wave, "resource_id": "core.waveform_mean"},
            {**lfp, "resource_id": "core.lfp", "unit": "uV", "conversion": 2.0, "offset": 0.5},
        ],
        "core.array_dimensions": [
            {**wave, "axis_index": 0, "dimension_name": "unit", "coordinate_resource": "core.units"},
            {
                **wave,
                "axis_index": 1,
                "dimension_name": "channel",
                "coordinate_resource": "core.electrodes",
                "depends_on_axis_index": 0,
            },
            {
                **wave,
                "axis_index": 2,
                "dimension_name": "sample",
                "origin_value": -1.0,
                "step_value": 1.0,
                "coordinate_unit": "{sample}",
            },
            {
                **lfp,
                "axis_index": 0,
                "dimension_name": "time",
                "clock_id": CLOCK_PROBE,
                "origin_tick": 1000,
                "step_tick_num": 1875,
                "step_tick_den": 2,
            },
            {**lfp, "axis_index": 1, "dimension_name": "channel", "coordinate_resource": "core.electrodes"},
        ],
        "core.array_labels": core_labels[::-1],
        "core.array_channels": [],
        "analysis.array_assets": [{**rates, "resource_id": "analysis.unit_rates"}],
        "analysis.array_dimensions": [
            {**rates, "axis_index": 0, "dimension_name": "unit", "coordinate_resource": "core.units"},
            {
                **rates,
                "axis_index": 1,
                "dimension_name": "time_bin",
                "origin_value": 0.0,
                "step_value": 1.0,
                "coordinate_unit": "1",
            },
        ],
        "analysis.array_labels": labels(rates, 0, [[12, 11]])[::-1],
    }


def _zarr_json(root, uri, shape):
    """Array metadata with no chunk written: describing an array must not read its values."""
    store = root / uri
    store.mkdir(parents=True)
    document = {
        "zarr_format": 3,
        "node_type": "array",
        "shape": list(shape),
        "data_type": "int16",
        "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": list(shape)}},
        "chunk_key_encoding": {"name": "default", "configuration": {"separator": "/"}},
        "fill_value": 0,
        "codecs": [{"name": "bytes", "configuration": {"endian": "little"}}],
    }
    (store / "zarr.json").write_text(json.dumps(document))


def _array_packet(tmp_path, packet_root, edit, arrays):
    """Copy the fixture packet and add the arrays, after `edit` changes their rows; `arrays` adds more."""
    root = tmp_path / "with_arrays"
    shutil.copytree(packet_root, root)
    rows = _rows()
    if edit is not None:
        edit(rows)
    manifest = json.loads((root / "packet.json").read_text())
    registry = read_registry(root)
    for resource_id, (columns, key, references) in DECLARED.items():
        namespace, name = resource_id.split(".")
        table = pa.table(
            {c["name"]: pa.array([r.get(c["name"]) for r in rows[resource_id]], type=TYPES[c["type"]]) for c in columns}
        )
        (root / "tables" / namespace).mkdir(parents=True, exist_ok=True)
        pq.write_table(table, root / "tables" / namespace / f"{name}.parquet")
        manifest["resources"].append(resource_entry(resource_id, f"tables/{namespace}/{name}.parquet"))
        registry["resources"][resource_id] = {
            "content_class": namespace,
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {"columns": columns, "primary_key": key, "references": references, "rules": []},
        }
    for namespace in ("core", "analysis"):
        registry["resources"][f"{namespace}.array_asset_instances"] = {
            "content_class": namespace,
            "kind": "dense_array",
            "instances": {
                "mode": "catalog",
                "catalog_resource": f"{namespace}.array_assets",
                "resource_id_column": "resource_id",
            },
            "requires": [],
            "lineage": "optional",
            "array": {"axes_resource": f"{namespace}.array_dimensions"},
        }
    for resource_id, (namespace, shape) in {**ARRAYS, **(arrays or {})}.items():
        uri = f"arrays/{resource_id}.zarr"
        _zarr_json(root, uri, shape)
        manifest["resources"].append(
            resource_entry(resource_id, uri, declaration_id=f"{namespace}.array_asset_instances")
        )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    install_registry(root, registry)
    return open_packet(root)


@pytest.fixture
def array_packet(tmp_path, packet_root):
    """Build the packet holding the described arrays: ``array_packet(edit=None, arrays=None)``.

    `edit` changes the table rows before they are written, and `arrays` maps further resource IDs
    to their (catalog namespace, shape).
    """

    def build(edit=None, arrays=None):
        return _array_packet(tmp_path, packet_root, edit, arrays)

    return build
