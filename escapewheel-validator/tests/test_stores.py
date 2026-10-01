"""Part 04 §4.3's digest functions and Part 04 §5.3's store-checksum route."""

import base64
import hashlib
import json
import shutil
from typing import ClassVar

import fsspec
import pytest
from escapewheel_reader import open_packet
from fsspec.implementations.memory import MemoryFileSystem

from escapewheel_validator import validate
from escapewheel_validator.errors import ResourceMissing, StoreUnreachable, UnknownAlgorithm
from escapewheel_validator.stores import (
    crc32c_python,
    crc64nvme_python,
    digest,
    digest_resource,
    hasher,
    listing,
    listing_digest,
    read_member,
    store_checksums,
    store_digest,
)

#: Part 04 §4.3's check values: each function of the nine ASCII bytes `123456789`.
CHECK = {
    "sha256": "15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225",
    "crc64nvme": "ae8b14860a799888",
    "crc32c": "e3069283",
    "crc32": "cbf43926",
}


@pytest.mark.parametrize("algorithm", sorted(CHECK))
def test_each_function_gives_its_check_value_across_blocks(algorithm):
    function = hasher(algorithm)
    for block in (b"1234", b"", b"56789"):
        function.update(block)
    assert function.hexdigest() == CHECK[algorithm]


def test_the_fallbacks_agree_with_the_check_values():
    assert f"{crc64nvme_python(0, b'123456789'):016x}" == CHECK["crc64nvme"]
    assert f"{crc32c_python(0, b'123456789'):08x}" == CHECK["crc32c"]
    assert f"{crc64nvme_python(0, bytes(4096)):016x}" == "6482d367eb22b64e", "an NVM Command Set vector"
    assert crc64nvme_python(0, b"") == 0 and crc32c_python(0, b"") == 0


@pytest.mark.parametrize(("algorithm", "width"), [("crc64nvme", 16), ("crc32c", 8), ("crc32", 8)])
def test_an_empty_object_has_a_zero_crc_of_full_width(algorithm, width):
    assert hasher(algorithm).hexdigest() == "0" * width


def test_an_unadmitted_algorithm_is_refused():
    with pytest.raises(UnknownAlgorithm) as refused:
        hasher("md5")
    assert refused.value.algorithm == "md5"


def test_a_store_value_converts_from_base64_to_hexadecimal():
    assert store_checksums({"ChecksumType": "FULL_OBJECT", "ChecksumCRC64NVME": "rosUhgp5mIg="}) == {
        "crc64nvme": "ae8b14860a799888"
    }
    assert store_checksums({"crc32c": base64.b64encode(bytes.fromhex(CHECK["crc32c"])).decode()}) == {
        "crc32c": CHECK["crc32c"]
    }


@pytest.mark.parametrize(
    "info",
    [
        pytest.param({"ChecksumType": "COMPOSITE", "ChecksumCRC32C": "4waSgw=="}, id="composite"),
        pytest.param({"ChecksumCRC32C": "4waSgw=="}, id="type_unstated"),
        pytest.param({"ChecksumType": "FULL_OBJECT", "ChecksumCRC32C": "4waSgw==-3"}, id="part_count"),
        pytest.param({"ChecksumType": "FULL_OBJECT", "ChecksumCRC32": "AAAAAAAA"}, id="wrong_width"),
    ],
)
def test_a_value_the_store_does_not_report_as_full_object_is_not_taken(info):
    assert store_checksums(info) == {}


def test_a_multipart_entity_tag_is_recorded_verbatim_as_etag():
    """Part 04 §5.4: an entity tag is kept whatever produced it, under `etag` and never another name."""
    tag = '"9b2cf535f27731c974343645a3985328-102"'
    recorded = store_digest({"ETag": tag})
    assert (recorded.algorithm, recorded.value) == ("etag", tag)
    assert store_digest({}) is None


def test_an_empty_prefix_does_not_exist(tmp_path):
    (tmp_path / "empty.zarr").mkdir()
    for uri in (str(tmp_path / "empty.zarr"), str(tmp_path / "absent.zarr")):
        with pytest.raises(ResourceMissing) as refused:
            listing(uri)
        assert (refused.value.uri, refused.value.key) == (uri, None)


def test_a_member_that_cannot_be_read_is_named_by_uri_and_key(tmp_path):
    for uri in (str(tmp_path), "ewabsent://bucket/arr"):
        with pytest.raises(StoreUnreachable) as refused:
            read_member(uri, "zarr.json")
        assert (refused.value.uri, refused.value.key) == (uri, "zarr.json")
        assert not isinstance(refused.value, ResourceMissing)


