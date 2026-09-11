"""Write a dense array into a packet as Zarr v3.

`03` §6.1 requires a packet-owned array to be v3; v2 is permitted only for one the packet
references. `03` §6.1 pins the rest of the shape: a regular chunk grid, little-endian, an
explicit `fill_value`, and no `transpose` codec -- axes are stored in the order the packet
declares them, and a column-major binding enumerates them in reverse rather than the format
rearranging itself.

Layout, measured
----------------

`conformance/zarr-probe/waveforms.py` ran the combinations against 6,781 real unit waveforms.
Three results shaped what this module does and what it refuses to do:

**The chunk is the unit of the question.** One unit's template reads in 0.6 ms from a
one-unit chunk and 3.9 ms from a 512-unit one. Chunking for the file rather than for the read
costs six times.

**The shard keeps that from meaning one file per chunk.** Sharding turned 6,782 files into 15
for 0.4% more bytes and no loss of speed, which matters most where R14 expects large resources
to live: 6,782 files is 6,782 requests against object storage.

**Object size follows AWS's own guidance, checked against a measurement.** Amazon's S3
performance guidance recommends byte-range fetches of *8-16 MB* for parallel reads, warns that
objects under *128 KB* are billed as 128 KB in Standard-IA, One Zone-IA and Glacier Instant
Retrieval, sets *5 MB* as the smallest multipart part, and suggests multipart above *100 MB*.
Those four numbers bracket the shard: 128 KB is a floor, 100 MB a ceiling, and 8-16 MB the
band to aim at. `target_object_bytes` derives the same band from latency and bandwidth rather
than hardcoding it, because 8-16 MB is that arithmetic evaluated at ordinary off-region
figures and the answer is several times smaller from inside the region.

**The compressor goes inside the shard.** zarr-python applies a default compressor when none
is named, and an outer codec over a shard disables the partial read that sharding exists for
-- the whole shard must be inflated to reach one chunk. Measured at 188 ms against 0.6 ms,
announced only by a warning. `write_zarr` always passes `compressors=None` and puts the codec
in the shard's own pipeline, so the fault cannot be reintroduced by omission.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from .writer import StagedArray

#: `03` §6.4's reader floor: what every conforming reader MUST support. It is a *reader*
#: obligation and not a writer restriction -- `03` §6.4 generalized the declaration to an open
#: one, so "a writer MAY use any Zarr codec; the manifest MUST name it; a reader MUST check
#: before opening an array and fail naming what it lacks." Refusing a codec here would enforce
#: against a writer a floor written for readers, and `escapewheel_reader.Packet.unopenable` is
#: where the check belongs.
FLOOR = {"none", "gzip", "zstd"}

#: Array-to-array codecs, which run before the bytes codec rather than after it. Named as the
#: store names them -- zarr registers numcodecs codecs under a `numcodecs.` prefix, and `04` §5.3
#: compares the manifest against the store, so `delta` and `numcodecs.delta` are not the same
#: claim.
FILTERS = {"numcodecs.delta"}


#: Round-trip latency and single-stream bandwidth of the store a packet will be read from.
#: Measured against `aind-open-data` from outside AWS: fixed latency is 86% of a 128 KB fetch,
#: 73% of 1 MB, 18% of 4 MB, 15% of 8 MB, which puts the round trip at ~34 ms and the stream at
#: ~40 MB/s. In-region on EC2 both improve by roughly an order and a factor, which is why these
#: are parameters rather than a constant -- the object size that follows is three times smaller
#: there, and a number baked in here would be wrong in exactly the place the data will live.
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
    """Return the codec names a manifest must declare for this array, outermost first (`03` §6.4).

    Derived from the layout, not from `codecs` alone, because **sharding is a codec**. An array
    written with a shard uses `sharding_indexed` whether or not the caller named it, and a
    manifest omitting it tells a reader it needs less than it does -- which is the claim R15
    §2 exists to make checkable, and which a reader without sharding support would discover
    only on opening the array.

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
    """Build one bytes-to-bytes codec by the name a manifest declares (`03` §6.4).

    `differenced` says a delta filter runs first, which decides blosc's shuffle. Bit shuffle
    wins where the high bits go constant, and differencing a smooth signal is what makes them
    constant -- so on real waveforms in R3 §5's layout it is 0.92 MB against byte shuffle's
    0.96 undifferenced, and 0.86 against 0.95 differenced.
    """
    from zarr.codecs import BloscCodec, GzipCodec, ZstdCodec

    if name == "zstd":
        return ZstdCodec()
    if name == "gzip":
        return GzipCodec()
    if name == "blosc":
        # zstd inside blosc: 11.4% smaller than plain zstd on real waveforms, matching the 11%
        # R3 §7.3 measured on synthetic ephys.
        return BloscCodec(cname="zstd", shuffle="bitshuffle" if differenced else "shuffle")
    raise ValueError(f"{name} is not a bytes codec this writer emits")


def _filter(name: str, dtype: Any) -> Any:
    """Build one array-to-array codec, which sees values rather than bytes."""
    from numcodecs.zarr3 import Delta

    if name == "numcodecs.delta":
        return Delta(dtype=str(dtype))
    raise ValueError(f"{name} is not an array codec this writer emits")


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
    ValueError
        If a declared codec is outside `03` §6.4's permitted set, or the shard is not a whole
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
            raise ValueError(f"shard is not a whole number of chunks on axes {[a for a, _, _ in misfit]}")
        # `compressors=None` is load-bearing; see the module docstring.
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
    )
    array[:] = spec.values
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


__all__ = [
    "BAND",
    "DEFAULT_BANDWIDTH_BPS",
    "DEFAULT_LATENCY_S",
    "FILTERS",
    "FLOOR",
    "MINIMUM_OBJECT_BYTES",
    "TRANSFER_SHARE",
    "declared_codecs",
    "shard_for",
    "target_object_bytes",
    "write_zarr",
]
