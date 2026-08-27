"""Validate a packet against the registry it declares.

Four layers, in ``09`` §10's order: the manifest's shape, the registry it embeds, each
resource's physical schema, then the rules.

The split between SQL and this module is not a matter of convenience (R12 §4). SQL covers
what the data *says* — values, keys, references, vocabularies. This module covers how it is
*stored* — physical order, file presence, column types — because a query cannot see any of
that, and a storage-layer check written as SQL fails silently rather than loudly.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from typing import Any

import jsonschema
import pyarrow.parquet as pq

from .._sql import sql_name
from ..errors import PacketError
from ..packet import Packet
from .generate import generate

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
    """

    level: str
    check: str
    message: str
    rows: tuple[tuple[str, ...], ...] = ()


@dataclass
class Report:
    """The outcome of validating a packet."""

    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> int:
        """How many error-level findings were produced."""
        return sum(f.level == "error" for f in self.findings)

    @property
    def warnings(self) -> int:
        """How many warning-level findings were produced."""
        return sum(f.level == "warning" for f in self.findings)

    @property
    def passed(self) -> bool:
        """Whether the packet is valid. Warnings do not make a packet invalid."""
        return self.errors == 0

    def add(self, level: str, check: str, message: str, rows: Sequence[Sequence[Any]] = ()) -> None:
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
            Finding(level, check, message, tuple(tuple(str(v) for v in row) for row in list(rows)[:5]))
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
            "validator": {"name": "nwb_lake_reader", "version": _version()},
            "summary": {"errors": self.errors, "warnings": self.warnings},
            "findings": [
                {"level": f.level, "check": f.check, "message": f.message, "rows": [list(r) for r in f.rows]}
                for f in self.findings
            ],
        }


def _version() -> str:
    from .. import __version__

    return __version__


def _registry_meta_schema() -> dict[str, Any]:
    text = importlib_resources.files("nwb_lake_reader").joinpath("schemas/registry.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


def _check_embedded_registry(packet: Packet, embedded: Mapping[str, Any], report: Report) -> None:
    """Layer 1: the registry the packet carries (R2 §8, §9)."""
    for error in jsonschema.Draft202012Validator(_registry_meta_schema()).iter_errors(embedded):
        report.add("error", "registry.schema", f"{'/'.join(str(p) for p in error.path)}: {error.message}")
    declared = packet.manifest.registry_version
    if embedded.get("registry_version") != declared:
        report.add(
            "error",
            "registry.version_mismatch",
            f"manifest says {declared}, embedded registry says {embedded.get('registry_version')}",
        )


def _check_codec_declarations(packet: Packet, report: Report) -> None:
    """Layer 1b: manifest-internal codec consistency (R15 §4, level 1).

    Both sides are manifest fields, so this holds offline. Whether a declared codec matches
    the array's actual metadata is level 2 for packet-owned arrays and level 3 -- the
    requested external mode -- for the rest.
    """
    declared: set[str] = set()
    for resource in packet.resources():
        declared |= set(resource.codecs)
    summary = set(packet.manifest.required_codecs)
    if declared != summary:
        detail = []
        if missing := sorted(declared - summary):
            detail.append(f"resources use {', '.join(missing)} but required_codecs omits them")
        if extra := sorted(summary - declared):
            detail.append(f"required_codecs lists {', '.join(extra)} that no resource uses")
        report.add("error", "manifest.required_codecs_is_the_union", "; ".join(detail))

    # An external resource's codecs, sha256 and size_bytes are claims this mode does not
    # verify (R14 §2.3.1, R15 §4). Say so, rather than let "passed" imply otherwise.
    external = [r.resource_id for r in packet.resources() if r.is_external]
    if external:
        report.add(
            "info",
            "external.unverified",
            f"{len(external)} external resource(s) not resolved; their codecs, sha256 and "
            "size_bytes are unverified claims",
            [(name,) for name in external],
        )


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
    actual = str(schema.field(column["name"]).type)
    if actual != ARROW_TYPES[column["type"]]:
        report.add(
            "error",
            "schema.column_type",
            f"{resource_id}.{column['name']} is {actual}, registry declares {column['type']}",
        )


def _check_ordering(tables: Mapping[str, Any], present: Mapping[str, Any], report: Report) -> None:
    """Layer 3: declared sort order, read in written order (R10 §2, R12 §2)."""
    for resource_id, handle in present.items():
        keys = tables[resource_id].get("sort")
        if not keys:
            continue
        columns = pq.read_table(handle.path, columns=keys).to_pydict()
        rows = list(zip(*(columns[k] for k in keys)))
        ordered = [tuple((v is None, v) for v in row) for row in rows]
        offending = [(i, rows[i - 1], rows[i]) for i in range(1, len(ordered)) if ordered[i] < ordered[i - 1]]
        if offending:
            report.add(
                "warning",
                f"{resource_id}.physical_order",
                f"rows are not in declared sort order ({', '.join(keys)})",
                [(f"row {i}", str(prev), str(cur)) for i, prev, cur in offending],
            )


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


def _run_rules(packet: Packet, registry: Mapping[str, Any], present: Mapping[str, Any], report: Report) -> None:
    """Layer 4: Tier 1 checks generated from structure, then Tier 2 rules (R2 §7)."""
    connection = packet.duckdb()

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

    for check in generate(registry, only=set(present)):
        try:
            rows = connection.sql(check.sql).fetchall()
        except Exception as exc:  # noqa: BLE001 - an engine error is a finding, not a crash
            report.add("error", check.id, f"check could not run: {str(exc).splitlines()[0][:90]}")
            continue
        if rows:
            report.add(check.level, check.id, check.message, rows)


def validate(packet: Packet, *, registry: Mapping[str, Any] | None = None) -> Report:
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

    Returns
    -------
    Report
        Every finding, in the order the layers ran.

    Raises
    ------
    PacketError
        If no registry is available.
    """
    report = Report()
    embedded = packet.registry
    effective = registry if registry is not None else embedded
    if effective is None:
        raise PacketError(
            f"{packet.manifest.packet_id} embeds no registry at schemas/logical_schemas.json and none was supplied"
        )

    if embedded is not None:
        _check_embedded_registry(packet, embedded, report)
    _check_codec_declarations(packet, report)
    present = _check_schemas(packet, effective["tables"], report)
    _check_ordering(effective["tables"], present, report)
    _run_rules(packet, effective, present, report)
    return report


__all__ = ["ARROW_TYPES", "Finding", "Report", "sql_name", "validate"]
