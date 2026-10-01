"""Validate a packet against the registries it binds (Part 05 §5).

- :func:`validate` -- run every layer over an opened packet and return its :class:`.Report`.
- :func:`check_packet_manifest` -- the manifest and registry-binding phases alone, from the
  manifest's bytes.
- :func:`verify_order` -- pass batches through, raising :exc:`.OrderViolation` where they leave
  their declared order or repeat a key.
- :data:`LIMITS` -- the DuckDB settings :func:`validate` bounds itself by.

The layers run in order: the manifest's shape, the registries the packet binds, each resource's
physical schema, then the rules. Storage is checked in Python and not in SQL, because a query
cannot see how data is stored and a storage check written as SQL passes in silence.
"""

from __future__ import annotations

import contextlib
import itertools
import json
import shutil
import tempfile
from collections import Counter
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from escapewheel_reader import Location, Packet, PacketError, ResourceUnreadableError, UnresolvedSource
from escapewheel_reader.manifest import MANIFEST_FILENAME, Manifest
from escapewheel_reader.ordering import stored_order
from escapewheel_reader.profile import parquet_floor, physical_profile, zarr_floor_admits
from escapewheel_reader.resource_ids import (
    CORE_ARRAY_CHANNELS,
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCKS,
    CORE_SESSIONS,
)
from escapewheel_reader.resources import ZARR_METADATA_FILENAMES
from escapewheel_reader.uri import decode

from . import amendment, check_table, stores
from .check_table import CheckEntry
from .declarations import check_resource_declarations, check_sources
from .errors import OrderFault, OrderViolation, ResourceMissing, StoreUnreachable, _Unmappable
from .generate import Check, Specialisation, adjacency_settles_uniqueness, concerns, generate
from .manifest import (
    Bound,
    Issue,
    bind_registries,
    check_manifest,
    confirm_replaced,
    named_registries,
)
from .opaque import describe, findings
from .registry_document import (
    UCUM_URI,
    CheckedRegistryContext,
    ucum_error,
)
from .registry_types import (
    ARROW_TYPES,
    DDL,
    registry_meta_schema,  # noqa: F401 - `escapewheel_writer.scaffold` imports it from here
    table_contracts,
)
from .report import Report
from .rule_language import PROFILE_ID, RuleProfileError, check_rule
from .vocabulary import EvaluationStatus, Level, RegistryState


def _clock_graph(packet: Packet) -> dict[int, dict[str, Any]]:
    """Each clock's parent and the transform onto it, from `core.clocks`."""
    clocks = packet.table(CORE_CLOCKS)
    names = clocks.column_names
    columns = {c: clocks.column(c).to_pylist() for c in ("parent_clock_id", "transform_slope", "transform_offset")}
    graph: dict[int, dict[str, Any]] = {}
    for row, clock in enumerate(clocks.column("clock_id").to_pylist()):
        graph[clock] = {c: (columns[c][row] if c in names else None) for c in columns}
    return graph


def _ancestry(clock: int, graph: Mapping[int, Mapping[str, Any]]) -> list[int]:
    """Walk from `clock` through its parents to the root, stopping where a cycle repeats."""
    chain = [clock]
    while (parent := graph.get(chain[-1], {}).get("parent_clock_id")) is not None and parent not in chain:
        chain.append(parent)
    return chain


def _step(
    tick: int,
    child: int,
    graph: Mapping[int, Mapping[str, Any]],
    by_clock: Mapping[int, tuple[Any, Any]],
    bound: float,
    *,
    upward: bool,
) -> int:
    """Carry one tick across the edge from `child` to its parent, or back down it."""
    from escapewheel_reader.clocks import align
    from escapewheel_reader.errors import Unanchored

    edge = graph[child]
    if edge["transform_slope"] is not None and edge["transform_offset"] is not None:
        slope, offset = float(edge["transform_slope"]), float(edge["transform_offset"])
        return int(np.rint(offset + slope * tick if upward else (tick - offset) / slope))
    if child not in by_clock:
        raise _Unmappable(f"{child} declares neither a transform nor anchors onto its parent")
    anchor_t, anchor_p = by_clock[child]
    try:
        converted, defined = align(
            np.array([tick], dtype=np.int64),
            *((anchor_t, anchor_p) if upward else (anchor_p, anchor_t)),
            bound=bound,
        )
    except (Unanchored, ValueError) as refused:
        raise _Unmappable(f"{child}'s anchors do not map: {refused}") from refused
    if not defined[0]:
        raise _Unmappable(f"tick {tick} lies beyond the alignment bound of {child}'s anchors")
    return int(converted[0])


def _onto(
    tick: int,
    clock: int,
    reference: int,
    graph: Mapping[int, Mapping[str, Any]],
    by_clock: Mapping[int, tuple[Any, Any]],
    bound: float,
) -> int:
    """Carry a tick from `clock` to `reference` along the parent chain joining them.

    The path climbs from `clock` to the nearest clock it shares with the reference's ancestry, then
    descends to the reference through the inverse of each edge, so a reference that is itself a
    child clock is reached as well as one at the root.
    """
    up, down = _ancestry(clock, graph), _ancestry(reference, graph)
    shared = next((c for c in up if c in down), None)
    if shared is None:
        raise _Unmappable(f"{clock} and {reference} share no ancestor, so no path joins them")
    for child in up[: up.index(shared)]:
        tick = _step(tick, child, graph, by_clock, bound, upward=True)
    for child in reversed(down[: down.index(shared)]):
        tick = _step(tick, child, graph, by_clock, bound, upward=False)
    return tick


def check_time_origin(packet: Packet, report: Report) -> None:
    """Part 05 §5.3: each declared `t_zero_tick` is its session's earliest observation start.

    Not SQL: the minimum is taken across clocks, and carrying a start onto the reference walks the
    parent chain through each clock's anchors or transform, which no query expresses. Each session
    is judged on its own reference clock and alignment bound. A session declaring no origin is not
    checked; one declaring a wrong origin shifts every second a consumer derives.
    """
    from escapewheel_reader.clocks import BOUND, anchors

    try:
        sessions = packet.table(CORE_SESSIONS)
        intervals = packet.table(CORE_CLOCK_OBSERVATION_INTERVALS)
    except PacketError:
        return
    if "t_zero_tick" not in sessions.column_names or not intervals.num_rows:
        return

    def column(table: pa.Table, name: str) -> list[Any]:
        return table.column(name).to_pylist() if name in table.column_names else [None] * table.num_rows

    starts_by_session: dict[Any, list[tuple[int, int]]] = {}
    for session, clock, start in zip(
        column(intervals, "session_id"), column(intervals, "clock_id"), column(intervals, "start_tick"), strict=True
    ):
        if start is not None:
            starts_by_session.setdefault(session, []).append((clock, int(start)))

    try:
        graph, by_clock = _clock_graph(packet), anchors(packet)
    except (PacketError, ValueError):
        graph, by_clock = {}, {}

    for session, stated, reference, bound in zip(
        column(sessions, "session_id"),
        column(sessions, "t_zero_tick"),
        column(sessions, "reference_clock_id"),
        column(sessions, "alignment_bound"),
        strict=True,
    ):
        # Part 01 §2.2 forbids an origin where the session observed nothing; no checker verifies it.
        if stated is None or not (starts := starts_by_session.get(session)):
            continue
        if reference is None:
            report.add(
                check_table.TIME_ORIGIN_UNMAPPABLE,
                f"session {session} declares t_zero_tick but no reference clock to state it on",
                [(str(session),)],
                registry="core",
            )
            continue
        mapped = []
        for clock, start in starts:
            try:
                mapped.append(_onto(start, clock, reference, graph, by_clock, BOUND if bound is None else float(bound)))
            except _Unmappable as refused:
                report.add(
                    check_table.TIME_ORIGIN_UNMAPPABLE,
                    f"session {session}: {clock}'s observation start {start} does not map to {reference}, "
                    f"so no origin is defined ({refused})",
                    [(str(session), str(clock), str(start))],
                    registry="core",
                )
                break
        else:
            expected = min(mapped)
            # A writer's estimator may fit anchors it does not record, so one reference tick of
            # disagreement is rounding rather than a wrong origin.
            if abs(int(stated) - expected) > 1:
                report.add(
                    check_table.TIME_ORIGIN_NOT_EARLIEST,
                    f"session {session} declares t_zero_tick {stated} but its earliest observation start "
                    f"on {reference} is {expected}",
                    [(str(session), str(stated), str(expected))],
                    registry="core",
                )


def _codec_names(pipeline: Iterable[Any]) -> set[str]:
    """Every codec a v3 pipeline names, inside a shard too, where Part 03 §6.2 bans `transpose` as well."""
    names = set()
    for codec in pipeline:
        if isinstance(codec, str):
            names.add(codec)
            continue
        names.add(str(codec.get("name", "")))
        configuration = codec.get("configuration") or {}
        for member in ("codecs", "index_codecs"):
            names |= _codec_names(configuration.get(member) or ())
    return names


def _floor_level(resource: Any) -> Level:
    """`warning` only where a packet-owned resource exceeds a floor its writer is also held to (Part 05 §5.3)."""
    role = physical_profile()["interfaces"][resource.interface]["floor_role"]
    return Level.WARNING if role == "reader_and_packet_writer" and not resource.is_external else Level.INFO


def check_zarr_floor(resource: Any, metadata: Mapping[str, Any], report: Report) -> None:
    """Report an array whose own metadata matches no entry of its variant's reader floor (Part 03 §6.4).

    An unrecognized codec is valid metadata outside the floor, so it draws this finding and nothing else;
    metadata too malformed to compare is upstream invalidity, not a floor observation.
    """
    variants = physical_profile()["interfaces"]["zarr"]["variants"]
    zarr_format = metadata.get("zarr_format")
    selected = next(((name, v) for name, v in variants.items() if v["format_version"] == zarr_format), None)
    if selected is None:
        return
    variant, entry = selected
    try:
        if zarr_floor_admits(metadata, entry["reader_floor"]):
            return
    except (AttributeError, KeyError, TypeError):
        return
    members = ("codecs",) if zarr_format == 3 else ("filters", "compressor")
    observed = [(member, json.dumps(metadata.get(member), separators=(",", ":"))) for member in members]
    report.add(
        check_table.PHYSICAL_OUTSIDE_READER_FLOOR.at(_floor_level(resource)),
        f"{resource.resource_id}: zarr {variant} "
        + "; ".join(f"{member} {value}" for member, value in observed)
        + " is outside the reader floor of Part 03 §6.4",
        observed,
        registry=report.resource_owner(resource.resource_id),
    )


