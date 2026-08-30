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
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any

import jsonschema
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from nwb_lake_reader import Packet, PacketError, ResourceUnreadableError, sql_name

from .generate import adjacency_settles_uniqueness, generate

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
        runs = packet.table("core.processing_runs", columns=["processing_run_id"])
    except PacketError:
        report.add(
            "error",
            "provenance.no_processing_runs_table",
            f"{len(named)} resource(s) name a processing run but the packet carries no core.processing_runs",
        )
        return
    for missing in sorted(named - set(runs.column("processing_run_id").to_pylist())):
        report.add(
            "error",
            "provenance.unknown_processing_run",
            f"processing_run_id {missing!r} appears in no row of core.processing_runs (R31 §5)",
        )


def _declared_axes(packet: Packet, owned: Sequence[Any], report: Report) -> dict[str, set[int]] | None:
    """Axis indices `core.array_dimensions` gives per array asset, or None if it has none.

    A null `axis_index` is skipped: it is a required column, so Tier 1 reports it, and
    counting it here would report the same defect a second time as a rank disagreement.
    """
    try:
        rows = packet.table("core.array_dimensions", columns=["array_asset_id", "axis_index"])
    except PacketError:
        report.add(
            "error",
            "array.no_array_dimensions_table",
            f"{len(owned)} packet-owned array(s) but no core.array_dimensions, so no axis is named (R3 §3.0)",
        )
        return None
    axes: dict[str, set[int]] = {}
    for asset, axis in zip(
        rows.column("array_asset_id").to_pylist(), rows.column("axis_index").to_pylist(), strict=True
    ):
        if asset is not None and axis is not None:
            axes.setdefault(str(asset), set()).add(int(axis))
    return axes


def _check_one_array(resource: Any, handle: Any, axes: dict[str, set[int]] | None, report: Report) -> None:
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
    elif axes is not None and (named := axes.get(str(asset), set())) != set(range(rank)):
        report.add(
            "error",
            "array.rank_disagrees_with_dimensions",
            f"{resource.resource_id} has rank {rank} but core.array_dimensions gives axis_index "
            f"{sorted(named) or 'none'} for {asset!r}; R3 §5 requires one row per stored axis",
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
    owned = [r for r in packet.resources(kind="dense_array_asset") if not r.is_external]
    if not owned:
        return
    axes = _declared_axes(packet, owned, report)
    for resource in owned:
        _check_one_array(resource, packet.array_resource(resource.resource_id), axes, report)


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
        keys = spec.get("sort")
        if not keys:
            continue
        unique = spec["primary_key"] if adjacency_settles_uniqueness(spec) else None
        # A constant column decides nothing, so drop it from both the order and the key it
        # settles -- but never to nothing, since a wholly constant key is every row duplicated.
        constant = _constant(handle.path, keys)
        keys = [k for k in keys if k not in constant] or list(keys)
        if unique:
            unique = [k for k in unique if k not in constant] or list(unique)
        offending: list[tuple[int, Any, Any]] = []
        duplicated: list[tuple[int, Any]] = []
        tail: tuple[Any, ...] | None = None
        start = 0
        # Read the string keys as codes. The scan compares them, and `_breaks` compares a
        # dictionary by rank without ever materialising a string; decoding here would build a
        # Python-free but still per-row copy of four identifier columns over the whole table.
        coded = [k for k in keys if pa.types.is_string(handle.schema().field(k).type)]
        reader = pq.ParquetFile(handle.path, read_dictionary=coded or None)
        for batch in reader.iter_batches(batch_size=ORDER_BATCH, columns=keys):
            first = _row_at(batch, keys, 0)
            if tail is not None and _sortable(first) < _sortable(tail):
                offending.append((start, tail, first))
            descents, repeats = _breaks(batch, keys, unique)
            offending.extend(
                (start + offset, _row_at(batch, keys, offset - 1), _row_at(batch, keys, offset)) for offset in descents
            )
            if unique:
                # The batch boundary needs its own comparison: the scan compares within a
                # batch, so a duplicate split across two would otherwise pass unseen.
                if tail is not None and _row_at(batch, unique, 0) == _tail_key(tail, keys, unique):
                    duplicated.append((start, _row_at(batch, unique, 0)))
                duplicated.extend((start + offset, _row_at(batch, unique, offset)) for offset in repeats)
            tail = _row_at(batch, keys, batch.num_rows - 1)
            start += batch.num_rows
            if len(offending) >= ORDER_REPORT and len(duplicated) >= ORDER_REPORT:
                break
        if offending:
            report.add(
                "warning",
                f"{resource_id}.physical_order",
                f"rows are not in declared sort order ({', '.join(keys)})",
                [(f"row {i}", str(prev), str(cur)) for i, prev, cur in offending[:ORDER_REPORT]],
            )
        if unique and offending:
            # Adjacency settles uniqueness only for a file actually in order: a duplicate
            # anywhere but beside its twin is invisible to a scan of neighbours. Ordering is a
            # warning by design -- a packet in the wrong order still conforms -- so uniqueness
            # falls back to the aggregate rather than being escalated or skipped.
            unsound.add(resource_id)
        elif duplicated:
            report.add(
                "error",
                f"{resource_id}.primary_key_unique",
                "duplicate primary key",
                [(f"row {i}", str(row)) for i, row in duplicated[:ORDER_REPORT]],
            )
    return unsound


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
) -> None:
    """Layer 4: Tier 1 checks generated from structure, then Tier 2 rules (R2 §7)."""
    with _spill_beside(packet) as spill:
        connection = _bounded(packet.duckdb(), LIMITS if limits is None else limits, spill)
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

            for check in generate(registry, only=set(present), advisory=advisory, aggregate=unsound or set()):
                try:
                    rows = _offending(connection, check.sql)
                except Exception as exc:  # noqa: BLE001 - an engine error is a finding, not a crash
                    report.add("error", check.id, f"check could not run: {str(exc).splitlines()[0][:90]}")
                    continue
                if rows:
                    report.add(check.level, check.id, check.message, rows)
        finally:
            with contextlib.suppress(Exception):
                connection.close()


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
    _check_packet_owned_arrays(packet, report)
    _check_materialization_provenance(packet, report)
    present = _check_schemas(packet, effective["tables"], report)
    unsound = _check_ordering(effective["tables"], present, report, scan)
    _run_rules(packet, effective, present, report, advisory, limits, unsound)
    return report


__all__ = ["ARROW_TYPES", "Finding", "Report", "sql_name", "validate"]
