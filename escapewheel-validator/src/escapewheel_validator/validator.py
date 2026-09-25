"""Validate a packet against the registry it declares.

Four layers: the manifest's shape, the registry it embeds, each resource's physical schema,
then the rules. No part states that order -- it is this module's, and what each layer owes is
Part 05 §5's.

The split between SQL and this module is not a matter of convenience (R12 §4). SQL covers
what the data *says* — values, keys, references, vocabularies. This module covers how it is
*stored* — physical order, file presence, column types — because a query cannot see any of
that, and a storage-layer check written as SQL fails silently rather than loudly.
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
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from escapewheel_reader import Location, Packet, PacketError, ResourceUnreadableError, sql_name
from escapewheel_reader.location import SOURCES_FILENAME
from escapewheel_reader.ordering import stored_order
from escapewheel_reader.profile import parquet_floor, physical_profile, zarr_floor_admits

from .generate import Check, adjacency_settles_uniqueness, concerns, generate
from .manifest import MANIFEST_FILENAME, Bound, Issue, bind_registries, check_manifest, named_registries
from .registry_document import (
    UCUM_URI,
    CheckedRegistryContext,
    RegistryResult,
    ucum_error,
)
from .rule_language import PROFILE_ID, RuleProfileError, check_rule
from .stores import ROUTES, ResourceMissing, StoreUnreachable, digest_resource, listing, read_member

#: Registry column type -> the Arrow type a conforming writer must emit (Part 03 §5.5).
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


def _tables(registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Project the table contracts from registry resource declarations."""
    return {
        str(name): declaration["table"]
        for name, declaration in registry.get("resources", {}).items()
        if declaration.get("kind") == "table" and "table" in declaration
    }


def _declarations(
    core: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Mapping[str, Any]]:
    """Combine the visible declarations without creating another serialized authority."""
    visible = dict(core.get("resources", {}))
    for document in extensions:
        visible.update(document.get("resources", {}))
    return visible


def _check_resource_declarations(  # noqa: C901 - one ordered cross-artifact validation phase
    packet: Packet,
    core: Mapping[str, Any],
    extensions: Mapping[str, Mapping[str, Any]],
    withheld: Collection[str],
    report: Report,
) -> None:
    """Part 04 §10's `declaration` phase, from the bound registries that may direct checks.

    An entry in the namespace of an extension registry that failed binding or its registry result
    is withheld rather than reported undeclared: nothing about it can be decided (Part 05 §14.5).
    """
    visible = _declarations(core, list(extensions.values()))
    entries = [entry for entry in packet.resources() if entry.declaration_id.split(".", 1)[0] not in withheld]
    by_id = {entry.resource_id: entry for entry in packet.resources()}

    for entry in entries:
        declaration = visible.get(entry.declaration_id)
        if declaration is None:
            report.add(
                "error",
                "packet.resource.declaration_unknown",
                f"{entry.resource_id}: declaration {entry.declaration_id!r} is not visible",
            )
            continue
        instances = declaration["instances"]
        mode = instances["mode"]
        if mode == "singleton" and entry.resource_id != entry.declaration_id:
            report.add(
                "error",
                "packet.resource.singleton_identity",
                f"{entry.resource_id}: singleton identity must equal {entry.declaration_id}",
                registry=report.owner(entry.declaration_id),
            )
        if mode == "family" and entry.resource_id.split(".", 1)[0] != entry.declaration_id.split(".", 1)[0]:
            report.add(
                "error",
                "packet.resource.family_namespace",
                f"{entry.resource_id}: family identity is outside {entry.declaration_id}'s namespace",
                registry=report.owner(entry.declaration_id),
            )
        for dependency in declaration["requires"]:
            if dependency not in by_id:
                report.add(
                    "error",
                    "packet.resource.dependency_missing",
                    f"{entry.resource_id}: required singleton {dependency} is absent",
                    registry=report.owner(entry.declaration_id),
                )
        if declaration["kind"] == "dense_array":
            axes = declaration["array"]["axes_resource"]
            if axes not in by_id:
                report.add(
                    "error",
                    "packet.resource.array_axes_missing",
                    f"{entry.resource_id}: declaration-selected axes resource {axes} is absent",
                    registry=report.owner(entry.declaration_id),
                )

        present = "derived_from" in entry.entry
        if declaration["lineage"] == "required" and not present:
            report.add(
                "error",
                "packet.resource.derived_from_required",
                f"{entry.resource_id}: derived_from is required by {entry.declaration_id}",
                registry=report.owner(entry.declaration_id),
            )
        elif declaration["lineage"] == "forbidden" and present:
            report.add(
                "error",
                "packet.resource.derived_from_forbidden",
                f"{entry.resource_id}: derived_from is forbidden by {entry.declaration_id}",
                registry=report.owner(entry.declaration_id),
            )

    active_extension_ids = set(extensions)
    for declaration_id, declaration in visible.items():
        instances = declaration["instances"]
        active = declaration_id.split(".", 1)[0] in {"core", "analysis"} | active_extension_ids
        if (
            active
            and instances["mode"] == "singleton"
            and instances["presence"] == "required"
            and declaration_id not in by_id
        ):
            report.add(
                "error",
                "packet.resource.required_missing",
                f"required singleton {declaration_id} is absent",
                registry=report.owner(declaration_id),
            )

    for declaration_id, declaration in visible.items():
        if declaration["kind"] != "table" or declaration_id not in by_id:
            continue
        for reference in declaration["table"]["references"]:
            target = str(reference["resource"])
            if target in by_id:
                continue
            columns = list(reference["columns"])
            try:
                table = packet.table(declaration_id, columns=columns)
            except (PacketError, OSError, pa.ArrowException):
                continue
            values = zip(
                *(table.column(column).to_pylist() for column in columns),
                strict=True,
            )
            if any(all(value is not None for value in row) for row in values):
                report.add(
                    "error",
                    "packet.resource.reference_target_missing",
                    f"{declaration_id}: populated foreign key {columns} requires {target}",
                    registry=report.owner(declaration_id),
                )

    catalog_families = {
        (declaration["instances"]["catalog_resource"], declaration["instances"]["resource_id_column"]): (
            declaration_id,
            declaration,
        )
        for declaration_id, declaration in visible.items()
        if declaration["instances"]["mode"] == "catalog"
    }
    for (catalog_id, column), (declaration_id, _) in catalog_families.items():
        if catalog_id not in by_id:
            continue
        try:
            values = packet.table(catalog_id, columns=[column]).column(column).to_pylist()
        except (PacketError, OSError, pa.ArrowException) as exc:
            report.add(
                "error",
                "packet.resource.catalog_table_unreadable",
                f"{catalog_id}.{column}: {exc}",
                registry=report.owner(catalog_id),
            )
            continue
        normalized = [str(value) for value in values if value is not None]
        counts = Counter(normalized)
        for value, count in counts.items():
            matches = [
                entry for entry in entries if entry.resource_id == value and entry.declaration_id == declaration_id
            ]
            if count != 1 or len(matches) != 1:
                report.add(
                    "error",
                    "packet.resource.catalog_row_binding",
                    f"{catalog_id}.{column}={value!r} does not bind one {declaration_id} resource",
                    registry=report.owner(declaration_id),
                )
        catalog_values = set(normalized)
        for entry in entries:
            if entry.declaration_id == declaration_id and entry.resource_id not in catalog_values:
                report.add(
                    "error",
                    "packet.resource.catalog_row_binding",
                    f"{entry.resource_id}: no row in {catalog_id}.{column}",
                    registry=report.owner(declaration_id),
                )

    permitted = {
        "core": {"core"},
        "extension": {"core", "extension"},
        "analysis": {"core", "extension", "analysis"},
        "compatibility_projection": {"core", "extension", "analysis"},
        "documentation": set(),
    }
    graph: dict[str, set[str]] = {}
    for entry in entries:
        declaration = visible.get(entry.declaration_id)
        sources = entry.entry.get("derived_from", [])
        if declaration is None or not isinstance(sources, list):
            continue
        graph[entry.resource_id] = set(map(str, sources))
        for source in sources:
            source_entry = by_id.get(str(source))
            source_declaration = None if source_entry is None else visible.get(source_entry.declaration_id)
            if source_declaration is None:
                report.add(
                    "error",
                    "packet.resource.lineage_unresolved",
                    f"{entry.resource_id}: lineage source {source!r} is absent or undeclared",
                    registry=report.owner(entry.declaration_id),
                )
            elif source_declaration["content_class"] not in permitted[declaration["content_class"]]:
                report.add(
                    "error",
                    "packet.resource.lineage_class",
                    f"{entry.resource_id}: {declaration['content_class']} may not derive from "
                    f"{source_declaration['content_class']}",
                    registry=report.owner(entry.declaration_id),
                )

    def cyclic(node: str, path: frozenset[str]) -> bool:
        return node in path or any(cyclic(child, path | {node}) for child in graph.get(node, ()) if child in graph)

    for node in graph:
        if cyclic(node, frozenset()):
            report.add("error", "packet.resource.lineage_cycle", f"lineage cycle reaches {node}")
            break