def check_parquet_floor(resource: Any, metadata: Any, report: Report) -> None:
    """Compare a table's footer-reported compressions and encodings with the Parquet floor (Part 03 §5.5)."""
    floor = parquet_floor()
    compressions: set[str] = set()
    encodings: set[str] = set()
    for index in range(metadata.num_row_groups):
        group = metadata.row_group(index)
        for column in range(group.num_columns):
            chunk = group.column(column)
            compressions.add(str(chunk.compression).upper())
            encodings.update(str(value).upper() for value in chunk.encodings)
    observed = [("compression", value) for value in sorted(compressions - set(floor["compressions"]))]
    observed += [("encoding", value) for value in sorted(encodings - set(floor["encodings"]))]
    if observed:
        report.add(
            check_table.PHYSICAL_OUTSIDE_READER_FLOOR.at(_floor_level(resource)),
            f"{resource.resource_id}: parquet "
            + ", ".join(f"{member} {value}" for member, value in observed)
            + " is outside the reader floor of Part 03 §5.5",
            observed,
            registry=report.resource_owner(resource.resource_id),
        )


def _check_one_array(resource: Any, handle: Any, declared: Mapping[str, ArrayAxes], report: Report) -> None:
    """Check one packet-owned array against the metadata document in its own store."""
    try:
        metadata = handle.metadata()
        actual = _codec_names(metadata.get("codecs") or handle.codecs)
        rank = len(handle.shape)
    except (ResourceUnreadableError, OSError, ValueError, KeyError) as exc:
        report.add(
            check_table.ARRAY_UNREADABLE,
            f"{resource.resource_id}: {exc}",
            registry=report.resource_owner(resource.resource_id),
        )
        return

    if handle.zarr_format != 3:
        report.add(
            check_table.ARRAY_NOT_ZARR_V3,
            f"{resource.resource_id} is packet-owned but stored as Zarr v{handle.zarr_format}; "
            "Part 03 §6.1 allows v2 only for an array the packet references",
            registry=report.resource_owner(resource.resource_id),
        )

    if "transpose" in actual:
        report.add(
            check_table.ARRAY_TRANSPOSE_CODEC,
            f"{resource.resource_id} uses the transpose codec, which Part 03 §6.2 forbids: axes are stored in the "
            "order the packet declares them",
            registry=report.resource_owner(resource.resource_id),
        )

    check_zarr_floor(resource, metadata, report)

    if (grid := metadata.get("chunk_grid", {}).get("name")) != "regular":
        report.add(
            check_table.ARRAY_IRREGULAR_CHUNK_GRID,
            f"{resource.resource_id} declares a {grid!r} chunk grid; Part 03 §6.1 requires a regular one",
            registry=report.resource_owner(resource.resource_id),
        )

    if "fill_value" not in metadata:
        report.add(
            check_table.ARRAY_NO_FILL_VALUE,
            f"{resource.resource_id} declares no fill_value, which Part 03 §6.1 requires",
            registry=report.resource_owner(resource.resource_id),
        )

    if (axes := declared.get(resource.resource_id)) is None:
        return
    shape = [int(n) for n in handle.shape]
    if set(axes.names) != set(range(rank)):
        report.add(
            check_table.ARRAY_RANK_DISAGREES_WITH_DIMENSIONS,
            f"{resource.resource_id} has rank {rank} but its declaration-selected axes resource "
            f"gives axis_index {sorted(axes.names) or 'none'}; Part 03 §6.3 requires one row per stored axis",
            registry=report.resource_owner(resource.resource_id),
        )
        return
    _report_axes(resource, shape, axes, _OWNED_AXIS_CHECKS, report)
    names = [axes.names[axis] for axis in range(rank)]
    if metadata.get("dimension_names") != names:
        report.add(
            check_table.ARRAY_DIMENSION_NAMES,
            f"{resource.resource_id} stores dimension_names {metadata.get('dimension_names')!r} where its axes "
            f"resource names {names!r}; Part 03 §6.5 requires a packet-owned array to carry them",
            registry=report.resource_owner(resource.resource_id),
        )


def check_packet_owned_arrays(packet: Packet, report: Report) -> None:
    """Layer 1c: every packet-owned array against its own Zarr metadata (Part 04 §5.3, level 2).

    Always runs, and needs no Zarr: a Zarr array's metadata is a JSON document in the store,
    which `ArrayResource` parses directly. The packet owns these bytes, so an array it
    describes wrongly is a defect in the packet rather than in the reader's situation. An
    external array is level 3 and stays with the requested mode, and `report_unassessed` reports it
    where that mode did not read it.

    Storage, not values, so the shim and not SQL (R12 §4): no query can see a chunk grid or a codec
    pipeline.
    """
    # A resource naming a source is not packet-owned whatever `external` says, and `check_sources`
    # has already reported the contradiction; resolving it here would raise instead of report.
    owned = [r for r in packet.resources(kind="dense_array") if not r.is_external and r.source is None]
    if not owned:
        return
    declared = declared_axes(packet)
    if not declared:
        report.add(
            check_table.ARRAY_NO_ARRAY_DIMENSIONS_TABLE,
            f"{len(owned)} packet-owned array(s) but no declaration-selected axes rows were resolved",
        )
    for resource in owned:
        try:
            stores.listing(owned_uri(packet, resource.entry))
        except ResourceMissing as exc:
            report.add(
                check_table.RESOURCE_MISSING,
                f"{resource.resource_id}: {exc}",
                registry=report.resource_owner(resource.resource_id),
            )
            continue
        except StoreUnreachable:
            pass  # `_check_one_array` reports what it cannot read
        _check_one_array(resource, packet.array_resource(resource.resource_id), declared, report)


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
            report.add(
                check_table.RESOURCE_MISSING,
                f"{resource.resource_id}: {exc}",
                registry=report.resource_owner(resource.resource_id),
            )
            continue
        except StoreUnreachable:
            continue  # a remote packet this validator cannot reach; its digest check reports that
        keys = () if found.is_single_object else [member.key for member in found.members]
        for directory, names, reason in findings(decode(resource.uri), keys):
            report.add(
                check_table.PHYSICAL_OPAQUE_NAME_PORTABILITY,
                describe(resource.resource_id, directory, names, reason),
                [(resource.resource_id, directory, *names)],
                registry=report.resource_owner(resource.resource_id),
            )


def report_unassessed(packet: Packet, assessed: Collection[str], report: Report) -> None:
    """One `info` finding per external resource with a reader floor whose own metadata was not read (Part 05 §5.3)."""
    for resource in packet.resources():
        if resource.is_external and resource.interface is not None and resource.resource_id not in assessed:
            report.add(
                check_table.EXTERNAL_PHYSICAL_UNASSESSED,
                f"{resource.resource_id}: its {resource.interface} metadata was not read, so its physical "
                "version, codecs, compression and encodings are unassessed",
                [(resource.resource_id,)],
                registry=report.resource_owner(resource.resource_id),
            )


