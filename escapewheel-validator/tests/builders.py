"""Packets the validator's tests build on the fixture packet, each changing one thing about it."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
from packet_fixture import install_registry, read_registry

from .conftest import owned_digest


def read_table(root, name):
    """Read a core table's file."""
    return pq.read_table(root / "tables" / "core" / f"{name}.parquet")


def rewrite_table(root, name, table):
    """Replace a core table's file with `table`."""
    pq.write_table(table, root / "tables" / "core" / f"{name}.parquet", compression="zstd")


def with_column(table, name, values):
    """Return `table` with the column `name` holding `values`."""
    return table.set_column(table.schema.get_field_index(name), name, values)


def add_family_declaration(root, declaration_id, *, content_class="core"):
    """Add an opaque family for tests concerned with generic manifest behavior."""
    registry = read_registry(root)
    registry["resources"][declaration_id] = {
        "content_class": content_class,
        "kind": "opaque",
        "instances": {"mode": "family"},
        "requires": [],
        "lineage": "forbidden" if content_class == "documentation" else "optional",
    }
    install_registry(root, registry)


def declare_analysis(root, **overrides):
    """Add an analysis resource to the manifest, pointing at a table that already exists."""
    registry = read_registry(root)
    registry["resources"]["analysis.test_output"] = {
        "content_class": "analysis",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "required",
        "table": {**registry["resources"]["core.intervals"]["table"], "rules": [], "amendment_groups": []},
    }
    install_registry(root, registry)
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    entry = {
        "resource_id": "analysis.test_output",
        "declaration_id": "analysis.test_output",
        "uri": "tables/core/intervals.parquet",
        "digest": owned_digest(root, "tables/core/intervals.parquet"),
        "validation_state": "passed",
        "derived_from": ["core.intervals"],
        **overrides,
    }
    manifest["resources"].append({key: value for key, value in entry.items() if value is not None})
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def zarr_v3_metadata(*, sharded=True, fill_value=0, grid="regular"):
    """Return a Zarr v3 array's metadata document.

    Stored with no chunk files it is still a valid array, every chunk reading as `fill_value`, so
    the metadata is the whole array.
    """
    codecs = [{"name": "bytes"}, {"name": "blosc"}]
    document = {
        "zarr_format": 3,
        "node_type": "array",
        "shape": [4, 2, 3],
        "data_type": "int16",
        "chunk_grid": {"name": grid, "configuration": {"chunk_shape": [4, 2, 3] if sharded else [1, 2, 3]}},
        "chunk_key_encoding": {"name": "default"},
        "codecs": (
            [{"name": "sharding_indexed", "configuration": {"chunk_shape": [1, 2, 3], "codecs": codecs}}]
            if sharded
            else codecs
        ),
        "dimension_names": ["unit", "channel", "sample"],
    }
    if fill_value is not None:
        document["fill_value"] = fill_value
    return document


