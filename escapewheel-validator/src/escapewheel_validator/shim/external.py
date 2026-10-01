"""An external resource against what the manifest claims about it, where a mode asks.

- :func:`resolve_external` -- resolve each external URI and compare its size, members, digests and
  array shape with the manifest's claims.

Nothing here runs by default: resolving a URI reaches a store, and a digest reads every byte.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from typing import Any

from escapewheel_reader import Packet, UnresolvedSource
from escapewheel_reader.resources import ZARR_METADATA_FILENAMES

from .. import check_table, stores
from ..errors import StoreUnreachable
from ..report import Report
from .arrays import ArrayAxes, compare_shape, declared_axes
from .floors import check_zarr_floor
from .owned import route_summary


def resolve_external(
    packet: Packet,
    report: Report,
    checksums: bool = False,
    store_digests: bool = False,
    store_checksums: bool = True,
) -> set[str]:
    """Level 3 (Part 04 §5.3): resolve external URIs and check what was claimed about them.

    Requested explicitly, never by default. Part 04 §5.3 keeps structural validation off the
    network because reachability, credentials and whether the validator is offline are
    properties of the reader's situation rather than of the packet.

    Findings are reported against the resource entry. An unreachable resource is a `warning`
    and not an error: it says the claim could not be checked, which is the same standing the
    default mode gives it, while a claim that resolved and *disagrees* is an error.

    **A check with nothing to compare against is reported, not counted as a pass.** A manifest
    need not record `digest` or `size_bytes`, so either can be absent on a resource that resolves
    cleanly. `external.verified` therefore names what it compared rather than asserting a resource
    was "checked", and a requested digest with nothing to compare gets its own finding.

    Parameters
    ----------
    checksums : bool, default False
        Also establish each recorded `digest` (level 3c). It reads every byte, where the rest of
        this mode is a list operation; off separately for that reason.
    store_digests : bool, default False
        Also compare each declared member's `store_digest` against what the store reports now
        (Part 04 §5.4). The listing already performed carries the values, so this costs what the
        level below it does, and it answers a weaker question than `checksums` does.
    store_checksums : bool, default True
        With `checksums`, take the store's full-object checksums in place of reading an object
        where it reports one in the digest's algorithm (Part 04 §5.3).

    Returns
    -------
    set of str
        The external arrays whose own metadata was read and compared with the reader floor.
    """
    assessed: set[str] = set()
    checked = 0
    compared: Counter[str] = Counter()
    unchecksummed: list[str] = []
    routes: list[tuple[str, str, str]] = []
    # Only read core.array_dimensions where an external array would use it.
    external_arrays = [r for r in packet.resources(kind="dense_array") if r.is_external]
    axes_by_array = declared_axes(packet) if external_arrays else {}
    for resource in packet.resources():
        if not resource.is_external:
            continue
        try:
            uri = packet.location.resolve(resource.uri, resource.source).uri
        except UnresolvedSource as exc:
            # Which sources resolve is the reader's situation (Part 04 §5.5): unreachable, not wrong.
            report.add(
                check_table.EXTERNAL_UNREACHABLE,
                f"{resource.resource_id}: {exc}",
                registry=report.resource_owner(resource.resource_id),
            )
            continue
        fields = _compare_external(
            resource, uri, report, checksums, store_digests, axes_by_array, store_checksums, routes, assessed
        )
        if fields is None:
            continue
        checked += 1
        compared.update(fields)
        if checksums and "digest" not in fields:
            unchecksummed.append(resource.resource_id)
    if unchecksummed:
        report.add(
            check_table.EXTERNAL_NO_CHECKSUM,
            f"{len(unchecksummed)} of {checked} resolved resource(s) record no digest, so a digest "
            "was asked for and nothing was compared against (Part 04 §5.2)",
            [(name,) for name in unchecksummed],
        )
    if checked:
        did = ", ".join(f"{count} {field}" for field, count in sorted(compared.items())) or "nothing"
        established = f"; digest {route_summary(routes)}" if routes else ""
        report.add(
            check_table.EXTERNAL_VERIFIED,
            f"{checked} external resource(s) resolved; compared {did}{established}",
            routes,
        )
    return assessed


def _compare_external(
    resource: Any,
    uri: str,
    report: Report,
    checksums: bool,
    store_digests: bool = False,
    axes_by_array: Mapping[str, ArrayAxes] | None = None,
    store_checksums: bool = True,
    routes: list[tuple[str, str, str]] | None = None,
    assessed: set[str] | None = None,
) -> list[str] | None:
    """Check one external resource, resolved to `uri`, returning the fields actually compared.

    None means the store could not be reached, which is already reported and leaves the resource
    out of every count: nothing about it was established either way. Each digest established is
    appended to `routes` as its resource ID, algorithm, and route, and an array whose metadata was
    compared with the reader floor is added to `assessed`.
    """
    entry = resource.entry
    try:
        found = stores.listing(uri)
    except StoreUnreachable as exc:
        report.add(
            check_table.EXTERNAL_UNREACHABLE,
            f"{resource.resource_id}: {exc}",
            registry=report.resource_owner(resource.resource_id),
        )
        return None
    fields = []
    if (declared := entry.get("members")) is not None:
        fields.extend(_compare_members(resource, declared, found, report, store_digests))
    if (claimed := entry.get("size_bytes")) is not None:
        fields.append("size_bytes")
        if found.size_bytes != claimed:
            report.add(
                check_table.EXTERNAL_SIZE_BYTES,
                f"{resource.resource_id}: {found.size_bytes:,} bytes over {len(found.members)} object(s), "
                f"manifest claims {claimed:,}",
                registry=report.resource_owner(resource.resource_id),
            )
    if resource.kind == "dense_array" and (metadata := _stored_metadata(uri, found)) is not None:
        check_zarr_floor(resource, metadata, report)
        if assessed is not None:
            assessed.add(resource.resource_id)
        if axes_by_array:
            fields.extend(compare_shape(resource, metadata, axes_by_array, report))
    if checksums and isinstance(claimed := entry.get("digest"), Mapping):
        try:
            found_digest = stores.digest_resource(uri, str(claimed["algorithm"]), store_checksums=store_checksums)
        except StoreUnreachable as exc:
            report.add(
                check_table.EXTERNAL_UNREACHABLE,
                f"{resource.resource_id}: {exc}",
                registry=report.resource_owner(resource.resource_id),
            )
            return None
        fields.append("digest")
        if routes is not None:
            routes.append((resource.resource_id, found_digest.algorithm, found_digest.route))
        if found_digest.value != claimed["value"]:
            report.add(
                check_table.EXTERNAL_DIGEST,
                f"{resource.resource_id}: {found_digest.algorithm} gives {found_digest.value[:16]}…, "
                f"manifest records {str(claimed['value'])[:16]}…",
                registry=report.resource_owner(resource.resource_id),
            )
    return fields


def _compare_members(resource: Any, declared: Any, found: Any, report: Report, store_digests: bool) -> list[str]:
    """Check a declared member list against what the store holds (Part 04 §5.4).

    This is what makes level 3a per-member rather than aggregate: `size_bytes` on the resource is
    a total, so two members changing in opposite directions leave it correct. It is also what
    enforces Part 04 §5.4's rule that a digested listing is the declared one -- where the declared
    members and the store agree, Part 04 §4.3's listing is the same either way, so `digest` and
    `members` cannot describe different things.
    """
    fields = ["members"]
    held = {member.key: member for member in found.members}
    claimed = {str(entry.get("key", "")): entry for entry in declared}
    if missing := sorted(claimed.keys() - held.keys()):
        report.add(
            check_table.EXTERNAL_MEMBERS,
            f"{resource.resource_id}: {len(missing)} declared member(s) the store does not hold",
            [(key,) for key in missing[:20]],
            registry=report.resource_owner(resource.resource_id),
        )
    if extra := sorted(held.keys() - claimed.keys()):
        report.add(
            check_table.EXTERNAL_MEMBERS,
            f"{resource.resource_id}: the store holds {len(extra)} member(s) the manifest does not "
            "declare, so a digest over the declared listing would not describe it",
            [(key,) for key in extra[:20]],
            registry=report.resource_owner(resource.resource_id),
        )
    if sized := sorted(
        key
        for key in claimed.keys() & held.keys()
        if claimed[key].get("size_bytes") is not None and claimed[key]["size_bytes"] != held[key].size_bytes
    ):
        report.add(
            check_table.EXTERNAL_MEMBERS,
            f"{resource.resource_id}: {len(sized)} member(s) differ in size from the manifest",
            [(key, claimed[key]["size_bytes"], held[key].size_bytes) for key in sized[:20]],
            registry=report.resource_owner(resource.resource_id),
        )
    if not store_digests:
        return fields
    compared, skipped, changed = 0, [], []
    for key in sorted(claimed.keys() & held.keys()):
        recorded, offered = claimed[key].get("store_digest"), held[key].store_digest
        if not isinstance(recorded, Mapping) or offered is None:
            skipped.append(key)
            continue
        compared += 1
        if str(recorded.get("algorithm")) != offered.algorithm or str(recorded.get("value")) != offered.value:
            changed.append(key)
    if changed:
        report.add(
            check_table.EXTERNAL_STORE_DIGEST,
            f"{resource.resource_id}: {len(changed)} member(s) changed in place since recording",
            [(key,) for key in changed[:20]],
            registry=report.resource_owner(resource.resource_id),
        )
    if skipped:
        report.add(
            check_table.EXTERNAL_NO_STORE_DIGEST,
            f"{resource.resource_id}: {len(skipped)} of {len(claimed)} member(s) not checked -- the "
            "manifest recorded no store digest, or the store offers none (Part 04 §5.4)",
            [(key,) for key in skipped[:20]],
            registry=report.resource_owner(resource.resource_id),
        )
    if compared:
        fields.append("store_digest")
    return fields


def _stored_metadata(uri: str, found: Any) -> Mapping[str, Any] | None:
    """Return the Zarr metadata document under a prefix, or None where there is not one.

    Read through the same store the listing came from, so an object store answers it the way a
    filesystem does. One request either way, and both callers share it.
    """
    # A prefix holding both documents is read as version 2.
    for key in (ZARR_METADATA_FILENAMES[2], ZARR_METADATA_FILENAMES[3]):
        if any(member.key == key for member in found.members):
            try:
                parsed = json.loads(stores.read_member(uri, key))
            except (ValueError, StoreUnreachable):
                return None
            return parsed if isinstance(parsed, Mapping) else None
    return None


__all__: list[str] = []
