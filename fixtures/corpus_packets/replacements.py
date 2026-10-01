"""Packets that name the packets they replace."""

import hashlib

from .record import Build, Expected, Packet
from .session import variant


def replaced(packet_id: str, packet_version: str = "0.1.0", **extra) -> dict:
    """A `replaces` item naming a version whose manifest bytes are the id and version (Part 04 §3)."""
    body = f"{packet_id} {packet_version}".encode()
    digest = hashlib.sha256(body).hexdigest()
    return {"packet_id": packet_id, "packet_version": packet_version, "sha256": digest, **extra}


def replaces(version: str, items: list[dict]) -> Build:
    """`valid` at `version`, naming `items` as the packets it replaces."""
    return variant(edit=lambda manifest: manifest.update(packet_version=version, replaces=items))


#: Part 04 §3's `replaces`: a packet naming the packets it replaces, and each way an item is wrong.
REPLACEMENT_PACKETS = (
    Packet("replaces_own_packet", replaces("1.0.0", [replaced("replaces_own_packet")])),
    Packet("replaces_another_packet", replaces("0.1.0", [replaced("session_000", "3.0.0")])),
    Packet(
        "replaces_same_major",
        replaces("0.1.0", [replaced("replaces_same_major")]),
        Expected("error", "packet.replaces.major_version"),
    ),
    Packet(
        "replaces_item_with_location",
        replaces("1.0.0", [replaced("replaces_item_with_location", uri="../old")]),
        Expected("error", "packet.manifest.schema"),
    ),
    Packet(
        "replaces_item_without_digest",
        replaces("1.0.0", [{"packet_id": "replaces_item_without_digest", "packet_version": "0.1.0"}]),
        Expected("error", "packet.manifest.schema"),
    ),
)
