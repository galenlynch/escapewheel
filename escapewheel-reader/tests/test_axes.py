"""Describing a dense array's axes and scaling from the packet's tables (Part 03 §6.3)."""

import json
import shutil
from fractions import Fraction

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_reader import open_packet
from escapewheel_reader.axes import LabelledAxis, NumericAxis, Scaling, TickAxis, UnresolvableAxis, describe

from .conftest import CLOCK_PROBE, SESSION, _col, _resource, install_registry, read_registry

#: Two core arrays and an analysis one. The analysis array shares the LFP's number, since each
#: catalog numbers its own, so a read not scoped to its own tables finds the other's rows.
WAVE, LFP, RATES = 30, 31, 31
ELECTRODES = (100, 101, 102, 103)

TYPES = {"int32": pa.int32(), "int64": pa.int64(), "string": pa.string(), "float64": pa.float64()}


def _index(name, presence="required"):
    return _col(name, "int64", presence, role="structural_index")


def _axes_columns(namespace):
    return [
        _col("session_id", "int32", "required"),
        _col("array_asset_id", "int32", "required"),
        _index("axis_index"),
        _col("dimension_name", "string", "required"),
        _col(
            "coordinate_resource",
            "string",
            "nullable",
            role="discriminator",
            resolves="required",
            discriminates_via=f"{namespace}.array_labels.axis_index",
            discriminates="label_id",
        ),
        _index("depends_on_axis_index", "nullable"),
        _col("coordinate_array_asset_id", "int32", "nullable"),
        _col("coordinate_unit", "string", "nullable"),
        _col("step_value", "float64", "nullable"),
        _col("origin_value", "float64", "nullable"),
        _col("step_tick_num", "int64", "nullable"),
        _col("step_tick_den", "int64", "nullable"),
        _col("origin_tick", "int64", "nullable"),
        _col("clock_id", "int32", "nullable"),
    ]


def _label_columns():
    return [
        _col("session_id", "int32", "required"),
        _col("array_asset_id", "int32", "required"),
        _index("axis_index"),
        _index("depends_on_position_index"),
        _index("position_index"),
        _col("label_id", "int32", "nullable"),
    ]


