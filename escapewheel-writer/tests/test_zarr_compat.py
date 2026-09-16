"""Zarr v2 arrays decode from their chunk bytes, including the ones zarr-python refuses."""

import numpy as np
import pytest

from escapewheel_writer.sources.zarr_compat import DenseV2, UnsupportedEncoding, attrs, members, read_array
from tests import nwbfixture


def test_a_numeric_array_reads(tmp_path):
    nwbfixture.array(tmp_path / "a", np.arange(5, dtype=np.int64))
    assert read_array(tmp_path / "a").tolist() == [0, 1, 2, 3, 4]


def test_a_vlen_utf8_array_reads(tmp_path):
    nwbfixture.text(tmp_path / "a", ["one", "two"])
    assert read_array(tmp_path / "a").tolist() == ["one", "two"]


def test_a_vlen_bytes_scalar_reads_despite_its_numeric_fill_value(tmp_path):
    """The encoding zarr-python 3.3 rejects with `Invalid type: 0. Expected a string.`"""
    nwbfixture.array(tmp_path / "a", [b"2025-04-09T17:25:12-07:00"], filter_id="vlen-bytes")
    assert read_array(tmp_path / "a")[0] == b"2025-04-09T17:25:12-07:00"


def test_a_multi_chunk_array_reassembles(tmp_path):
    values = np.arange(10, dtype=np.float64)
    path = nwbfixture.array(tmp_path / "a", values)
    _rechunk(path, values, stride=4)
    assert read_array(path).tolist() == values.tolist()


def test_a_limit_decodes_only_the_chunks_that_hold_it(tmp_path):
    """The saving is the point: an LFP series is 7,983,750 timestamps and callers want two."""
    values = np.arange(10, dtype=np.float64)
    path = nwbfixture.array(tmp_path / "a", values)
    _rechunk(path, values, stride=4)
    (path / "2").unlink()  # a full read would refuse this array; a bounded one never looks
    assert read_array(path, limit=2).tolist() == [0.0, 1.0]
    assert read_array(path, limit=5).tolist() == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_a_limit_past_the_end_is_the_whole_array(tmp_path):
    nwbfixture.array(tmp_path / "a", np.arange(3, dtype=np.int64))
    assert read_array(tmp_path / "a", limit=99).tolist() == [0, 1, 2]


def test_a_limit_of_nothing_reads_nothing(tmp_path):
    nwbfixture.array(tmp_path / "a", np.arange(3, dtype=np.int64))
    empty = read_array(tmp_path / "a", limit=0)
    assert empty.tolist() == [] and empty.dtype == np.int64


def test_a_pickled_array_is_refused_not_unpickled(tmp_path):
    nwbfixture.array(tmp_path / "a", ["<ref>"], filter_id="pickle")
    with pytest.raises(UnsupportedEncoding, match="pickled"):
        read_array(tmp_path / "a")


def test_a_multidimensional_array_is_refused(tmp_path):
    path = nwbfixture.array(tmp_path / "a", np.zeros(4))
    marker = path / ".zarray"
    marker.write_text(marker.read_text().replace('"shape": [4]', '"shape": [2, 2]'))
    with pytest.raises(UnsupportedEncoding, match="rank 2"):
        read_array(path)


def test_a_missing_array_is_refused(tmp_path):
    with pytest.raises(UnsupportedEncoding, match="not a Zarr v2 array"):
        read_array(tmp_path / "absent")


def test_members_lists_children_without_zarrs_dot_files(tmp_path):
    nwbfixture.group(tmp_path / "g", note="hello")
    nwbfixture.array(tmp_path / "g" / "b", np.zeros(1))
    nwbfixture.array(tmp_path / "g" / "a", np.zeros(1))
    assert members(tmp_path / "g") == ["a", "b"]
    assert attrs(tmp_path / "g") == {"note": "hello"}
    assert attrs(tmp_path) == {}


def _dense(path, values, chunks, *, omit=()):
    """Write a rank-N Zarr v2 array as a grid of chunks, edge chunks padded as zarr writes them.

    `omit` leaves those chunks unwritten, which is what zarr does for a chunk that is entirely
    the fill value -- the case a reader has to stand in for rather than fail on.
    """
    import itertools
    import json

    import numcodecs

    path.mkdir(parents=True, exist_ok=True)
    codec = numcodecs.get_codec(nwbfixture.BLOSC)
    (path / ".zarray").write_text(
        json.dumps(
            {
                "zarr_format": 2,
                "shape": list(values.shape),
                "chunks": list(chunks),
                "dtype": values.dtype.str,
                "compressor": nwbfixture.BLOSC,
                "filters": None,
                "fill_value": 0,
                "order": "C",
            }
        )
    )
    grid = [range((n + c - 1) // c) for n, c in zip(values.shape, chunks, strict=True)]
    for index in itertools.product(*grid):
        if index in omit:
            continue
        cut = tuple(slice(i * c, i * c + c) for i, c in zip(index, chunks, strict=True))
        block = np.zeros(chunks, dtype=values.dtype)
        held = values[cut]
        block[tuple(slice(0, n) for n in held.shape)] = held
        (path / ".".join(str(i) for i in index)).write_bytes(codec.encode(block.tobytes()))
    return path


def test_a_dense_array_reads_whole_and_in_slabs(tmp_path):
    """Chunks divide no axis evenly, so every edge chunk is partial in all three."""
    values = np.arange(7 * 5 * 4, dtype=np.float64).reshape(7, 5, 4)
    path = _dense(tmp_path / "a", values, (3, 2, 3))
    held = DenseV2(path)
    assert (held.shape, held.chunks, held.dtype) == ((7, 5, 4), (3, 2, 3), np.dtype("<f8"))
    assert np.array_equal(held[0 : held.shape[0]], values)
    for low, high in ((0, 1), (2, 5), (6, 7), (3, 3)):
        assert np.array_equal(held[low:high], values[low:high]), (low, high)


def test_an_unwritten_chunk_reads_as_the_fill_value(tmp_path):
    """Zarr writes no chunk where one is entirely the fill, so a reader stands in for it."""
    values = np.arange(4 * 4, dtype=np.int16).reshape(4, 4)
    values[2:, 2:] = 0
    path = _dense(tmp_path / "a", values, (2, 2), omit={(1, 1)})
    assert np.array_equal(DenseV2(path)[0:4], values)


def test_a_one_dimensional_array_is_sent_to_read_array(tmp_path):
    """The two readers split on rank, and each says which one the caller wanted."""
    nwbfixture.array(tmp_path / "a", np.arange(3, dtype=np.int64))
    with pytest.raises(UnsupportedEncoding, match="read_array"):
        DenseV2(tmp_path / "a")


def test_a_strided_slab_is_refused(tmp_path):
    """Every caller wants a contiguous block of units, and a stride would quietly mis-place rows."""
    path = _dense(tmp_path / "a", np.zeros((4, 2), dtype=np.int16), (2, 2))
    with pytest.raises(UnsupportedEncoding, match="strided"):
        DenseV2(path)[0:4:2]


def _rechunk(path, values, stride):
    """Rewrite a written array as several chunks, which the fixture never does itself."""
    import json

    import numcodecs

    marker = path / ".zarray"
    meta = json.loads(marker.read_text())
    meta["chunks"] = [stride]
    marker.write_text(json.dumps(meta))
    (path / "0").unlink()
    codec = numcodecs.get_codec(nwbfixture.BLOSC)
    for index in range((len(values) + stride - 1) // stride):
        (path / str(index)).write_bytes(codec.encode(values[index * stride : (index + 1) * stride].tobytes()))