#: Verdicts in increasing severity; a conjunction takes the most severe (Part 05 §9.5).
VERDICTS = ("passed", "incomplete", "failed")


def _worst(verdicts: Iterable[str]) -> str:
    return max(verdicts, key=VERDICTS.index, default="passed")


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
    registry : str or None
        The bound registry this finding belongs to, or None where it belongs to the packet
        (Part 05 §9.5). An extension's findings never count against core's verdict, nor core's
        against an extension's.
    """

    level: str
    check: str
    message: str
    rows: tuple[tuple[str, ...], ...] = ()
    registry: str | None = None


@dataclass(frozen=True)
class Evaluation:
    """A registry-level Tier 2 evaluation outcome distinct from packet findings."""

    registry: str
    status: str
    rule: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class RegistryEvaluation:
    """A complete registry-document result and the external role it evaluated."""

    subject: str
    result: RegistryResult
    directs_checks: bool = False
    core: bool = False


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
    bound : tuple of str
        The registry IDs the manifest binds, each of which receives a verdict.
    """

    findings: list[Finding] = field(default_factory=list)
    evaluations: list[Evaluation] = field(default_factory=list)
    registries: list[RegistryEvaluation] = field(default_factory=list)
    advisory: bool = False
    bound: tuple[str, ...] = ()
    #: Declaration ID -> the bound registry holding it, for attributing a finding about an entry.
    declared_by: dict[str, str] = field(default_factory=dict)
    #: Resource ID -> declaration ID, from the manifest's entries.
    declarations: dict[str, str] = field(default_factory=dict)

    @property
    def errors(self) -> int:
        """How many error-level findings were produced, whatever their subject."""
        return sum(f.level == "error" for f in self.findings)

    @property
    def warnings(self) -> int:
        """How many warning-level findings were produced."""
        return sum(f.level == "warning" for f in self.findings)

    def verdict(self, registry: str | None = None) -> str:
        """Return one bound registry's verdict, or the packet's where `registry` is None (Part 05 §9.5).

        A registry passes only once its required evaluation is recorded complete, so a registry whose
        evaluation was withheld, or never reached, is ``incomplete`` rather than ``passed``. The
        packet's verdict is the worst of its own findings' and every bound registry's.

        Advisory rules cannot be ``error`` (Part 02 §10.2), so no verdict depends on the
        ``advisory`` flag.
        """
        if registry is None:
            own = "failed" if any(f.level == "error" and f.registry is None for f in self.findings) else "passed"
            return _worst([own, *(self.verdict(name) for name in self.bound)])
        if any(f.level == "error" and f.registry == registry for f in self.findings):
            return "failed"
        states = {item.result.state for item in self.registries if item.subject == registry}
        statuses = {e.status for e in self.evaluations if e.registry == registry}
        if "invalid" in states | statuses:
            return "failed"
        if states != {"valid"} or statuses != {"complete"}:
            return "incomplete"
        return "passed"

    @property
    def passed(self) -> bool:
        """Whether the packet's verdict is ``passed``, the only one supporting a conformance claim."""
        return self.verdict() == "passed"

    def attribute(self, declared_by: Mapping[str, str], entries: Iterable[Any]) -> None:
        """Record which registry holds each declaration, and which declaration each entry names."""
        self.declared_by = dict(declared_by)
        self.declarations = {entry.resource_id: entry.declaration_id for entry in entries}

    def owner(self, declaration_id: str) -> str | None:
        """Return the bound registry holding a declaration, or None where none holds it.

        A declaration no directing registry exposes is attributed by namespace to a bound extension,
        so a finding about a withheld extension's entry is still that extension's.
        """
        if (registry := self.declared_by.get(declaration_id)) is not None:
            return registry
        namespace = declaration_id.split(".", 1)[0]
        return namespace if namespace in self.bound and namespace != "core" else None

    def resource_owner(self, resource_id: str) -> str | None:
        """Return the registry declaring the resource an entry locates, or None for the packet."""
        declaration = self.declarations.get(resource_id, resource_id)
        return self.owner(declaration)

    def record_evaluation(self, registry: str, status: str, *, rule: str | None = None, detail: str = "") -> None:
        """Record a Tier 2 outcome without turning validator inability into a finding."""
        self.evaluations.append(Evaluation(registry, status, rule, detail))

    def record_registry(
        self, subject: str, context: CheckedRegistryContext, *, directs_checks: bool = False, core: bool = False
    ) -> None:
        """Retain a complete result, labelled by registry ID, and expose its invalid outcomes."""
        self.registries.append(RegistryEvaluation(subject, context.result, directs_checks, core))
        for outcome in context.result.findings:
            self.add(
                "error",
                outcome.id,
                f"{subject} registry {outcome.instance or '<root>'}: "
                f"{outcome.detail or outcome.reason or outcome.state}",
                registry=subject,
            )

    def add(
        self,
        level: str,
        check: str,
        message: str,
        rows: Sequence[Sequence[Any]] = (),
        registry: str | None = None,
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
        registry : str, optional
            The bound registry the finding belongs to; None for the packet.
        """
        self.findings.append(
            Finding(level, check, message, tuple(tuple(str(v) for v in row) for row in list(rows)[:5]), registry)
        )

    def to_dict(self, packet_id: str) -> dict[str, Any]:
        """Render the report as the JSON structure Part 05 describes.

        ``status`` is the packet's verdict and ``verdicts`` each bound registry's. A finding whose
        ``registry`` is null belongs to the packet (Part 05 §9.5).

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
            "status": self.verdict(),
            "verdicts": {name: self.verdict(name) for name in self.bound},
            # An empty advisory list is ambiguous between "none fired" and "not run" (R26 §5).
            "advisory": self.advisory,
            "validator": {"name": "escapewheel_validator", "version": _version()},
            "summary": {"errors": self.errors, "warnings": self.warnings},
            "findings": [
                {
                    "level": f.level,
                    "check": f.check,
                    "message": f.message,
                    "rows": [list(r) for r in f.rows],
                    "registry": f.registry,
                }
                for f in self.findings
            ],
            "evaluations": [
                {"registry": e.registry, "status": e.status, "rule": e.rule, "detail": e.detail}
                for e in self.evaluations
            ],
            "registries": [
                {
                    "subject": item.subject,
                    "core": item.core,
                    "directs_checks": item.directs_checks,
                    "result": item.result.to_dict(),
                }
                for item in self.registries
            ],
        }


