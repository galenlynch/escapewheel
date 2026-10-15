"""A packet-owned resource's bytes: its payload's names and the digest the manifest records.

- :func:`check_packet_owned_opaque` -- every opaque payload is present, and its names survive a
  copy to another filesystem.
- :func:`check_owned_sizes` -- every recorded `size_bytes` holds.
- :func:`check_owned_digests` -- every recorded digest holds, where a mode asks for the read.
- :func:`owned_uri` -- where a packet-owned entry's bytes are.
- :func:`route_summary` -- how each digest was established, for a summary finding.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from escapewheel_reader import Packet
from escapewheel_reader.uri import decode

from .. import check_table, stores
from ..errors import ResourceMissing, StoreUnreachable
from ..opaque import describe, findings
from ..report import Report


def check_packet_owned_opaque(packet: Packet, report: Report) -> None:
    """Every packet-owned opaque payload is present, and its names survive a copy (Part 05 §5.3).

    A payload is one file or a directory of them (Part 03 §11), so its listing is all either check
    reads. Its names draw `physical.opaque_name_portability` at `warning` and never fail the packet.
    """
    for resource in packet.resources(kind="opaque"):
        if resource.is_external or resource.source is not None:
            continue
        try:
            found = stores.listing(owned_uri(packet, resource.entry))
        except ResourceMissing as exc:
            report.add_about(
                resource.resource_id,
                check_table.RESOURCE_MISSING,
                f"{resource.resource_id}: {exc}",
            )
            continue
        except StoreUnreachable:
            continue  # a remote packet this validator cannot reach; its digest check reports that
        keys = () if found.is_single_object else [member.key for member in found.members]
        for directory, names, reason in findings(decode(resource.uri), keys):
            report.add_about(
                resource.resource_id,
                check_table.PHYSICAL_OPAQUE_NAME_PORTABILITY,
                describe(resource.resource_id, directory, names, reason),
                [(resource.resource_id, directory, *names)],
            )


def check_owned_sizes(packet: Packet, report: Report) -> None:
    """Every packet-owned resource's recorded `size_bytes` covers the bytes its digest does (Part 03 §10).

    A reader takes a remote table's size from the entry to read its footer first, so a wrong one
    makes the table unreadable. Sizing needs a listing and no read, so this runs on every validation.
    Where nothing is there, or the store cannot be reached, the digest and table checks report it.
    """
    for resource in packet.resources():
        if resource.is_external or resource.source is not None:
            continue
        claimed = resource.entry.get("size_bytes")
        if not isinstance(claimed, int) or isinstance(claimed, bool):
            continue
        try:
            found = stores.listing(owned_uri(packet, resource.entry))
        except (ResourceMissing, StoreUnreachable):
            continue
        if found.size_bytes != claimed:
            report.add_about(
                resource.resource_id,
                check_table.OWNED_SIZE_BYTES,
                f"{resource.resource_id}: holds {found.size_bytes:,} bytes, manifest records {claimed:,}",
            )


def check_owned_digests(packet: Packet, report: Report, store_checksums: bool = True) -> None:
    """Part 04 §5.3, level 2: every packet-owned resource's recorded digest holds.

    A disagreement is an **error**, where the external equivalent is one too but means something
    weaker. An external resource that changed is the world moving under a packet that never
    promised otherwise (Part 03 §8); a packet-owned file that changed is the packet being wrong
    about itself, and it is the premise Part 05 §15.4 spends to bound revalidation.

    An entry recording no digest is `packet.resource.digest_missing`, which the `entries` phase
    reports and which withholds this one. `owned.verified` names each digest's route.
    """
    checked, matched, routes = 0, 0, []
    for resource in packet.resources():
        if resource.is_external:
            continue
        entry = resource.entry
        if not isinstance(claimed := entry.get("digest"), Mapping):
            continue
        try:
            found = stores.digest_resource(
                owned_uri(packet, entry), str(claimed["algorithm"]), store_checksums=store_checksums
            )
        except StoreUnreachable as exc:
            report.add_about(
                resource.resource_id,
                check_table.RESOURCE_MISSING,
                f"{resource.resource_id}: {exc}",
            )
            continue
        checked += 1
        routes.append((resource.resource_id, found.algorithm, found.route))
        if found.value == claimed["value"]:
            matched += 1
        else:
            report.add_about(
                resource.resource_id,
                check_table.OWNED_DIGEST,
                f"{resource.resource_id}: {found.algorithm} gives {found.value[:16]}…, manifest records "
                f"{str(claimed['value'])[:16]}… — a packet-owned resource is immutable (Part 03 §8.1) and "
                "Part 05 §15.4 bounds revalidation on that",
            )
    if checked:
        report.add(
            check_table.OWNED_VERIFIED,
            f"{matched} of {checked} packet-owned resource(s) hold their recorded digest; {route_summary(routes)}",
            routes,
            counts={"checked": checked, "matched": matched},
        )


def owned_uri(packet: Packet, entry: Mapping[str, Any]) -> str:
    """Where a packet-owned entry's bytes are, under the packet's own location."""
    return packet.location.resolve(str(entry.get("uri", ""))).uri


def route_summary(routes: Sequence[tuple[str, str, str]]) -> str:
    """Name how each digest was established (Part 04 §5.3), by resource where the routes differ.

    A finding keeps five rows, so the message carries the route of every digest.
    """
    taken = [route for route in stores.ROUTES if any(row[2] == route for row in routes)]
    if len(taken) == 1:
        return f"route: {taken[0]} for all {len(routes)}"
    return "route: " + "; ".join(
        f"{route} for {', '.join(name for name, _, used in routes if used == route)}" for route in taken
    )


__all__: list[str] = []
