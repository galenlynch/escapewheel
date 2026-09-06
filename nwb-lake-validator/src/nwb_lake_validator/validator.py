"""Validate a packet against the registry it declares.

Four layers, in ``09`` §10's order: the manifest's shape, the registry it embeds, each
resource's physical schema, then the rules.

The split between SQL and this module is not a matter of convenience (R12 §4). SQL covers
what the data *says* — values, keys, references, vocabularies. This module covers how it is
*stored* — physical order, file presence, column types — because a query cannot see any of
that, and a storage-layer check written as SQL fails silently rather than loudly.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import tempfile
from collections import Counter
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from nwb_lake_reader import Packet, PacketError, ResourceUnreadableError, sql_name
from nwb_lake_reader.location import SOURCES_FILENAME

from .generate import adjacency_settles_uniqueness, concerns, generate
from .stores import StoreUnreachable, digest, listing, read_member

#: Registry column type -> the Arrow type a conforming writer must emit (R3 §2.1).
ARROW_TYPES = {
    "string": "string",
    "int32": "int32",
    "int64": "int64",
    "float32": "float",
    "float64": "double",
    "bool": "bool",
    "date": "date32[day]",
    "timestamp": "timestamp[us, tz=UTC]",
    "json_string": "string",
}


@dataclass(frozen=True)
class Finding:
    """One validation finding.

    Attributes
    ----------
    level : str
        ``error``, ``warning``, or ``info``.
    check : str
        Identifier of the check that produced it.
    message : str
        What went wrong.
    rows : tuple
        Offending rows, truncated. For SQL checks these are the query's result.
    extension : str or None
        The extension whose table this is about, or None for core. R17 §4 requires the two be
        reported separately: a finding against an extension's table is not a finding against the
        packet's **core** conformance, because a core validator is not required to hold that
        extension's schema at all.
    """

    level: str
    check: str
    message: str
    rows: tuple[tuple[str, ...], ...] = ()
    extension: str | None = None


@dataclass
class Report:
    """The outcome of validating a packet.

    Attributes
    ----------
    findings : list of Finding
        Every finding, in the order the layers ran.
    advisory : bool
        Whether advisory rules were run (R26 §5). Recorded because an empty advisory
        result is otherwise ambiguous between "none fired" and "not asked for".
    """

    findings: list[Finding] = field(default_factory=list)
    advisory: bool = False

    @property
    def errors(self) -> int:
        """How many error-level findings were produced, core and extensions together."""
        return sum(f.level == "error" for f in self.findings)

    @property
    def warnings(self) -> int:
        """How many warning-level findings were produced."""
        return sum(f.level == "warning" for f in self.findings)

    @property
    def passed(self) -> bool:
        """Whether the packet is valid **as core**. Warnings do not make a packet invalid.

        Advisory rules cannot be ``error`` (R26 §3), so this is invariant under the
        ``advisory`` flag: asking for more to read never changes the verdict.

        An extension's findings are excluded (R17 §4). A packet stays core-conformant carrying
        extension registries a validator cannot parse, so one it *can* parse must not be able to
        change the core verdict either -- otherwise holding the schema would make a packet fail
        that passes without it.
        """
        return sum(f.level == "error" and f.extension is None for f in self.findings) == 0

    def extension_passed(self, extension: str) -> bool:
        """Whether one extension's tables validated."""
        return sum(f.level == "error" and f.extension == extension for f in self.findings) == 0

    @property
    def extensions(self) -> tuple[str, ...]:
        """Extensions this report says anything about."""
        return tuple(dict.fromkeys(f.extension for f in self.findings if f.extension is not None))

    def add(
        self,
        level: str,
        check: str,
        message: str,
        rows: Sequence[Sequence[Any]] = (),
        extension: str | None = None,
    ) -> None:
        """Record a finding.

        Parameters
        ----------
        level : str
            ``error``, ``warning``, or ``info``.
        check : str
            Identifier of the check.
        message : str
            What went wrong.
        rows : sequence, optional
            Offending rows; only the first five are kept.
        """
        self.findings.append(
            Finding(level, check, message, tuple(tuple(str(v) for v in row) for row in list(rows)[:5]), extension)
        )

    def to_dict(self, packet_id: str) -> dict[str, Any]:
        """Render the report as the JSON structure ``05`` describes.

        Parameters
        ----------
        packet_id : str
            The packet this report concerns.

        Returns
        -------
        dict
            The report.
        """
        return {
            "packet_id": packet_id,
            "status": "passed" if self.passed else "failed",
            # An empty advisory list is ambiguous between "none fired" and "not run" (R26 §5).
            "advisory": self.advisory,
            "validator": {"name": "nwb_lake_validator", "version": _version()},
            "summary": {"errors": self.errors, "warnings": self.warnings},
            "findings": [
                {"level": f.level, "check": f.check, "message": f.message, "rows": [list(r) for r in f.rows]}
                for f in self.findings
            ],
        }


def _version() -> str:
    from . import __version__

    return __version__


