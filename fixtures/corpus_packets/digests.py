"""Packets about the digests a manifest records."""

import hashlib
from pathlib import Path

from .record import Build, Expected, Packet
from .session import content, variant
from .writing import digest, edit_manifest, listing, write_packet

#: A prefix's objects as a store would list them, for the manifest-only prefix variants.
FRAMES = {"frames/0.png": b"123456789", "frames/1.png": b"frame one"}


def prefix_entry(algorithm: str, members: list[dict]) -> dict:
    """An external image prefix recording `members`, and a `digest` of that listing (Part 04 §4.3).

    Media is declared by catalog, so the entry needs no row; nothing reads the URI.
    """
    body = listing((m["key"], m["size_bytes"], m["digest"]) for m in members if "digest" in m)
    return {
        "resource_id": "core.frames",
        "declaration_id": "core.media_asset_instances",
        "uri": "s3://example-bucket/session/frames",
        "external": True,
        "validation_state": "not_run",
        "size_bytes": sum(m["size_bytes"] for m in members),
        "digest": {
            "algorithm": algorithm,
            "value": hashlib.sha256(body).hexdigest(),
        },
        "members": members,
    }


def framed(algorithm: str) -> list[dict]:
    return [{"key": key, "size_bytes": len(body), "digest": digest(algorithm, body)} for key, body in FRAMES.items()]


def one_byte_off(algorithm: str) -> Build:
    """`valid` under `algorithm`, one table's recorded value being of its file with one byte flipped."""

    def build(out: Path) -> None:
        write_packet(out, content(), algorithm=algorithm)

        def change(manifest):
            # The file itself stays readable.
            entry = next(e for e in manifest["resources"] if e["resource_id"] == "core.intervals")
            body = bytearray((out / entry["uri"]).read_bytes())
            body[len(body) // 2] ^= 0x01
            entry["digest"]["value"] = digest(algorithm, bytes(body))

        edit_manifest(out, change)

    return build


def without_digest(manifest):
    del manifest["resources"][0]["digest"]


def crc_prefix(manifest):
    manifest["resources"].append(prefix_entry("crc32c", framed("crc32c")))


def crc_prefix_disagrees(manifest):
    entry = prefix_entry("crc32c", framed("crc32c"))
    entry["members"][0]["digest"] = digest("crc32c", b"123456780")
    manifest["resources"].append(entry)


def member_digest_partial(manifest):
    members = framed("sha256")
    entry = prefix_entry("sha256", members)
    del members[1]["digest"]
    manifest["resources"].append(entry)


def member_digest_width(manifest):
    entry = prefix_entry("crc64nvme", framed("crc64nvme"))
    entry["members"][0]["digest"] = digest("crc32c", FRAMES["frames/0.png"])
    manifest["resources"].append(entry)


#: Part 04 §4.3's digests: each admitted algorithm passing, and each way one can be wrong.
DIGEST_PACKETS = (
    Packet("crc64nvme", variant(algorithm="crc64nvme"), checksums=True),
    Packet("crc64nvme_one_byte_off", one_byte_off("crc64nvme"), Expected("error", "owned.digest"), checksums=True),
    Packet("crc32c", variant(algorithm="crc32c"), checksums=True),
    Packet("crc32c_one_byte_off", one_byte_off("crc32c"), Expected("error", "owned.digest"), checksums=True),
    Packet("crc32", variant(algorithm="crc32"), checksums=True),
    Packet("crc32_one_byte_off", one_byte_off("crc32"), Expected("error", "owned.digest"), checksums=True),
    Packet(
        "owned_without_digest",
        variant(edit=without_digest),
        Expected("error", "packet.resource.digest_missing"),
    ),
    Packet("crc_prefix", variant(edit=crc_prefix)),
    Packet(
        "crc_prefix_disagrees",
        variant(edit=crc_prefix_disagrees),
        Expected("error", "packet.resource.member_digest"),
    ),
    Packet("member_digest_partial", variant(edit=member_digest_partial), Expected("error", "packet.manifest.schema")),
    Packet("member_digest_width", variant(edit=member_digest_width), Expected("error", "packet.manifest.schema")),
)
