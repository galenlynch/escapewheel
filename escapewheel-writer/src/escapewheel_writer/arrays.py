"""Write a dense array into a packet as Zarr v3.

Part 03 §6.1 requires a packet-owned array to be v3, with a regular chunk grid; v2 is permitted
only for one the packet references. Part 03 §6.2 forbids the `transpose` codec -- axes are stored
in the order the packet declares them, and a column-major binding enumerates them in reverse
rather than the format rearranging itself. Zarr v3 requires the `fill_value` every array is
written with, and Part 03 §6.3 leaves the byte order to the writer, which takes zarr-python's
default.

- :func:`write_zarr` -- write one staged array and return its size on disk in bytes.
- :func:`declared_codecs` -- the codec names an array will be written with, outermost first.
- :func:`shard_for` -- a shard shape whose objects are large enough that a fetch is mostly transfer.
- :func:`target_object_bytes` -- the object size at which a given share of a fetch is transfer.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .errors import UsageError, UsageFault

if TYPE_CHECKING:  # pragma: no cover
    from .bindings import StagedArray

#: Array-to-array codecs, which run before the bytes codec rather than after it. Named as the
#: store names them -- zarr registers numcodecs codecs under a `numcodecs.` prefix, so `delta`
#: would name a codec no stored pipeline carries.
FILTERS = {"numcodecs.delta"}


#: Round-trip latency and single-stream bandwidth of the store a packet will be read from. The
#: defaults are an object store read from outside its region. In-region both improve, which is
#: why these are parameters rather than a constant -- the object size that follows is three
#: times smaller there, and a number baked in here would be wrong in exactly the place the data
#: will live.
DEFAULT_LATENCY_S = 0.034
DEFAULT_BANDWIDTH_BPS = 40e6

#: How much of a fetch should be moving bytes rather than waiting. At 0.9 an object is nine
#: times the bandwidth-delay product; AWS's published 8-16 MB guidance is this share evaluated
#: at ordinary off-region numbers, so the guidance and the arithmetic agree rather than one
#: standing in for the other.
TRANSFER_SHARE = 0.9

#: How far from the target an object may sit and still be accepted, so that a power of two can
#: be preferred without drifting out of the range where a fetch is mostly transfer.
BAND = 1.5

#: The floor is billing, not performance: IA and Glacier Instant Retrieval charge a minimum of
#: 128 KB per object, so chunk-per-object at a few KB is billed at many times its size.
MINIMUM_OBJECT_BYTES = 128 * 1024


def target_object_bytes(
    latency_s: float = DEFAULT_LATENCY_S,
    bandwidth_bps: float = DEFAULT_BANDWIDTH_BPS,
    share: float = TRANSFER_SHARE,
) -> float:
    """Return the object size at which `share` of a fetch is transfer rather than latency.

    Solving `(S/B) / (L + S/B) = share` gives `S = share/(1 - share) * L * B` -- the
    bandwidth-delay product scaled by how much waiting is tolerable. Never below the billing
    floor, since an object smaller than that is charged as if it were that size anyway.
    """
    return max(share / (1 - share) * latency_s * bandwidth_bps, MINIMUM_OBJECT_BYTES)


def shard_for(
    shape: tuple[int, ...],
    chunks: tuple[int, ...],
    compressed_per_chunk: float,
    target_bytes: float | None = None,
) -> tuple[int, ...] | None:
    """Choose a shard that puts one object where a fetch is mostly transfer.

    Grows the slowest-varying axis only, because that is the one a chunk grid divides into
    independent pieces; growing a faster axis would merge chunks a reader asks for separately.
    Returns None when the whole array already fits in one object, since a shard would then add
    an index and nothing else.

    Parameters
    ----------
    shape : tuple of int
        The array's shape.
    chunks : tuple of int
        The chunk shape, chosen as the unit of the question rather than of the file.
    compressed_per_chunk : float
        Bytes a chunk takes once written. Measured, not guessed: it depends on the data.
    target_bytes : float, optional
        Object size to aim for. Defaults to :func:`target_object_bytes` for a store read from
        outside AWS; pass a smaller one for in-region reads, where latency is lower.

    Returns
    -------
    tuple of int or None
        A shard shape, a whole number of chunks on every axis.
    """
    target = target_object_bytes() if target_bytes is None else target_bytes
    along = -(-shape[0] // chunks[0])  # chunks along the slowest axis
    if along * compressed_per_chunk <= target:
        return None

    exact = max(1.0, target / max(compressed_per_chunk, 1))
    # A power of two if one lands inside the band, the exact answer otherwise. The band is
    # what makes this a preference rather than a fudge: the transfer share moves slowly near
    # the target, so a factor of 1.5 either way is still mostly transfer, and a grid that
    # divides evenly is easier to reason about and to align a request against. AWS's own
    # 8-16 MB is a factor of two, so a power of two is generally inside it by construction.
    low = 1 << max(0, int(exact).bit_length() - 1)
    for candidate in sorted((low, low * 2), key=lambda n: abs(n - exact)):
        if target / BAND <= candidate * compressed_per_chunk <= target * BAND:
            per_shard = candidate
            break
    else:
        per_shard = max(1, round(exact))
    return (min(per_shard, along) * chunks[0], *chunks[1:])


def declared_codecs(spec: StagedArray) -> tuple[str, ...]:
    """Return the codec names this array will be written with, outermost first.

    Derived from the layout, not from `codecs` alone, because **sharding is a codec**. An array
    written with a shard uses `sharding_indexed` whether or not the caller named it. The stored
    metadata, not this list, is what Part 03 §6.3 compares with the reader floor.

    Parameters
    ----------
    spec : StagedArray
        The array as it will be written.

    Returns
    -------
    tuple of str
        Codec names, outermost first, excluding the mandatory `bytes` codec.
    """
    inner = tuple(name for name in spec.codecs if name not in {"none", "sharding_indexed"})
    return ("sharding_indexed", *inner) if spec.shard is not None else inner


def _codec(name: str, *, differenced: bool = False) -> Any:
    """Build one bytes-to-bytes codec by the name `StagedArray.codecs` gives it.

    `differenced` says a delta filter runs first, which decides blosc's shuffle. Bit shuffle
    wins where the high bits go constant, and differencing a smooth signal is what makes them
    constant -- so on real waveforms in Part 03 §6.2's layout it is 0.92 MB against byte shuffle's
    0.96 undifferenced, and 0.86 against 0.95 differenced.
    """
    from zarr.codecs import BloscCodec, GzipCodec, ZstdCodec

    if name == "zstd":
        return ZstdCodec()
    if name == "gzip":
        return GzipCodec()
    if name == "blosc":
        # zstd inside blosc: 11.4% smaller than plain zstd on real waveforms, matching the 11%
        # measured on synthetic ephys.
        return BloscCodec(cname="zstd", shuffle="bitshuffle" if differenced else "shuffle")
    raise UsageError(f"{name} is not a bytes codec this writer emits", code=UsageFault.UNKNOWN_CODEC, where=name)


def _filter(name: str, dtype: Any) -> Any:
    """Build one array-to-array codec, which sees values rather than bytes."""
    from numcodecs.zarr3 import Delta

    if name == "numcodecs.delta":
        return Delta(dtype=str(dtype))
    raise UsageError(f"{name} is not an array codec this writer emits", code=UsageFault.UNKNOWN_CODEC, where=name)


def write_zarr(path: Path, spec: StagedArray) -> int:
    """Write one staged array and return its size on disk in bytes.

    Parameters
    ----------
    path : Path
        Where the array goes. Created; an existing one is not overwritten in place.
    spec : StagedArray
        Values and layout.

    Returns
    -------
    int
        Bytes written, for the manifest's `size_bytes`.

    Raises
    ------
    UsageError
        If a declared codec is outside Part 03 §6.3's permitted set, or the shard is not a whole
        number of chunks in every axis -- a partial shard is not a regular grid.
    """
    import zarr
    from zarr.codecs import BytesCodec, ShardingCodec

    filters = [_filter(name, spec.values.dtype) for name in spec.codecs if name in FILTERS]
    inner = [
        _codec(name, differenced=bool(filters))
        for name in spec.codecs
        if name not in {"none", "sharding_indexed", *FILTERS}
    ]
    # A filter runs on values, so it sits before the bytes codec -- inside the shard where
    # there is one, and in zarr's own `filters` argument where there is not.
    pipeline: list[Any] = [*filters, BytesCodec(), *inner]

    if spec.shard is None:
        serializer, grid = BytesCodec(), spec.chunks
        compressors: Any = inner or None
    else:
        misfit = [
            (axis, shard, chunk)
            for axis, (shard, chunk) in enumerate(zip(spec.shard, spec.chunks, strict=True))
            if shard % chunk
        ]
        if misfit:
            raise UsageError(
                f"shard is not a whole number of chunks on axes {[a for a, _, _ in misfit]}",
                code=UsageFault.SHARD_MISFIT,
                where=spec.resource_id,
            )
        # `compressors=None` is load-bearing: zarr applies a default compressor when none is named,
        # and an outer codec over a shard means inflating the whole shard to reach one chunk.
        serializer, grid, compressors = ShardingCodec(chunk_shape=spec.chunks, codecs=pipeline), spec.shard, None

    array = zarr.create_array(
        store=str(path),
        shape=spec.values.shape,
        dtype=spec.values.dtype,
        chunks=grid,
        serializer=serializer,
        compressors=compressors,
        filters=filters if spec.shard is None else None,
        fill_value=spec.fill_value,
        dimension_names=spec.dimension_names,
    )
    array[:] = spec.values
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


__all__ = [
    "BAND",
    "DEFAULT_BANDWIDTH_BPS",
    "DEFAULT_LATENCY_S",
    "FILTERS",
    "MINIMUM_OBJECT_BYTES",
    "TRANSFER_SHARE",
    "declared_codecs",
    "shard_for",
    "target_object_bytes",
    "write_zarr",
]
