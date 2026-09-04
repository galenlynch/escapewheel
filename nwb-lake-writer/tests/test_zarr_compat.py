"""Zarr v2 arrays decode from their chunk bytes, including the ones zarr-python refuses."""

import numpy as np
import pytest

from nwb_lake_writer.sources.zarr_compat import UnsupportedEncoding, attrs, members, read_array
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