def registry_meta_schema() -> dict[str, Any]:
    """R2 §9's published meta-schema, as this distribution vendors it.

    Public because R57 §2.1 makes its `$id` something a writer has to state: a document declares
    which meta-schema governs it, and the writer that emits the declaration must not keep its own
    copy of the URI.
    """
    text = importlib_resources.files("nwb_lake_validator").joinpath("schemas/registry.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


def _check_embedded_registry(packet: Packet, embedded: Mapping[str, Any], report: Report) -> None:
    """Layer 1: the registry the packet carries (R2 §8, §9)."""
    for error in jsonschema.Draft202012Validator(registry_meta_schema()).iter_errors(embedded):
        report.add("error", "registry.schema", f"{'/'.join(str(p) for p in error.path)}: {error.message}")
    declared = packet.manifest.registry_version
    if embedded.get("registry_version") != declared:
        report.add(
            "error",
            "registry.version_mismatch",
            f"manifest says {declared}, embedded registry says {embedded.get('registry_version')}",
        )


def _check_materialization_provenance(packet: Packet, report: Report) -> None:
    """Layer 1c: every analysis resource names the run that produced it (R31 §5).

    Not SQL, and deliberately. `processing_run_id` lives in the manifest, which no query sees,
    so a Tier 1 foreign key cannot reach it -- a rule written in SQL here would pass silently
    on a packet whose manifest names a run that does not exist, which is the failure mode R12
    was written about.
    """
    analysis = [r for r in packet.resources() if r.layer == "analysis"]
    if not analysis:
        return

    for resource_id in sorted(r.resource_id for r in analysis if not r.entry.get("processing_run_id")):
        report.add(
            "error",
            "provenance.no_processing_run",
            f"{resource_id} is derived but names no processing_run_id (R31 §3)",
        )

    named = {r.entry["processing_run_id"] for r in analysis if r.entry.get("processing_run_id")}
    if not named:
        return
    try:
        runs = packet.table("core.processing_runs")
    except PacketError:
        report.add(
            "error",
            "provenance.no_processing_runs_table",
            f"{len(named)} resource(s) name a processing run but the packet carries no core.processing_runs",
        )
        return
    # A manifest names a run and the table numbers it (R53 §2), so the join is across the
    # `*_name` column. Both are accepted: a packet built before R53 has names in both places.
    known = set(runs.column("processing_run_id").to_pylist())
    if "processing_run_name" in runs.column_names:
        known |= {n for n in runs.column("processing_run_name").to_pylist() if n is not None}
    for missing in sorted(named - known):
        report.add(
            "error",
            "provenance.unknown_processing_run",
            f"processing_run_id {missing!r} appears in no row of core.processing_runs (R31 §5)",
        )


def _check_time_origin(packet: Packet, report: Report) -> None:
    """Layer 1d: `t_zero_tick` is the earliest observation start on the reference clock (R39 §2.4).

    Not SQL, and for the reason R39 §2.4 gives: the minimum is taken across clocks, and getting
    a clock's `start_tick` onto the reference is R13's anchor-based mapping -- arithmetic no
    query expresses. A packet declaring no origin is conforming and is not checked; one that
    declares a *wrong* origin silently shifts every second a consumer derives, which is why the
    check exists at all.
    """
    from nwb_lake_reader.clocks import align, anchors, declared_bound, reference_clock

    try:
        sessions = packet.table("core.sessions")
        intervals = packet.table("core.clock_observation_intervals")
    except PacketError:
        return
    if "t_zero_tick" not in sessions.column_names or not intervals.num_rows:
        return
    declared = [t for t in sessions.column("t_zero_tick").to_pylist() if t is not None]
    if not declared:
        return

    try:
        reference, by_clock = reference_clock(packet), anchors(packet)
        bound = declared_bound(packet)
    except (PacketError, ValueError) as refused:
        report.add("error", "time.origin_unmappable", f"t_zero_tick is declared but {refused}")
        return

    starts: list[int] = []
    for clock, start in zip(
        intervals.column("clock_id").to_pylist(), intervals.column("start_tick").to_pylist(), strict=True
    ):
        if clock == reference:
            starts.append(int(start))
            continue
        if clock not in by_clock:
            report.add(
                "error",
                "time.origin_unmappable",
                f"{clock} declares an observation window but no anchors, so the minimum R39 §2.1 "
                "defines cannot be taken",
                [(clock,)],
            )
            return
        converted, defined = align(np.array([start], dtype=np.int64), *by_clock[clock], bound=bound)
        if not defined[0]:
            report.add(
                "error",
                "time.origin_unmappable",
                f"{clock}'s observation start does not map to {reference} within the alignment "
                "bound, so no origin is defined (R39 §2.4)",
                [(clock, str(start))],
            )
            return
        starts.append(int(converted[0]))

    expected = min(starts)
    for stated in declared:
        # The writer's own estimator is not bit-reproducible from the packet -- it may have
        # fitted over anchors it then withheld -- so agreement is judged at R37 §3.3's
        # tolerance of one parent tick rather than exactly.
        if abs(int(stated) - expected) > 1:
            report.add(
                "error",
                "time.origin_not_earliest",
                f"t_zero_tick is {stated} but the earliest observation start on {reference} is {expected} (R39 §2.1)",
                [(str(stated), str(expected))],
            )


def _check_one_array(resource: Any, handle: Any, extents: Mapping[str, Any], report: Report) -> None:
    """Check one packet-owned array against the metadata document in its own store."""
    try:
        metadata = handle.metadata()
        actual = set(handle.codecs)
        rank = len(handle.shape)
    except (ResourceUnreadableError, OSError, ValueError, KeyError) as exc:
        report.add("error", "array.unreadable", f"{resource.resource_id}: {exc}")
        return

    if handle.zarr_format != 3:
        report.add(
            "error",
            "array.not_zarr_v3",
            f"{resource.resource_id} is packet-owned but stored as Zarr v{handle.zarr_format}; "
            "R21 §3.1 allows v2 only for an array the packet references",
        )

    declared = set(resource.codecs)
    if declared != actual:
        detail = []
        if undeclared := sorted(actual - declared):
            detail.append(f"the store uses {', '.join(undeclared)}, which the manifest omits")
        if unused := sorted(declared - actual):
            detail.append(f"the manifest declares {', '.join(unused)}, which the store does not use")
        report.add("error", "array.codecs_disagree_with_store", f"{resource.resource_id}: {'; '.join(detail)} (R15 §4)")

    if "transpose" in actual:
        report.add(
            "error",
            "array.transpose_codec",
            f"{resource.resource_id} uses the transpose codec, which R3 §5 forbids: axes are stored in the "
            "order the packet declares them",
        )

    if (grid := metadata.get("chunk_grid", {}).get("name")) != "regular":
        report.add(
            "error",
            "array.irregular_chunk_grid",
            f"{resource.resource_id} declares a {grid!r} chunk grid; R3 §7.1 requires a regular one",
        )

    if "fill_value" not in metadata:
        report.add(
            "error", "array.no_fill_value", f"{resource.resource_id} declares no fill_value, which R3 §7.1 requires"
        )

    asset = resource.entry.get("array_asset_id")
    if asset is None:
        report.add(
            "error",
            "array.no_array_asset_id",
            f"{resource.resource_id} names no array_asset_id, so core.array_dimensions cannot reach it",
        )
        return
    if not (declared := extents.get(str(asset), {})):
        return
    if set(declared) != set(range(rank)):
        report.add(
            "error",
            "array.rank_disagrees_with_dimensions",
            f"{resource.resource_id} has rank {rank} but core.array_dimensions gives axis_index "
            f"{sorted(declared) or 'none'} for {asset!r}; R3 §5 requires one row per stored axis",
        )
        return
    # An axis whose coordinates are a table has one row per position, so that count is its length.
    # The external path checks this too; a packet-owned array gets the stronger check for free,
    # since its shape is already in hand.
    offending = [
        (axis, length, int(handle.shape[axis]))
        for axis, length in sorted(declared.items())
        if length is not None and int(handle.shape[axis]) != length
    ]
    if offending:
        report.add(
            "error",
            "array.shape_disagrees_with_coordinates",
            f"{resource.resource_id}: {len(offending)} axis/axes are not the length their coordinate table gives them",
            [(f"axis {axis}", f"{rows} rows", f"stored {stored}") for axis, rows, stored in offending],
        )


def _check_packet_owned_arrays(packet: Packet, report: Report) -> None:
    """Layer 1c: every packet-owned array against its own Zarr metadata (R15 §4, level 2).

    Always runs, and needs no Zarr: a Zarr array's metadata is a JSON document in the store,
    which `ArrayResource` parses directly. The packet owns these bytes, so an array it
    describes wrongly is a defect in the packet rather than in the reader's situation. An
    external array is level 3 and stays with the requested mode, where
    `_check_codec_declarations` already reports it as `info`.

    Storage, not values, so the shim and not SQL (R12 §4). No query can see a chunk grid, and
    a codec the manifest omits is exactly the kind of disagreement a SQL rule passes silently.
    """
    # A resource naming a source is not packet-owned whatever `external` says, and `_check_sources`
    # has already reported the contradiction; resolving it here would raise instead of report.
    owned = [
        r for r in packet.resources(kind="dense_array_asset") if not r.is_external and r.source is None
    ]
    if not owned:
        return
    extents = _declared_extents(packet)
    if not extents:
        report.add(
            "error",
            "array.no_array_dimensions_table",
            f"{len(owned)} packet-owned array(s) but no core.array_dimensions, so no axis is named (R3 §3.0)",
        )
    for resource in owned:
        _check_one_array(resource, packet.array_resource(resource.resource_id), extents, report)


#: The codec floor, per Zarr version (R21 §3.3). A codec's readability is a property of the
#: pair `(zarr_format, codec)` rather than of the codec: `gzip` is in R3 §7.2's baseline and
#: Zarr.jl reads it in v3 and not in v2, because the two versions name codecs differently and
#: the library registers only the v3 spelling. A MUST that one of the two target languages
#: cannot honour is not a floor, so v2's row omits it.
FLOOR = {
    "zarr_v3": frozenset({"none", "gzip", "zstd", "blosc", "sharding_indexed"}),
    "zarr_v2": frozenset({"none", "zstd", "blosc"}),
}


def _check_codec_declarations(packet: Packet, report: Report, resolved: bool = False) -> None:
    """Layer 1b: manifest-internal codec consistency (R15 §4, level 1).

    Both sides are manifest fields, so this holds offline. Whether a declared codec matches
    the array's actual metadata is level 2 for packet-owned arrays and level 3 -- the
    requested external mode -- for the rest.

    Parameters
    ----------
    resolved : bool, default False
        Whether level 3 ran, in which case the external claims are not reported as unchecked.
    """
    declared: set[str] = set()
    for resource in packet.resources():
        declared |= set(resource.codecs)
        # R14 §2.3's "absolute uri implies external" and R21 §3.2's "zarr_v2 implies external"
        # are stated in the manifest JSON Schema, which refuses such a packet at open. Saying
        # them again here would be a second, weaker copy that never runs. The floor is not
        # expressible there -- it is a set relation between two fields -- so it lives here.
        profile = str(resource.entry.get("physical_profile", ""))
        if profile in FLOOR and (beyond := sorted(set(resource.codecs) - FLOOR[profile])):
            report.add(
                "info",
                "codec.outside_the_floor",
                f"{resource.resource_id} uses {', '.join(beyond)}, outside the {profile} floor; "
                "conforming but not portable by default (R14 §2.2)",
            )
    summary = set(packet.manifest.required_codecs)
    if declared != summary:
        detail = []
        if missing := sorted(declared - summary):
            detail.append(f"resources use {', '.join(missing)} but required_codecs omits them")
        if extra := sorted(summary - declared):
            detail.append(f"required_codecs lists {', '.join(extra)} that no resource uses")
        report.add("error", "manifest.required_codecs_is_the_union", "; ".join(detail))

    # An external resource's codecs, sha256 and size_bytes are claims the default mode does
    # not verify (R14 §2.3.1, R15 §4). Say so, rather than let "passed" imply otherwise. The
    # requested mode reports what it resolved instead, so the two never both speak.
    if not resolved and (names := [r.resource_id for r in packet.resources() if r.is_external]):
        report.add(
            "info",
            "external.unverified",
            f"{len(names)} external resource(s) not resolved; their codecs, sha256 and "
            "size_bytes are unverified claims",
            [(name,) for name in names],
        )


def _check_owned_digests(packet: Packet, report: Report) -> None:
    """R52 §2.3: recompute the digest of every packet-owned resource that records one.

    A disagreement is an **error**, where the external equivalent is one too but means something
    weaker. An external resource that changed is the world moving under a packet that never
    promised otherwise (R14 §2.3.1); a packet-owned file that changed is the packet being wrong
    about itself, and it is the premise R35 §2 spends to bound revalidation.

    A resource recording no digest is not checked, and the count is reported rather than passed
    over -- every packet built before R52 records none.
    """
    checked, matched, skipped = 0, 0, []
    for resource in packet.resources():
        if resource.is_external:
            continue
        entry = resource.entry
        if (claimed := entry.get("sha256")) is None:
            skipped.append(resource.resource_id)
            continue
        try:
            actual = digest(str(packet.root / str(entry.get("uri", ""))))
        except StoreUnreachable as exc:
            report.add("error", "resource.missing", f"{resource.resource_id}: {exc}")
            continue
        checked += 1
        if actual == claimed:
            matched += 1
        else:
            report.add(
                "error",
                "owned.sha256",
                f"{resource.resource_id}: digests to {actual[:16]}…, manifest claims {claimed[:16]}… — "
                "a packet-owned file is immutable (R14 §2.3) and R35 §2 bounds revalidation on that",
            )
    if skipped:
        report.add(
            "warning",
            "owned.no_checksum",
            f"{len(skipped)} packet-owned resource(s) record no sha256, so immutability was not "
            "checked for them (R52 §2.3)",
            [(name,) for name in skipped[:20]],
        )
    if checked:
        report.add(
            "info",
            "owned.verified",
            f"{matched} of {checked} packet-owned resource(s) digested to what the manifest records",
        )


def _check_sources(packet: Packet, report: Report) -> None:
    """R80: what a source declaration must be, decided without reaching the network.

    Three things are structural and one is not. A `source` names a body of data rather than a
    location, so the entry's `uri` MUST be relative to it (R80 §2.1) and the entry MUST be
    external, since the mechanism exists for bytes the packet does not own. `sources.json` MUST
    NOT be a declared resource (R80 §2.3): being outside the manifest is what keeps R14 §2.3's
    immutability off it, and a packet that declared it would freeze the one file that has to
    stay editable.

    Whether a source **resolves** is not structural and is reported rather than failed. R80 §2.4
    makes an unresolved source a fact about the reader's situation -- which mirrors it can reach
    -- and R14 §2.3.2 keeps structural validation off the network, so this reports what the
    packet names and leaves reachability to the mode that asks for it.
    """
    named: dict[str, list[str]] = {}
    for resource in packet.resources():
        source = resource.source
        if source is None:
            if Path(str(resource.entry.get("uri", ""))).name == SOURCES_FILENAME:
                report.add(
                    "error",
                    "sources.declared",
                    f"{resource.resource_id} declares {SOURCES_FILENAME} as a resource; R80 §2.3 keeps it "
                    "outside the manifest so R14 §2.3's immutability does not reach it",
                )
            continue
        named.setdefault(source, []).append(resource.resource_id)
        if not resource.is_external:
            report.add(
                "error",
                "source.not_external",
                f"{resource.resource_id} names source {source!r} without external: true; a source locates "
                "bytes the packet does not own (R80 §2.1)",
            )
        if "://" in resource.uri:
            report.add(
                "error",
                "source.absolute_uri",
                f"{resource.resource_id} names source {source!r} and an absolute uri {resource.uri!r}; "
                "where a source is named the uri is a path under it (R80 §2.1)",
            )
    if not named:
        return
    located = dict(packet.location.sources)
    unresolved = sorted(name for name in named if name not in located)
    report.add(
        "info",
        "sources.declared_count",
        f"{len(named)} source(s) named by {sum(len(v) for v in named.values())} resource(s); "
        f"{len(named) - len(unresolved)} located by a resolution document",
    )
    if unresolved:
        # A fact, not a defect (R80 §2.4): the packet is conforming and this reader cannot reach
        # those bytes. Reported so a report says which, rather than leaving it to a later failure.
        report.add(
            "info",
            "sources.unresolved",
            f"{len(unresolved)} source(s) no available resolution document locates (R80 §2.4)",
            [(name, ", ".join(named[name][:3])) for name in unresolved[:20]],
        )


def _resolve_external(packet: Packet, report: Report, checksums: bool = False, store_digests: bool = False) -> None:
    """Level 3 (R15 §4): resolve external URIs and check what was claimed about them.

    Requested explicitly, never by default. R14 §2.3.2 keeps structural validation off the
    network because reachability, credentials and whether the validator is offline are
    properties of the reader's situation rather than of the packet.

    Findings are reported against the resource entry. An unreachable resource is a `warning`
    and not an error: it says the claim could not be checked, which is the same standing the
    default mode gives it, while a claim that resolved and *disagrees* is an error.

    **A check with nothing to compare against is reported, not counted as a pass.** A manifest
    need not record `sha256` or `size_bytes`, and a Zarr v3 array does not carry its codecs where
    `_stored_codecs` reads them -- so any of the three can be absent on a resource that resolves
    cleanly. `external.verified` therefore names what it compared rather than asserting a resource
    was "checked", and a requested digest with nothing to compare gets its own finding.

    Parameters
    ----------
    checksums : bool, default False
        Also recompute `sha256`, which reads every byte -- 6.8 GB for a session's LFP, 75 s from
        local disk and 88 s from S3 -- where the rest of this mode is a list operation. Off
        separately for that reason.
    store_digests : bool, default False
        Also compare each declared member's `store_digest` against what the store reports now
        (R51 §2.3). The listing already performed carries the values, so this is the same 1.31 s
        the level below it costs, and it answers a weaker question than `checksums` does.
    """
    checked = 0
    compared: Counter[str] = Counter()
    unchecksummed: list[str] = []
    # Only read core.array_dimensions where an external array would use it.
    external_arrays = [r for r in packet.resources(kind="dense_array_asset") if r.is_external]
    extents = _declared_extents(packet) if external_arrays else {}
    for resource in packet.resources():
        if not resource.is_external:
            continue
        fields = _compare_external(resource, report, checksums, store_digests, extents)
        if fields is None:
            continue
        checked += 1
        compared.update(fields)
        if checksums and "sha256" not in fields:
            unchecksummed.append(resource.resource_id)
    if unchecksummed:
        report.add(
            "warning",
            "external.no_checksum",
            f"{len(unchecksummed)} of {checked} resolved resource(s) record no sha256, so a digest "
            "was asked for and nothing was compared against (R36 §2.4)",
            [(name,) for name in unchecksummed],
        )
    if checked:
        did = ", ".join(f"{count} {field}" for field, count in sorted(compared.items())) or "nothing"
        report.add("info", "external.verified", f"{checked} external resource(s) resolved; compared {did}")


def _compare_external(
    resource: Any,
    report: Report,
    checksums: bool,
    store_digests: bool = False,
    extents: Mapping[str, Any] | None = None,
) -> list[str] | None:
    """Check one external resource, returning the fields actually compared.

    None means the store could not be reached, which is already reported and leaves the resource
    out of every count: nothing about it was established either way.
    """
    entry = resource.entry
    uri = str(entry.get("uri", ""))
    try:
        found = listing(uri)
    except StoreUnreachable as exc:
        report.add("warning", "external.unreachable", f"{resource.resource_id}: {exc}")
        return None
    fields = []
    if (declared := entry.get("members")) is not None:
        fields.extend(_compare_members(resource, declared, found, report, store_digests))
    if (claimed := entry.get("size_bytes")) is not None:
        fields.append("size_bytes")
        if found.size_bytes != claimed:
            report.add(
                "error",
                "external.size_bytes",
                f"{resource.resource_id}: {found.size_bytes:,} bytes over {len(found.members)} object(s), "
                f"manifest claims {claimed:,}",
            )
    if extents:
        fields.extend(_compare_shape(resource, uri, found, extents, report))
    if (declared := set(resource.codecs)) and (stored := _stored_codecs(uri, found)) is not None:
        fields.append("codecs")
        if stored != declared:
            report.add(
                "error",
                "external.codecs",
                f"{resource.resource_id}: stores {', '.join(sorted(stored)) or 'no codec'}, "
                f"manifest declares {', '.join(sorted(declared))}",
            )
    if checksums and (claimed_sha := entry.get("sha256")) is not None:
        try:
            actual = digest(uri)
        except StoreUnreachable as exc:
            report.add("warning", "external.unreachable", f"{resource.resource_id}: {exc}")
            return None
        fields.append("sha256")
        if actual != claimed_sha:
            report.add(
                "error",
                "external.sha256",
                f"{resource.resource_id}: digests to {actual[:16]}…, manifest claims {claimed_sha[:16]}…",
            )
    return fields


def _compare_members(resource: Any, declared: Any, found: Any, report: Report, store_digests: bool) -> list[str]:
    """Check a declared member list against what the store holds (R51 §2.1).

    This is what makes level 3a per-member rather than aggregate: `size_bytes` on the resource is
    a total, so two members changing in opposite directions leave it correct. It is also what
    enforces R51 §2.1's rule that a digested listing is the declared one -- where the declared
    members and the store agree, R36 §2.2's canonical listing is the same either way, so `sha256`
    and `members` cannot describe different things.
    """
    fields = ["members"]
    held = {member.key: member for member in found.members}
    claimed = {str(entry.get("key", "")): entry for entry in declared}
    if missing := sorted(claimed.keys() - held.keys()):
        report.add(
            "error",
            "external.members",
            f"{resource.resource_id}: {len(missing)} declared member(s) the store does not hold",
            [(key,) for key in missing[:20]],
        )
    if extra := sorted(held.keys() - claimed.keys()):
        report.add(
            "error",
            "external.members",
            f"{resource.resource_id}: the store holds {len(extra)} member(s) the manifest does not "
            "declare, so a digest over the declared listing would not describe it",
            [(key,) for key in extra[:20]],
        )
    if sized := sorted(
        key
        for key in claimed.keys() & held.keys()
        if claimed[key].get("size_bytes") is not None and claimed[key]["size_bytes"] != held[key].size_bytes
    ):
        report.add(
            "error",
            "external.members",
            f"{resource.resource_id}: {len(sized)} member(s) differ in size from the manifest",
            [(key, claimed[key]["size_bytes"], held[key].size_bytes) for key in sized[:20]],
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
            "error",
            "external.store_digest",
            f"{resource.resource_id}: {len(changed)} member(s) changed in place since recording",
            [(key,) for key in changed[:20]],
        )
    if skipped:
        report.add(
            "warning",
            "external.no_store_digest",
            f"{resource.resource_id}: {len(skipped)} of {len(claimed)} member(s) not checked -- the "
            "manifest recorded no store digest, or the store offers none (R51 §2.3)",
            [(key,) for key in skipped[:20]],
        )
    if compared:
        fields.append("store_digest")
    return fields


def _stored_metadata(uri: str, found: Any) -> Mapping[str, Any] | None:
    """Return the Zarr metadata document under a prefix, or None where there is not one.

    Read through the same store the listing came from, so an object store answers it the way a
    filesystem does. One request either way, and both callers share it.
    """
    for key in (".zarray", "zarr.json"):
        if any(member.key == key for member in found.members):
            try:
                parsed = json.loads(read_member(uri, key))
            except (ValueError, StoreUnreachable):
                return None
            return parsed if isinstance(parsed, Mapping) else None
    return None


def _stored_codecs(uri: str, found: Any) -> set[str] | None:
    """Codecs a Zarr v2 array declares, or None where the metadata is not v2 or not readable."""
    if not any(member.key == ".zarray" for member in found.members):
        return None
    parsed = _stored_metadata(uri, found)
    if parsed is None:
        return None
    names = {str(f["id"]) for f in parsed.get("filters") or []}
    if compressor := parsed.get("compressor"):
        names.add(str(compressor["id"]))
    return names


def _declared_extents(packet: Packet) -> dict[str, dict[int, int | None]]:
    """Per array asset, the axes `core.array_dimensions` names and the length each implies.

    An axis whose coordinates are a rule -- R20's origin and step -- fixes spacing and not
    extent, so its length is None and only its presence is checkable. An axis whose coordinates
    are a table has one row per position, so that table's row count for the asset and axis *is*
    the axis length. This is the shape a packet asserts without ever storing a shape (R3 §3.0:
    the array declares its own, and the tables must not restate it).
    """
    # Read only what is there. A column the registry requires and a packet omits is the schema
    # layer's finding to report; crashing here would replace that finding with a traceback.
    try:
        names = set(packet.table_resource("core.array_dimensions").schema().names)
        wanted_columns: list[str] = [c for c in ("array_asset_id", "axis_index", "coordinate_resource") if c in names]
        if not {"array_asset_id", "axis_index"} <= set(wanted_columns):
            return {}
        rows = packet.table("core.array_dimensions", columns=wanted_columns)
    except PacketError:
        return {}
    coordinates_named = (
        rows.column("coordinate_resource").to_pylist()
        if "coordinate_resource" in wanted_columns
        else [None] * rows.num_rows
    )
    extents: dict[str, dict[int, int | None]] = {}
    wanted: dict[str, list[tuple[str, int]]] = {}
    for asset, axis, coordinate in zip(
        rows.column("array_asset_id").to_pylist(),
        rows.column("axis_index").to_pylist(),
        coordinates_named,
        strict=True,
    ):
        if asset is None or axis is None:
            continue
        extents.setdefault(str(asset), {})[int(axis)] = None
        if coordinate:
            wanted.setdefault(str(coordinate), []).append((str(asset), int(axis)))
    for resource_id, pairs in wanted.items():
        # Only a coordinate table keyed by (array_asset_id, axis_index) has one row per position
        # of one axis, which is what makes its row count that axis's length. `core.unit_electrodes`
        # is a coordinate resource and is not keyed that way -- a unit's electrodes are a subset,
        # not an enumeration of the axis -- so it says nothing about extent and is skipped.
        try:
            names = set(packet.table_resource(resource_id).schema().names)
        except PacketError:
            continue
        if not {"array_asset_id", "axis_index"} <= names:
            continue
        coordinates = packet.table(resource_id, columns=["array_asset_id", "axis_index"])
        counts: dict[tuple[str, int], int] = {}
        for asset, axis in zip(
            coordinates.column("array_asset_id").to_pylist(),
            coordinates.column("axis_index").to_pylist(),
            strict=True,
        ):
            if asset is not None and axis is not None:
                counts[(str(asset), int(axis))] = counts.get((str(asset), int(axis)), 0) + 1
        for pair in pairs:
            if pair in counts:
                extents[pair[0]][pair[1]] = counts[pair]
    return extents


def _compare_shape(resource: Any, uri: str, found: Any, extents: Mapping[str, Any], report: Report) -> list[str]:
    """Check an external array's stored shape against what the packet's tables assert (R3 §3.0).

    This is the check that catches a change actually invalidating the packet. A re-generated
    array with a different channel count leaves `core.array_channels` describing positions that
    are not there; one at a different sample rate leaves `core.array_dimensions` wrong. Neither
    changes what the packet claims about the array's *values*, which it claims nothing about --
    which is why this and not a content digest is what an external array needs verified.

    Free: the metadata document is read for codecs anyway, and both go through one request.
    """
    asset = resource.entry.get("array_asset_id")
    if asset is None or not (declared := extents.get(str(asset))):
        return []
    metadata = _stored_metadata(uri, found)
    if metadata is None or not isinstance(shape := metadata.get("shape"), list):
        return []
    if len(shape) != len(declared):
        report.add(
            "error",
            "external.array_rank",
            f"{resource.resource_id} is stored with rank {len(shape)} but core.array_dimensions "
            f"gives axis_index {sorted(declared)} for {asset!r}; R3 §5 requires one row per stored axis",
        )
        return ["rank"]
    offending = [
        (axis, length, int(shape[axis]))
        for axis, length in sorted(declared.items())
        if length is not None and axis < len(shape) and int(shape[axis]) != length
    ]
    if offending:
        report.add(
            "error",
            "external.array_shape",
            f"{resource.resource_id}: {len(offending)} axis/axes are not the length the packet's "
            "coordinate tables give them",
            [(f"axis {axis}", f"{rows} rows", f"stored {stored}") for axis, rows, stored in offending],
        )
    return ["rank", "shape"] if any(length is not None for length in declared.values()) else ["rank"]


def _check_schemas(packet: Packet, tables: Mapping[str, Any], report: Report) -> dict[str, Any]:
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
            report.add("error", "resource.missing", str(exc))
            continue
        present[resource_id] = handle
        for column in spec["columns"]:
            _check_column(resource_id, column, schema, report)
    return present


def _check_column(resource_id: str, column: Mapping[str, Any], schema: Any, report: Report) -> None:
    """Check one column's presence and type against the registry."""
    if column["name"] not in schema.names:
        if column["presence"] != "optional":
            report.add(
                "error",
                "schema.column_absent",
                f"{resource_id}.{column['name']} absent (presence={column['presence']})",
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
            "error",
            "schema.column_type",
            f"{resource_id}.{column['name']} is {actual}, registry declares {column['type']}",
        )


#: Rows per batch when checking physical order, and how many breaks are worth reporting.
#: Read whole, a real session's spike table is a quarter of a billion rows across five sort
#: columns -- four of them strings -- which as Python objects is around a billion of them and
#: will take a workstation down. Batched, peak memory is this many rows however large the
#: table, and a reader only needs to see that the order broke and where it first did.
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
    separately compared every column twice, which on the spike table's five-column key was the
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


def _check_ordering(
    tables: Mapping[str, Any],
    present: Mapping[str, Any],
    report: Report,
    scan: Collection[str] | None = None,
) -> set[str]:
    """Layer 3: declared sort order, and the uniqueness that order settles (R10 §2, R12 §2).

    One pass answers both. A table sorted by its primary key puts duplicates next to each
    other, so comparing neighbours — which this scan already does to find descents — decides
    uniqueness too. `generate` leaves the `GROUP BY` out for those tables: on 287 M spikes it
    spilled 26 GB, because the key is four string columns and an aggregate materialises every
    one of them, while the scan reads them in order and holds one batch.

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
        if not spec.get("sort"):
            continue
        if _scan_one_ordering(resource_id, handle, spec, report):
            unsound.add(resource_id)
    return unsound


def _scan_one_ordering(resource_id: str, handle: Any, spec: Mapping[str, Any], report: Report) -> bool:
    """One table's ordering scan. True where uniqueness must fall back to the aggregate."""
    keys = spec["sort"]
    unique = spec["primary_key"] if adjacency_settles_uniqueness(spec) else None
    offending: list[tuple[int, Any, Any]] = []
    duplicated: list[tuple[int, Any]] = []
    tail: tuple[Any, ...] | None = None
    start = 0
    try:
        keys, unique, batches = _ordering_scan(handle, keys, unique)
    except (OSError, pa.ArrowException) as exc:
        report.add("error", "resource.unreadable", f"{resource_id}: {exc}")
        return False
    damaged = None
    while True:
        # Stepped rather than iterated, so a page that fails to decompress becomes a finding
        # instead of a traceback -- without wrapping the scan body, where the same exception type
        # would mean something else. Streaming is not negotiable here: this table is 287 M rows,
        # and holding its key columns is the difference between one batch and 26 GB.
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
        tail = _row_at(batch, keys, batch.num_rows - 1)
        start += batch.num_rows
        if len(offending) >= ORDER_REPORT and len(duplicated) >= ORDER_REPORT:
            break
    if damaged is not None:
        # The order cannot be established, so nothing partial is reported for it: what the scan
        # saw before the damage says nothing about the file as a whole.
        report.add("error", "resource.unreadable", f"{resource_id}: {damaged}")
        return False
    if offending:
        report.add(
            "warning",
            f"{resource_id}.physical_order",
            f"rows are not in declared sort order ({', '.join(keys)})",
            [(f"row {i}", str(prev), str(cur)) for i, prev, cur in offending[:ORDER_REPORT]],
        )
        # Adjacency settles uniqueness only for a file actually in order: a duplicate anywhere but
        # beside its twin is invisible to a scan of neighbours. Ordering is a warning by design --
        # a packet in the wrong order still conforms -- so uniqueness falls back to the aggregate
        # rather than being escalated or skipped.
        return bool(unique)
    if duplicated:
        report.add(
            "error",
            f"{resource_id}.primary_key_unique",
            "duplicate primary key",
            [(f"row {i}", str(row)) for i, row in duplicated[:ORDER_REPORT]],
        )
    return False


class OrderViolation(Exception):
    """A stream of batches is not in the order it declares, or repeats a key."""


def verify_order(batches: Iterable[Any], keys: Sequence[str], unique: Sequence[str] | None = None) -> Iterator[Any]:
    """Yield batches, raising if one sorts before its predecessor or repeats the key.

    The same comparison :func:`_check_ordering` makes against a written file, made instead
    against the batches on their way into one. It is offered because a writer is the one caller
    that can establish a file's order without reading the file: the rows pass through its hands
    already, so the check costs the comparison and not the 467 MB re-read that finding the same
    answer afterwards costs on a quarter of a billion spikes.

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
        On the first row that breaks the declared order, naming where it is.
    """
    tail: tuple[Any, ...] | None = None
    start = 0
    for batch in batches:
        if batch.num_rows:
            first = _row_at(batch, keys, 0)
            if tail is not None and _sortable(first) < _sortable(tail):
                raise OrderViolation(f"row {start} sorts before the row above it: {tail} then {first}")
            descents, repeats = _breaks(batch, keys, unique)
            if descents:
                offset = descents[0]
                raise OrderViolation(
                    f"row {start + offset} sorts before the row above it: "
                    f"{_row_at(batch, keys, offset - 1)} then {_row_at(batch, keys, offset)}"
                )
            if unique:
                if tail is not None and _row_at(batch, unique, 0) == _tail_key(tail, keys, unique):
                    raise OrderViolation(f"row {start} repeats the key above it: {_row_at(batch, unique, 0)}")
                if repeats:
                    offset = repeats[0]
                    raise OrderViolation(
                        f"row {start + offset} repeats the key above it: {_row_at(batch, unique, offset)}"
                    )
            tail = _row_at(batch, keys, batch.num_rows - 1)
            start += batch.num_rows
        yield batch


def _tail_key(tail: tuple[Any, ...], keys: Sequence[str], unique: Sequence[str]) -> tuple[Any, ...]:
    """Return the key columns of a row already pulled out over the sort columns."""
    index = {name: position for position, name in enumerate(keys)}
    return tuple(tail[index[name]] for name in unique)


#: Registry column type -> the DuckDB type used for the empty stand-in tables below.
_DDL = {
    "string": "VARCHAR",
    "int32": "INTEGER",
    "int64": "BIGINT",
    "float32": "FLOAT",
    "float64": "DOUBLE",
    "bool": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMPTZ",
    "json_string": "VARCHAR",
}


#: What a validating DuckDB connection is allowed to take. Left to itself it claims 80% of
#: system memory and every core, which on a real session's spike table means a quarter of a
#: billion rows grouped on a five-column key with a hundred-gigabyte budget -- enough to take
#: a workstation down.
#:
#: `temp_directory` is not optional here. An in-memory DuckDB has none by default, so a memory
#: limit has nothing to spill *to* and bounds nothing; the two settings only work as a pair.
#: The default follows the packet, because a temp directory on tmpfs -- which `/tmp` is on
#: several distributions -- spills into the memory the limit exists to protect.
#:
#: Measured on 247,758,402 spikes: bounded this way, every check passes at 4.0 GB peak, and
#: the one expensive check, `core.spike_events.primary_key_unique`, takes 78 s. So this costs
#: time and never correctness.
LIMITS: dict[str, Any] = {"memory_limit": "4GB", "threads": 4}


def _bounded(connection: Any, limits: Mapping[str, Any], spill: Path | None = None) -> Any:
    """Apply resource limits to a connection, ignoring settings this DuckDB lacks.

    `spill` supplies `temp_directory` when the caller has not, since a memory limit without
    one bounds nothing.
    """
    settings = dict(limits)
    if spill is not None and "memory_limit" in settings:
        settings.setdefault("temp_directory", str(spill))
    for name, value in settings.items():
        rendered = f"'{value}'" if isinstance(value, str) else value
        with contextlib.suppress(Exception):  # an unknown setting must not fail a validation
            connection.execute(f"SET {name} = {rendered}")
    return connection


@contextlib.contextmanager
def _spill_beside(packet: Packet) -> Iterator[Path | None]:
    """Yield a directory for DuckDB to spill into, removed afterwards.

    Beside the packet, not inside it. The filesystem has to be the packet's -- `/tmp` is tmpfs
    on several distributions, so spilling there consumes the memory the limit exists to bound
    -- but the packet root is the wrong place to put it: validating a packet would write into
    a directory whose bytes are supposed to be settled (R14 §2.3), leave it behind, and fail
    outright on read-only media. Measured on 287 M spikes, the uniqueness check spills 26 GB,
    which is 31x the packet it is checking.
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


def _run_rules(
    packet: Packet,
    registry: Mapping[str, Any],
    present: Mapping[str, Any],
    report: Report,
    advisory: bool,
    limits: Mapping[str, Any] | None = None,
    unsound: set[str] | None = None,
    recheck: Collection[str] | None = None,
) -> None:
    """Layer 4: Tier 1 checks generated from structure, then Tier 2 rules (R2 §7)."""
    with _spill_beside(packet) as spill:
        # Every table, because a validator runs every rule: this is the one caller that
        # wants what the reader stopped doing by default.
        connection = _bounded(packet.duckdb(tables="all"), LIMITS if limits is None else limits, spill)
        try:
            # A Tier 2 rule may reference a table other than the one it is declared on --
            # core.clocks.one_alignment_model reads core.clock_anchors, for instance. A packet that
            # does not declare a table genuinely has no rows of it, so an empty stand-in lets such a
            # rule evaluate rather than fail to run. A table that IS declared but unreadable is a
            # different case, already reported as resource.missing.
            for resource_id, spec in registry["tables"].items():
                if resource_id in present:
                    continue
                columns = ", ".join(f'"{c["name"]}" {_DDL[c["type"]]}' for c in spec["columns"])
                connection.sql(f"CREATE OR REPLACE TABLE {sql_name(resource_id)} ({columns})")

            connection.sql("CREATE OR REPLACE TABLE manifest_sessions (session_id VARCHAR)")
            for session in packet.manifest.sessions:
                connection.sql("INSERT INTO manifest_sessions VALUES (?)", params=[session])

            kinds = _declared_kinds(packet, registry)
            checks = generate(registry, only=set(present), advisory=advisory, aggregate=unsound or set(),
                              kinds=kinds, specialises=_specialisations(packet, registry))
            if recheck is not None:
                checks = [check for check in checks if concerns(check, recheck)]
            _run_checks(connection, checks, report, None)
            _check_extensions(packet, connection, registry, report, advisory, kinds)
        finally:
            with contextlib.suppress(Exception):
                connection.close()


def _run_checks(connection: Any, checks: Sequence[Any], report: Report, extension: str | None) -> None:
    """Run generated checks and record what they returned."""
    for check in checks:
        try:
            rows = _offending(connection, check.sql)
        except Exception as exc:  # noqa: BLE001 - an engine error is a finding, not a crash
            report.add("error", check.id, f"check could not run: {str(exc).splitlines()[0][:90]}", extension=extension)
            continue
        if rows:
            report.add(check.level, check.id, check.message, rows, extension=extension)


def _resolve_column(spec: Mapping[str, Any]) -> str | None:
    """Return the column a paired value joins to, or None where the resource is not namable.

    R55 §2.3.1 requires a single-column key, since a paired value holds one identifier. Which
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


def _declared_kinds(packet: Packet, registry: Mapping[str, Any]) -> dict[str, str | None]:
    """Every resource a discriminator may name, mapped to the column a paired value joins to.

    Built from the packet's registry *and* the extension registries it carries, because R49 §2.4
    lets a kind name an extension table and R55 §2.5 makes that the case the check must reach --
    the one whose hand-written union over core matched no branch and passed in silence.
    """
    tables = dict(registry["tables"])
    # Core's absent tables get empty stand-ins in _layer4, so all of them can be joined. An
    # extension's do not, so only what the packet carries can appear in the union.
    carried = {resource.resource_id for resource in packet.resources(kind="table")}
    for document in packet.extensions().values():
        if isinstance(document.get("tables"), Mapping):
            tables.update({n: t for n, t in document["tables"].items() if n in carried})
    # Every declarable resource, whether or not a *paired* value could name it. R55 §2.3.3's
    # single-column-key rule governs the paired shape alone; R54's shared-key discriminator
    # names tables whose key is composite by construction, and dropping them here made a
    # correctly declared `interval_kind` read as naming nothing.
    return {name: _resolve_column(spec) for name, spec in tables.items()}


def _specialisations(packet: Packet, registry: Mapping[str, Any]) -> dict[str, list[tuple[str, dict[str, str]]]]:
    """Which resources could specialise which, keyed by the discriminated resource.

    A specialisation declares a reference back over the discriminated table's **whole** key
    (R55 §2.3.1). Anything else a discriminator could name is a resource that could not carry
    the key, so generating R72 §2.1's reverse check for it would be checking the impossible.
    """
    tables = dict(registry["tables"])
    carried = {resource.resource_id for resource in packet.resources(kind="table")}
    for document in packet.extensions().values():
        if isinstance(document.get("tables"), Mapping):
            tables.update({n: t for n, t in document["tables"].items() if n in carried})
    found: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for name, spec in tables.items():
        for reference in spec.get("references", []):
            target = reference["resource"]
            key = (tables.get(target) or {}).get("primary_key") or []
            mapping = dict(zip(reference.get("resource_columns", []), reference["columns"], strict=False))
            if key and set(mapping) >= set(key):
                # The mapping, not just the name: R55 §2.3.1 requires the whole key and does not
                # require the same column names for it. `dynamic_foraging.trials` carries the
                # interval's id as `trial_id`, so a join on matching names finds nothing.
                found.setdefault(target, []).append((name, mapping))
    return found


def _check_extensions(
    packet: Packet,
    connection: Any,
    registry: Mapping[str, Any],
    report: Report,
    advisory: bool,
    kinds: Mapping[str, str | None] | None = None,
) -> None:
    """Validate each extension registry the packet carries (R17 §4).

    R17 §3's claim is that nothing here is per-extension: the same `generate` produces an
    extension's Tier 1 checks from its structure and carries its Tier 2 rules, because an
    extension registry *is* a registry document. What this function adds is which tables its
    references may resolve against -- core's, since R17 §2 lets an extension reference them and
    forbids the reverse -- and the layer its findings are filed under.

    Findings are recorded against the extension, so they cannot change the packet's core verdict.
    A core validator is not required to hold an extension's schema at all (`09` §6), so holding
    one must not be able to fail a packet that passes without it.
    """
    for extension_id, document in packet.extensions().items():
        if not isinstance(document.get("tables"), Mapping):
            report.add(
                "error",
                "extension.unusable",
                f"{extension_id}: the declared registry has no tables",
                extension=extension_id,
            )
            continue
        declared = set(document["tables"])
        # What the *packet* declares, not what the core registry knows: an extension's tables are
        # by definition absent from core's, and `present` is built from core's.
        carried = declared & {r.resource_id for r in packet.resources(kind="table")}
        if absent := sorted(declared - carried):
            report.add(
                "info",
                "extension.table_absent",
                f"{extension_id}: declares {len(absent)} table(s) this packet does not carry",
                [(name,) for name in absent],
                extension=extension_id,
            )
        if not carried:
            continue
        checks = generate(document, only=carried, advisory=advisory, resolvable=set(registry["tables"]), kinds=kinds)
        _run_checks(connection, checks, report, extension_id)
        report.add(
            "info",
            "extension.validated",
            f"{extension_id}: {len(checks)} check(s) over {len(carried)} table(s)",
            extension=extension_id,
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


def validate(
    packet: Packet,
    *,
    registry: Mapping[str, Any] | None = None,
    advisory: bool = False,
    limits: Mapping[str, Any] | None = None,
    scan: Collection[str] | None = None,
    recheck: Collection[str] | None = None,
    external: bool = False,
    checksums: bool = False,
    store_digests: bool = False,
) -> Report:
    """Validate a packet.

    The registry is taken from the packet unless one is supplied. Nothing is bundled: a
    packet SHOULD embed the registry it was written against (R2 §8), and a bundled copy
    would go stale against the reference one.

    Parameters
    ----------
    packet : Packet
        The packet to validate.
    registry : Mapping, optional
        Registry to validate against. Defaults to the packet's embedded copy.
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
        Resources this call has just written, restricting the rules to those R35 §5 obliges to
        run: the ones attached to such a resource, and the ones whose query names one. `None`,
        the default, runs every rule, which is what a first commit and a packet of unknown
        provenance both need. An amendment passes what it writes, because R32 §3 forbids it
        modifying anything else and R14 §2.3 declares those bytes immutable, so a rule reading
        only them is already answered.
    external : bool, default False
        Resolve external URIs and check the `sha256`, `size_bytes` and `codecs` claimed for
        them (R15 §4, level 3). Off by default because R14 §2.3.2 forbids structural validation
        reaching for a resource the packet does not own: whether one is reachable is a property
        of the reader's situation, not of the packet. An unreachable resource is a warning; one
        that resolves and disagrees with its claim is an error.
    checksums : bool, default False
        Recompute every recorded `sha256`: each packet-owned resource (R52 §2.3), and with
        `external`, each external one too. Separate because it reads every byte -- 0.60 s for the
        1,209 MB a packet owns, against 75 s for the 6.8 GB of LFP it merely references.
    store_digests : bool, default False
        With `external`, also compare each member's recorded `store_digest` against what the
        store reports now (R51 §2.3). This is the level between the other two: it costs the
        listing already performed, and it answers "has anything changed in place" rather than
        "are these the bytes". A member with nothing recorded, or a store offering nothing, is
        not checked, and the report says how many were skipped.

    Returns
    -------
    Report
        Every finding, in the order the layers ran.

    Raises
    ------
    PacketError
        If no registry is available.
    """
    report = Report(advisory=advisory)
    embedded = packet.registry
    effective = registry if registry is not None else embedded
    if effective is None:
        raise PacketError(
            f"{packet.manifest.packet_id} embeds no registry at schemas/logical_schemas.json and none was supplied"
        )

    if embedded is not None:
        _check_embedded_registry(packet, embedded, report)
    _check_sources(packet, report)
    _check_codec_declarations(packet, report, resolved=external)
    if external:
        _resolve_external(packet, report, checksums, store_digests)
    if checksums:
        _check_owned_digests(packet, report)
    _check_packet_owned_arrays(packet, report)
    _check_materialization_provenance(packet, report)
    _check_time_origin(packet, report)
    present = _check_schemas(packet, effective["tables"], report)
    unsound = _check_ordering(effective["tables"], present, report, scan)
    _run_rules(packet, effective, present, report, advisory, limits, unsound, recheck)
    return report


__all__ = ["ARROW_TYPES", "Finding", "Report", "registry_meta_schema", "sql_name", "validate"]
