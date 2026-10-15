"""Validate a packet against the registries it binds (Part 05 §5).

- :func:`validate` -- run every phase over an opened packet and return its :class:`.Report`.
- :func:`check_packet_manifest` -- the manifest and registry-binding phases alone, from the
  manifest's bytes.

`validate` is four phases over one context: the manifest and the registries it binds, what each
resource stores, each table's physical schema and order, then the rules. A phase reads what the
ones before it established. Storage is checked in Python and not in SQL, because a query cannot see
how data is stored and a storage check written as SQL passes in silence.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyarrow as pa
from escapewheel_reader import Location, Packet, PacketError
from escapewheel_reader.manifest import MANIFEST_FILENAME, Manifest
from escapewheel_reader.registries import declared_tables

from . import amendment, check_table
from .declarations import check_resource_declarations, check_sources
from .manifest import (
    Bound,
    Issue,
    bind_registries,
    check_manifest,
    confirm_replaced,
    named_registries,
)
from .registry_document import CheckedRegistryContext
from .report import Report
from .rules import LIMITS, bounded, run_rules, spill_beside
from .shim.arrays import check_packet_owned_arrays
from .shim.external import resolve_external
from .shim.floors import report_page_types_unassessed, report_unassessed
from .shim.ordering import check_ordering
from .shim.owned import check_owned_digests, check_owned_sizes, check_packet_owned_opaque
from .shim.tables import (
    check_duplication,
    check_reserved_values,
    check_schemas,
    check_unfilled_metadata,
    check_unit_codes,
)
from .shim.time_origin import check_time_origin
from .verification import Verification
from .vocabulary import EvaluationStatus


def validate(
    packet: Packet,
    *,
    advisory: bool = False,
    limits: Mapping[str, Any] | None = None,
    scan: Collection[str] | None = None,
    recheck: Collection[str] | None = None,
    verification: Verification | None = None,
    superseded: Mapping[str, Any] | None = None,
    replaced: Sequence[str | Path] = (),
    external: bool | None = None,
    checksums: bool | None = None,
    store_digests: bool | None = None,
    store_checksums: bool | None = None,
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
    verification : Verification, optional
        Which claims about stored bytes to establish beyond structure: recorded digests, store
        digests, and what the manifest claims of each external resource. The default establishes
        none, since structural validation reaches for no resource the packet does not own
        (Part 04 §5.3).
    superseded : Mapping, optional
        The manifest this one supersedes, for a writer validating an amendment before it retains
        that manifest. Absent, the retained manifest immediately preceding this version is compared
        (Part 05 §15.6), and a packet retaining none has nothing to compare.
    replaced : sequence of str or Path, optional
        Packet roots, or manifest files, to read as packets the manifest's `replaces` names. Each
        difference from the item it is read as is a `packet.replaces.mismatch` warning (Part 04 §3);
        a packet no one supplies is not looked for.
    external, checksums, store_digests, store_checksums : bool, optional
        The modes as separate keywords, for a caller written before `verification`. Each sets the
        member of :class:`.Verification` it is named for, and `external` is off unless given. Not
        accepted beside `verification`.

    Returns
    -------
    Report
        Every finding, in the order the layers ran.

    Raises
    ------
    ReplacedPacketUnreadable
        If no published manifest can be read at a path in `replaced`.
    TypeError
        If a mode keyword is given beside `verification`.
    """
    context = _Context(
        packet,
        _modes(
            verification,
            external=external,
            checksums=checksums,
            store_digests=store_digests,
            store_checksums=store_checksums,
        ),
        advisory=advisory,
        limits=limits,
        scan=scan,
        recheck=recheck,
        superseded=superseded,
        replaced=replaced,
    )
    if _bind(context):
        _check_resources(context)
        _check_tables(context)
        _check_rules(context)
    return context.report


@dataclass
class _Context:
    """What the phases of one validation share: what was asked, and what each phase established."""

    packet: Packet
    modes: Verification
    advisory: bool = False
    limits: Mapping[str, Any] | None = None
    scan: Collection[str] | None = None
    recheck: Collection[str] | None = None
    superseded: Mapping[str, Any] | None = None
    replaced: Sequence[str | Path] = ()
    report: Report = field(default_factory=Report)
    #: What binding established; set where the manifest phases reached it.
    bound: Bound | None = None
    #: The core registry's checked context, where it directs packet checks.
    core: CheckedRegistryContext | None = None
    #: Every directing registry's table contracts, by resource ID.
    tables: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    #: External resources whose own metadata a mode read.
    assessed: set[str] = field(default_factory=set)
    #: Each table whose file opened, by resource ID.
    present: dict[str, Any] = field(default_factory=dict)
    #: Tables whose uniqueness the ordering scan could not settle, which the aggregate decides.
    unsound: set[str] = field(default_factory=set)

    @property
    def documents(self) -> list[Mapping[str, Any]]:
        """Core's registry document, then each directing extension's."""
        assert self.bound is not None and self.core is not None
        return [self.core.document, *(extension.document for extension in self.bound.extensions.values())]