def add_array(root, *, declared, document=None, axes=3, external=False):
    """Bolt an array onto a packet, with whatever the manifest should claim about it."""
    manifest = json.loads((root / "packet.json").read_text())
    uri = "arrays/core/wf.zarr"
    store = root / uri
    store.mkdir(parents=True)
    (store / "zarr.json").write_text(json.dumps(document or zarr_v3_metadata()))

    registry = read_registry(root)
    common = {
        "content_class": "core",
        "requires": [],
        "lineage": "optional",
    }
    registry["resources"]["core.array_assets"] = {
        **common,
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "table": {
            "columns": [
                {
                    "name": "array_asset_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "Array row identity.",
                },
                {
                    "name": "array_asset_name",
                    "type": "string",
                    "presence": "optional",
                    "role": "data",
                    "vocabulary": "free",
                    "description": "Source array label.",
                },
                {
                    "name": "resource_id",
                    "type": "string",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "carried",
                    "vocabulary": "free",
                    "description": "Packet resource identity.",
                },
                {
                    "name": "metadata",
                    "type": "json_string",
                    "presence": "optional",
                    "role": "data",
                    "description": (
                        "What the source stated about this row that the standard does not model, "
                        "carried in the source's own vocabulary and read by no rule."
                    ),
                },
            ],
            "primary_key": ["array_asset_id"],
            "amendment_groups": [["array_asset_id"]],
            "references": [],
            "rules": [],
        },
    }
    registry["resources"]["core.array_dimensions"] = {
        **common,
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "table": {
            "columns": [
                {
                    "name": "array_asset_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "Array row identity.",
                },
                {
                    "name": "axis_index",
                    "type": "int64",
                    "presence": "required",
                    "role": "structural_index",
                    "description": "Zero-based axis index.",
                },
                {
                    "name": "dimension_name",
                    "type": "string",
                    "presence": "required",
                    "role": "data",
                    "vocabulary": "free",
                    "description": "Axis name.",
                },
                {
                    "name": "coordinate_resource",
                    "type": "string",
                    "presence": "optional",
                    "role": "data",
                    "vocabulary": "free",
                    "description": "Optional coordinate resource.",
                },
            ],
            "primary_key": ["array_asset_id", "axis_index"],
            "amendment_groups": [["array_asset_id", "axis_index"]],
            "references": [
                {
                    "columns": ["array_asset_id"],
                    "resource": "core.array_assets",
                    "resource_columns": ["array_asset_id"],
                }
            ],
            "rules": [],
        },
    }
    registry["resources"]["core.array_asset_instances"] = {
        **common,
        "kind": "dense_array",
        "instances": {
            "mode": "catalog",
            "catalog_resource": "core.array_assets",
            "resource_id_column": "resource_id",
        },
        "array": {"axes_resource": "core.array_dimensions"},
    }
    install_registry(root, registry)
    manifest["registries"] = json.loads((root / "packet.json").read_text())["registries"]

    assets = pa.table(
        {
            "array_asset_id": pa.array([1], type=pa.int32()),
            "array_asset_name": pa.array(["wf"]),
            "resource_id": pa.array(["core.waveform_mean"]),
        }
    )
    pq.write_table(assets, root / "tables" / "core" / "array_assets.parquet")
    manifest["resources"].append(
        {
            "resource_id": "core.array_assets",
            "declaration_id": "core.array_assets",
            "uri": "tables/core/array_assets.parquet",
            "digest": owned_digest(root, "tables/core/array_assets.parquet"),
            "validation_state": "passed",
        }
    )

    if axes is not None:
        dimensions = pa.table(
            {
                "array_asset_id": pa.array([1] * axes, type=pa.int32()),
                "axis_index": pa.array(list(range(axes)), type=pa.int64()),
                "dimension_name": pa.array(["unit", "channel", "sample"][:axes]),
            }
        )
        (root / "tables" / "core").mkdir(parents=True, exist_ok=True)
        pq.write_table(dimensions, root / "tables" / "core" / "array_dimensions.parquet")
        manifest["resources"].append(
            {
                "resource_id": "core.array_dimensions",
                "declaration_id": "core.array_dimensions",
                "uri": "tables/core/array_dimensions.parquet",
                "digest": owned_digest(root, "tables/core/array_dimensions.parquet"),
                "validation_state": "passed",
            }
        )

    entry = {
        "resource_id": "core.waveform_mean",
        "declaration_id": "core.array_asset_instances",
        "uri": uri,
        "validation_state": "passed",
    }
    if external:
        entry |= {"external": True, "uri": f"file://{store}"}
    else:
        entry["digest"] = owned_digest(root, uri)
    manifest["resources"].append(entry)
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return root


def checks_under(report, prefix="array."):
    """Return the check IDs of a report's findings that start with `prefix`."""
    return {f.check for f in report.findings if f.check.startswith(prefix)}