def _asset_columns():
    return [
        _col("session_id", "int32", "required"),
        _col("array_asset_id", "int32", "required"),
        _col("resource_id", "string", "required"),
        _col("unit", "string", "nullable"),
        _col("conversion", "float64", "nullable"),
        _col("offset", "float64", "nullable"),
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
            _col("session_id", "int32", "required"),
            _col("electrode_id", "int32", "required"),
            _col("electrode_name", "string", "required"),
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
            _col("session_id", "int32", "required"),
            _col("array_asset_id", "int32", "required"),
            _index("axis_index"),
            _index("channel_index"),
            _col("unit", "string", "nullable"),
            _col("offset", "float64", "nullable"),
            _col("conversion", "float64", "nullable"),
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


def _packet(tmp_path, packet_root, edit=None):
    """Copy the fixture packet and add the three arrays, after `edit` changes their rows."""
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
        manifest["resources"].append(_resource(resource_id, f"tables/{namespace}/{name}.parquet"))
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
    for resource_id, (namespace, shape) in ARRAYS.items():
        uri = f"arrays/{resource_id}.zarr"
        _zarr_json(root, uri, shape)
        manifest["resources"].append(_resource(resource_id, uri, declaration_id=f"{namespace}.array_asset_instances"))
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    install_registry(root, registry)
    return open_packet(root)


def _axis(rows, resource_id, axis):
    (row,) = [r for r in rows[resource_id] if r["array_asset_id"] == WAVE and r["axis_index"] == axis]
    return row


# -- labels --------------------------------------------------------------------------------


def test_a_dependent_axis_names_each_units_own_contacts(tmp_path, packet_root):
    """Channel position 1 is the first unit's contact 102 and the second's 101."""
    channel = describe(_packet(tmp_path, packet_root), "core.waveform_mean").axes[1].coordinates
    assert isinstance(channel, LabelledAxis)
    assert (channel.resource_id, channel.key, channel.depends_on, channel.shape) == (
        "core.electrodes",
        "electrode_id",
        0,
        (2, 3),
    )
    assert channel.rows["depends_on_position_index"].to_pylist() == [0, 0, 0, 1, 1, 1]
    assert channel.rows["electrode_name"].to_pylist() == ["e102", "e100", "e103", "e101", "e103", None]


def test_padding_is_masked_and_not_filled(tmp_path, packet_root):
    """Any fill is a label like the others, so only the mask says the last position is no contact."""
    channel = describe(_packet(tmp_path, packet_root), "core.waveform_mean").axes[1].coordinates
    assert isinstance(channel, LabelledAxis)
    labels = channel.labels()
    assert labels.tolist() == [[102, 100, 103], [101, 103, None]]
    assert labels.mask.tolist() == [[False, False, False], [False, False, True]]


def test_an_independent_axis_reads_its_own_array_in_position_order(tmp_path, packet_root):
    """The LFP's labels are stored reversed among the waveform's, which name the same electrodes."""
    channel = describe(_packet(tmp_path, packet_root), "core.lfp").axes[1].coordinates
    assert isinstance(channel, LabelledAxis)
    assert channel.depends_on is None and channel.shape == (3,)
    assert channel.rows.column_names[:2] == ["position_index", "electrode_id"]
    assert channel.labels().tolist() == [100, 101, 102]


def test_an_analysis_array_numbered_like_a_core_one_reads_its_own_labels(tmp_path, packet_root):
    """`analysis.unit_rates` and `core.lfp` are both array 31, and each keeps its labels in its own table."""
    packet = _packet(tmp_path, packet_root)
    unit = describe(packet, "analysis.unit_rates").axes[0].coordinates
    assert isinstance(unit, LabelledAxis)
    assert (unit.resource_id, unit.key, unit.labels().tolist()) == ("core.units", "unit_id", [12, 11])
    channel = describe(packet, "core.lfp").axes[1].coordinates
    assert isinstance(channel, LabelledAxis)
    assert channel.labels().tolist() == [100, 101, 102]


def test_a_missing_label_is_refused(tmp_path, packet_root):
    """Padding is a row with a null label, so a position with no row at all is a gap, not padding."""

    def drop_padding(rows):
        rows["core.array_labels"] = [r for r in rows["core.array_labels"] if r["label_id"] is not None]

    with pytest.raises(UnresolvableAxis, match="5 label rows for its 6 positions"):
        describe(_packet(tmp_path, packet_root, drop_padding), "core.waveform_mean")


def test_a_label_naming_no_row_is_refused(tmp_path, packet_root):
    def unknown_contact(rows):
        (row,) = [r for r in rows["core.array_labels"] if r["array_asset_id"] == WAVE and r["label_id"] == 101]
        row["label_id"] = 999

    with pytest.raises(UnresolvableAxis, match="1 labels name no row of core.electrodes"):
        describe(_packet(tmp_path, packet_root, unknown_contact), "core.waveform_mean")


def test_a_dependency_on_a_dependent_axis_is_refused(tmp_path, packet_root):
    """The unit axis depending on the channel axis leaves neither to decide the other's labels."""

    def mutual(rows):
        _axis(rows, "core.array_dimensions", 0)["depends_on_axis_index"] = 1

    with pytest.raises(UnresolvableAxis, match="not on another independent axis"):
        describe(_packet(tmp_path, packet_root, mutual), "core.waveform_mean")


# -- regular axes and forms ----------------------------------------------------------------


def test_a_rational_step_is_not_rounded(tmp_path, packet_root):
    """937.5 ticks per sample puts every other sample between ticks."""
    time = describe(_packet(tmp_path, packet_root), "core.lfp").axes[0].coordinates
    assert isinstance(time, TickAxis)
    assert time.clock_id == CLOCK_PROBE
    assert time.ticks(np.arange(4)).tolist() == [1000, 1937.5, 2875, 3812.5]


def test_a_whole_step_gives_integer_ticks():
    """A tick is an integer wherever the step allows, so an adapter can index by it exactly."""
    ticks = TickAxis(clock_id=0, origin_tick=-500, step=Fraction(24)).ticks(np.arange(3))
    assert ticks.dtype == np.int64
    assert ticks.tolist() == [-500, -476, -452]


def test_a_numeric_axis_keeps_its_origin_step_and_unit(tmp_path, packet_root):
    sample = describe(_packet(tmp_path, packet_root), "core.waveform_mean").axes[2].coordinates
    assert sample == NumericAxis(-1.0, 1.0, "{sample}")


@pytest.mark.parametrize(
    ("change", "forms"),
    [({"origin_value": None}, 0), ({"coordinate_resource": "core.units"}, 2)],
    ids=["none", "two"],
)
def test_an_axis_declaring_other_than_one_form_is_refused(tmp_path, packet_root, change, forms):
    """Nothing says which of two forms governs, and with none a position is only a number."""

    def reform(rows):
        _axis(rows, "core.array_dimensions", 2).update(change)

    with pytest.raises(UnresolvableAxis, match=f"declares {forms} coordinate forms"):
        describe(_packet(tmp_path, packet_root, reform), "core.waveform_mean")


def test_a_dependent_axis_without_labels_is_refused(tmp_path, packet_root):
    def sample_depends(rows):
        _axis(rows, "core.array_dimensions", 2)["depends_on_axis_index"] = 0

    with pytest.raises(UnresolvableAxis, match="no labels to vary"):
        describe(_packet(tmp_path, packet_root, sample_depends), "core.waveform_mean")


# -- scaling -------------------------------------------------------------------------------


def _per_channel(conversions, *, array_level=False):
    """Give the LFP's channels their own conversions, and drop its array-level one unless kept."""

    def edit(rows):
        rows["core.array_channels"] = [
            {
                "session_id": SESSION,
                "array_asset_id": LFP,
                "axis_index": 1,
                "channel_index": i,
                "unit": "uV",
                "conversion": c,
            }
            for i, c in conversions.items()
        ]
        if not array_level:
            (asset,) = [r for r in rows["core.array_assets"] if r["array_asset_id"] == LFP]
            asset.update(unit=None, conversion=None, offset=None)

    return edit


def test_scaling_declared_on_the_array_is_one_pair(tmp_path, packet_root):
    """Stored 3 becomes 3 * 2.0 + 0.5 uV at every position."""
    scaling = describe(_packet(tmp_path, packet_root), "core.lfp").scaling
    assert scaling is not None
    assert (scaling.unit, scaling.conversion, scaling.offset, scaling.axis) == ("uV", 2.0, 0.5, None)


def test_scaling_declared_per_channel_runs_along_the_channel_axis(tmp_path, packet_root):
    """Each channel's own conversion in position order, an absent offset adding nothing, and none for the
    analysis array sharing the LFP's number."""
    packet = _packet(tmp_path, packet_root, _per_channel({2: 3.0, 0: 1.0, 1: 2.0}))
    scaling = describe(packet, "core.lfp").scaling
    assert scaling is not None
    assert scaling.axis == 1 and scaling.unit == ("uV", "uV", "uV")
    assert scaling.conversion.tolist() == [1.0, 2.0, 3.0]  # type: ignore[union-attr]
    assert scaling.offset.tolist() == [0.0, 0.0, 0.0]  # type: ignore[union-attr]
    assert describe(packet, "analysis.unit_rates").scaling is None


def test_no_declared_scaling_is_none(tmp_path, packet_root):
    """Nothing to apply, and no guess at a unit."""
    assert describe(_packet(tmp_path, packet_root), "core.waveform_mean").scaling is None


def test_a_unit_without_a_conversion_is_already_physical(tmp_path, packet_root):
    """The unit still has to reach the caller, or rates in Hz read as unitless numbers."""

    def in_hertz(rows):
        rows["analysis.array_assets"][0]["unit"] = "Hz"

    scaling = describe(_packet(tmp_path, packet_root, in_hertz), "analysis.unit_rates").scaling
    assert scaling == Scaling("Hz", 1.0, 0.0)


def test_scaling_at_both_levels_is_refused(tmp_path, packet_root):
    """Two statements of one relation, and nothing says which governs."""
    packet = _packet(tmp_path, packet_root, _per_channel({0: 1.0, 1: 2.0, 2: 3.0}, array_level=True))
    with pytest.raises(UnresolvableAxis, match="one_scaling_level"):
        describe(packet, "core.lfp")


def test_an_array_unit_disagreeing_with_its_channels_is_refused(tmp_path, packet_root):
    """Two statements of the values' unit, and nothing says which holds."""
    edit = _per_channel({0: 1.0, 1: 2.0, 2: 3.0})

    def in_millivolts(rows):
        edit(rows)
        (asset,) = [r for r in rows["core.array_assets"] if r["array_asset_id"] == LFP]
        asset["unit"] = "mV"

    with pytest.raises(UnresolvableAxis, match="values in mV and its channels in"):
        describe(_packet(tmp_path, packet_root, in_millivolts), "core.lfp")


def test_scaling_some_channels_is_refused(tmp_path, packet_root):
    """The middle channel has no conversion, so its values have no physical unit."""
    with pytest.raises(UnresolvableAxis, match="2 of the 3 channels"):
        describe(_packet(tmp_path, packet_root, _per_channel({0: 1.0, 2: 3.0})), "core.lfp")