def _bind(context: _Context) -> bool:
    """Run the manifest phases, and return whether a core registry directs the phases after them."""
    packet = context.packet
    # The manifest the packet carries, which for an amendment's candidate is not the file on disk. A
    # reader already refused bytes the `json` phase would, so re-encoding what it decoded loses no finding.
    manifest = json.dumps(packet.manifest.entry).encode()
    report, bound = check_packet_manifest(packet.location, advisory=context.advisory, manifest=manifest)
    context.report, context.bound = report, bound
    if bound is None:
        return False
    for message, rows in confirm_replaced(packet.manifest.entry, context.replaced):
        report.add(check_table.PACKET_REPLACES_MISMATCH, message, rows)
    core_context = bound.core
    extensions = {name: extension.document for name, extension in bound.extensions.items()}
    directing = ([] if core_context is None else [(bound.core_id, core_context.document)]) + list(extensions.items())
    report.attribute(
        {declaration: str(name) for name, document in directing for declaration in document.get("resources", {})},
        packet.resources(),
    )
    check_sources(packet, report)
    if core_context is None:
        return False
    effective = core_context.document
    withheld = set(packet.manifest.extensions) - set(extensions)
    context.core = core_context
    context.packet = packet.with_declarations(effective, *extensions.values())
    check_resource_declarations(context.packet, effective, extensions, withheld, report)
    return True


def _check_resources(context: _Context) -> None:
    """Check what each resource stores against what the manifest and the tables say of it."""
    packet, report, modes = context.packet, context.report, context.modes
    if modes.resolves_external:
        context.assessed = resolve_external(packet, report, modes.checksums, modes.store_digests, modes.store_checksums)
    if modes.checksums:
        check_owned_digests(packet, report, modes.store_checksums)
    check_packet_owned_arrays(packet, report)
    check_packet_owned_opaque(packet, report)
    check_owned_sizes(packet, report)
    check_time_origin(packet, report)


def _check_tables(context: _Context) -> None:
    """Give every directing registry's tables the same storage checks (Part 05 §5.4)."""
    report = context.report
    for document in context.documents:
        context.tables.update(declared_tables(document))
    tables = context.tables
    present = context.present = check_schemas(context.packet, tables, report)
    report_page_types_unassessed(len(present), report)
    report_unassessed(context.packet, context.assessed | set(present), report)
    context.unsound = check_ordering(tables, present, report, context.scan)
    check_duplication(present, tables, report)
    check_unfilled_metadata(present, tables, report)
    check_reserved_values(present, tables, report)
    check_unit_codes(present, tables, report)


def _check_rules(context: _Context) -> None:
    """Run each directing registry's rules, then compare an amendment with what it supersedes."""
    assert context.bound is not None and context.core is not None
    run_rules(
        context.packet,
        context.core,
        context.bound.extensions,
        context.present,
        context.report,
        context.advisory,
        context.limits,
        context.unsound,
        context.recheck,
    )
    _check_amendment(
        context.packet, context.documents, context.tables, context.report, context.limits, context.superseded
    )


def _modes(verification: Verification | None, **keywords: bool | None) -> Verification:
    """Return the modes a call asked for, through `verification` or through the separate keywords."""
    given = {name: value for name, value in keywords.items() if value is not None}
    if verification is None:
        return Verification(**{"external": False, **given})
    if given:
        raise TypeError(f"validate() takes verification or {', '.join(given)}, not both")
    return verification


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
        report.add(
            finding.check,
            finding.message,
            finding.rows,
            registry=owner,
            resource=finding.resource,
            counts=finding.counts,
        )


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
        report.add(issue.check, issue.message, issue.rows, registry=issue.registry, resource=issue.resource)
    if bound is not None:
        for name, context in bound.contexts.items():
            report.record_registry(name, context, directs_checks=bound.directs(name), core=name == bound.core_id)
    return report, bound


__all__ = [
    "check_packet_manifest",
    "validate",
]
