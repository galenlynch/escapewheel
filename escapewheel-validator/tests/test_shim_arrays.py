"""A dense array's own metadata and shape against what the packet's tables say of it."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader import open_packet
from packet_fixture import install_registry, read_registry

from escapewheel_validator import Verification, validate

from .builders import add_array, checks_under, zarr_v3_metadata
from .conftest import owned_digest


def test_an_array_declaring_its_codecs_correctly_is_clean(packet_root):
    add_array(packet_root, declared=["sharding_indexed", "blosc"])
    assert checks_under(validate(open_packet(packet_root))) == set()


def test_a_packet_owned_array_must_be_zarr_v3(packet_root):
    """Part 03 §6.1 allows v2 only for an array the packet references."""
    v2 = {"zarr_format": 2, "shape": [4, 2, 3], "chunks": [1, 2, 3], "dtype": "<i2", "fill_value": 0}
    store = packet_root / "arrays" / "core" / "wf.zarr"
    add_array(packet_root, declared=[])
    (store / "zarr.json").unlink()
    (store / ".zarray").write_text(json.dumps(v2))
    assert "array.not_zarr_v3" in checks_under(validate(open_packet(packet_root)))


def test_an_array_without_a_fill_value_is_caught(packet_root):
    """Zarr v3 requires one, and Part 03 §6.1 requires a packet-owned array to be Zarr v3."""
    add_array(packet_root, declared=["sharding_indexed", "blosc"], document=zarr_v3_metadata(fill_value=None))
    report = validate(open_packet(packet_root))
    assert checks_under(report) == {"array.no_fill_value"}
    (finding,) = [f for f in report.findings if f.check == "array.no_fill_value"]
    assert finding.message == (
        "core.waveform_mean declares no fill_value, which Zarr v3 requires of array metadata; "
        "Part 03 §6.1 requires a packet-owned array to be Zarr v3"
    )


def test_an_irregular_chunk_grid_is_caught(packet_root):
    add_array(packet_root, declared=["sharding_indexed", "blosc"], document=zarr_v3_metadata(grid="rectilinear"))
    assert "array.irregular_chunk_grid" in checks_under(validate(open_packet(packet_root)))


def test_a_transpose_inside_a_shard_is_caught(packet_root):
    """Part 03 §6.2 bans `transpose` from the whole chain, a shard's own pipeline included."""
    document = zarr_v3_metadata()
    document["codecs"][0]["configuration"]["codecs"].insert(0, {"name": "transpose"})
    add_array(packet_root, declared=["sharding_indexed", "blosc"], document=document)
    assert "array.transpose_codec" in checks_under(validate(open_packet(packet_root)))


def test_a_rank_the_dimensions_do_not_cover_is_caught(packet_root):
    """Part 02 §12.11: axis_index enumerates every stored axis, so two rows cannot describe rank 3."""
    add_array(packet_root, declared=["sharding_indexed", "blosc"], axes=2)
    assert "array.rank_disagrees_with_dimensions" in checks_under(validate(open_packet(packet_root)))


def test_no_array_dimensions_at_all_is_caught(packet_root):
    add_array(packet_root, declared=["sharding_indexed", "blosc"], axes=None)
    assert "array.no_array_dimensions_table" in checks_under(validate(open_packet(packet_root)))


def test_an_external_array_is_left_to_the_external_mode(packet_root):
    """Level 3, not level 2: reaching it is the reader's situation, not the packet's defect."""
    add_array(packet_root, declared=["blosc"], external=True)
    assert checks_under(validate(open_packet(packet_root))) == set()


def test_an_external_arrays_rank_is_checked_against_the_dimensions(packet_root):
    """The check `_check_one_array` does for a packet-owned array, for an external one."""
    root = add_array(packet_root, declared=["blosc"], external=True, axes=2)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert not report.passed
    assert "external.array_rank" in {f.check for f in report.findings}


def test_a_matching_rank_passes_and_is_counted(packet_root):
    root = add_array(packet_root, declared=["blosc"], external=True, axes=3)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert "external.array_rank" not in {f.check for f in report.findings}
    assert "1 rank" in next(f for f in report.findings if f.check == "external.verified").message


def _manifest_table(root, manifest, name, table):
    """Write a core table and declare it in `manifest`, once."""
    path = f"tables/core/{name.removeprefix('core.')}.parquet"
    pq.write_table(table, root / path)
    manifest["resources"] = [r for r in manifest["resources"] if r["resource_id"] != name]
    manifest["resources"].append(
        {
            "resource_id": name,
            "declaration_id": name,
            "uri": path,
            "digest": owned_digest(root, path),
            "validation_state": "passed",
        }
    )