@pytest.mark.parametrize("algorithm", sorted(CHECK))
def test_a_prefix_value_is_the_sha256_of_its_listing(tmp_path, algorithm):
    store = tmp_path / "a.zarr"
    (store / "c").mkdir(parents=True)
    (store / "zarr.json").write_bytes(b"123456789")
    (store / "c" / "0").write_bytes(b"")
    found = digest_resource(str(store), algorithm)
    empty = hasher(algorithm).hexdigest()
    assert found.members == (empty, CHECK[algorithm]), "in key order, `c/0` before `zarr.json`"
    assert found.value == listing_digest([("zarr.json", 9, CHECK[algorithm]), ("c/0", 0, empty)])
    assert len(found.value) == 64 and found.route == "computed"


#: Part 04 §4.3's listing, written out by hand: RFC 8785, Section 3.2.2.2's escapes for a newline,
#: U+001F, `"`, and `\`; U+007F, `é`, and U+1F600 as their UTF-8; keys sorted by those bytes; sizes as
#: plain integers.
PINNED_LISTING = (
    b'[["a\\nb",1,"11"],'
    b'["a\\u001fb",0,"00"],'
    b'["a\\"b",2,"22"],'
    b'["a\\\\b",3,"33"],'
    b'["a\x7fb",4,"44"],'
    b'["dir/\xc3\xa9",1234567890123,"55"],'
    b'["\xf0\x9f\x98\x80",6,"66"]]'
)


def test_a_listing_writes_its_keys_in_utf8_under_rfc_8785():
    """Part 04 §4.3: a key is its names as they are, never ASCII-escaped or percent-encoded."""
    rows = [
        ("\U0001f600", 6, "66"),
        ("dir/é", 1234567890123, "55"),
        ("a\x7fb", 4, "44"),
        ("a\\b", 3, "33"),
        ('a"b', 2, "22"),
        ("a\x1fb", 0, "00"),
        ("a\nb", 1, "11"),
    ]
    assert hashlib.sha256(PINNED_LISTING).hexdigest() == (
        "4964ea1545c95fea542d2227a1909468728bab0397c49c30d2f338535d873b86"
    )
    assert listing_digest(rows) == "4964ea1545c95fea542d2227a1909468728bab0397c49c30d2f338535d873b86"


def test_a_local_prefix_lists_its_keys_by_name_as_they_are(tmp_path):
    """No percent-encoding and no normalization: an NFC and an NFD name are two keys."""
    store = tmp_path / "payload"
    (store / "dir").mkdir(parents=True)
    names = {"a\nb", "a\x1fb", 'a"b', "a\\b", "a\x7fb", "dir/é", "dir/e\u0301", "\U0001f600", "QC report.pdf"}
    for name in names:
        (store / name).write_bytes(b"x")
    keys = [member.key for member in listing(str(store)).members]
    assert keys == sorted(keys, key=str.encode)
    assert set(keys) == names


class ChecksumMemory(MemoryFileSystem):
    """An object store double whose `info` reports checksums, and which counts what it reads."""

    protocol = ("ewcheck",)
    store: ClassVar[dict] = {}
    pseudo_dirs: ClassVar[list] = [""]
    checksums: ClassVar[dict] = {}
    reads: ClassVar[list] = []

    @classmethod
    def _strip_protocol(cls, path):
        return super()._strip_protocol(path.removeprefix("ewcheck://"))

    def info(self, path, **kwargs):
        found = super().info(path, **kwargs)
        return {**found, **self.checksums.get(self._strip_protocol(path), {})}

    def _open(self, path, mode="rb", **kwargs):
        if "r" in mode:
            self.reads.append(self._strip_protocol(path))
        return super()._open(path, mode, **kwargs)


@pytest.fixture
def object_store():
    fsspec.register_implementation("ewcheck", ChecksumMemory, clobber=True)
    ChecksumMemory.store.clear()
    ChecksumMemory.pseudo_dirs[:] = [""]
    ChecksumMemory.checksums.clear()
    ChecksumMemory.reads.clear()
    filesystem = fsspec.filesystem("ewcheck")
    objects = {"arr/zarr.json": b"123456789", "arr/c/0": b"chunk zero", "arr/c/1": b"chunk one"}
    for key, body in objects.items():
        filesystem.pipe(f"/{key}", body)
    return filesystem, objects


def _report(objects, algorithm, *, keys=None, kind="FULL_OBJECT"):
    """Have the double report `algorithm` for `keys`, computed from the bytes it holds."""
    member = {"crc64nvme": "ChecksumCRC64NVME", "crc32c": "ChecksumCRC32C", "crc32": "ChecksumCRC32"}[algorithm]
    for key in keys or objects:
        function = hasher(algorithm)
        function.update(objects[key])
        value = base64.b64encode(bytes.fromhex(function.hexdigest())).decode()
        ChecksumMemory.checksums[f"/{key}"] = {"ChecksumType": kind, member: value}