def _version() -> str:
    from . import __version__

    return __version__


def registry_meta_schema() -> dict[str, Any]:
    """Part 02 §9.2's published meta-schema, as this distribution vendors it.

    Public because Part 02 §9.2 makes its `$id` something a writer has to state: a document declares
    which meta-schema governs it, and the writer that emits the declaration must not keep its own
    copy of the URI.
    """
    text = importlib_resources.files("escapewheel_validator").joinpath("schemas/registry.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


def _check_time_origin(packet: Packet, report: Report) -> None:
    """Layer 1d: `t_zero_tick` is the earliest observation start on the reference clock (Part 01 §2.2).

    Not SQL, and for the reason Part 01 §2.2 gives: the minimum is taken across clocks, and getting
    a clock's `start_tick` onto the reference is R13's anchor-based mapping -- arithmetic no
    query expresses. A packet declaring no origin is conforming and is not checked; one that
    declares a *wrong* origin silently shifts every second a consumer derives, which is why the
    check exists at all.
    """
    from escapewheel_reader.clocks import align, anchors, declared_bound, reference_clock

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
        report.add("error", "time.origin_unmappable", f"t_zero_tick is declared but {refused}", registry="core")
        return

    starts: list[int] = []
    for clock, start in zip(
        intervals.column("clock_id").to_pylist(), intervals.column("start_tick").to_pylist(), strict=True
    ):
        if start is None:
            continue
        if clock == reference:
            starts.append(int(start))
            continue
        if clock not in by_clock:
            report.add(
                "error",
                "time.origin_unmappable",
                f"{clock} declares an observation window but no anchors, so the minimum Part 01 §2.2 "
                "defines cannot be taken",
                [(clock,)],
                registry="core",
            )
            return
        converted, defined = align(np.array([start], dtype=np.int64), *by_clock[clock], bound=bound)
        if not defined[0]:
            report.add(
                "error",
                "time.origin_unmappable",
                f"{clock}'s observation start does not map to {reference} within the alignment "
                "bound, so no origin is defined (Part 01 §2.2)",
                [(clock, str(start))],
                registry="core",
            )
            return
        starts.append(int(converted[0]))

    expected = min(starts)
    for stated in declared:
        # The writer's own estimator is not bit-reproducible from the packet -- it may have
        # fitted over anchors it then withheld -- so agreement is judged at Part 01 §3.9's
        # tolerance of one parent tick rather than exactly.
        if abs(int(stated) - expected) > 1:
            report.add(
                "error",
                "time.origin_not_earliest",
                f"t_zero_tick is {stated} but the earliest observation start on {reference} "
                f"is {expected} (Part 01 §2.2)",
                [(str(stated), str(expected))],
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


def _floor_level(resource: Any) -> str:
    """`warning` only where a packet-owned resource exceeds a floor its writer is also held to (Part 05 §5.3)."""
    role = physical_profile()["interfaces"][resource.interface]["floor_role"]
    return "warning" if role == "reader_and_packet_writer" and not resource.is_external else "info"


def _check_zarr_floor(resource: Any, metadata: Mapping[str, Any], report: Report) -> None:
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
        _floor_level(resource),
        "physical.outside_reader_floor",
        f"{resource.resource_id}: zarr {variant} "
        + "; ".join(f"{member} {value}" for member, value in observed)
        + " is outside the reader floor of Part 03 §6.4",
        observed,
        registry=report.resource_owner(resource.resource_id),
    )


def _check_parquet_floor(resource: Any, metadata: Any, report: Report) -> None:
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
            _floor_level(resource),
            "physical.outside_reader_floor",
            f"{resource.resource_id}: parquet "
            + ", ".join(f"{member} {value}" for member, value in observed)
            + " is outside the reader floor of Part 03 §5.5",
            observed,
            registry=report.resource_owner(resource.resource_id),
        )


def _check_one_array(resource: Any, handle: Any, extents: Mapping[str, Any], report: Report) -> None:
    """Check one packet-owned array against the metadata document in its own store."""
    try:
        metadata = handle.metadata()
        actual = _codec_names(metadata.get("codecs") or handle.codecs)
        rank = len(handle.shape)
    except (ResourceUnreadableError, OSError, ValueError, KeyError) as exc:
        report.add(
            "error",
            "array.unreadable",
            f"{resource.resource_id}: {exc}",
            registry=report.resource_owner(resource.resource_id),
        )
        return

    if handle.zarr_format != 3:
        report.add(
            "error",
            "array.not_zarr_v3",
            f"{resource.resource_id} is packet-owned but stored as Zarr v{handle.zarr_format}; "
            "Part 03 §6.1 allows v2 only for an array the packet references",
            registry=report.resource_owner(resource.resource_id),
        )

    if "transpose" in actual:
        report.add(
            "error",
            "array.transpose_codec",
            f"{resource.resource_id} uses the transpose codec, which Part 03 §6.2 forbids: axes are stored in the "
            "order the packet declares them",
            registry=report.resource_owner(resource.resource_id),
        )

    _check_zarr_floor(resource, metadata, report)

    if (grid := metadata.get("chunk_grid", {}).get("name")) != "regular":
        report.add(
            "error",
            "array.irregular_chunk_grid",
            f"{resource.resource_id} declares a {grid!r} chunk grid; Part 03 §6.1 requires a regular one",
            registry=report.resource_owner(resource.resource_id),
        )

    if "fill_value" not in metadata:
        report.add(
            "error",
            "array.no_fill_value",
            f"{resource.resource_id} declares no fill_value, which Part 03 §6.1 requires",
            registry=report.resource_owner(resource.resource_id),
        )

    if not (declared := extents.get(resource.resource_id, {})):
        return
    if set(declared) != set(range(rank)):
        report.add(
            "error",
            "array.rank_disagrees_with_dimensions",
            f"{resource.resource_id} has rank {rank} but its declaration-selected axes resource "
            f"gives axis_index {sorted(declared) or 'none'}; Part 03 §6.2 requires one row per stored axis",
            registry=report.resource_owner(resource.resource_id),
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
            registry=report.resource_owner(resource.resource_id),
        )