def external_array(root, *, zarray=None, **overrides):
    """Point a packet at a Zarr v2 array beside it, the way an LFP reference does.

    `zarray` replaces members of the array's `.zarray`; `overrides` replaces members of its entry.
    """
    array = root.parent / "external.zarr"
    array.mkdir(exist_ok=True)
    (array / ".zarray").write_text(
        json.dumps(
            {
                "shape": [4, 2],
                "chunks": [4, 2],
                "dtype": "<i2",
                "zarr_format": 2,
                "compressor": {"id": "blosc"},
                "filters": None,
                "order": "C",
                "fill_value": 0,
                **(zarray or {}),
            }
        )
    )
    (array / "0.0").write_bytes(b"x" * 100)
    total = sum(f.stat().st_size for f in array.rglob("*") if f.is_file())
    add_array(root, declared=["blosc"], axes=2, external=True)
    manifest = json.loads((root / "packet.json").read_text())
    entry = next(resource for resource in manifest["resources"] if resource["resource_id"] == "core.waveform_mean")
    entry.update(
        {
            "uri": array.resolve().as_uri(),
            "external": True,
            "size_bytes": total,
            **overrides,
        }
    )
    for key, value in tuple(entry.items()):
        if value is None:
            entry.pop(key)
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def add_extension(root, *, tables=None, mutate=None):
    """Give the packet an extension registry and a table conforming to it."""
    document = {
        "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
        "registry_id": "task",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.2",
        "extension_id": "task",
        "resources": {
            "task.trials": {
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
                            "description": "Session identity.",
                        },
                        {
                            "name": "interval_id",
                            "type": "int32",
                            "presence": "required",
                            "role": "identifier",
                            "identity": "assigned",
                            "description": "Interval identity.",
                        },
                        {
                            "name": "choice",
                            "type": "string",
                            "presence": "nullable",
                            "role": "data",
                            "vocabulary": "closed",
                            "enum": ["left", "right"],
                            "description": "Choice.",
                        },
                    ],
                    "primary_key": ["session_id", "interval_id"],
                    "amendment_groups": [["session_id", "interval_id"]],
                    "references": [
                        {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                        {"columns": ["interval_id"], "resource": "core.intervals", "resource_columns": ["interval_id"]},
                    ],
                    "rules": [],
                },
            }
        },
    }
    intervals = pq.read_table(root / "tables" / "core" / "intervals.parquet")
    rows = {
        "session_id": intervals["session_id"].to_pylist(),
        "interval_id": intervals["interval_id"].to_pylist(),
        "choice": ["left"] * intervals.num_rows,
    }
    if mutate is not None:
        mutate(rows)
    (root / "tables" / "task").mkdir(parents=True, exist_ok=True)
    types = {"session_id": pa.int32(), "interval_id": pa.int32(), "choice": pa.string()}
    table = pa.table({name: pa.array(values, type=types.get(name)) for name, values in rows.items()})
    pq.write_table(table, root / "tables" / "task" / "trials.parquet")
    install_registry(root, document)

    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "task.trials",
            "declaration_id": "task.trials",
            "uri": "tables/task/trials.parquet",
            "digest": owned_digest(root, "tables/task/trials.parquet"),
            "validation_state": "passed",
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def verdicts_of(report, *registries):
    """Return the packet's verdict, then each named registry's."""
    return report.verdict(), *(report.verdict(name) for name in registries)


#: A digest that is no held manifest's.
OTHER_SHA = "0" * 64


def replaced_item(packet_id="session_001", packet_version="0.1.0", sha256=OTHER_SHA, **extra):
    """One entry of a manifest's `replaces`: a packet version, named by its manifest's digest."""
    return {"packet_id": packet_id, "packet_version": packet_version, "sha256": sha256, **extra}


def set_replaces(root, version, *items):
    """Rewrite the packet's manifest at `version`, naming `items` as the packets it replaces."""
    path = root / "packet.json"
    manifest = json.loads(path.read_text()) | {"packet_version": version, "replaces": list(items)}
    path.write_text(json.dumps(manifest, indent=2) + "\n")
