"""The physical-profile descriptor this package carries, checked once on first use.

- :func:`physical_profile` -- the checked descriptor.
- :func:`interface_for` -- the physical interface for one logical kind.
- :func:`variant_for_zarr_format` -- the descriptor variant a Zarr format version selects.
- :func:`parquet_floor`, :func:`zarr_floor_admits` -- the reader floors (Part 03 §6.4).
- :func:`physical_profile_schema` -- the schema the descriptor is checked against.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import cache
from importlib import resources as importlib_resources
from typing import Any

from .descriptor import check_physical_profile
from .errors import PhysicalProfileError


def _bundled_json(relative: str) -> dict[str, Any]:
    text = importlib_resources.files(__package__).joinpath(relative).read_text()
    value: dict[str, Any] = json.loads(text)
    return value


@cache
def physical_profile_schema() -> dict[str, Any]:
    """Return the bundled reusable descriptor schema."""
    return _bundled_json("schemas/physical_profile.schema.json")


@cache
def physical_profile() -> dict[str, Any]:
    """Return the bundled profile after one cached conformance check."""
    descriptor = _bundled_json("schemas/physical_profiles/escapewheel-portable-v0.1.json")
    errors = check_physical_profile(descriptor, physical_profile_schema())
    if errors:
        raise PhysicalProfileError("; ".join(errors))
    return descriptor


def interface_for(kind: str) -> str | None:
    """Derive the generic physical interface for one checked logical kind."""
    value = physical_profile()["kind_interfaces"].get(kind)
    return str(value) if value is not None else None


def variant_for_zarr_format(format_version: int) -> Mapping[str, Any] | None:
    """Return the descriptor variant selected by format-owned Zarr metadata."""
    variants = physical_profile()["interfaces"]["zarr"]["variants"]
    return next((entry for entry in variants.values() if entry["format_version"] == format_version), None)


def parquet_floor() -> Mapping[str, Any]:
    """Return the incorporated Parquet reader and packet-writer floor."""
    return physical_profile()["interfaces"]["parquet"]["reader_floor"]


def zarr_floor_admits(metadata: Mapping[str, Any], reader_floor: Mapping[str, Any]) -> bool:
    """Whether a Zarr array's own metadata lies within a variant's reader floor (Part 03 §6.4).

    The floor's members drive the comparison, so a restated floor needs no code. A v2 floor lists
    `metadata_patterns`; a v3 floor lists ordered `codec_sequences`, compared with the stored
    pipeline codec by codec, each codec a name or a pattern of name and configuration. The
    pipeline is not flattened: a sharded one is the sharding codec alone, which only a floor with a
    `sharding` member admits. In a pattern null matches only null and an unstated member does not
    participate.

    Parameters
    ----------
    metadata : Mapping
        The parsed `zarr.json` or `.zarray`.
    reader_floor : Mapping
        The `reader_floor` of the variant the metadata's format selects.

    Returns
    -------
    bool
        True where some floor entry admits the array.
    """
    if "metadata_patterns" in reader_floor:
        return any(_matches(metadata, pattern) for pattern in reader_floor["metadata_patterns"])
    pipeline = metadata.get("codecs", ())
    sequences = reader_floor["codec_sequences"]
    if any(_sequence_matches(pipeline, sequence) for sequence in sequences):
        return True
    sharding = reader_floor.get("sharding")
    if sharding is None or len(pipeline) != 1 or _codec(pipeline[0]).get("name") != "sharding_indexed":
        return False
    shard = _codec(pipeline[0]).get("configuration", {})
    return (
        any(_sequence_matches(shard.get("codecs", ()), sequence) for sequence in sequences)
        and any(_sequence_matches(shard.get("index_codecs", ()), s) for s in sharding["index_codec_sequences"])
        # `end` is the sharding codec's own default, so an absent location is not a different one.
        and shard.get("index_location", "end") == sharding["index_location"]
    )


def _codec(entry: str | Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a codec or codec pattern as an object, since Zarr v3 lets a bare name stand for one."""
    return {"name": entry} if isinstance(entry, str) else entry


def _sequence_matches(pipeline: Sequence[Any], sequence: Sequence[Any]) -> bool:
    """Whether a pipeline matches a floor sequence, codec for codec in order."""
    return len(pipeline) == len(sequence) and all(
        _codec(codec).get("name") == _codec(pattern)["name"]
        and _matches(_codec(codec).get("configuration", {}), _codec(pattern).get("configuration", {}))
        for codec, pattern in zip(pipeline, sequence, strict=True)
    )


def _matches(observed: Any, pattern: Any) -> bool:
    """Whether a JSON value matches a pattern: stated members equal, unstated ones ignored."""
    if isinstance(pattern, Mapping):
        return isinstance(observed, Mapping) and all(
            key in observed and _matches(observed[key], value) for key, value in pattern.items()
        )
    if pattern is None:
        return observed is None
    return bool(observed == pattern)