def _check_packet_owned_arrays(packet: Packet, report: Report) -> None:
    """Layer 1c: every packet-owned array against its own Zarr metadata (Part 04 §5.3, level 2).

    Always runs, and needs no Zarr: a Zarr array's metadata is a JSON document in the store,
    which `ArrayResource` parses directly. The packet owns these bytes, so an array it
    describes wrongly is a defect in the packet rather than in the reader's situation. An
    external array is level 3 and stays with the requested mode, and `_report_unassessed` reports it
    where that mode did not read it.

    Storage, not values, so the shim and not SQL (R12 §4): no query can see a chunk grid or a codec
    pipeline.
    """
    # A resource naming a source is not packet-owned whatever `external` says, and `_check_sources`
    # has already reported the contradiction; resolving it here would raise instead of report.
    owned = [r for r in packet.resources(kind="dense_array") if not r.is_external and r.source is None]
    if not owned:
        return
    extents = _declared_extents(packet)
    if not extents:
        report.add(
            "error",
            "array.no_array_dimensions_table",
            f"{len(owned)} packet-owned array(s) but no declaration-selected axes rows were resolved",
        )
    for resource in owned:
        try:
            listing(_owned_uri(packet, resource.entry))
        except ResourceMissing as exc:
            report.add(
                "error",
                "resource.missing",
                f"{resource.resource_id}: {exc}",
                registry=report.resource_owner(resource.resource_id),
            )
            continue
        except StoreUnreachable:
            pass  # `_check_one_array` reports what it cannot read
        _check_one_array(resource, packet.array_resource(resource.resource_id), extents, report)


def _report_unassessed(packet: Packet, assessed: Collection[str], report: Report) -> None:
    """One `info` finding per external resource with a reader floor whose own metadata was not read (Part 05 §5.3)."""
    for resource in packet.resources():
        if resource.is_external and resource.interface is not None and resource.resource_id not in assessed:
            report.add(
                "info",
                "external.physical_unassessed",
                f"{resource.resource_id}: its {resource.interface} metadata was not read, so its physical "
                "version, codecs, compression and encodings are unassessed",
                [(resource.resource_id,)],
                registry=report.resource_owner(resource.resource_id),
            )


def _report_page_types_unassessed(tables: int, report: Report) -> None:
    """Part 03 §5.5: a validator comparing only footers states that it did not assess data-page types."""
    if tables:
        report.add(
            "info",
            "physical.page_types_unassessed",
            f"{tables} Parquet footer(s) compared with the floor's compressions and encodings; data-page "
            "types were not assessed, since they are recorded in page headers",
        )


