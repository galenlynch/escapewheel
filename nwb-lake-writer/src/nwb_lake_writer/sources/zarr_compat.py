"""Read one-dimensional Zarr v2 arrays out of an NWB-Zarr directory.

AIND writes approximately all of its NWB output as NWB-Zarr (`zarr_format: 2`), and
everything an importer needs from one -- table columns, timestamps, scalar metadata -- is a
one-dimensional array. Decoding those from their chunk bytes with the codecs they declare
takes `numcodecs` and nothing else, so this package depends on neither `zarr`, `hdmf-zarr`,
nor `pynwb`. `07` permits PyNWB at the import boundary; not needing it is better, and it
also sidesteps two faults that make zarr-python 3.3 refuse these files outright. Both are
measured in `inventory/nwb-zarr-776259-2025-04-09.md` §1; neither is exotic, and any reader
of these files meets them:

**vlen-bytes with a numeric fill value.** Four arrays -- ``session_start_time``,
``timestamps_reference_time``, ``file_create_date`` and ``general/subject/date_of_birth`` --
are ``|O`` with ``fill_value: 0`` and a ``vlen-bytes`` filter, and the v2 parser rejects the
fill value:

.. code-block:: text

    TypeError: Invalid type: 0. Expected a string.

The same fault is why the file cannot be opened through its consolidated metadata at all;
these arrays appear in ``.zmetadata``. Decoding from chunk bytes never consults the fill
value, so the fault does not arise here.

**Pickled object references.** ``electrodes/group`` is ``|O`` with an ``object_codec_id`` of
``pickle``, holding `hdmf-zarr` object references. It raises
:class:`UnsupportedEncoding`, which is the right outcome: the pickle holds a reference this
package has no business unpickling, and the same information is in the plain
``group_name`` column beside it.

The multi-dimensional arrays -- waveforms, LFP -- are dense array assets, which R14 says a
packet references rather than copies, so nothing here needs to read them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray


class UnsupportedEncoding(ValueError):
    """An array uses an encoding this package will not decode, such as ``pickle``."""


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
    consulted. Every array this package reads from an NWB is one-dimensional; the
    multi-dimensional ones (waveforms, LFP) are dense arrays, and Phase 5 references them
    rather than reading them.

    Parameters
    ----------
    path : Path
        The array directory.
    limit : int, optional
        Stop after this many values. Only the chunks holding them are decoded, which matters
        where an array is large and the caller wants its head: an LFP series stores 7,983,750
        timestamps and the sampling interval is the first two.

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
        raise UnsupportedEncoding(f"{path} is not a Zarr v2 array")
    if len(meta["shape"]) != 1:
        raise UnsupportedEncoding(f"{path}: rank {len(meta['shape'])}; only 1-D arrays are read here")
    filters = list(meta.get("filters") or [])
    if any(f.get("id") == "pickle" for f in filters):
        raise UnsupportedEncoding(f"{path} is pickled; read the plain column beside it instead")

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
            raise UnsupportedEncoding(f"{path}: chunk {index} is absent and the fill value is not decodable")
        buffer: Any = chunk.read_bytes()
        if compressor is not None:
            buffer = compressor.decode(buffer)
        for codec in reversed(pipeline):
            buffer = codec.decode(buffer)
        pieces.append(np.frombuffer(buffer, dtype=dtype) if not pipeline else np.asarray(buffer))
    return np.concatenate(pieces)[:length]


__all__ = ["UnsupportedEncoding", "attrs", "members", "read_array"]
