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
import json
import shutil
import tempfile
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from escapewheel_reader import Location, Packet, PacketError
from escapewheel_reader.manifest import MANIFEST_FILENAME, Manifest
from escapewheel_reader.ordering import stored_order
from escapewheel_reader.resource_ids import (
    CORE_SESSIONS,
)

from . import amendment, check_table
from .declarations import check_resource_declarations, check_sources
from .errors import OrderFault, OrderViolation
from .generate import Check, Specialisation, adjacency_settles_uniqueness, concerns, generate
from .manifest import (
    Bound,
    Issue,
    bind_registries,
    check_manifest,
    confirm_replaced,
    named_registries,
)
from .registry_document import (
    CheckedRegistryContext,
)
from .registry_types import (
    DDL,
    registry_meta_schema,  # noqa: F401 - `escapewheel_writer.scaffold` imports it from here
    table_contracts,
)
from .report import Report
from .rule_language import PROFILE_ID, RuleProfileError, check_rule
from .shim.arrays import check_packet_owned_arrays
from .shim.external import resolve_external
from .shim.floors import report_page_types_unassessed, report_unassessed
from .shim.owned import check_owned_digests, check_packet_owned_opaque
from .shim.tables import (
    check_duplication,
    check_reserved_values,
    check_schemas,
    check_unfilled_metadata,
    check_unit_codes,
)
from .shim.time_origin import check_time_origin
from .vocabulary import EvaluationStatus, Level, RegistryState

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