def _check_owned_digests(packet: Packet, report: Report, store_checksums: bool = True) -> None:
    """Part 04 §5.3, level 2: every packet-owned resource's recorded digest holds.

    A disagreement is an **error**, where the external equivalent is one too but means something
    weaker. An external resource that changed is the world moving under a packet that never
    promised otherwise (Part 03 §8); a packet-owned file that changed is the packet being wrong
    about itself, and it is the premise Part 03 §9.4 spends to bound revalidation.

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
            found = digest_resource(
                _owned_uri(packet, entry), str(claimed["algorithm"]), store_checksums=store_checksums
            )
        except StoreUnreachable as exc:
            report.add(
                "error",
                "resource.missing",
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
                "error",
                "owned.digest",
                f"{resource.resource_id}: {found.algorithm} gives {found.value[:16]}…, manifest records "
                f"{str(claimed['value'])[:16]}… — a packet-owned resource is immutable (Part 03 §8.1) and "
                "Part 03 §9.4 bounds revalidation on that",
                registry=report.resource_owner(resource.resource_id),
            )
    if checked:
        report.add(
            "info",
            "owned.verified",
            f"{matched} of {checked} packet-owned resource(s) hold their recorded digest; {_routes(routes)}",
            routes,
        )


def _owned_uri(packet: Packet, entry: Mapping[str, Any]) -> str:
    """Where a packet-owned entry's bytes are, under the packet's own location."""
    return packet.location.resolve(str(entry.get("uri", ""))).uri


def _routes(routes: Sequence[tuple[str, str, str]]) -> str:
    """Name how each digest was established (Part 04 §5.3), by resource where the routes differ.

    A finding keeps five rows, so the message carries the route of every digest.
    """
    taken = [route for route in ROUTES if any(row[2] == route for row in routes)]
    if len(taken) == 1:
        return f"route: {taken[0]} for all {len(routes)}"
    return "route: " + "; ".join(
        f"{route} for {', '.join(name for name, _, used in routes if used == route)}" for route in taken
    )


def _check_sources(packet: Packet, report: Report) -> None:
    """R80: what a source declaration must be, decided without reaching the network.

    Two things are structural and one is not; the manifest schema already requires `external` beside
    a `source`. A `source` names a body of data rather than a location, so the entry's `uri` MUST be
    relative to it (Part 04 §5.5). `sources.json` MUST
    NOT be a declared resource (Part 04 §5.5): being outside the manifest is what keeps Part 03 §8.1's
    immutability off it, and a packet that declared it would freeze the one file that has to
    stay editable.

    Whether a source **resolves** is not structural and is reported rather than failed. Part 04 §5.5
    makes an unresolved source a fact about the reader's situation -- which mirrors it can reach
    -- and Part 04 §5.3 keeps structural validation off the network, so this reports what the
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
                    f"{resource.resource_id} declares {SOURCES_FILENAME} as a resource; Part 04 §5.5 keeps it "
                    "outside the manifest so Part 03 §8.1's immutability does not reach it",
                    registry=report.resource_owner(resource.resource_id),
                )
            continue
        named.setdefault(source, []).append(resource.resource_id)
        if "://" in resource.uri:
            report.add(
                "error",
                "source.absolute_uri",
                f"{resource.resource_id} names source {source!r} and an absolute uri {resource.uri!r}; "
                "where a source is named the uri is a path under it (Part 04 §5.5)",
                registry=report.resource_owner(resource.resource_id),
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
        # A fact, not a defect (Part 04 §5.5): the packet is conforming and this reader cannot reach
        # those bytes. Reported so a report says which, rather than leaving it to a later failure.
        report.add(
            "info",
            "sources.unresolved",
            f"{len(unresolved)} source(s) no available resolution document locates (Part 04 §5.5)",
            [(name, ", ".join(named[name][:3])) for name in unresolved[:20]],
        )


def _resolve_external(
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
        Also establish each recorded `digest` (level 3c). Reading every byte costs 6.8 GB for a
        session's LFP, 75 s from local disk and 88 s from S3, where the rest of this mode is a list
        operation; off separately for that reason.
    store_digests : bool, default False
        Also compare each declared member's `store_digest` against what the store reports now
        (Part 04 §5.4). The listing already performed carries the values, so this is the same 1.31 s
        the level below it costs, and it answers a weaker question than `checksums` does.
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
    extents = _declared_extents(packet) if external_arrays else {}
    for resource in packet.resources():
        if not resource.is_external:
            continue
        fields = _compare_external(
            resource, report, checksums, store_digests, extents, store_checksums, routes, assessed
        )
        if fields is None:
            continue
        checked += 1
        compared.update(fields)
        if checksums and "digest" not in fields:
            unchecksummed.append(resource.resource_id)
    if unchecksummed:
        report.add(
            "warning",
            "external.no_checksum",
            f"{len(unchecksummed)} of {checked} resolved resource(s) record no digest, so a digest "
            "was asked for and nothing was compared against (Part 04 §5.2)",
            [(name,) for name in unchecksummed],
        )
    if checked:
        did = ", ".join(f"{count} {field}" for field, count in sorted(compared.items())) or "nothing"
        established = f"; digest {_routes(routes)}" if routes else ""
        report.add(
            "info",
            "external.verified",
            f"{checked} external resource(s) resolved; compared {did}{established}",
            routes,
        )
    return assessed


def _compare_external(
    resource: Any,
    report: Report,
    checksums: bool,
    store_digests: bool = False,
    extents: Mapping[str, Any] | None = None,
    store_checksums: bool = True,
    routes: list[tuple[str, str, str]] | None = None,
    assessed: set[str] | None = None,
) -> list[str] | None:
    """Check one external resource, returning the fields actually compared.

    None means the store could not be reached, which is already reported and leaves the resource
    out of every count: nothing about it was established either way. Each digest established is
    appended to `routes` as its resource ID, algorithm, and route, and an array whose metadata was
    compared with the reader floor is added to `assessed`.
    """
    entry = resource.entry
    uri = str(entry.get("uri", ""))
    try:
        found = listing(uri)
    except StoreUnreachable as exc:
        report.add(
            "warning",
            "external.unreachable",
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
                "error",
                "external.size_bytes",
                f"{resource.resource_id}: {found.size_bytes:,} bytes over {len(found.members)} object(s), "
                f"manifest claims {claimed:,}",
                registry=report.resource_owner(resource.resource_id),
            )
    if resource.kind == "dense_array" and (metadata := _stored_metadata(uri, found)) is not None:
        _check_zarr_floor(resource, metadata, report)
        if assessed is not None:
            assessed.add(resource.resource_id)
        if extents:
            fields.extend(_compare_shape(resource, metadata, extents, report))
    if checksums and isinstance(claimed := entry.get("digest"), Mapping):
        try:
            found_digest = digest_resource(uri, str(claimed["algorithm"]), store_checksums=store_checksums)
        except StoreUnreachable as exc:
            report.add(
                "warning",
                "external.unreachable",
                f"{resource.resource_id}: {exc}",
                registry=report.resource_owner(resource.resource_id),
            )
            return None
        fields.append("digest")
        if routes is not None:
            routes.append((resource.resource_id, found_digest.algorithm, found_digest.route))
        if found_digest.value != claimed["value"]:
            report.add(
                "error",
                "external.digest",
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
            "error",
            "external.members",
            f"{resource.resource_id}: {len(missing)} declared member(s) the store does not hold",
            [(key,) for key in missing[:20]],
            registry=report.resource_owner(resource.resource_id),
        )
    if extra := sorted(held.keys() - claimed.keys()):
        report.add(
            "error",
            "external.members",
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
            "error",
            "external.members",
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
            "error",
            "external.store_digest",
            f"{resource.resource_id}: {len(changed)} member(s) changed in place since recording",
            [(key,) for key in changed[:20]],
            registry=report.resource_owner(resource.resource_id),
        )
    if skipped:
        report.add(
            "warning",
            "external.no_store_digest",
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
    for key in (".zarray", "zarr.json"):
        if any(member.key == key for member in found.members):
            try:
                parsed = json.loads(read_member(uri, key))
            except (ValueError, StoreUnreachable):
                return None
            return parsed if isinstance(parsed, Mapping) else None
    return None


def _declared_extents(packet: Packet) -> dict[str, dict[int, int | None]]:  # noqa: C901
    """Resolve each dense array's axes through its declaration and catalog row."""
    declarations: dict[str, Mapping[str, Any]] = {}
    for document in (packet.registry, *packet.extensions().values()):
        if isinstance(document, Mapping):
            declarations.update(document.get("resources", {}))

    extents: dict[str, dict[int, int | None]] = {}
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
        catalog_table = catalog_declaration["table"]
        axes_table = axes_declaration["table"]
        catalog_key = list(catalog_table["primary_key"] or [])
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
        try:
            catalog_rows = packet.table(catalog_id, columns=[resource_column, *catalog_key])
            axes_names = set(packet.table_resource(axes_id).schema().names)
            axes_columns = [*binding["columns"], "axis_index"]
            if "coordinate_resource" in axes_names:
                axes_columns.append("coordinate_resource")
            axes_rows = packet.table(axes_id, columns=axes_columns)
        except (PacketError, OSError, pa.ArrowException):
            continue
        key_by_resource = {
            str(values[0]): tuple(values[1:])
            for values in zip(
                catalog_rows.column(resource_column).to_pylist(),
                *(catalog_rows.column(name).to_pylist() for name in catalog_key),
                strict=True,
            )
            if values[0] is not None
        }
        wanted_key = key_by_resource.get(resource.resource_id)
        if wanted_key is None:
            continue
        coordinates = (
            axes_rows.column("coordinate_resource").to_pylist()
            if "coordinate_resource" in axes_rows.column_names
            else [None] * axes_rows.num_rows
        )
        wanted_coordinates: list[tuple[str, int]] = []
        for values, coordinate in zip(
            zip(
                *(axes_rows.column(name).to_pylist() for name in binding["columns"]),
                axes_rows.column("axis_index").to_pylist(),
                strict=True,
            ),
            coordinates,
            strict=True,
        ):
            if tuple(values[:-1]) == wanted_key and values[-1] is not None:
                axis = int(values[-1])
                extents.setdefault(resource.resource_id, {})[axis] = None
                if coordinate:
                    wanted_coordinates.append((str(coordinate), axis))
        for coordinate_id, axis in wanted_coordinates:
            try:
                coordinate_names = set(packet.table_resource(coordinate_id).schema().names)
            except PacketError:
                continue
            needed = [*binding["columns"], "axis_index"]
            if not set(needed) <= coordinate_names:
                continue
            coordinate_rows = packet.table(coordinate_id, columns=needed)
            count = sum(
                1
                for values in zip(
                    *(coordinate_rows.column(name).to_pylist() for name in binding["columns"]),
                    coordinate_rows.column("axis_index").to_pylist(),
                    strict=True,
                )
                if tuple(values[:-1]) == wanted_key and values[-1] == axis
            )
            if count:
                extents[resource.resource_id][axis] = count
    return extents


def _compare_shape(resource: Any, metadata: Mapping[str, Any], extents: Mapping[str, Any], report: Report) -> list[str]:
    """Check an external array's stored shape against what the packet's tables assert (Part 02 §6).

    This is the check that catches a change actually invalidating the packet. A re-generated
    array with a different channel count leaves `core.array_channels` describing positions that
    are not there; one at a different sample rate leaves `core.array_dimensions` wrong. Neither
    changes what the packet claims about the array's *values*, which it claims nothing about --
    which is why this and not a content digest is what an external array needs verified.

    Cheap: one request for the metadata document the array's store already holds.
    """
    if not (declared := extents.get(resource.resource_id)):
        return []
    if not isinstance(shape := metadata.get("shape"), list):
        return []
    if len(shape) != len(declared):
        report.add(
            "error",
            "external.array_rank",
            f"{resource.resource_id} is stored with rank {len(shape)} but its declaration-selected "
            f"axes resource gives axis_index {sorted(declared)}; Part 03 §6.2 requires one row per stored axis",
            registry=report.resource_owner(resource.resource_id),
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
            registry=report.resource_owner(resource.resource_id),
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
            report.add("error", "resource.missing", str(exc), registry=report.resource_owner(resource_id))
            continue
        present[resource_id] = handle
        for column in spec["columns"]:
            _check_column(resource_id, column, schema, report)
        path, filesystem = (handle.path, None) if handle.is_local else handle.location.store()
        try:
            footer = pq.read_metadata(path, filesystem=filesystem)
        except (OSError, pa.ArrowException):
            continue  # an unreadable footer leaves the floor unassessed, not failed (Part 05 §9.4)
        _check_parquet_floor(handle.resource, footer, report)
    return present


def _check_column(resource_id: str, column: Mapping[str, Any], schema: Any, report: Report) -> None:
    """Check one column's presence and type against the registry."""
    if column["name"] not in schema.names:
        if column["presence"] != "optional":
            report.add(
                "error",
                "schema.column_absent",
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
            "error",
            "schema.column_type",
            f"{resource_id}.{column['name']} is {actual}, registry declares {column['type']}",
            registry=report.resource_owner(resource_id),
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


def _duplicated_columns(handle: Any, spec: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Pairs of this table's columns holding equal values in every row (Part 07 §4).

    Bounded by the footer, not by a row sample. Two columns can hold equal values in every row
    only if their per-chunk minimum, maximum and null count agree, which Parquet already records,
    so statistics decide almost every pair and values are read for the few that survive. Measured
    on `ecephys_776259`: 2,126 pairs across 32 tables reduce to 51 in 0.06 s with no values read.

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


def _check_duplication(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 07 §4. Reported at `info` and never as a failure.

    R95 §2.3 measures why it may not fail: four identifiers numbered independently coincide on
    both packaged sessions, which is a fact about a packet rather than a defect in it.
    """
    for resource_id, handle in present.items():
        try:
            pairs = _duplicated_columns(handle, tables[resource_id])
        except (OSError, pa.ArrowException):
            continue
        for a, b in pairs:
            report.add(
                "info",
                f"{resource_id}.columns_duplicated",
                f"{a} and {b} hold equal values in every row",
                registry=report.resource_owner(resource_id),
            )


def _check_unfilled_metadata(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 02 §8.6. A declared `metadata` column that no row of the packet fills, at `info`.

    Whether a table in Part 02 §8.6's middle band declares one is a judgement, and this is the
    evidence against which it is revisited: `core.spike_events` carried the column on
    286,896,563 rows that no adapter ever filled. Never a failure — Part 02 §6 makes an optional
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
                "info",
                f"{resource_id}.metadata_unfilled",
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
                    "info",
                    f"{resource_id}.metadata_unfilled",
                    "metadata is null in every row",
                    registry=report.resource_owner(resource_id),
                )


def _check_reserved_values(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 02 §9.3. A value outside a column's reserved set, at `info`.

    Never a failure: the vocabulary is open (Part 02 §9.3) and an unrecognised value is exactly what
    openness admits. What the report is for is the case R101 §2.5 measured — `core.array_assets`
    carried `dense_array_asset`, a manifest resource kind, in the column reserving `raw`, `ap`,
    `lfp` and `waveform`, and nothing could see it because no column declared a set.

    Whether a value is a *synonym* for a reserved one stays uncheckable, so Part 02 §9.3's prohibition
    binds a writer and no rule (Part 01 §3.5).
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
                    "info",
                    f"{resource_id}.{name}.outside_reserved_set",
                    f"{len(outside)} value(s) outside the reserved set: "
                    f"{', '.join(repr(v) for v in outside[:5])}" + (" ..." if len(outside) > 5 else ""),
                    registry=report.resource_owner(resource_id),
                )


def _check_unit_codes(present: Mapping[str, Any], tables: Mapping[str, Any], report: Report) -> None:
    """Part 05 §5.3. Every non-null value of a unit column is a UCUM code (Part 02 §8.4).

    Covers every table a directing registry declares (Part 05 §5.4), and files each finding and each
    unreadable column under that registry. Distinct values are parsed once each.
    """
    for resource_id, handle in present.items():
        for column in tables[resource_id]["columns"]:
            if not any(entry.get("uri") == UCUM_URI for entry in column.get("authority", ())):
                continue
            name = column["name"]
            check = f"{resource_id}.{name}.ucum_code"
            registry = report.resource_owner(resource_id) or "core"
            try:
                values = pc.unique(pq.read_table(handle.path, columns=[name]).column(name)).to_pylist()
            except (OSError, pa.ArrowException, KeyError) as exc:
                report.record_evaluation(registry, "incomplete", rule=check, detail=str(exc).splitlines()[0][:160])
                continue
            invalid = sorted(value for value in values if value is not None and ucum_error(value) is not None)
            if invalid:
                report.add(
                    "error",
                    check,
                    f"{len(invalid)} value(s) are not UCUM codes: {', '.join(repr(v) for v in invalid[:5])}"
                    + (" ..." if len(invalid) > 5 else ""),
                    [(value,) for value in invalid],
                    registry=registry,
                )


def _check_ordering(
    tables: Mapping[str, Any],
    present: Mapping[str, Any],
    report: Report,
    scan: Collection[str] | None = None,
) -> set[str]:
    """Layer 3: declared sort order, and the uniqueness that order settles (Part 03 §5.3, Part 03 §5.3).

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
        if _scan_one_ordering(resource_id, handle, spec, report):
            unsound.add(resource_id)
    return unsound


def _scan_one_ordering(  # noqa: C901
    resource_id: str, handle: Any, spec: Mapping[str, Any], report: Report
) -> bool:
    """One table's ordering scan. True where uniqueness must fall back to the aggregate."""
    # Part 03 §5.3 puts every table in its key's order unless Part 03 §5.4 overrides it, and R93 §3.3
    # moved that list out of the registry, so both come from `escapewheel_reader.ordering`.
    keys = stored_order(resource_id, spec)
    unique = spec["primary_key"] if adjacency_settles_uniqueness(resource_id, spec) else None
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
        report.add("error", "resource.unreadable", f"{resource_id}: {exc}", registry=report.resource_owner(resource_id))
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
            "error", "resource.unreadable", f"{resource_id}: {damaged}", registry=report.resource_owner(resource_id)
        )
        return False
    if broken:
        report.add(
            "error",
            f"{resource_id}.determined_by",
            "a column declared determined_by the key differs between two rows sharing it",
            [(f"row {i}", col, f"{a} != {b}") for i, col, a, b in broken[:ORDER_REPORT]],
            registry=report.resource_owner(resource_id),
        )
    if offending:
        report.add(
            "error",
            f"{resource_id}.physical_order",
            f"rows are not in declared sort order ({', '.join(keys)})",
            [(f"row {i}", str(prev), str(cur)) for i, prev, cur in offending[:ORDER_REPORT]],
            registry=report.resource_owner(resource_id),
        )
        # Adjacency settles uniqueness only for a file actually in order: a duplicate anywhere but
        # beside its twin is invisible to a scan of neighbours. Part 03 §5.3 makes the departure an
        # error, and uniqueness still falls back to the aggregate rather than being skipped.
        return bool(unique)
    if duplicated:
        report.add(
            "error",
            f"{resource_id}.primary_key_unique",
            "duplicate primary key",
            [(f"row {i}", str(row)) for i, row in duplicated[:ORDER_REPORT]],
            registry=report.resource_owner(resource_id),
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
def _spill_beside(packet: Packet) -> Iterator[Path | None]:
    """Yield a directory for DuckDB to spill into, removed afterwards.

    Beside the packet, not inside it. The filesystem has to be the packet's -- `/tmp` is tmpfs
    on several distributions, so spilling there consumes the memory the limit exists to bound
    -- but the packet root is the wrong place to put it: validating a packet would write into
    a directory whose bytes are supposed to be settled (Part 03 §8.1), leave it behind, and fail
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
        context.document for context in extension_contexts.values() if context.result.state == "valid"
    ]
    with _spill_beside(packet) as spill:
        connection = _bounded(packet.duckdb(), LIMITS if limits is None else limits, spill)
        try:
            unreadable = _install_rule_relations(packet, connection, [registry, *extension_documents])

            kinds = _declared_kinds(packet, registry, extension_documents)
            tier1 = generate(
                core_context,
                only=set(present),
                advisory=advisory,
                aggregate=unsound or set(),
                kinds=kinds,
                specialises=_specialisations(packet, registry, extension_documents),
                declared=False,
            )
            tier2 = _tier2_checks(registry, registry, report, "core", advisory)
            checks = [*tier1, *tier2]
            if recheck is not None:
                checks = [check for check in checks if concerns(check, recheck)]
            _run_checks(connection, checks, report, "core", unreadable, finalize=False)
            _check_manifest_sessions(packet, report)
            if not any(e.registry == "core" and e.status != "complete" for e in report.evaluations):
                report.record_evaluation("core", "complete")
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
        for resource_id, spec in _tables(document).items():
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
            columns = ", ".join(f'"{c["name"]}" {_DDL[c["type"]]}' for c in spec["columns"])
            connection.sql(f"CREATE OR REPLACE TABLE {resource_id} ({columns})")
    return unreadable


def _tier2_checks(
    document: Mapping[str, Any],
    core_registry: Mapping[str, Any],
    report: Report,
    registry_id: str,
    advisory: bool,
) -> list[Check]:
    """Return checked Tier 2 rules, or record why this registry cannot be evaluated."""
    language = document.get("rule_language")
    if language != PROFILE_ID:
        report.record_evaluation(
            registry_id,
            "unsupported",
            detail=f"rule language {language!r} is not supported; expected {PROFILE_ID!r}",
        )
        return []
    checked: list[Check] = []
    invalid = False
    for resource, table in _tables(document).items():
        for rule in table.get("rules", []):
            if rule.get("advisory") and not advisory:
                continue
            try:
                parsed = check_rule(rule["sql"], document, core_resources=core_registry)
            except RuleProfileError as exc:
                invalid = True
                report.record_evaluation(registry_id, "invalid", rule=rule.get("id"), detail=str(exc))
                continue
            checked.append(
                Check(
                    rule["id"],
                    rule["level"],
                    rule["message"],
                    parsed.sql,
                    resource,
                    tier=2,
                    dependencies=parsed.resources,
                )
            )
    return [] if invalid else checked


def _run_checks(
    connection: Any,
    checks: Sequence[Check],
    report: Report,
    registry_id: str,
    unreadable: set[str],
    *,
    finalize: bool = True,
) -> None:
    """Run generated checks and record what they returned."""
    tier2_incomplete = False
    for check in checks:
        if check.tier == 2 and (missing := sorted(check.dependencies & unreadable)):
            tier2_incomplete = True
            report.record_evaluation(
                registry_id,
                "incomplete",
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
                tier2_incomplete = True
                report.record_evaluation(
                    registry_id,
                    "incomplete",
                    rule=check.id,
                    detail=str(exc).splitlines()[0][:160],
                )
            else:
                report.add(
                    "error",
                    check.id,
                    f"check could not run: {str(exc).splitlines()[0][:90]}",
                    registry=registry_id,
                )
            continue
        if rows:
            report.add(check.level, check.id, check.message, rows, registry=registry_id)
    prior_failure = any(e.registry == registry_id and e.status != "complete" for e in report.evaluations)
    if finalize and not tier2_incomplete and not prior_failure:
        report.record_evaluation(registry_id, "complete")


def _check_manifest_sessions(packet: Packet, report: Report) -> None:
    """Compare the manifest inventory with ``core.sessions`` at the Part 05 shim."""
    check = "core.sessions.manifest_sessions_match"
    message = (
        "the manifest's session inventory and core.sessions disagree; the manifest names a "
        "session by its session_name, since an assigned session_id means nothing outside the "
        "packet that assigned it"
    )
    declared = {resource.resource_id for resource in packet.resources(kind="table")}
    table_values: list[str] = []
    if "core.sessions" in declared:
        try:
            table_values = [
                value
                for value in packet.table("core.sessions", columns=["session_name"]).column("session_name").to_pylist()
                if value is not None
            ]
        except (PacketError, OSError, pa.ArrowException) as exc:
            report.record_evaluation("core", "incomplete", rule=check, detail=str(exc))
            return
    listed = list(packet.manifest.sessions)
    listed_set, table_set = set(listed), set(table_values)
    rows = [(value,) for value in table_values if value not in listed_set]
    rows.extend((value,) for value in listed if value not in table_set)
    if rows:
        report.add("error", check, message, rows, registry="core")


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


def _declared_kinds(
    packet: Packet, registry: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, str | None]:
    """Every resource a discriminator may name, mapped to the column a paired value joins to.

    Built from the packet's registry *and* the extension registries it carries, because Part 02 §8.3
    lets a kind name an extension table and Part 02 §8.3 makes that the case the check must reach --
    the one whose hand-written union over core matched no branch and passed in silence.
    """
    tables = dict(_tables(registry))
    # Core's absent tables get empty stand-ins in _layer4, so all of them can be joined. An
    # extension's do not, so only what the packet carries can appear in the union.
    carried = {resource.resource_id for resource in packet.resources(kind="table")}
    for document in extensions:
        if isinstance(_tables(document), Mapping):
            tables.update({n: t for n, t in _tables(document).items() if n in carried})
    # Every declarable resource, whether or not a *paired* value could name it. Part 02 §8.3's
    # single-column-key rule governs the paired shape alone; R54's shared-key discriminator
    # names tables whose key is composite by construction, and dropping them here made a
    # correctly declared `interval_kind` read as naming nothing.
    return {name: _resolve_column(spec) for name, spec in tables.items()}


def _specialisations(
    packet: Packet, registry: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, list[tuple[str, dict[str, str]]]]:
    """Which resources could specialise which, keyed by the discriminated resource.

    A specialisation declares a reference back over the discriminated table's **whole** key
    (Part 02 §8.3). Anything else a discriminator could name is a resource that could not carry
    the key, so generating Part 02 §8.3's reverse check for it would be checking the impossible.
    """
    tables = dict(_tables(registry))
    carried = {resource.resource_id for resource in packet.resources(kind="table")}
    for document in extensions:
        if isinstance(_tables(document), Mapping):
            tables.update({n: t for n, t in _tables(document).items() if n in carried})
    found: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for name, spec in tables.items():
        for reference in spec.get("references", []):
            target = reference["resource"]
            key = (tables.get(target) or {}).get("primary_key") or []
            mapping = dict(zip(reference.get("resource_columns", []), reference["columns"], strict=False))
            if key and set(mapping) >= set(key):
                # The mapping, not just the name: Part 02 §8.3 requires the whole key and does not
                # require the same column names for it. `dynamic_foraging.trials` carries the
                # interval's id as `trial_id`, so a join on matching names finds nothing.
                found.setdefault(target, []).append((name, mapping))
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
) -> None:
    """Run each directing extension registry's generated and declared checks (Part 05 §5.4).

    R17 §3's claim is that nothing here is per-extension: the same `generate` produces an
    extension's Tier 1 checks from its structure and carries its Tier 2 rules, because an
    extension registry *is* a registry document. What this function adds is which tables its
    references may resolve against -- core's, since Part 09 §2 lets an extension reference them and
    forbids the reverse -- and the registry its findings are filed under, so they decide the
    extension's verdict and never core's (Part 05 §9.5).
    """
    registry = core_context.document
    assert isinstance(registry, Mapping)
    for extension_id, extension_context in extension_contexts.items():
        if extension_context.result.state != "valid":
            continue
        document = extension_context.document
        assert isinstance(document, Mapping)
        declared = set(_tables(document))
        # What the *packet* declares, not what the core registry knows: an extension's tables are
        # by definition absent from core's, and `present` is built from core's.
        carried = declared & {r.resource_id for r in packet.resources(kind="table")}
        if absent := sorted(declared - carried):
            report.add(
                "info",
                "extension.table_absent",
                f"{extension_id}: declares {len(absent)} table(s) this packet does not carry",
                [(name,) for name in absent],
                registry=extension_id,
            )
        tier1 = generate(
            extension_context,
            only=carried,
            advisory=advisory,
            aggregate=unsound or set(),
            resolvable=set(_tables(registry)),
            kinds=kinds,
            declared=False,
        )
        tier2 = _tier2_checks(document, registry, report, extension_id, advisory)
        checks = [*tier1, *tier2]
        if recheck is not None:
            checks = [check for check in checks if concerns(check, recheck)]
        _run_checks(connection, checks, report, extension_id, unreadable or set())
        report.add(
            "info",
            "extension.validated",
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
        Resources this call has just written, restricting the rules to those Part 03 §9.4 obliges to
        run: the ones attached to such a resource, and the ones whose query names one. `None`,
        the default, runs every rule, which is what a first commit and a packet of unknown
        provenance both need. An amendment passes what it writes, because Part 03 §9.2 forbids it
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
        byte -- 0.60 s for the 1,209 MB a packet owns, against 75 s for the 6.8 GB of LFP it merely
        references. The report names each digest's route.
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

    Returns
    -------
    Report
        Every finding, in the order the layers ran.
    """
    # The manifest the packet carries, which for an amendment's candidate is not the file on disk. A
    # reader already refused bytes the `json` phase would, so re-encoding what it decoded loses no finding.
    manifest = json.dumps(packet.manifest.entry).encode()
    report, bound = check_packet_manifest(packet.location, advisory=advisory, manifest=manifest)
    if bound is None:
        return report
    core_context = bound.core
    extensions = {name: context.document for name, context in bound.extensions.items()}
    directing = ([] if core_context is None else [(bound.core_id, core_context.document)]) + list(extensions.items())
    report.attribute(
        {declaration: str(name) for name, document in directing for declaration in document.get("resources", {})},
        packet.resources(),
    )
    _check_sources(packet, report)
    if core_context is None:
        return report
    effective = core_context.document
    withheld = set(packet.manifest.extensions) - set(extensions)
    packet = packet.with_declarations(effective, *extensions.values())
    _check_resource_declarations(packet, effective, extensions, withheld, report)
    assessed = _resolve_external(packet, report, checksums, store_digests, store_checksums) if external else set()
    if checksums:
        _check_owned_digests(packet, report, store_checksums)
    _check_packet_owned_arrays(packet, report)
    _check_time_origin(packet, report)
    # Every directing registry's tables receive the same storage checks (Part 05 §5.4).
    tables = _tables(effective)
    for document in extensions.values():
        tables.update(_tables(document))
    present = _check_schemas(packet, tables, report)
    _report_page_types_unassessed(len(present), report)
    _report_unassessed(packet, assessed | set(present), report)
    unsound = _check_ordering(tables, present, report, scan)
    _check_duplication(present, tables, report)
    _check_unfilled_metadata(present, tables, report)
    _check_reserved_values(present, tables, report)
    _check_unit_codes(present, tables, report)
    _run_rules(
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
    return report


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
        report.add("error", "packet.manifest.invalid_json", f"no readable {MANIFEST_FILENAME} at {location}: {exc}")
        return report, None
    report.bound = named_registries(raw)
    document = check_manifest(raw, issues)
    bound = None if document is None else bind_registries(location, document, issues)
    for issue in issues:
        report.add("error", issue.check, issue.message, issue.rows, registry=issue.registry)
    if bound is not None:
        for name, context in bound.contexts.items():
            report.record_registry(name, context, directs_checks=bound.directs(name), core=name == bound.core_id)
    return report, bound


__all__ = [
    "ARROW_TYPES",
    "VERDICTS",
    "Evaluation",
    "Finding",
    "Report",
    "check_packet_manifest",
    "registry_meta_schema",
    "sql_name",
    "validate",
]