def test_store_checksums_establish_a_digest_without_a_read(object_store):
    _, objects = object_store
    _report(objects, "crc64nvme")
    found = digest_resource("ewcheck://arr", "crc64nvme", store_checksums=True)
    assert found.route == "store" and ChecksumMemory.reads == []
    assert found.value == digest("ewcheck://arr", "crc64nvme")


def test_an_object_the_store_reports_nothing_for_is_read(object_store):
    _, objects = object_store
    _report(objects, "crc32c", keys=["arr/c/0"])
    found = digest_resource("ewcheck://arr", "crc32c", store_checksums=True, workers=1)
    assert found.route == "combined"
    assert sorted(ChecksumMemory.reads) == ["/arr/c/1", "/arr/zarr.json"]


def test_a_checksum_in_another_algorithm_is_not_taken(object_store):
    _, objects = object_store
    _report(objects, "crc32")
    assert digest_resource("ewcheck://arr", "crc64nvme", store_checksums=True).route == "computed"


def test_a_composite_checksum_does_not_stand_in_for_a_read(object_store):
    """Part 04 §5.3: a composite value never counts, so level 3c reads the objects."""
    _, objects = object_store
    _report(objects, "crc32c", kind="COMPOSITE")
    found = digest_resource("ewcheck://arr", "crc32c", store_checksums=True, workers=1)
    assert found.route == "computed" and len(ChecksumMemory.reads) == 3


def _external_packet(packet_root, algorithm):
    """Reference the double's prefix from the packet, recording its digest under `algorithm`.

    Its declaration is immaterial here: only level 3's digest comparison is under test.
    """
    manifest = json.loads((packet_root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "core.lfp",
            "declaration_id": "core.clocks",
            "uri": "ewcheck://arr",
            "external": True,
            "validation_state": "not_run",
            "digest": {"algorithm": algorithm, "value": digest("ewcheck://arr", algorithm)},
        }
    )
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    return packet_root


def test_a_report_names_the_store_route(packet_root, object_store):
    _, objects = object_store
    _report(objects, "crc64nvme")
    root = _external_packet(packet_root, "crc64nvme")
    ChecksumMemory.reads.clear()
    report = validate(open_packet(root), external=True, checksums=True)
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert "route: store for all 1" in verified.message
    assert ("core.lfp", "crc64nvme", "store") in verified.rows
    assert ChecksumMemory.reads == []

    ChecksumMemory.checksums.clear()
    report = validate(open_packet(root), external=True, checksums=True)
    assert "route: computed for all 1" in next(f for f in report.findings if f.check == "external.verified").message
    read = validate(open_packet(root), external=True, checksums=True, store_checksums=False)
    assert "external.digest" not in {f.check for f in read.findings}


def test_a_tree_digest_does_not_depend_on_enumeration_order(tmp_path):
    """Part 04 §5.4 sorts the member keys, which is what makes the digest reproducible.

    Two implementations enumerate an object-store prefix and a local directory in different
    orders; a digest that folded them in arrival order would disagree between them.
    """
    prefix = tmp_path / "array.zarr"
    (prefix / "c").mkdir(parents=True)
    for name, body in (("zarr.json", b"{}"), ("c/0", b"aaa"), ("c/1", b"bb"), ("c/2", b"c")):
        (prefix / name).write_bytes(body)
    first = digest(str(prefix))

    # Re-create in the opposite order; the listing the digest is taken over must not care.
    shutil.rmtree(prefix)
    (prefix / "c").mkdir(parents=True)
    for name, body in (("c/2", b"c"), ("c/1", b"bb"), ("c/0", b"aaa"), ("zarr.json", b"{}")):
        (prefix / name).write_bytes(body)
    assert digest(str(prefix)) == first


def test_changing_one_member_changes_the_tree_digest(tmp_path):
    """A digest that missed a chunk edit would make R52's immutability premise unfalsifiable."""
    prefix = tmp_path / "array.zarr"
    prefix.mkdir()
    (prefix / "zarr.json").write_bytes(b"{}")
    (prefix / "chunk").write_bytes(b"aaa")
    before = digest(str(prefix))
    (prefix / "chunk").write_bytes(b"aab")
    assert digest(str(prefix)) != before


def test_adding_a_member_changes_the_tree_digest(tmp_path):
    """Part 04 §5.4: the declared members and the digested listing cannot disagree."""
    prefix = tmp_path / "array.zarr"
    prefix.mkdir()
    (prefix / "zarr.json").write_bytes(b"{}")
    before = digest(str(prefix))
    (prefix / "extra").write_bytes(b"")
    assert digest(str(prefix)) != before
