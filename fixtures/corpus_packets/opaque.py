"""Packets that own an opaque payload."""

import hashlib
from pathlib import Path
from urllib.parse import quote

from .digests import FRAMES
from .record import Build, Expected, Packet
from .registry import EXTENSION
from .session import content
from .writing import digest, edit_manifest, listing, write_packet

#: A fixture-local extension declaring an opaque singleton, which core does not.
QC_EXTENSION = {
    "$schema": EXTENSION["$schema"],
    "registry_id": "qc_documents",
    "registry_version": "0.1.0",
    "logical_standard_version": EXTENSION["logical_standard_version"],
    "rule_language": EXTENSION["rule_language"],
    "extension_id": "qc_documents",
    "resources": {
        "qc_documents.report": {
            "content_class": "extension",
            "kind": "opaque",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
        }
    },
}

#: The keys of `listing_key_spelling`'s payload: each character RFC 8785 escapes differently from
#: a percent-encoder or from `ensure_ascii`, and one below a directory.
SPELLED_KEYS = ['"', "\\", "\n", "\x7f", "\u00e9", "more/\U0001f600"]

#: That payload's listing, written out by hand: RFC 8785's `\"`, `\\`, and `\n`; U+007F, `é`, and
#: U+1F600 as their UTF-8; each digest the CRC32C of the key's own UTF-8.
SPELLED_LISTING = (
    b'[["\\n",1,"399f7b69"],'
    b'["\\"",1,"93fbad78"],'
    b'["\\\\",1,"4e1b4652"],'
    b'["more/\xf0\x9f\x98\x80",9,"bd6a29c1"],'
    b'["\x7f",1,"7df63b78"],'
    b'["\xc3\xa9",2,"1bab8ddc"]]'
)


def owned_opaque(
    out: Path,
    resource_id: str,
    name: str,
    payload,
    *,
    algorithm: str = "sha256",
    declaration_id: str = "core.media_asset_instances",
) -> dict:
    """Publish a payload at `opaque/<resource_id>/<name>` as a build does (Part 03 §11), and
    return its entry.

    `payload` is the bytes of a payload that is one file, or a mapping from each file's path
    within it to its bytes. The `uri` percent-encodes every octet but the unreserved ones in
    uppercase (Part 03 §4), which is what `quote` does with nothing marked safe.
    """
    where = out / "opaque" / resource_id / name
    if isinstance(payload, bytes):
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_bytes(payload)
        value, size = digest(algorithm, payload), len(payload)
    else:
        for key, body in payload.items():
            (where / key).parent.mkdir(parents=True, exist_ok=True)
            (where / key).write_bytes(body)
        rows = [(key, len(body), digest(algorithm, body)) for key, body in payload.items()]
        value = hashlib.sha256(listing(rows)).hexdigest()
        size = sum(len(body) for body in payload.values())
    return {
        "resource_id": resource_id,
        "declaration_id": declaration_id,
        "uri": "/".join(("opaque", quote(resource_id, safe=""), quote(name, safe=""))),
        "validation_state": "not_run",
        "size_bytes": size,
        "digest": {"algorithm": algorithm, "value": value},
    }


def publish(out: Path, *payloads, extensions=()) -> list[dict]:
    """Write `valid` plus each `(resource_id, name, payload, options)` payload, and return their entries."""
    write_packet(out, content(), extensions=extensions)
    entries = [owned_opaque(out, rid, file, body, **options) for rid, file, body, options in payloads]
    edit_manifest(out, lambda m: m["resources"].extend(entries))
    return entries


def owning(*payloads, extensions=()) -> Build:
    """A build of `publish`."""

    def build(out: Path) -> None:
        publish(out, *payloads, extensions=extensions)

    return build


def owned_opaque_encoded_name(out: Path) -> None:
    (entry,) = publish(out, ("core.qc_report", "QC report \u00e9.pdf", b"%PDF-1.7", {}))
    assert entry["uri"] == "opaque/core.qc_report/QC%20report%20%C3%A9.pdf", entry["uri"]


