"""What a source hands the writer to own or to reference: a dense array, an image or a video."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from escapewheel_reader.uri import canonical, is_absolute

from .errors import (
    UsageError,
    UsageFault,
)


@dataclass(frozen=True)
class StagedArray:
    """A dense array to write into the packet, with the layout it should take.

    The chunk should be the unit of the question, the shard keeps that from becoming one file
    per chunk, and the compressor belongs *inside* the shard -- wrapping a shard in an outer
    codec disables the partial read it exists for (`conformance/zarr-probe/waveforms.py`).
    """

    values: Any
    resource_id: str
    #: Empty for an array delivered by name alone, which `add_array` binds by its catalog row.
    declaration_id: str
    array_asset_id: str
    chunks: tuple[int, ...] = ()
    shard: tuple[int, ...] | None = None
    codecs: tuple[str, ...] = ("blosc",)
    fill_value: Any = 0
    #: Each axis's `dimension_name`, in stored order (Part 03 §6.5). Unset, staging takes them
    #: from the axes records this array's catalog row has.
    dimension_names: tuple[str, ...] | None = None
    #: Where an adapter already wrote this array, for one delivered out of process (Part 03
    #: §11.3). Set, the layout above is the array's own and is read back off it rather than
    #: applied: staging moves the directory where it would have written one.
    written: Path | None = None


@dataclass(frozen=True)
class ExternalArray:
    """A dense array the packet references rather than owns (Part 04 §5.1).

    Referencing is the expected form for a large one. Copying duplicates the bulk of a dataset
    for no gain, and transcoding to the portable floor throws away the acquisition's own
    compression.

    `digest`, `size_bytes`, `members` and `verified_at` record what was true when someone
    looked, not a promise about now: immutability covers packet-owned bytes only (Part 03 §8),
    and an external array may change or vanish without the packet changing at all. `digest` is
    Part 04 §4.3's `{"algorithm", "value"}` object.

    `members` is Part 04 §5.4's record of what the prefix held, each entry carrying its own digest
    where the resource records one and the store's entity tag where it offered one. It is a record
    and not a resolution rule -- a reader hands the URI to Zarr, which addresses chunks by key and
    never enumerates.
    """

    array_asset_id: str
    declaration_id: str
    uri: str
    #: Part 04 §5.5: the body of data these bytes belong to. Where set, `uri` is a path relative to
    #: wherever that source turns out to be rather than a location, and a resolution document
    #: says where that is.
    source: str | None = None
    physical_profile: str = "zarr_v3"
    codecs: tuple[str, ...] = ()
    digest: Mapping[str, str] | None = None
    size_bytes: int | None = None
    verified_at: str | None = None
    members: tuple[dict[str, Any], ...] | None = None


@dataclass(frozen=True)
class ExternalMedia:
    """An image or video the packet references rather than owns (Part 04 §5.1).

    The same bargain `ExternalArray` makes, for the same reason: a session's behaviour video is
    larger than everything else it holds, so a packet that copied it would be mostly video.
    What the packet owns instead is the timing -- one row per frame
    in `core.media_frames`, on a declared clock -- which is what makes the video addressable and
    is the part no player can supply.

    `digest`, `size_bytes` and `verified_at` record what was true when someone looked, not a
    promise about now (Part 04 §5.2).
    """

    media_asset_id: str
    declaration_id: str
    uri: str
    format: str = ""
    #: Part 04 §5.5, as on `ExternalArray`.
    source: str | None = None
    digest: Mapping[str, str] | None = None
    size_bytes: int | None = None
    verified_at: str | None = None


@dataclass(frozen=True)
class ExternalResource:
    """An opaque resource the packet references, of a catalog keyed on `resource_id` (Part 04 §5.1).

    No assigned identifier stands between such a catalog's row and its resource, so the resource ID
    a recipe chose binds the row carrying it, as it does a sidecar's (Part 02 §12.10). `digest`,
    `size_bytes` and `verified_at` record what was true when someone looked (Part 04 §5.2).
    """

    declaration_id: str
    uri: str
    #: Part 04 §5.5, as on `ExternalArray`.
    source: str | None = None
    digest: Mapping[str, str] | None = None
    size_bytes: int | None = None
    verified_at: str | None = None


def check_reference(resource_id: str, uri: str, source: str | None) -> str:
    """Return a referenced URI as the manifest records it, refusing one no reader could resolve.

    Relative where the entry names a source, because the source supplies the part in front and an
    absolute URI there would ignore it (Part 04 §5.5). A relative one is a relative reference, which
    the manifest spells in one form (Part 03 §4); without a source it resolves under the packet root,
    which an external resource may (Part 04 §5.1).
    """
    if is_absolute(uri):
        if source is not None:
            raise UsageError(
                f"{resource_id}: {uri!r} is absolute, so naming source {source!r} would have no effect",
                code=UsageFault.SOURCE_ON_ABSOLUTE_URI,
                where=resource_id,
            )
        return uri
    try:
        return canonical(uri)
    except ValueError as exc:
        raise UsageError(
            f"{resource_id}: uri is neither absolute nor a relative reference: {exc} (Part 03 §4)",
            code=UsageFault.URI_UNRESOLVABLE,
            where=resource_id,
        ) from None


__all__ = ["ExternalArray", "ExternalMedia", "ExternalResource", "StagedArray", "check_reference"]
