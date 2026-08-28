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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any

import jsonschema
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from nwb_lake_reader import Packet, PacketError, sql_name

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
        """How many error-level findings were produced."""
        return sum(f.level == "error" for f in self.findings)

    @property
    def warnings(self) -> int:
        """How many warning-level findings were produced."""
        return sum(f.level == "warning" for f in self.findings)

    @property
    def passed(self) -> bool:
        """Whether the packet is valid. Warnings do not make a packet invalid.

        Advisory rules cannot be ``error`` (R26 §3), so this is invariant under the
        ``advisory`` flag: asking for more to read never changes the verdict.
        """
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


def _registry_meta_schema() -> dict[str, Any]:
    text = importlib_resources.files("nwb_lake_validator").joinpath("schemas/registry.schema.json").read_text()
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


def _descents(batch: Any, keys: Sequence[str]) -> list[int]:
    """Offsets where a batch decreases lexicographically over `keys`.

    Vectorized per column rather than per row: a quarter of a billion Python tuple
    comparisons is minutes of wall clock, and the same comparison in Arrow is seconds. A
    descent at row i means some key decreases there while every earlier key is equal, so the
    equal-so-far mask carries forward across columns. Null sorts first, matching the writer.
    """
    n = batch.num_rows - 1
    if n < 1:
        return []
    descending: Any = pa.array([False] * n)
    equal_so_far: Any = pa.array([True] * n)
    for key in keys:
        column: Any = batch.column(key)
        prior, current = column.slice(0, n), column.slice(1, n)
        prior_null, current_null = pc.is_null(prior), pc.is_null(current)
        # null < value, value !< null, null == null
        less = pc.or_(
            pc.and_(current_null, pc.invert(prior_null)),
            pc.and_(pc.invert(pc.or_(prior_null, current_null)), pc.less(current, prior)),
        )
        same = pc.or_(
            pc.and_(prior_null, current_null),
            pc.and_(pc.invert(pc.or_(prior_null, current_null)), pc.equal(current, prior)),
        )
        descending = pc.or_(descending, pc.and_(equal_so_far, pc.fill_null(less, False)))
        equal_so_far = pc.and_(equal_so_far, pc.fill_null(same, False))
    return [i + 1 for i in pc.indices_nonzero(descending).to_pylist()]


def _check_ordering(tables: Mapping[str, Any], present: Mapping[str, Any], report: Report) -> None:
    """Layer 3: declared sort order, read in written order (R10 §2, R12 §2)."""
    for resource_id, handle in present.items():
        keys = tables[resource_id].get("sort")
        if not keys:
            continue
        offending: list[tuple[int, Any, Any]] = []
        tail: tuple[Any, ...] | None = None
        start = 0
        for batch in pq.ParquetFile(handle.path).iter_batches(batch_size=ORDER_BATCH, columns=keys):
            first = _row_at(batch, keys, 0)
            if tail is not None and _sortable(first) < _sortable(tail):
                offending.append((start, tail, first))
            offending.extend(
                (start + offset, _row_at(batch, keys, offset - 1), _row_at(batch, keys, offset))
                for offset in _descents(batch, keys)
            )
            tail = _row_at(batch, keys, batch.num_rows - 1)
            start += batch.num_rows
            if len(offending) >= ORDER_REPORT:
                del offending[ORDER_REPORT:]
                break
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


def _run_rules(
    packet: Packet,
    registry: Mapping[str, Any],
    present: Mapping[str, Any],
    report: Report,
    advisory: bool,
    limits: Mapping[str, Any] | None = None,
) -> None:
    """Layer 4: Tier 1 checks generated from structure, then Tier 2 rules (R2 §7)."""
    spill = Path(packet.root) / ".duckdb-spill" if hasattr(packet, "root") else None
    connection = _bounded(packet.duckdb(), LIMITS if limits is None else limits, spill)

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

    for check in generate(registry, only=set(present), advisory=advisory):
        try:
            rows = _offending(connection, check.sql)
        except Exception as exc:  # noqa: BLE001 - an engine error is a finding, not a crash
            report.add("error", check.id, f"check could not run: {str(exc).splitlines()[0][:90]}")
            continue
        if rows:
            report.add(check.level, check.id, check.message, rows)


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
    _check_codec_declarations(packet, report)
    present = _check_schemas(packet, effective["tables"], report)
    _check_ordering(effective["tables"], present, report)
    _run_rules(packet, effective, present, report, advisory, limits)
    return report


__all__ = ["ARROW_TYPES", "Finding", "Report", "sql_name", "validate"]
