"""A Zarr store over a PyArrow filesystem reads what Zarr's own local store reads, and nothing wider."""

import asyncio
import pickle

import numpy as np
import pytest

zarr = pytest.importorskip("zarr")

from pyarrow import fs  # noqa: E402
from zarr.abc.store import OffsetByteRequest, RangeByteRequest, SuffixByteRequest  # noqa: E402
from zarr.core.buffer import default_buffer_prototype  # noqa: E402

from escapewheel_reader.arrow_store import ArrowStore  # noqa: E402

#: Ten bytes whose values are their offsets, so a range's contents name the range.
TEN = bytes(range(10))


@pytest.fixture
def store(tmp_path):
    """A store over `tmp_path/array`, holding one ten-byte key, beside a sibling it must not reach."""
    (tmp_path / "array" / "c").mkdir(parents=True)
    (tmp_path / "array" / "c" / "0").write_bytes(TEN)
    (tmp_path / "array" / "zarr.json").write_text("{}")
    (tmp_path / "sibling").mkdir()
    (tmp_path / "sibling" / "zarr.json").write_text("{}")
    return ArrowStore(fs.LocalFileSystem(), str(tmp_path / "array"))


def _get(store, key, request=None):
    found = asyncio.run(store.get(key, default_buffer_prototype(), request))
    return None if found is None else found.to_bytes()


def test_each_byte_request_reads_the_bytes_it_names(store):
    """Zarr's ranges are half-open; a suffix longer than the key is the whole key, as Zarr's local store reads it."""
    assert _get(store, "c/0") == TEN
    assert _get(store, "c/0", RangeByteRequest(2, 5)) == bytes([2, 3, 4])
    assert _get(store, "c/0", RangeByteRequest(8, 20)) == bytes([8, 9])
    assert _get(store, "c/0", OffsetByteRequest(7)) == bytes([7, 8, 9])
    assert _get(store, "c/0", SuffixByteRequest(3)) == bytes([7, 8, 9])
    assert _get(store, "c/0", SuffixByteRequest(30)) == TEN


def test_an_absent_key_is_none_and_not_an_error(store):
    """Zarr reads an absent chunk as the fill value, so absence must not raise."""
    assert _get(store, "c/1") is None
    assert _get(store, "c/1", RangeByteRequest(0, 2)) is None
    assert asyncio.run(store.exists("c/0"))
    assert not asyncio.run(store.exists("c/1"))


def test_a_write_is_refused(store):
    with pytest.raises(PermissionError, match="read-only"):
        asyncio.run(store.set("c/0", default_buffer_prototype().buffer.from_bytes(b"x")))
    with pytest.raises(PermissionError, match="read-only"):
        asyncio.run(store.delete("c/0"))


def test_listing_stays_inside_the_array(store):
    """A store is rooted at one array, so no listing reaches the prefix beside it."""

    async def collect(listing):
        return sorted([key async for key in listing])

    assert asyncio.run(collect(store.list())) == ["c/0", "zarr.json"]
    assert asyncio.run(collect(store.list_prefix("c/"))) == ["c/0"]
    assert asyncio.run(collect(store.list_dir(""))) == ["c", "zarr.json"]


def test_a_store_pickles_without_its_open_files(store):
    """A dask worker receives the store by pickling, and an open file does not pickle."""
    assert _get(store, "c/0", RangeByteRequest(0, 1)) == b"\x00"
    copy = pickle.loads(pickle.dumps(store))
    assert copy == store
    assert _get(copy, "c/0", RangeByteRequest(1, 2)) == b"\x01"


def test_a_sharded_array_reads_as_through_zarrs_own_store(tmp_path):
    """Sharding reads each shard's index by suffix and its chunks by range, the requests a whole read never makes."""
    path = tmp_path / "sharded.zarr"
    values = np.arange(6 * 4 * 5, dtype="int16").reshape(6, 4, 5)
    zarr.create_array(store=str(path), shape=values.shape, chunks=(1, 4, 5), shards=(3, 4, 5), dtype="int16")[:] = (
        values
    )

    opened = zarr.open_array(ArrowStore(fs.LocalFileSystem(), str(path)), mode="r")

    assert np.array_equal(opened[:], values)
    assert np.array_equal(opened.oindex[[0, 4, 5]], values[[0, 4, 5]])
