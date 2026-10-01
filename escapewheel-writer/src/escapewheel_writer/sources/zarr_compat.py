"""Read Zarr v2 arrays from their chunk bytes, with `numcodecs` and nothing else.

- :func:`read_array` -- a one-dimensional array's values, or its first few.
- :class:`DenseV2` -- a multi-dimensional array, read a slab of rows at a time.
- :func:`members` -- a group's children by name.
- :func:`attrs`, :func:`attrs_at` -- a node's attributes, from its `.zattrs` or the `.zmetadata`.

:func:`read_array` never consults a fill value, so it reads a vlen-bytes array with a numeric one,
which zarr-python refuses. A pickled array raises
:exc:`~escapewheel_writer.errors.UnsupportedEncoding`, and its values are in the plain column
beside it.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..errors import SourceFault, UnsupportedEncoding


def _meta(path: Path) -> dict[str, Any] | None:
    """Read a v2 array's ``.zarray``, or None if the path is not a v2 array."""
    marker = path / ".zarray"
    if not marker.is_file():
        return None
    parsed: dict[str, Any] = json.loads(marker.read_text())
    return parsed


def members(path: Path) -> list[str]:
    """List a group's children by name, sorted.

    A Zarr group is a directory, so its children are its subdirectories. Listing them
    directly also avoids zarr-python's eager member fetch, which raises on the first child it
    cannot parse -- one pickled column would make the whole electrodes table unlistable.

    Parameters
    ----------
    path : Path
        The group directory.

    Returns
    -------
    list of str
        Child names, excluding Zarr's dot-files.
    """
    return sorted(child.name for child in path.iterdir() if not child.name.startswith("."))


def attrs(path: Path) -> dict[str, Any]:
    """Read a node's ``.zattrs``, or an empty mapping if it has none.

    Parameters
    ----------
    path : Path
        The node directory.

    Returns
    -------
    dict
        The attributes.
    """
    marker = path / ".zattrs"
    if not marker.is_file():
        return {}
    parsed: dict[str, Any] = json.loads(marker.read_text())
    return parsed


def attrs_at(root: Path, node: str) -> dict[str, Any]:
    """Read a node's attributes from its own ``.zattrs`` or from the store's ``.zmetadata``.

    A consolidated store need not write a directory per node, and SpikeInterface's does not:
    a `SortingAnalyzer`'s `recording_info` -- which carries the length of the recording that
    was sorted -- exists only inside ``.zmetadata``. Reading one without the other finds
    nothing and reports it as an absent fact rather than an unread one.
    """
    if direct := attrs(root / node):
        return direct
    marker = root / ".zmetadata"
    if not marker.is_file():
        return {}
    consolidated = json.loads(marker.read_text()).get("metadata") or {}
    found: dict[str, Any] = consolidated.get(f"{node}/.zattrs") or {}
    return found