def _index(name, **extra):
    return {
        "name": name,
        "type": "int64",
        "presence": "required",
        "role": "structural_index",
        "description": "d",
        **extra,
    }


def _label_axis(root, labels, *, depends_on=None, kind="core.sessions"):
    """Label axis 1 of the test array by `kind`'s rows (Part 02 §12.11).

    `labels` holds (`depends_on_position_index`, `position_index`, `label_id`) rows; `depends_on`
    makes axis 1 depend on that axis.
    """
    registry = read_registry(root)
    dimensions = registry["resources"]["core.array_dimensions"]["table"]
    replaced = {"coordinate_resource", "depends_on_axis_index"}
    dimensions["columns"] = [c for c in dimensions["columns"] if c["name"] not in replaced] + [
        {
            "name": "coordinate_resource",
            "type": "string",
            "presence": "nullable",
            "role": "discriminator",
            "resolves": "required",
            "discriminates_via": "core.array_labels.axis_index",
            "discriminates": "label_id",
            "description": "d",
        },
        _index("depends_on_axis_index", presence="nullable"),
    ]
    registry["resources"]["core.array_labels"] = {
        "content_class": "core",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {
            "columns": [
                {
                    "name": "array_asset_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "d",
                },
                _index("axis_index"),
                _index("depends_on_position_index"),
                _index("position_index"),
                {
                    "name": "label_id",
                    "type": "int32",
                    "presence": "nullable",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "d",
                },
            ],
            "primary_key": ["array_asset_id", "axis_index", "depends_on_position_index", "position_index"],
            "amendment_groups": [["array_asset_id", "axis_index", "depends_on_position_index", "position_index"]],
            "references": [
                {
                    "columns": ["array_asset_id", "axis_index"],
                    "resource": "core.array_dimensions",
                    "resource_columns": ["array_asset_id", "axis_index"],
                }
            ],
            "rules": [],
        },
    }
    install_registry(root, registry)
    manifest = json.loads((root / "packet.json").read_text())
    current = pq.read_table(root / "tables" / "core" / "array_dimensions.parquet").to_pydict()
    rank = len(current["axis_index"])
    _manifest_table(
        root,
        manifest,
        "core.array_dimensions",
        pa.table(
            {
                "array_asset_id": pa.array(current["array_asset_id"], type=pa.int32()),
                "axis_index": pa.array(current["axis_index"], type=pa.int64()),
                "dimension_name": pa.array(current["dimension_name"]),
                "coordinate_resource": pa.array([kind if axis == 1 else None for axis in range(rank)]),
                "depends_on_axis_index": pa.array(
                    [depends_on if axis == 1 else None for axis in range(rank)], type=pa.int64()
                ),
            }
        ),
    )
    _manifest_table(
        root,
        manifest,
        "core.array_labels",
        pa.table(
            {
                "array_asset_id": pa.array([1] * len(labels), type=pa.int32()),
                "axis_index": pa.array([1] * len(labels), type=pa.int64()),
                "depends_on_position_index": pa.array([row[0] for row in labels], type=pa.int64()),
                "position_index": pa.array([row[1] for row in labels], type=pa.int64()),
                "label_id": pa.array([row[2] for row in labels], type=pa.int32()),
            }
        ),
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_an_external_axis_is_checked_against_its_labels(packet_root):
    """A re-generated array with a different channel count leaves its labels naming positions that
    are not there, or positions with none (Part 02 §12.11)."""
    root = add_array(packet_root, declared=["blosc"], external=True, axes=3)
    _label_axis(root, [(0, 0, 1), (0, 1, 1)])  # axis 1 is 2 long in zarr_v3_metadata's [4, 2, 3]
    report = validate(open_packet(root), verification=Verification(external=True))
    assert report.passed, [f for f in report.findings if f.level == "error"]
    assert "1 labels" in next(f for f in report.findings if f.check == "external.verified").message

    _label_axis(root, [(0, 0, 1), (0, 1, 1), (0, 2, 1)])
    assert "external.array_label_position_out_of_range" in checks_under(
        validate(open_packet(root), verification=Verification(external=True)), ""
    )

    _label_axis(root, [(0, 0, 1)])
    assert "external.array_label_missing" in checks_under(
        validate(open_packet(root), verification=Verification(external=True)), ""
    )


def test_a_packet_owned_axis_is_checked_against_its_labels(packet_root):
    """Checked without asking, unlike an external array, since the owned array's shape is in hand."""
    root = add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    _label_axis(root, [(0, 0, 1), (0, 1, 1)])
    assert validate(open_packet(root)).passed

    _label_axis(root, [(0, 0, 1), (0, 1, 1), (0, -1, 1)])
    assert "array.label_position_out_of_range" in checks_under(validate(open_packet(root)))


def test_a_dependent_axis_is_labelled_at_every_pair_of_positions(packet_root):
    """Axis 1 depends on axis 0, which is 4 long, so its 2 positions need 8 rows; padding is a row."""
    root = add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    full = [(outer, position, 1 if position == 0 else None) for outer in range(4) for position in range(2)]
    _label_axis(root, full, depends_on=0)
    assert validate(open_packet(root)).passed

    _label_axis(root, full[:-1], depends_on=0)
    missing = next(f for f in validate(open_packet(root)).findings if f.check == "array.label_missing")
    assert missing.rows == (("axis_index 1", "depends_on_position_index 3, position_index 1", "1 missing"),)

    _label_axis(root, [*full, (4, 0, 1)], depends_on=0)
    assert "array.depends_on_position_out_of_range" in checks_under(validate(open_packet(root)))


def test_a_label_naming_no_row_is_caught(packet_root):
    """Part 02 §8.3: the paired value on the specialised table resolves in the kind its axis names."""
    root = add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    _label_axis(root, [(0, 0, 1), (0, 1, 7)])
    checks = {f.check for f in validate(open_packet(root)).findings if f.level == "error"}
    assert checks == {"core.array_dimensions.coordinate_resource.core_sessions_resolves"}


def test_a_label_on_an_unlabelled_axis_is_caught(packet_root):
    """A label row whose axis names no kind has a value nothing can resolve (Part 02 §8.3)."""
    root = add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    _label_axis(root, [(0, 0, 1), (0, 1, 1)], kind=None)
    checks = {f.check for f in validate(open_packet(root)).findings if f.level == "error"}
    assert "core.array_dimensions.coordinate_resource.specialised_row_has_kind" in checks


def test_a_packet_owned_array_carries_its_axes_names(packet_root):
    """Part 03 §6.4: the axes table owns the names, and a packet-owned array repeats them."""
    document = zarr_v3_metadata()
    document["dimension_names"] = ["unit", "sample", "channel"]
    add_array(packet_root, declared=["sharding_indexed", "blosc"], document=document)
    assert "array.dimension_names" in checks_under(validate(open_packet(packet_root)))


def test_a_packet_owned_array_without_dimension_names_is_caught(packet_root):
    document = zarr_v3_metadata()
    del document["dimension_names"]
    add_array(packet_root, declared=["sharding_indexed", "blosc"], document=document)
    assert "array.dimension_names" in checks_under(validate(open_packet(packet_root)))


def test_a_referenced_array_may_name_its_axes_otherwise(packet_root):
    """The axes table governs an external array's names, which its producer chose (Part 03 §6.4)."""
    document = zarr_v3_metadata()
    del document["dimension_names"]
    root = add_array(packet_root, declared=["blosc", "sharding_indexed"], document=document, external=True)
    assert validate(open_packet(root), verification=Verification(external=True)).passed


def _channels(root, *, rows):
    """Give axis 1 of the test array `rows` channels in `core.array_channels`."""
    registry = read_registry(root)
    registry["resources"]["core.array_channels"] = {
        "content_class": "core",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {
            "columns": [
                {
                    "name": "array_asset_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "d",
                },
                _index("axis_index"),
                _index("channel_index"),
            ],
            "primary_key": ["array_asset_id", "channel_index"],
            "amendment_groups": [["array_asset_id", "channel_index"]],
            "references": [
                {
                    "columns": ["array_asset_id", "axis_index"],
                    "resource": "core.array_dimensions",
                    "resource_columns": ["array_asset_id", "axis_index"],
                }
            ],
            "rules": [],
        },
    }
    install_registry(root, registry)
    manifest = json.loads((root / "packet.json").read_text())
    _manifest_table(
        root,
        manifest,
        "core.array_channels",
        pa.table(
            {
                "array_asset_id": pa.array([1] * rows, type=pa.int32()),
                "axis_index": pa.array([1] * rows, type=pa.int64()),
                "channel_index": pa.array(list(range(rows)), type=pa.int64()),
            }
        ),
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_a_channel_index_beyond_its_axis_is_caught(packet_root):
    """`core.array_channels` describes positions of an axis, so each must be one (Part 05 §5.3)."""
    root = add_array(packet_root, declared=["blosc"], external=True, axes=3)
    _channels(root, rows=2)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert report.passed
    assert "1 channels" in next(f for f in report.findings if f.check == "external.verified").message

    _channels(root, rows=3)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert "external.array_channel_index_out_of_range" in checks_under(report, "")
