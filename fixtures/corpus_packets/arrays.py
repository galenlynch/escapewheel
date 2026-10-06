"""Zarr arrays for the packets that carry one: their pipelines, catalogue rows and manifest entries."""

import hashlib
import json
from pathlib import Path

from .record import Build
from .session import content
from .writing import digest, edit_manifest, listing, write_packet

#: The reference writer's default and sharded pipelines, both inside the v3 reader floor, and its
#: delta-filtered one, outside it (Part 03 §6.3).
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

#: Part 02 §12.11's numeric form for an axis that is only an order: position k is k.
ORDER_ONLY = {"origin_value": 0.0, "step_value": 1.0, "coordinate_unit": "1"}


def zarr_metadata(codecs: list[dict], shape: tuple = (2, 3), dimension_names: tuple | None = AXES) -> bytes:
    """A Zarr v3 array with no chunk written, so every element is its fill value.

    Its metadata is all a floor assessment or an axis check reads, and the corpus needs no Zarr
    library to write it. Part 03 §6.4 has a packet-owned array name its axes.
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
    """Catalogue one array per name, as `core.<name>`, each axis only an order (Part 02 §12.11)."""
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


#: A waveform-shaped array: two units, a channel axis four positions long, and three samples.
LABELLED_SHAPE = (2, 4, 3)
LABELLED_AXES = ("unit", "channel", "sample")

#: Each unit's contacts along the channel axis. The second unit has two, so its last two
#: positions are padding, which is what the one positive variant holds (Part 02 §12.11).
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