def read_array(path: Path, limit: int | None = None) -> NDArray[Any]:
    """Read a one-dimensional Zarr v2 array, whatever zarr-python makes of it.

    Chunks are decoded with the codecs the array declares, so a numeric ``fill_value`` on a
    vlen-string array -- which zarr-python rejects before it gets that far -- is simply never
    consulted. Every array this package reads from an NWB is one-dimensional; a
    multi-dimensional one is a dense array, which :class:`DenseV2` reads or a packet references.

    Parameters
    ----------
    path : Path
        The array directory.
    limit : int, optional
        Stop after this many values. Only the chunks holding them are decoded, which matters
        where an array is large and the caller wants its head: an LFP series stores a timestamp
        per sample and the sampling interval is the first two.

    Returns
    -------
    numpy.ndarray
        The values, trimmed to the declared shape, or to `limit` where that is smaller.

    Raises
    ------
    UnsupportedEncoding
        If the array is pickled, or is not a one-dimensional v2 array.
    """
    import numcodecs

    meta = _meta(path)
    if meta is None:
        raise UnsupportedEncoding(f"{path} is not a Zarr v2 array", code=SourceFault.NOT_ZARR_V2, where=str(path))
    if len(meta["shape"]) != 1:
        raise UnsupportedEncoding(
            f"{path}: rank {len(meta['shape'])}; only 1-D arrays are read here",
            code=SourceFault.ARRAY_RANK,
            where=str(path),
        )
    filters = list(meta.get("filters") or [])
    if any(f.get("id") == "pickle" for f in filters):
        raise UnsupportedEncoding(
            f"{path} is pickled; read the plain column beside it instead", code=SourceFault.PICKLED, where=str(path)
        )

    compressor = numcodecs.get_codec(meta["compressor"]) if meta.get("compressor") else None
    pipeline = [numcodecs.get_codec(f) for f in filters]
    length, stride = int(meta["shape"][0]), int(meta["chunks"][0])
    dtype = np.dtype(meta["dtype"])
    if limit is not None:
        length = min(length, max(limit, 0))

    if length == 0:  # an empty array, or a caller that asked for nothing
        return np.empty(0, dtype=dtype)

    pieces = []
    for index in range((length + stride - 1) // stride):
        chunk = path / str(index)
        if not chunk.is_file():  # an unwritten chunk is the fill value, which vlen dtypes lack
            raise UnsupportedEncoding(
                f"{path}: chunk {index} is absent and the fill value is not decodable",
                code=SourceFault.FILL_VALUE,
                where=str(path),
            )
        buffer: Any = chunk.read_bytes()
        if compressor is not None:
            buffer = compressor.decode(buffer)
        for codec in reversed(pipeline):
            buffer = codec.decode(buffer)
        pieces.append(np.frombuffer(buffer, dtype=dtype) if not pipeline else np.asarray(buffer))
    return np.concatenate(pieces)[:length]


class DenseV2:
    """A multi-dimensional Zarr v2 array, read a slab of rows at a time.

    The same chunk decoding :func:`read_array` does, over a chunk grid rather than a line of
    chunks. It exists because the one-dimensional reader refuses rank 2 and above, and the
    templates a sorting analyzer holds are rank 3.

    Nothing here is zarr-python, which buys the two things this module exists for. A path is
    only ever asked whether it is a file and for its bytes, so a store path works exactly as a
    local one does -- the sorted assets these are read from are `s3://` prefixes reached through
    a cached `UPath`. And a name with a `#` in it is a path segment rather than a URL fragment,
    which is what SpikeInterface's stream folders are: `...Record Node 109#Neuropix-PXI-100...`.

    Parameters
    ----------
    path : Path
        The array directory, local or on a store.

    Attributes
    ----------
    shape, chunks : tuple of int
        As the array declares them.
    dtype : numpy.dtype
        As the array declares it.
    """

    def __init__(self, path: Any) -> None:
        meta = _meta(path)
        if meta is None:
            raise UnsupportedEncoding(f"{path} is not a Zarr v2 array", code=SourceFault.NOT_ZARR_V2, where=str(path))
        filters = list(meta.get("filters") or [])
        if any(f.get("id") == "pickle" for f in filters):
            raise UnsupportedEncoding(
                f"{path} is pickled; this reader decodes values, not references",
                code=SourceFault.PICKLED,
                where=str(path),
            )
        if len(meta["shape"]) < 2:
            raise UnsupportedEncoding(
                f"{path}: rank {len(meta['shape'])}; read_array reads those",
                code=SourceFault.ARRAY_RANK,
                where=str(path),
            )
        self.path = path
        self.shape = tuple(int(n) for n in meta["shape"])
        self.chunks = tuple(int(n) for n in meta["chunks"])
        self.dtype = np.dtype(meta["dtype"])
        self._order = meta.get("order", "C")
        self._fill = meta.get("fill_value")
        self._separator = meta.get("dimension_separator", ".")
        self._meta = meta
        self._filters = filters

    def __getitem__(self, rows: slice) -> NDArray[Any]:
        """Return rows `[start, stop)` of the slowest axis, whole along every other."""
        start, stop, step = rows.indices(self.shape[0])
        if step != 1:
            raise UnsupportedEncoding(
                f"{self.path}: a strided read is not supported; take a contiguous slab",
                code=SourceFault.STRIDED_READ,
                where=str(self.path),
            )
        held = np.full((max(stop - start, 0), *self.shape[1:]), self._blank(), dtype=self.dtype)
        if stop <= start:
            return held
        first, last = start // self.chunks[0], (stop - 1) // self.chunks[0]
        grid = [range(first, last + 1)]
        grid += [range((n + c - 1) // c) for n, c in zip(self.shape[1:], self.chunks[1:], strict=True)]
        for index in itertools.product(*grid):
            block = self._chunk(index)
            if block is None:
                continue
            # Where this chunk sits in the array, and the part of it the caller asked for.
            begins = [i * c for i, c in zip(index, self.chunks, strict=True)]
            taken, placed = [], []
            for axis, (begin, extent) in enumerate(zip(begins, self.chunks, strict=True)):
                low = max(begin, start) if axis == 0 else begin
                high = min(begin + extent, stop if axis == 0 else self.shape[axis])
                taken.append(slice(low - begin, high - begin))
                placed.append(slice(low - start, high - start) if axis == 0 else slice(low, high))
            held[tuple(placed)] = block[tuple(taken)]
        return held

    def _blank(self) -> Any:
        """Return what an unwritten chunk stands for, or zero where the array declares nothing."""
        return self.dtype.type(0) if self._fill is None else self.dtype.type(self._fill)

    def _chunk(self, index: tuple[int, ...]) -> NDArray[Any] | None:
        """Decode one chunk, or None where it was never written and is therefore the fill."""
        import numcodecs

        chunk = self.path / self._separator.join(str(i) for i in index)
        if not chunk.is_file():
            return None
        buffer: Any = chunk.read_bytes()
        if self._meta.get("compressor"):
            buffer = numcodecs.get_codec(self._meta["compressor"]).decode(buffer)
        for codec in reversed([numcodecs.get_codec(f) for f in self._filters]):
            buffer = codec.decode(buffer)
        return np.frombuffer(buffer, dtype=self.dtype).reshape(self.chunks, order=self._order)


__all__ = ["DenseV2", "attrs", "members", "read_array"]