def report_page_types_unassessed(tables: int, report: Report) -> None:
    """Part 03 §5.5: a validator comparing only footers states that it did not assess data-page types."""
    if tables:
        report.add(
            check_table.PHYSICAL_PAGE_TYPES_UNASSESSED,
            f"{tables} Parquet footer(s) compared with the floor's compressions and encodings; data-page "
            "types were not assessed, since they are recorded in page headers",
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
            report.add(
                check_table.RESOURCE_MISSING,
                f"{resource.resource_id}: {exc}",
                registry=report.resource_owner(resource.resource_id),
            )
            continue
        checked += 1
        routes.append((resource.resource_id, found.algorithm, found.route))
        if found.value == claimed["value"]:
            matched += 1
        else:
            report.add(
                check_table.OWNED_DIGEST,
                f"{resource.resource_id}: {found.algorithm} gives {found.value[:16]}…, manifest records "
                f"{str(claimed['value'])[:16]}… — a packet-owned resource is immutable (Part 03 §8.1) and "
                "Part 05 §15.4 bounds revalidation on that",
                registry=report.resource_owner(resource.resource_id),
            )
    if checked:
        report.add(
            check_table.OWNED_VERIFIED,
            f"{matched} of {checked} packet-owned resource(s) hold their recorded digest; {route_summary(routes)}",
            routes,
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


@dataclass
class ArrayAxes:
    """What a packet's tables assert about one dense array's axes (Part 03 §6.3).

    Keyed by stored `axis_index`. `labels` holds each labelled axis's rows as
    (`depends_on_position_index`, `position_index`), and `channels` holds `core.array_channels`
    rows as (`axis_index`, `channel_index`).
    """

    names: dict[int, Any] = field(default_factory=dict)
    depends: dict[int, int] = field(default_factory=dict)
    labelled: set[int] = field(default_factory=set)
    labels: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    channels: list[tuple[int, int]] = field(default_factory=list)


def _rows_by_array(
    packet: Packet, table_id: str, key: Sequence[str], columns: Sequence[str], cache: dict[Any, Any]
) -> dict[tuple[Any, ...], list[tuple[Any, ...]]]:
    """Read a table once and group the named columns by the array key, or return {} if unreadable."""
    if (table_id, tuple(key), tuple(columns)) in cache:
        return cache[table_id, tuple(key), tuple(columns)]
    grouped: dict[tuple[Any, ...], list[tuple[Any, ...]]] = {}
    try:
        present = set(packet.table_resource(table_id).schema().names)
        wanted = [*key, *(c for c in columns if c in present)]
        rows = packet.table(table_id, columns=list(dict.fromkeys(wanted)))
    except (PacketError, OSError, pa.ArrowException):
        cache[table_id, tuple(key), tuple(columns)] = grouped
        return grouped
    values = [rows.column(c).to_pylist() if c in rows.column_names else [None] * rows.num_rows for c in columns]
    for row in zip(*(rows.column(c).to_pylist() for c in key), *values, strict=True):
        grouped.setdefault(tuple(row[: len(key)]), []).append(tuple(row[len(key) :]))
    cache[table_id, tuple(key), tuple(columns)] = grouped
    return grouped


def declared_axes(packet: Packet) -> dict[str, ArrayAxes]:  # noqa: C901
    """Resolve each dense array's axes, labels and channels through its declaration and catalog row.

    The label rows are in the table the axes table's `coordinate_resource` names as its
    `discriminates_via` (Part 03 §6.3); they and `core.array_channels` reach the array through their
    reference to the axes table.
    """
    declarations: dict[str, Mapping[str, Any]] = {}
    for document in (packet.registry, *packet.extensions().values()):
        if isinstance(document, Mapping):
            declarations.update(document.get("resources", {}))

    cache: dict[Any, Any] = {}
    found: dict[str, ArrayAxes] = {}
    for resource in packet.resources(kind="dense_array"):
        declaration = declarations.get(resource.declaration_id)
        if declaration is None:
            continue
        instances = declaration["instances"]
        catalog_id = str(instances["catalog_resource"])
        resource_column = str(instances["resource_id_column"])
        axes_id = str(declaration["array"]["axes_resource"])
        catalog_declaration = declarations.get(catalog_id)
        axes_declaration = declarations.get(axes_id)
        if catalog_declaration is None or axes_declaration is None:
            continue
        catalog_key = list(catalog_declaration["table"]["primary_key"] or [])
        axes_table = axes_declaration["table"]
        binding = next(
            (
                reference
                for reference in axes_table["references"]
                if reference["resource"] == catalog_id and reference["resource_columns"] == catalog_key
            ),
            None,
        )
        if binding is None:
            continue
        catalog = _rows_by_array(packet, catalog_id, [resource_column], catalog_key, cache)
        if not (keys := catalog.get((resource.resource_id,))):
            continue
        wanted_key = keys[0]
        axes = ArrayAxes()
        extra = ["axis_index", "dimension_name", "coordinate_resource", "depends_on_axis_index"]
        for axis, name, coordinate, depends in _rows_by_array(packet, axes_id, binding["columns"], extra, cache).get(
            wanted_key, []
        ):
            if axis is None:
                continue
            axes.names[int(axis)] = name
            if coordinate is not None:
                axes.labelled.add(int(axis))
            if depends is not None:
                axes.depends[int(axis)] = int(depends)
        if not axes.names:
            continue
        found[resource.resource_id] = axes

        labels_id = next(
            (
                str(c["discriminates_via"]).rsplit(".", 1)[0]
                for c in axes_table["columns"]
                if c["name"] == "coordinate_resource" and c.get("discriminates_via")
            ),
            None,
        )
        for table_id, columns in (
            (labels_id, ["depends_on_position_index", "position_index"]),
            (CORE_ARRAY_CHANNELS, ["channel_index"]),
        ):
            table = (declarations.get(table_id or "") or {}).get("table")
            reference = next(
                (r for r in (table or {}).get("references", []) if r["resource"] == axes_id),
                None,
            )
            if reference is None:
                continue
            mapped = dict(zip(reference["resource_columns"], reference["columns"], strict=True))
            if "axis_index" not in mapped or not set(binding["columns"]) <= set(mapped):
                continue
            key = [mapped[c] for c in binding["columns"]]
            rows = _rows_by_array(packet, str(table_id), key, [mapped["axis_index"], *columns], cache)
            for row in rows.get(wanted_key, []):
                if any(value is None for value in row):
                    continue
                if table_id == labels_id:
                    axes.labels.setdefault(int(row[0]), []).append((int(row[1]), int(row[2])))
                else:
                    axes.channels.append((int(row[0]), int(row[1])))
    return found


#: Examples a finding carries per axis, so a wholly unlabelled axis does not list every position.
_EXAMPLES = 20


class _AxisFault(Enum):
    """One way an array's label and channel rows disagree with its shape (Part 03 §6.3)."""

    LABEL_POSITION = auto()
    DEPENDS_ON_POSITION = auto()
    LABEL_MISSING = auto()
    CHANNEL_INDEX = auto()


def _axis_findings(shape: Sequence[int], axes: ArrayAxes) -> dict[_AxisFault, list[tuple[Any, ...]]]:
    """Compare one array's shape with its label and channel rows, by fault (Part 03 §6.3)."""
    length = dict(enumerate(shape))
    found: dict[_AxisFault, list[tuple[Any, ...]]] = {fault: [] for fault in _AxisFault}
    for axis in sorted(axes.labelled | set(axes.labels)):
        if axis not in length:
            continue
        outer = axes.depends.get(axis)
        outer_length = length.get(outer, 0) if outer is not None else None
        seen: set[tuple[int, int]] = set()
        for depends_on, position in axes.labels.get(axis, []):
            if not 0 <= position < length[axis]:
                found[_AxisFault.LABEL_POSITION].append(
                    (f"axis_index {axis}", f"position_index {position}", f"length {length[axis]}")
                )
            elif outer_length is not None and not 0 <= depends_on < outer_length:
                found[_AxisFault.DEPENDS_ON_POSITION].append(
                    (f"axis_index {axis}", f"depends_on_position_index {depends_on}", f"length {outer_length}")
                )
            else:
                seen.add((depends_on if outer_length is not None else 0, position))
        if axis not in axes.labelled:
            continue
        outer_positions = outer_length if outer_length is not None else 1
        # `seen` holds only in-range pairs, and the key makes each unique, so the count is exact.
        if not (missing := outer_positions * length[axis] - len(seen)):
            continue
        pairs = itertools.product(range(outer_positions), range(length[axis]))
        for depends_on, position in itertools.islice((p for p in pairs if p not in seen), _EXAMPLES):
            where = f"position_index {position}"
            if outer_length is not None:
                where = f"depends_on_position_index {depends_on}, {where}"
            found[_AxisFault.LABEL_MISSING].append((f"axis_index {axis}", where, f"{missing} missing"))
    for axis, channel in axes.channels:
        if axis in length and not 0 <= channel < length[axis]:
            found[_AxisFault.CHANNEL_INDEX].append(
                (f"axis_index {axis}", f"channel_index {channel}", f"length {length[axis]}")
            )
    return found


_AXIS_MESSAGES = {
    _AxisFault.LABEL_POSITION: "label row(s) name a position_index beyond the axis (Part 03 §6.3)",
    _AxisFault.DEPENDS_ON_POSITION: (
        "label row(s) name a depends_on_position_index beyond the axis depended on (Part 03 §6.3)"
    ),
    _AxisFault.LABEL_MISSING: "position(s) of a labelled axis have no label row (Part 03 §6.3)",
    _AxisFault.CHANNEL_INDEX: "core.array_channels row(s) name a channel_index beyond their axis (Part 05 §5.3)",
}

#: The check each fault of a packet-owned array is reported under.
_OWNED_AXIS_CHECKS = {
    _AxisFault.LABEL_POSITION: check_table.ARRAY_LABEL_POSITION_OUT_OF_RANGE,
    _AxisFault.DEPENDS_ON_POSITION: check_table.ARRAY_DEPENDS_ON_POSITION_OUT_OF_RANGE,
    _AxisFault.LABEL_MISSING: check_table.ARRAY_LABEL_MISSING,
    _AxisFault.CHANNEL_INDEX: check_table.ARRAY_CHANNEL_INDEX_OUT_OF_RANGE,
}

#: The check each fault of an external array is reported under.
_EXTERNAL_AXIS_CHECKS = {
    _AxisFault.LABEL_POSITION: check_table.EXTERNAL_ARRAY_LABEL_POSITION_OUT_OF_RANGE,
    _AxisFault.DEPENDS_ON_POSITION: check_table.EXTERNAL_ARRAY_DEPENDS_ON_POSITION_OUT_OF_RANGE,
    _AxisFault.LABEL_MISSING: check_table.EXTERNAL_ARRAY_LABEL_MISSING,
    _AxisFault.CHANNEL_INDEX: check_table.EXTERNAL_ARRAY_CHANNEL_INDEX_OUT_OF_RANGE,
}


def _report_axes(
    resource: Any, shape: Sequence[int], axes: ArrayAxes, entries: Mapping[_AxisFault, CheckEntry], report: Report
) -> None:
    """Report each way an array's label and channel rows disagree with its shape, under its entry of `entries`."""
    for fault, rows in _axis_findings(shape, axes).items():
        if rows:
            report.add(
                entries[fault],
                f"{resource.resource_id}: {_AXIS_MESSAGES[fault]}",
                rows,
                registry=report.resource_owner(resource.resource_id),
            )


def compare_shape(
    resource: Any, metadata: Mapping[str, Any], declared: Mapping[str, ArrayAxes], report: Report
) -> list[str]:
    """Check an external array's stored shape against what the packet's tables assert (Part 03 §6.3).

    This is the check that catches a change actually invalidating the packet. A re-generated
    array with a different channel count leaves its label rows naming positions that are not
    there, or positions with none; neither changes what the packet claims about the array's
    values, which is why this and not a content digest is what an external array needs verified.

    Cheap: one request for the metadata document the array's store already holds.
    """
    if (axes := declared.get(resource.resource_id)) is None or not axes.names:
        return []
    if not isinstance(shape := metadata.get("shape"), list):
        return []
    if set(axes.names) != set(range(len(shape))):
        report.add(
            check_table.EXTERNAL_ARRAY_RANK,
            f"{resource.resource_id} is stored with rank {len(shape)} but its declaration-selected "
            f"axes resource gives axis_index {sorted(axes.names)}; Part 03 §6.3 requires one row per stored axis",
            registry=report.resource_owner(resource.resource_id),
        )
        return ["rank"]
    _report_axes(resource, [int(n) for n in shape], axes, _EXTERNAL_AXIS_CHECKS, report)
    return ["rank", *(["labels"] if axes.labelled else []), *(["channels"] if axes.channels else [])]


def check_schemas(packet: Packet, tables: Mapping[str, Any], report: Report) -> dict[str, Any]:
    """Layer 2: column presence and physical type, which SQL cannot see (R12 §4)."""
    declared = {r.resource_id for r in packet.resources()}
    present: dict[str, Any] = {}
    for resource_id, spec in tables.items():
        if resource_id not in declared:
            continue  # a packet need not carry every table
        handle = packet.table_resource(resource_id)
        try:
            schema = handle.schema()
        except PacketError as exc:
            report.add(check_table.RESOURCE_MISSING, str(exc), registry=report.resource_owner(resource_id))
            continue
        present[resource_id] = handle
        for column in spec["columns"]:
            _check_column(resource_id, column, schema, report)
        path, filesystem = (handle.path, None) if handle.is_local else handle.location.store()
        try:
            footer = pq.read_metadata(path, filesystem=filesystem)
        except (OSError, pa.ArrowException):
            continue  # an unreadable footer leaves the floor unassessed, not failed (Part 05 §9.4)
        check_parquet_floor(handle.resource, footer, report)
    return present


def _check_column(resource_id: str, column: Mapping[str, Any], schema: Any, report: Report) -> None:
    """Check one column's presence and type against the registry."""
    if column["name"] not in schema.names:
        if column["presence"] != "optional":
            report.add(
                check_table.SCHEMA_COLUMN_ABSENT,
                f"{resource_id}.{column['name']} absent (presence={column['presence']})",
                registry=report.resource_owner(resource_id),
            )
        return
    actual = schema.field(column["name"]).type
    # A dictionary is an encoding, not a type. Parquet has no dictionary type at all: the column
    # is BYTE_ARRAY/String either way, and only the Arrow schema pyarrow stores as metadata
    # distinguishes them. Comparing the wrapper would reject a conforming file over how its
    # writer chose to hold the column, which is the storage-versus-meaning line R12 §4 draws.
    if pa.types.is_dictionary(actual):
        actual = actual.value_type
    if str(actual) != ARROW_TYPES[column["type"]]:
        report.add(
            check_table.SCHEMA_COLUMN_TYPE,
            f"{resource_id}.{column['name']} is {actual}, registry declares {column['type']}",
            registry=report.resource_owner(resource_id),
        )


#: Rows per batch when checking physical order, and how many breaks are worth reporting.
#: Read whole, a spike table's sort columns are a Python object per row and column, which at
#: hundreds of millions of rows will take a workstation down. Batched, peak memory is this many
#: rows however large the table, and a reader only needs to see that the order broke and where
#: it first did.
ORDER_BATCH = 1 << 20
ORDER_REPORT = 20


def _row_at(batch: Any, keys: Sequence[str], offset: int) -> tuple[Any, ...]:
    """Pull one row of the sort key out of a batch, as Python values."""
    return tuple(batch.column(key)[offset].as_py() for key in keys)


def _sortable(row: Sequence[Any]) -> tuple[tuple[bool, Any], ...]:
    """Render a row as its sort key, with null ordering first and consistently."""
    return tuple((v is None, v) for v in row)


def _ranked(column: Any) -> Any:
    """Replace a dictionary column by its values' rank in sort order; leave any other alone.

    Codes cannot be compared -- a dictionary is unordered -- but the rank of each code's value
    can, and that is the same comparison over int32 rather than strings. Ranking is a few
    hundred dictionary entries beside a batch of a hundred thousand rows, so it is free:
    measured on 131,072 rows, 0.147 ms a column against 0.682 decoded to strings and 2.369
    handing the dictionary to Arrow, which decodes both sides on every call.
    """
    if not pa.types.is_dictionary(column.type):
        return column
    values = column.dictionary
    # argsort of argsort is the rank. Nulls sort last here and must stay null rather than
    # become the largest value, since the comparison below gives them their own ordering.
    rank = pc.sort_indices(pc.sort_indices(values))
    rank = pc.if_else(pc.is_null(values), pa.scalar(None, rank.type), rank)
    return rank.take(column.indices)


def _compared(column: Any) -> tuple[Any, Any]:
    """Per-row masks over one column: does row i+1 sort before row i, and does it equal it.

    Null sorts first, matching the writer, and two nulls are equal.
    """
    n = len(column) - 1
    prior, current = column.slice(0, n), column.slice(1, n)
    prior_null, current_null = pc.is_null(prior), pc.is_null(current)
    neither = pc.invert(pc.or_(prior_null, current_null))
    less = pc.or_(pc.and_(current_null, pc.invert(prior_null)), pc.and_(neither, pc.less(current, prior)))
    same = pc.or_(pc.and_(prior_null, current_null), pc.and_(neither, pc.equal(current, prior)))
    return pc.fill_null(less, False), pc.fill_null(same, False)


def _breaks(batch: Any, keys: Sequence[str], unique: Sequence[str] | None = None) -> tuple[list[int], list[int]]:
    """Offsets where the batch descends over `keys`, and where it repeats over `unique`.

    One pass over each column, not two. A descent needs the column's `less` mask and a
    duplicate needs its `same` mask, and a single comparison yields both; asking for them
    separately compares every column twice, which on a spike table's five-column key is the
    ordering scan's largest single cost.

    A descent at row i means some key decreases there while every earlier key is equal, so the
    equal-so-far mask carries forward across columns in the sort's order. A duplicate does not
    depend on order at all -- it is every key column equal at once -- which is why `unique` may
    name the same columns in a different one.
    """
    n = batch.num_rows - 1
    if n < 1:
        return [], []
    masks = {name: _compared(_ranked(batch.column(name))) for name in dict.fromkeys([*keys, *(unique or [])])}
    descending: Any = pa.array([False] * n)
    equal_so_far: Any = pa.array([True] * n)
    for key in keys:
        less, same = masks[key]
        descending = pc.or_(descending, pc.and_(equal_so_far, less))
        equal_so_far = pc.and_(equal_so_far, same)
    descents = [i + 1 for i in pc.indices_nonzero(descending).to_pylist()]
    if not unique:
        return descents, []
    equal: Any = pa.array([True] * n)
    for key in unique:
        equal = pc.and_(equal, masks[key][1])
    return descents, [i + 1 for i in pc.indices_nonzero(equal).to_pylist()]


def _constant(path: Path, keys: Sequence[str]) -> set[str]:
    """Return the sort keys the file stores as a single value, which cannot affect ordering.

    A column holding one value never decreases and is always equal to itself, so it contributes
    nothing to either the descent mask or the duplicate mask — yet it is still decoded and
    compared once per row. Parquet answers this from the footer: row-group statistics carry each
    column's min and max, so a constant column is knowable without reading a page of it.

    `session_id` is the usual case. A single-session packet otherwise spends a fifth of its
    ordering scan proving that a constant is not descending.

    The caller must keep at least one key. If every key is constant then every row is equal on
    the whole key, which is a table of duplicates rather than a table needing no check, and
    dropping them all would report neither.
    """
    metadata = pq.ParquetFile(path).metadata
    names = metadata.schema.names
    constant = set()
    for key in keys:
        if key not in names:
            continue
        column = names.index(key)
        seen: set[Any] = set()
        for group in range(metadata.num_row_groups):
            statistics = metadata.row_group(group).column(column).statistics
            if statistics is None or not statistics.has_min_max or statistics.null_count:
                seen = {object(), object()}  # unknown, so keep the column
                break
            seen |= {statistics.min, statistics.max}
        if len(seen) == 1:
            constant.add(key)
    return constant


def _ordering_scan(
    handle: Any, keys: Sequence[str], unique: Sequence[str] | None
) -> tuple[list[str], list[str] | None, Iterator[Any]]:
    """Read the key columns for the ordering scan, and drop the keys that decide nothing.

    A constant column never decreases and is always equal to itself, so it contributes to neither
    mask -- yet it is still decoded and compared once per row. Parquet answers it from the footer.
    Never to nothing: a wholly constant key is every row duplicated, not a table needing no check.

    The footer is read here, so a damaged one raises before the scan starts. The pages are not:
    the caller steps the iterator so a decompression failure becomes a finding at the point it
    happens, and the scan stays streaming.
    """
    constant = _constant(handle.path, keys)
    kept = [k for k in keys if k not in constant] or list(keys)
    settles = ([k for k in unique if k not in constant] or list(unique)) if unique else None
    # Read the string keys as codes. The scan compares them, and `_breaks` compares a dictionary
    # by rank without ever materialising a string; decoding here would build a Python-free but
    # still per-row copy of four identifier columns over the whole table.
    coded = [k for k in kept if pa.types.is_string(handle.schema().field(k).type)]
    reader = pq.ParquetFile(handle.path, read_dictionary=coded or None)
    return kept, settles, reader.iter_batches(batch_size=ORDER_BATCH, columns=kept)


def _duplicated_columns(handle: Any, spec: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Pairs of this table's columns holding equal values in every row (Part 05 §5.3).

    Bounded by the footer, not by a row sample. Two columns can hold equal values in every row
    only if their per-chunk minimum, maximum and null count agree, which Parquet already records,
    so statistics decide almost every pair and values are read for the few that survive.

    Constant columns are excluded rather than reported. A column holding one value equals every
    other column holding that value, which says nothing about either.
    """
    reader = pq.ParquetFile(handle.path)
    meta, names = reader.metadata, reader.schema_arrow.names
    ranges: dict[str, list[Any]] = {}
    for index, name in enumerate(names):
        chunks: list[tuple[Any, Any, int | None]] = []
        for group in range(meta.num_row_groups):
            stats = meta.row_group(group).column(index).statistics
            if stats is None or not stats.has_min_max:
                chunks = []
                break
            chunks.append((stats.min, stats.max, stats.null_count))
        ranges[name] = chunks
    candidates = [
        (a, b)
        for a, b in itertools.combinations(names, 2)
        if ranges[a] and ranges[a] == ranges[b] and any(c[0] != c[1] for c in ranges[a])
    ]
    if not candidates:
        return []
    wanted = sorted({n for pair in candidates for n in pair})
    table = reader.read(columns=wanted)
    return [(a, b) for a, b in candidates if table.column(a).equals(table.column(b))]


def check_duplication(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 05 §5.3. Reported at `info` and never as a failure.

    Independently numbered identifiers can coincide, which is a fact about a packet rather than a
    defect in it.
    """
    for resource_id, handle in present.items():
        try:
            pairs = _duplicated_columns(handle, tables[resource_id])
        except (OSError, pa.ArrowException):
            continue
        for a, b in pairs:
            report.add(
                check_table.columns_duplicated(resource_id),
                f"{a} and {b} hold equal values in every row",
                registry=report.resource_owner(resource_id),
            )


def check_unfilled_metadata(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 05 §5.3. A declared `metadata` column a resource's file omits or leaves null, at `info`.

    Whether a table in Part 02 §8.6's middle band declares one is a judgement, and this is the
    evidence against which it is revisited. Never a failure — Part 02 §6 makes an optional
    column's absence conforming, and a source with nothing unmodelled to say is the ordinary case.

    Bounded by the footer. A null count per row group is what Parquet already records, so no
    value is read.
    """
    for resource_id, handle in present.items():
        if not any(c["name"] == "metadata" for c in tables[resource_id]["columns"]):
            continue
        try:
            meta = pq.ParquetFile(handle.path).metadata
            index = meta.schema.names.index("metadata") if "metadata" in meta.schema.names else None
        except (OSError, pa.ArrowException):
            continue
        if index is None:
            report.add(
                check_table.metadata_unfilled(resource_id),
                "metadata is declared and the file omits it",
                registry=report.resource_owner(resource_id),
            )
            continue
        nulls = 0
        for group in range(meta.num_row_groups):
            stats = meta.row_group(group).column(index).statistics
            if stats is None or stats.null_count is None:
                break
            nulls += stats.null_count
        else:
            if meta.num_rows and nulls == meta.num_rows:
                report.add(
                    check_table.metadata_unfilled(resource_id),
                    "metadata is null in every row",
                    registry=report.resource_owner(resource_id),
                )


def check_reserved_values(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Report a value outside a column's reserved set at `info` (Part 02 §9.3).

    Never a failure: an open vocabulary admits an unrecognised value. A synonym of a reserved value
    is prohibited and cannot be recognised from the packet, so that obligation binds the writer and
    no check here enforces it.
    """
    for resource_id, handle in present.items():
        for column in tables[resource_id]["columns"]:
            reserved = column.get("reserved_values")
            if not reserved:
                continue
            name = column["name"]
            try:
                table = pq.read_table(handle.path, columns=[name])
            except (OSError, pa.ArrowException, KeyError):
                continue
            outside = sorted({v for v in table.column(name).to_pylist() if v is not None and v not in set(reserved)})
            if outside:
                report.add(
                    check_table.outside_reserved_set(resource_id, name),
                    f"{len(outside)} value(s) outside the reserved set: "
                    f"{', '.join(repr(v) for v in outside[:5])}" + (" ..." if len(outside) > 5 else ""),
                    registry=report.resource_owner(resource_id),
                )


def check_unit_codes(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 05 §5.3. Every non-null value of a unit column is a UCUM code (Part 02 §8.4).

    Covers every table a directing registry declares (Part 05 §5.4), and files each finding and each
    unreadable column under that registry. Distinct values are parsed once each.
    """
    for resource_id, handle in present.items():
        for column in tables[resource_id]["columns"]:
            if not any(entry.get("uri") == UCUM_URI for entry in column.get("authority", ())):
                continue
            name = column["name"]
            check = check_table.ucum_code(resource_id, name)
            registry = report.resource_owner(resource_id) or "core"
            try:
                values = pc.unique(pq.read_table(handle.path, columns=[name]).column(name)).to_pylist()
            except (OSError, pa.ArrowException, KeyError) as exc:
                report.record_evaluation(
                    registry, EvaluationStatus.INCOMPLETE, rule=check.id, detail=str(exc).splitlines()[0][:160]
                )
                continue
            invalid = sorted(value for value in values if value is not None and ucum_error(value) is not None)
            if invalid:
                report.add(
                    check,
                    f"{len(invalid)} value(s) are not UCUM codes: {', '.join(repr(v) for v in invalid[:5])}"
                    + (" ..." if len(invalid) > 5 else ""),
                    [(value,) for value in invalid],
                    registry=registry,
                )


def check_ordering(
    tables: Mapping[str, Any],
    present: Mapping[str, Any],
    report: Report,
    scan: Collection[str] | None = None,
) -> set[str]:
    """Layer 3: declared sort order, and the uniqueness that order settles (Part 03 §5.3, Part 03 §5.3).

    One pass answers both. A table sorted by its primary key puts duplicates next to each
    other, so comparing neighbours — which this scan already does to find descents — decides
    uniqueness too. `generate` leaves the `GROUP BY` out for those tables: an aggregate
    materialises every key column, and spills where they are strings over a spike table's rows,
    while the scan reads them in order and holds one batch.

    Parameters
    ----------
    scan : collection of str, optional
        Resources to establish by reading. `None`, the default, reads every one, which is what
        a validator handed an unknown packet must do. A caller that has already established a
        resource's order by other means passes the rest — see `validate`.
    """
    unsound: set[str] = set()
    for resource_id, handle in present.items():
        if scan is not None and resource_id not in scan:
            continue
        spec = tables[resource_id]
        if _scan_one_ordering(resource_id, handle, spec, report):
            unsound.add(resource_id)
    return unsound


def _row(index: int) -> str:
    """Name the row at an index of the table by its position, which starts at 1."""
    return f"row {index + 1}"


def _scan_one_ordering(  # noqa: C901
    resource_id: str, handle: Any, spec: Mapping[str, Any], report: Report
) -> bool:
    """One table's ordering scan. True where uniqueness must fall back to the aggregate."""
    # Part 03 §5.3 puts every table in its key's order unless the descriptor overrides it (Part 03
    # §5.4), so both come from `escapewheel_reader.ordering`.
    keys = stored_order(resource_id, spec)
    unique = spec["primary_key"] if adjacency_settles_uniqueness(resource_id, spec) else None
    declared = {c["name"] for c in spec.get("columns", ())}
    if missing := [k for k in keys if k not in declared]:
        # Part 03 §5.4: the bound registry cannot hold the required order, so the table departs.
        report.add(
            check_table.physical_order(resource_id),
            f"the bound registry declares no {', '.join(missing)}, so the table cannot be in its "
            f"required order ({', '.join(keys)})",
            registry=report.resource_owner(resource_id),
        )
        return bool(unique)
    # Part 03 §5.3: the declarations this table's adjacency argument leans on.
    determined = (
        [
            c["name"]
            for c in spec.get("columns", ())
            if c["name"] in keys and "determined_by" in c and set(c["determined_by"]) <= set(spec["primary_key"])
        ]
        if unique
        else []
    )
    offending: list[tuple[int, Any, Any]] = []
    duplicated: list[tuple[int, Any]] = []
    broken: list[tuple[int, str, Any, Any]] = []
    tail: tuple[Any, ...] | None = None
    start = 0
    try:
        keys, unique, batches = _ordering_scan(handle, keys, unique)
    except (OSError, pa.ArrowException) as exc:
        report.add(
            check_table.RESOURCE_UNREADABLE, f"{resource_id}: {exc}", registry=report.resource_owner(resource_id)
        )
        return False
    # A column the scan dropped holds one value, so it agrees with itself at every repeated key.
    determined = [name for name in determined if name in keys]
    damaged = None
    while True:
        # Stepped rather than iterated, so a page that fails to decompress becomes a finding
        # instead of a traceback -- without wrapping the scan body, where the same exception type
        # would mean something else. Streaming is not negotiable here: a spike table's key
        # columns held whole are gigabytes, where the scan holds one batch.
        try:
            batch = next(batches)
        except StopIteration:
            break
        except (OSError, pa.ArrowException) as exc:
            damaged = exc
            break
        first = _row_at(batch, keys, 0)
        if tail is not None and _sortable(first) < _sortable(tail):
            offending.append((start, tail, first))
        descents, repeats = _breaks(batch, keys, unique)
        offending.extend(
            (start + offset, _row_at(batch, keys, offset - 1), _row_at(batch, keys, offset)) for offset in descents
        )
        if unique:
            # The batch boundary needs its own comparison: the scan compares within a batch, so a
            # duplicate split across two would otherwise pass unseen.
            if tail is not None and _row_at(batch, unique, 0) == _tail_key(tail, keys, unique):
                duplicated.append((start, _row_at(batch, unique, 0)))
            duplicated.extend((start + offset, _row_at(batch, unique, offset)) for offset in repeats)
            # Part 03 §5.3. Two rows sharing the key must agree on every column declared a function
            # of it; where they do not, the declaration is false and the waiver it earns is
            # unearned. Reported apart from the duplicate, because the repair is different.
            for offset in repeats:
                for name in determined:
                    was, now = batch.column(name)[offset - 1].as_py(), batch.column(name)[offset].as_py()
                    if was != now:
                        broken.append((start + offset, name, was, now))
        tail = _row_at(batch, keys, batch.num_rows - 1)
        start += batch.num_rows
        if len(offending) >= ORDER_REPORT and len(duplicated) >= ORDER_REPORT:
            break
    if damaged is not None:
        # The order cannot be established, so nothing partial is reported for it: what the scan
        # saw before the damage says nothing about the file as a whole.
        report.add(
            check_table.RESOURCE_UNREADABLE, f"{resource_id}: {damaged}", registry=report.resource_owner(resource_id)
        )
        return False
    if broken:
        report.add(
            check_table.determined_by(resource_id),
            "a column declared determined_by the key differs between two rows sharing it",
            [(_row(index), col, f"{a} != {b}") for index, col, a, b in broken[:ORDER_REPORT]],
            registry=report.resource_owner(resource_id),
        )
    if offending:
        report.add(
            check_table.physical_order(resource_id),
            f"rows are not in declared sort order ({', '.join(keys)})",
            [(_row(index), str(prev), str(cur)) for index, prev, cur in offending[:ORDER_REPORT]],
            registry=report.resource_owner(resource_id),
        )
        # Adjacency settles uniqueness only for a file actually in order: a duplicate anywhere but
        # beside its twin is invisible to a scan of neighbours. Part 03 §5.3 makes the departure an
        # error, and uniqueness still falls back to the aggregate rather than being skipped.
        return bool(unique)
    if duplicated:
        report.add(
            check_table.primary_key_unique(resource_id),
            "duplicate primary key",
            [(_row(index), str(row)) for index, row in duplicated[:ORDER_REPORT]],
            registry=report.resource_owner(resource_id),
        )
    return False


def verify_order(batches: Iterable[Any], keys: Sequence[str], unique: Sequence[str] | None = None) -> Iterator[Any]:
    """Yield batches, raising if one sorts before its predecessor or repeats the key.

    The same comparison :func:`check_ordering` makes against a written file, made instead
    against the batches on their way into one. It is offered because a writer is the one caller
    that can establish a file's order without reading the file: the rows pass through its hands
    already, so the check costs the comparison and not the re-read of the file that finding the
    same answer afterwards costs.

    The seam between batches is compared as well as the inside of each, so a descent or a
    duplicate landing exactly on a boundary is caught rather than falling between two passes.

    Parameters
    ----------
    batches : iterable
        Record batches, in the order they will be written.
    keys : sequence of str
        The declared sort columns.
    unique : sequence of str, optional
        A key that adjacency settles, checked for repeats at the same time. Pass None where the
        sort does not begin with the key, since duplicates need not be neighbours there.

    Yields
    ------
    pyarrow.RecordBatch
        Each batch, unchanged.

    Raises
    ------
    OrderViolation
        On the first row that breaks the declared order, carrying its index and its fault.
    """
    tail: tuple[Any, ...] | None = None
    start = 0
    for batch in batches:
        if batch.num_rows:
            first = _row_at(batch, keys, 0)
            if tail is not None and _sortable(first) < _sortable(tail):
                raise OrderViolation(OrderFault.DESCENT, start, f"sorts before the row above it: {tail} then {first}")
            descents, repeats = _breaks(batch, keys, unique)
            if descents:
                offset = descents[0]
                raise OrderViolation(
                    OrderFault.DESCENT,
                    start + offset,
                    "sorts before the row above it: "
                    f"{_row_at(batch, keys, offset - 1)} then {_row_at(batch, keys, offset)}",
                )
            if unique:
                if tail is not None and _row_at(batch, unique, 0) == _tail_key(tail, keys, unique):
                    raise OrderViolation(
                        OrderFault.REPEAT, start, f"repeats the key above it: {_row_at(batch, unique, 0)}"
                    )
                if repeats:
                    offset = repeats[0]
                    raise OrderViolation(
                        OrderFault.REPEAT,
                        start + offset,
                        f"repeats the key above it: {_row_at(batch, unique, offset)}",
                    )
            tail = _row_at(batch, keys, batch.num_rows - 1)
            start += batch.num_rows
        yield batch


def _tail_key(tail: tuple[Any, ...], keys: Sequence[str], unique: Sequence[str]) -> tuple[Any, ...]:
    """Return the key columns of a row already pulled out over the sort columns."""
    index = {name: position for position, name in enumerate(keys)}
    return tuple(tail[index[name]] for name in unique)


#: What a validating DuckDB connection is allowed to take. Left to itself it claims 80% of
#: system memory and every core, which on a spike table means hundreds of millions of rows
#: grouped on a five-column key with most of the machine as its budget -- enough to take a
#: workstation down.
#:
#: `temp_directory` is not optional here. An in-memory DuckDB has none by default, so a memory
#: limit has nothing to spill *to* and bounds nothing; the two settings only work as a pair.
#: The default follows the packet, because a temp directory on tmpfs -- which `/tmp` is on
#: several distributions -- spills into the memory the limit exists to protect.
#:
#: Bounded this way every check still passes, and an aggregate that does not fit spills and
#: runs slower. So this costs time and never correctness.
LIMITS: dict[str, Any] = {"memory_limit": "4GB", "threads": 4}


def bounded(connection: Any, limits: Mapping[str, Any], spill: Path | None = None) -> Any:
    """Apply resource limits to a connection, ignoring settings this DuckDB lacks.

    `spill` supplies `temp_directory` when the caller has not, since a memory limit without
    one bounds nothing.
    """
    connection.execute("SET TimeZone = 'UTC'")
    settings = dict(limits)
    if spill is not None and "memory_limit" in settings:
        settings.setdefault("temp_directory", str(spill))
    for name, value in settings.items():
        rendered = f"'{value}'" if isinstance(value, str) else value
        with contextlib.suppress(Exception):  # an unknown setting must not fail a validation
            connection.execute(f"SET {name} = {rendered}")
    return connection


@contextlib.contextmanager
def spill_beside(packet: Packet) -> Iterator[Path | None]:
    """Yield a directory for DuckDB to spill into, removed afterwards.

    Beside the packet, not inside it. The filesystem has to be the packet's -- `/tmp` is tmpfs
    on several distributions, so spilling there consumes the memory the limit exists to bound
    -- but the packet root is the wrong place to put it: validating a packet would write into
    a directory whose bytes are supposed to be settled (Part 03 §8.1), leave it behind, and fail
    outright on read-only media. A uniqueness aggregate can spill many times the size of the
    packet it is checking.
    """
    root = getattr(packet, "root", None)
    if root is None:
        yield None
        return
    root = Path(root)
    for parent in (root.parent, root):
        try:
            spill = Path(tempfile.mkdtemp(prefix=".validate-", dir=parent))
        except OSError:
            continue
        try:
            yield spill
        finally:
            shutil.rmtree(spill, ignore_errors=True)
        return
    yield None


def run_rules(
    packet: Packet,
    core_context: CheckedRegistryContext,
    extension_contexts: Mapping[str, CheckedRegistryContext],
    present: Mapping[str, Any],
    report: Report,
    advisory: bool,
    limits: Mapping[str, Any] | None = None,
    unsound: set[str] | None = None,
    recheck: Collection[str] | None = None,
) -> None:
    """Layer 4: Tier 1 checks generated from structure, then Tier 2 rules (R2 §7)."""
    registry = core_context.document
    assert isinstance(registry, Mapping)
    extension_documents = [
        context.document for context in extension_contexts.values() if context.result.state == RegistryState.VALID
    ]
    with spill_beside(packet) as spill:
        connection = bounded(packet.duckdb(), LIMITS if limits is None else limits, spill)
        try:
            unreadable = _install_rule_relations(packet, connection, [registry, *extension_documents])

            kinds = _declared_kinds(packet, registry, extension_documents)
            keys = _declared_keys(packet, registry, extension_documents)
            specialises = _specialisations(packet, registry, extension_documents)
            tier1 = generate(
                core_context,
                only=set(present),
                advisory=advisory,
                aggregate=unsound or set(),
                kinds=kinds,
                specialises=specialises,
                declared=False,
                keys=keys,
            )
            tier2 = _tier2_checks(core_context, core_context, report, "core", advisory)
            checks = [*tier1, *tier2]
            if recheck is not None:
                checks = [check for check in checks if concerns(check, recheck)]
            _run_checks(connection, checks, report, "core", unreadable)
            _check_manifest_sessions(packet, report)
            report.complete("core")
            _check_extensions(
                packet,
                connection,
                core_context,
                extension_contexts,
                report,
                advisory,
                kinds,
                unreadable,
                recheck,
                unsound,
                keys,
                specialises,
            )
        finally:
            with contextlib.suppress(Exception):
                connection.close()


def _install_rule_relations(packet: Packet, connection: Any, documents: Sequence[Mapping[str, Any]]) -> set[str]:
    """Install exact qualified packet relations and typed empties for absent resources."""
    declared = {resource.resource_id for resource in packet.resources() if resource.kind == "table"}
    unreadable: set[str] = set()
    installed: set[str] = set()
    for document in documents:
        for resource_id, spec in table_contracts(document).items():
            if resource_id in installed:
                continue
            installed.add(resource_id)
            namespace, _ = resource_id.split(".", 1)
            connection.sql(f"CREATE SCHEMA IF NOT EXISTS {namespace}")
            if resource_id in declared:
                try:
                    packet.table_resource(resource_id).register(connection, name=resource_id)
                    continue
                except (PacketError, OSError, ValueError):
                    unreadable.add(resource_id)
            columns = ", ".join(f'"{c["name"]}" {DDL[c["type"]]}' for c in spec["columns"])
            connection.sql(f"CREATE OR REPLACE TABLE {resource_id} ({columns})")
    return unreadable


@dataclass(frozen=True)
class _Tier2:
    """A registry's Tier 2 rules as statically checked: the checks, or why none can run."""

    language: Any
    checks: tuple[Check, ...]
    #: The ID and the refusal of each rule outside the profile.
    invalid: tuple[tuple[Any, str], ...]


#: Checked rules by the bytes of the registry and of core, and whether advisory rules are included.
_TIER2: dict[tuple[bytes, bytes, bool], _Tier2] = {}
_TIER2_KEPT = 32


def _tier2(context: CheckedRegistryContext, core_context: CheckedRegistryContext, advisory: bool) -> _Tier2:
    """Statically check a registry's Tier 2 rules, once for each distinct registry and core."""
    from_bytes = context.input_kind == core_context.input_kind == "bytes"
    key = (context.exact_input, core_context.exact_input, advisory)
    if from_bytes and key in _TIER2:
        return _TIER2[key]
    document, core_registry = context.document, core_context.document
    language = document.get("rule_language")
    checked: list[Check] = []
    invalid: list[tuple[Any, str]] = []
    for resource, table in table_contracts(document).items() if language == PROFILE_ID else ():
        for rule in table.get("rules", []):
            if rule.get("advisory") and not advisory:
                continue
            try:
                parsed = check_rule(rule["sql"], document, core_resources=core_registry)
            except RuleProfileError as exc:
                invalid.append((rule.get("id"), str(exc)))
                continue
            checked.append(
                Check(
                    check_table.rule(rule["id"], rule["level"]),
                    rule["message"],
                    parsed.sql,
                    resource,
                    tier=2,
                    dependencies=parsed.resources,
                )
            )
    found = _Tier2(language, tuple(checked), tuple(invalid))
    if from_bytes:
        if len(_TIER2) >= _TIER2_KEPT:
            _TIER2.clear()
        _TIER2[key] = found
    return found


def _tier2_checks(
    context: CheckedRegistryContext,
    core_context: CheckedRegistryContext,
    report: Report,
    registry_id: str,
    advisory: bool,
) -> list[Check]:
    """Return checked Tier 2 rules, or record why this registry cannot be evaluated."""
    found = _tier2(context, core_context, advisory)
    if found.language != PROFILE_ID:
        report.record_evaluation(
            registry_id,
            EvaluationStatus.UNSUPPORTED,
            detail=f"rule language {found.language!r} is not supported; expected {PROFILE_ID!r}",
        )
        return []
    for rule_id, detail in found.invalid:
        report.record_evaluation(registry_id, EvaluationStatus.INVALID, rule=rule_id, detail=detail)
    return [] if found.invalid else list(found.checks)


def _run_checks(
    connection: Any,
    checks: Sequence[Check],
    report: Report,
    registry_id: str,
    unreadable: set[str],
) -> None:
    """Run generated checks and record what they returned; the caller completes the evaluation."""
    for check in checks:
        if check.tier == 2 and (missing := sorted(check.dependencies & unreadable)):
            report.record_evaluation(
                registry_id,
                EvaluationStatus.INCOMPLETE,
                rule=check.id,
                detail=f"unreadable input(s): {', '.join(missing)}",
            )
            continue
        if check.optional_columns and not check.optional_columns <= set(_relation_columns(connection, check.resource)):
            continue
        try:
            rows = _offending(connection, check.sql)
        except Exception as exc:  # noqa: BLE001 - converted to the layer-owned outcome below
            if check.tier == 2:
                report.record_evaluation(
                    registry_id,
                    EvaluationStatus.INCOMPLETE,
                    rule=check.id,
                    detail=str(exc).splitlines()[0][:160],
                )
            else:
                report.add(
                    check.entry.at(Level.ERROR),
                    f"check could not run: {str(exc).splitlines()[0][:90]}",
                    registry=registry_id,
                )
            continue
        if rows:
            report.add(check.entry, check.message, rows, registry=registry_id)


def _check_manifest_sessions(packet: Packet, report: Report) -> None:
    """Compare the manifest inventory with ``core.sessions`` at the Part 05 shim."""
    check = check_table.CORE_SESSIONS_MANIFEST_SESSIONS_MATCH
    message = (
        "the manifest's session inventory and core.sessions disagree; the manifest names a "
        "session by its session_name, since an assigned session_id means nothing outside the "
        "packet that assigned it"
    )
    declared = {resource.resource_id for resource in packet.resources(kind="table")}
    table_values: list[str] = []
    if CORE_SESSIONS in declared:
        try:
            table_values = [
                value
                for value in packet.table(CORE_SESSIONS, columns=["session_name"]).column("session_name").to_pylist()
                if value is not None
            ]
        except (PacketError, OSError, pa.ArrowException) as exc:
            report.record_evaluation("core", EvaluationStatus.INCOMPLETE, rule=check.id, detail=str(exc))
            return
    listed = list(packet.manifest.sessions)
    listed_set, table_set = set(listed), set(table_values)
    rows = [(value,) for value in table_values if value not in listed_set]
    rows.extend((value,) for value in listed if value not in table_set)
    if rows:
        report.add(check, message, rows, registry="core")


def _resolve_column(spec: Mapping[str, Any]) -> str | None:
    """Return the column a paired value joins to, or None where the resource is not namable.

    Part 02 §8.3 requires a single-column key, since a paired value holds one identifier. Which
    column it *matches* then follows from R53 §2.3: an `assigned` key is a number this format
    chose at build time, so a value written before the build cannot hold it and the join is on
    the `*_name` the owner carries for exactly this purpose. A `carried` key is the source's own
    number and is stable, so the join is on the key itself.
    """
    key = spec.get("primary_key")
    if not isinstance(key, list) or len(key) != 1:
        return None
    column = next((c for c in spec["columns"] if c["name"] == key[0]), None)
    if column is None:
        return None
    if column.get("identity") != "assigned":
        return key[0]
    named = f"{key[0].removesuffix('_id')}_name"
    return named if any(c["name"] == named for c in spec["columns"]) else None


def _namable(
    packet: Packet, registry: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Every table a discriminator may name: core's, and the carried tables of each extension.

    Part 02 §8.3 lets a kind name an extension table, and that is the case a check must reach.
    Core's absent tables get empty stand-ins in _layer4, so all of them can be joined; an
    extension's do not, so only what the packet carries can be.
    """
    tables = dict(table_contracts(registry))
    carried = {resource.resource_id for resource in packet.resources(kind="table")}
    for document in extensions:
        if isinstance(table_contracts(document), Mapping):
            tables.update({n: t for n, t in table_contracts(document).items() if n in carried})
    return tables


def _declared_kinds(
    packet: Packet, registry: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, str | None]:
    """Every resource a discriminator may name, mapped to the column a string paired value joins to.

    Every declarable resource, whether or not a paired value could name it: a shared-key
    discriminator names tables whose key is composite by construction.
    """
    return {name: _resolve_column(spec) for name, spec in _namable(packet, registry, extensions).items()}


def _declared_keys(
    packet: Packet, registry: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Every resource a discriminator may name, mapped to its one key column, or None.

    An identifier paired value holds that column's value, so it must share its type and identity
    (Part 02 §8.3).
    """
    found: dict[str, Any] = {}
    for name, spec in _namable(packet, registry, extensions).items():
        key = spec.get("primary_key")
        column = None
        if isinstance(key, list) and len(key) == 1:
            column = next((c for c in spec["columns"] if c["name"] == key[0]), None)
        found[name] = column
    return found


def _specialisations(
    packet: Packet, registry: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, list[Specialisation]]:
    """Every declared specialising reference, keyed by the discriminator it names (Part 02 §8.3).

    Only a declaration makes a table a specialisation: a table keyed by its reference to an
    interval may hold one row per interval without being a kind, and inference from references
    takes every related table for a misdirection.
    """
    tables = dict(table_contracts(registry))
    carried = {resource.resource_id for resource in packet.resources(kind="table")}
    for document in extensions:
        if isinstance(table_contracts(document), Mapping):
            tables.update({n: t for n, t in table_contracts(document).items() if n in carried})
    found: dict[str, list[Specialisation]] = {}
    for name, spec in tables.items():
        for reference in spec.get("references", []):
            if "specialises" not in reference:
                continue
            holder, column_name = str(reference["specialises"]).rsplit(".", 1)
            column = next((c for c in (tables.get(holder) or {}).get("columns", []) if c["name"] == column_name), {})
            via = None
            if target_column := column.get("discriminates_via"):
                target = str(target_column).rsplit(".", 1)[0]
                to_holder = next(
                    (
                        r
                        for r in (tables.get(target) or {}).get("references", [])
                        if r["resource"] == holder and str(target_column).rsplit(".", 1)[1] in r["columns"]
                    ),
                    None,
                )
                if to_holder is None:
                    continue  # the registry check reports a path that does not resolve
                via = tuple(zip(to_holder["columns"], to_holder["resource_columns"], strict=True))
            found.setdefault(str(reference["specialises"]), []).append(
                Specialisation(
                    detail=name,
                    target=str(reference["resource"]),
                    on=tuple(zip(reference["columns"], reference["resource_columns"], strict=True)),
                    holder=holder,
                    column=column_name,
                    via=via,
                )
            )
    return found


def _check_extensions(
    packet: Packet,
    connection: Any,
    core_context: CheckedRegistryContext,
    extension_contexts: Mapping[str, CheckedRegistryContext],
    report: Report,
    advisory: bool,
    kinds: Mapping[str, str | None] | None = None,
    unreadable: set[str] | None = None,
    recheck: Collection[str] | None = None,
    unsound: set[str] | None = None,
    keys: Mapping[str, Any] | None = None,
    specialises: Mapping[str, Collection[Specialisation]] | None = None,
) -> None:
    """Run each directing extension registry's generated and declared checks (Part 05 §5.4).

    R17 §3's claim is that nothing here is per-extension: the same `generate` produces an
    extension's Tier 1 checks from its structure and carries its Tier 2 rules, because an
    extension registry *is* a registry document. What this function adds is which tables its
    references may resolve against -- core's, since Part 09 §6.1 lets an extension reference them and
    forbids the reverse -- and the registry its findings are filed under, so they decide the
    extension's verdict and never core's (Part 05 §9.5).
    """
    registry = core_context.document
    assert isinstance(registry, Mapping)
    for extension_id, extension_context in extension_contexts.items():
        if extension_context.result.state != RegistryState.VALID:
            continue
        document = extension_context.document
        assert isinstance(document, Mapping)
        declared = set(table_contracts(document))
        # What the *packet* declares, not what the core registry knows: an extension's tables are
        # by definition absent from core's, and `present` is built from core's.
        carried = declared & {r.resource_id for r in packet.resources(kind="table")}
        if absent := sorted(declared - carried):
            report.add(
                check_table.EXTENSION_TABLE_ABSENT,
                f"{extension_id}: declares {len(absent)} table(s) this packet does not carry",
                [(name,) for name in absent],
                registry=extension_id,
            )
        tier1 = generate(
            extension_context,
            only=carried,
            advisory=advisory,
            aggregate=unsound or set(),
            resolvable=set(table_contracts(registry)),
            kinds=kinds,
            specialises=specialises,
            declared=False,
            keys=keys,
        )
        tier2 = _tier2_checks(extension_context, core_context, report, extension_id, advisory)
        checks = [*tier1, *tier2]
        if recheck is not None:
            checks = [check for check in checks if concerns(check, recheck)]
        _run_checks(connection, checks, report, extension_id, unreadable or set())
        report.complete(extension_id)
        report.add(
            check_table.EXTENSION_VALIDATED,
            f"{extension_id}: {len(checks)} check(s) over {len(carried)} table(s)",
            registry=extension_id,
        )


def _offending(connection: Any, sql: str) -> list[tuple[Any, ...]]:
    """Run a rule and return its offending rows.

    Results come back through Arrow rather than DuckDB's own Python conversion, which needs
    `pytz` to render a ``TIMESTAMP WITH TIME ZONE`` and raises if it is absent. That failure
    is worse than it sounds: an empty result converts nothing, so a rule projecting a
    wall-clock column runs fine until it actually has a finding to report, and then errors
    instead of reporting it -- with pass or fail decided by whether some unrelated package
    pulled in `pytz`. Arrow is already a dependency of the read path and uses `zoneinfo`.
    """
    table = connection.sql(sql).arrow().read_all()
    return list(zip(*[column.to_pylist() for column in table.columns], strict=True))


def _relation_columns(connection: Any, relation: str) -> list[str]:
    """Return the column names an installed packet relation carries."""
    return list(connection.sql(f"SELECT * FROM {relation} LIMIT 0").columns)


def validate(
    packet: Packet,
    *,
    advisory: bool = False,
    limits: Mapping[str, Any] | None = None,
    scan: Collection[str] | None = None,
    recheck: Collection[str] | None = None,
    external: bool = False,
    checksums: bool = False,
    store_digests: bool = False,
    store_checksums: bool = True,
    superseded: Mapping[str, Any] | None = None,
    replaced: Sequence[str | Path] = (),
) -> Report:
    """Validate a packet against the registries it binds.

    Only a bound registry that passes Part 04 §10's binding checks directs packet checks; no
    bundled or caller-supplied registry stands in for one (Part 05 §14.5).

    Parameters
    ----------
    packet : Packet
        The packet to validate.
    limits : Mapping, optional
        DuckDB settings bounding what validation may consume, defaulting to :data:`LIMITS`,
        with `temp_directory` filled in beside the packet so the limit has somewhere to spill.
        Pass ``{}`` to leave DuckDB at its own defaults, which are 80% of system memory and
        every core -- reasonable for an interactive query and not for unattended validation of
        a table with 10^8 rows.
    scan : collection of str, optional
        Resources whose physical order this call should establish by reading. `None`, the
        default, reads every one — the only safe answer for a packet of unknown provenance.

        A writer that has already compared every row as it wrote them passes the rest, which
        is not the writer vouching for itself: the same comparison ran, on the same rows, from
        the same code, one step earlier. What it costs is the distinction between "the batches
        handed to Parquet were ordered" and "the file is ordered", and that gap is closed by
        `_write_stream` making each batch exactly one row group.
    recheck : collection of str, optional
        Resources this call has just written, restricting the rules to those Part 05 §15.4 obliges to
        run: the ones attached to such a resource, and the ones whose query names one. `None`,
        the default, runs every rule, which is what a first commit and a packet of unknown
        provenance both need. An amendment passes what it writes, because Part 05 §15.1 forbids it
        modifying anything else and Part 03 §8.1 declares those bytes immutable, so a rule reading
        only them is already answered.
    external : bool, default False
        Resolve external URIs and check the `digest`, `size_bytes` and `members` claimed for
        them (Part 04 §5.3, level 3). Off by default because Part 04 §5.3 forbids structural validation
        reaching for a resource the packet does not own: whether one is reachable is a property
        of the reader's situation, not of the packet. An unreachable resource is a warning; one
        that resolves and disagrees with its claim is an error.
    checksums : bool, default False
        Establish every recorded `digest`: each packet-owned resource (Part 04 §5.3, level 2), and
        with `external`, each external one too (level 3c). Separate because reading costs every
        byte, and a packet may reference far more than it owns. The report names each digest's
        route.
    store_digests : bool, default False
        With `external`, also compare each member's recorded `store_digest` against what the
        store reports now (Part 04 §5.4). This is the level between the other two: it costs the
        listing already performed, and it answers "has anything changed in place" rather than
        "are these the bytes". A member with nothing recorded, or a store offering nothing, is
        not checked, and the report says how many were skipped.
    store_checksums : bool, default True
        With `checksums`, take a store's full-object checksums in the digest's algorithm in place
        of reading those objects (Part 04 §5.3). A composite value is never taken, an object the
        store reports nothing for is read, and a local packet has no store checksums to take.
    superseded : Mapping, optional
        The manifest this one supersedes, for a writer validating an amendment before it retains
        that manifest. Absent, the retained manifest immediately preceding this version is compared
        (Part 05 §15.6), and a packet retaining none has nothing to compare.
    replaced : sequence of str or Path, optional
        Packet roots, or manifest files, to read as packets the manifest's `replaces` names. Each
        difference from the item it is read as is a `packet.replaces.mismatch` warning (Part 04 §3);
        a packet no one supplies is not looked for.

    Returns
    -------
    Report
        Every finding, in the order the layers ran.

    Raises
    ------
    ReplacedPacketUnreadable
        If no published manifest can be read at a path in `replaced`.
    """
    # The manifest the packet carries, which for an amendment's candidate is not the file on disk. A
    # reader already refused bytes the `json` phase would, so re-encoding what it decoded loses no finding.
    manifest = json.dumps(packet.manifest.entry).encode()
    report, bound = check_packet_manifest(packet.location, advisory=advisory, manifest=manifest)
    if bound is None:
        return report
    for message, rows in confirm_replaced(packet.manifest.entry, replaced):
        report.add(check_table.PACKET_REPLACES_MISMATCH, message, rows)
    core_context = bound.core
    extensions = {name: context.document for name, context in bound.extensions.items()}
    directing = ([] if core_context is None else [(bound.core_id, core_context.document)]) + list(extensions.items())
    report.attribute(
        {declaration: str(name) for name, document in directing for declaration in document.get("resources", {})},
        packet.resources(),
    )
    check_sources(packet, report)
    if core_context is None:
        return report
    effective = core_context.document
    withheld = set(packet.manifest.extensions) - set(extensions)
    packet = packet.with_declarations(effective, *extensions.values())
    check_resource_declarations(packet, effective, extensions, withheld, report)
    assessed = resolve_external(packet, report, checksums, store_digests, store_checksums) if external else set()
    if checksums:
        check_owned_digests(packet, report, store_checksums)
    check_packet_owned_arrays(packet, report)
    check_packet_owned_opaque(packet, report)
    check_time_origin(packet, report)
    # Every directing registry's tables receive the same storage checks (Part 05 §5.4).
    tables = table_contracts(effective)
    for document in extensions.values():
        tables.update(table_contracts(document))
    present = check_schemas(packet, tables, report)
    report_page_types_unassessed(len(present), report)
    report_unassessed(packet, assessed | set(present), report)
    unsound = check_ordering(tables, present, report, scan)
    check_duplication(present, tables, report)
    check_unfilled_metadata(present, tables, report)
    check_reserved_values(present, tables, report)
    check_unit_codes(present, tables, report)
    run_rules(
        packet,
        core_context,
        bound.extensions,
        present,
        report,
        advisory,
        limits,
        unsound,
        recheck,
    )
    _check_amendment(packet, [effective, *extensions.values()], tables, report, limits, superseded)
    return report


def _check_amendment(
    packet: Packet,
    documents: Sequence[Mapping[str, Any]],
    tables: Mapping[str, Mapping[str, Any]],
    report: Report,
    limits: Mapping[str, Any] | None,
    superseded: Mapping[str, Any] | None,
) -> None:
    """Compare an amended packet with the version it supersedes (Part 05 §15.6).

    Where the superseded version cannot be read, the comparison is an evaluation that did not
    complete and not a finding (Part 05 §§9.4 and 9.5).
    """
    import duckdb

    current = packet.manifest.entry
    try:
        if superseded is None:
            if not packet.location.is_local:
                return
            superseded = amendment.predecessor(packet.location.path, current)
        if superseded is None:
            return
        earlier = Packet(packet.location, Manifest.from_dict(superseded)).with_declarations(*documents)
    except (OSError, ValueError, PacketError) as exc:
        report.record_evaluation(
            "core", EvaluationStatus.INCOMPLETE, rule="amendment", detail=str(exc).splitlines()[0][:160]
        )
        return
    classes: dict[str, str | None] = {}
    kinds: dict[str, str | None] = {}
    for version in (earlier, packet):
        for resource in version.resources():
            classes[resource.resource_id] = resource.content_class
            kinds[resource.resource_id] = resource.kind

    def located(version: Packet) -> Any:
        named = {resource.resource_id for resource in version.resources(kind="table")}
        return lambda resource_id: version.path(resource_id) if resource_id in named else None

    with spill_beside(packet) as spill:
        connection = bounded(duckdb.connect(), LIMITS if limits is None else limits, spill)
        try:
            found = amendment.compare(
                connection,
                current,
                superseded,
                tables=tables,
                classes=classes,
                kinds=kinds,
                current_path=located(packet),
                superseded_path=located(earlier),
            )
        except (OSError, PacketError, pa.ArrowException, duckdb.Error) as exc:
            report.record_evaluation(
                "core", EvaluationStatus.INCOMPLETE, rule="amendment", detail=str(exc).splitlines()[0][:160]
            )
            return
        finally:
            connection.close()
    for finding in found:
        owner = None if finding.resource is None else report.resource_owner(finding.resource)
        report.add(finding.check, finding.message, finding.rows, registry=owner)


def check_packet_manifest(
    root: Location | str | Path, *, advisory: bool = False, manifest: bytes | None = None
) -> tuple[Report, Bound | None]:
    """Run Part 04 §10's phases up to `registry_binding`, from the manifest's bytes.

    Needs no opened packet, so a manifest a reader refuses -- one repeating a member or a resource
    ID -- still gets its findings.

    Parameters
    ----------
    root : Location, str, or Path
        The packet root, against which descriptor paths resolve.
    advisory : bool, default False
        Recorded on the report.
    manifest : bytes, optional
        The manifest to check. Defaults to the root's `packet.json`.

    Returns
    -------
    Report
        The manifest and registry findings, and every acquired registry's complete result.
    Bound or None
        What binding established, or None where an earlier phase stopped evaluation.
    """
    report = Report(advisory=advisory)
    location = Location.of(root)
    issues: list[Issue] = []
    try:
        raw = location.join(MANIFEST_FILENAME).read_bytes() if manifest is None else manifest
    except Exception as exc:  # noqa: BLE001 - what a store raises on a failed read is its own business
        report.add(check_table.PACKET_MANIFEST_INVALID_JSON, f"no readable {MANIFEST_FILENAME} at {location}: {exc}")
        return report, None
    report.bound = named_registries(raw)
    document = check_manifest(raw, issues)
    bound = None if document is None else bind_registries(location, document, issues)
    for issue in issues:
        report.add(issue.check, issue.message, issue.rows, registry=issue.registry)
    if bound is not None:
        for name, context in bound.contexts.items():
            report.record_registry(name, context, directs_checks=bound.directs(name), core=name == bound.core_id)
    return report, bound


__all__ = [
    "check_packet_manifest",
    "validate",
    "verify_order",
]