def owned_opaque_one_byte_off(out: Path) -> None:
    publish(out, ("core.clip", "clip.mp4", b"\x00\x00\x00\x18ftypmp42", {}))
    edit_manifest(
        out,
        lambda m: m["resources"][-1]["digest"].update(value=digest("sha256", b"\x00\x00\x00\x18ftypmp43")),
    )


def listing_key_spelling(out: Path) -> None:
    spelled = {key: key.encode("utf-8") for key in SPELLED_KEYS}
    publish(out, ("core.keys", "keys", spelled, {"algorithm": "crc32c"}))
    rows = [(key, len(body), digest("crc32c", body)) for key, body in spelled.items()]
    assert listing(rows) == SPELLED_LISTING, listing(rows)


def misspelt_uri(file: str, uri: str) -> Build:
    """Part 03 §4's one form, broken one way; the file is where the `uri` decodes to, if anywhere."""

    def build(out: Path) -> None:
        publish(out, ("core.clip", file, b"clip", {}))
        edit_manifest(out, lambda m: m["resources"][-1].update(uri=uri))

    return build


#: `é` in NFC and `É` in NFD are one name folded; `12:00:00.png` is one Windows refuses.
PORTABILITY = {"\u00e9.png": b"a", "E\u0301.png": b"b", "12:00:00.png": b"c"}

#: Packet-owned opaque payloads (Part 03 §11): kept names, their `uri`, and their digest.
OPAQUE_PACKETS = (
    Packet(
        "owned_opaque_object",
        owning(("core.clip", "clip.mp4", b"\x00\x00\x00\x18ftypmp42", {})),
        checksums=True,
    ),
    Packet(
        "owned_opaque_prefix",
        owning(
            (
                "core.frames",
                "frames",
                {k.removeprefix("frames/"): v for k, v in FRAMES.items()},
                {},
            )
        ),
        checksums=True,
    ),
    Packet(
        "owned_opaque_singleton",
        owning(
            (
                "qc_documents.report",
                "QC.pdf",
                b"%PDF-1.7",
                {"declaration_id": "qc_documents.report"},
            ),
            extensions=(QC_EXTENSION,),
        ),
        checksums=True,
    ),
    Packet("owned_opaque_encoded_name", owned_opaque_encoded_name, checksums=True),
    Packet("owned_opaque_one_byte_off", owned_opaque_one_byte_off, Expected("error", "owned.digest"), checksums=True),
    Packet(
        "opaque_name_portability",
        owning(("core.frames", "frames", PORTABILITY, {})),
        Expected("warning", "physical.opaque_name_portability", count=2, conforming=True),
        checksums=True,
    ),
    Packet(
        "listing_key_spelling",
        listing_key_spelling,
        Expected("warning", "physical.opaque_name_portability", count=3, conforming=True),
        # Its digest is over keys in raw UTF-8, and a reader that escaped or encoded them would disagree.
        absent=frozenset({"owned.digest", "packet.resource.member_digest"}),
        checksums=True,
    ),
    Packet(
        "uri_raw_space",
        misspelt_uri("cam 1.mp4", "opaque/core.clip/cam 1.mp4"),
        Expected("error", "packet.resource.uri_form"),
    ),
    Packet(
        "uri_lowercase_hex",
        misspelt_uri("QC report \u00e9.pdf", "opaque/core.clip/QC%20report%20%c3%a9.pdf"),
        Expected("error", "packet.resource.uri_form"),
    ),
    Packet(
        "uri_encoded_unreserved",
        misspelt_uri("A.mp4", "opaque/core.clip/%41.mp4"),
        Expected("error", "packet.resource.uri_form"),
    ),
    Packet(
        "uri_dot_segment",
        misspelt_uri("clip.mp4", "opaque/core.clip/../core.clip/clip.mp4"),
        Expected("error", "packet.resource.uri_form"),
    ),
)
