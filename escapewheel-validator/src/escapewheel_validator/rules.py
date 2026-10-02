"""Run a registry's generated checks and its Tier 2 rules over a packet's tables.

- :func:`run_rules` -- core's checks, then each directing extension's, over one bounded DuckDB
  connection.
- :data:`LIMITS` -- the DuckDB settings a validation bounds itself by.
- :func:`bounded`, :func:`spill_beside` -- apply those limits to a connection, and give it a
  directory beside the packet to spill into.

A rule is SQL returning offending rows, so an empty result is a pass.
"""

from __future__ import annotations

import contextlib
import shutil
import tempfile
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
from escapewheel_reader import Packet, PacketError
from escapewheel_reader.registries import declared_tables
from escapewheel_reader.resource_ids import (
    CORE_SESSIONS,
)

from . import check_table
from .generate import Check, Specialisation, concerns, generate, rule_check
from .registry_document import (
    CheckedRegistryContext,
)
from .registry_types import DDL
from .report import Report
from .rule_language import PROFILE_ID, RuleProfileError, check_rule
from .vocabulary import EvaluationStatus, Level, RegistryState

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
    """Run Tier 1 checks generated from structure, then Tier 2 rules (Part 05 §§5.1 and 5.2)."""
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
        for resource_id, spec in declared_tables(document).items():
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
    supported = language == PROFILE_ID
    # What a rule may name: an extension's rule reaches core's tables beside its own (Part 11 §3).
    visible = {**declared_tables(core_registry), **declared_tables(document)} if supported else {}
    for resource, table in declared_tables(document).items() if supported else ():
        for rule in table.get("rules", []):
            if rule.get("advisory") and not advisory:
                continue
            try:
                parsed = check_rule(rule["sql"], document, core_resources=core_registry)
            except RuleProfileError as exc:
                invalid.append((rule.get("id"), str(exc)))
                continue
            entry = check_table.rule(rule["id"], rule["level"])
            checked.append(rule_check(entry, rule["message"], parsed.sql, resource, visible, parsed.resources))
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
        if check.incomplete is not None:
            report.record_evaluation(
                registry_id, EvaluationStatus.INCOMPLETE, rule=check.id, detail=check.incomplete[:160]
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
                    resource=check.resource,
                    column=check.column,
                )
            continue
        if rows:
            report.add(
                check.entry, check.message, rows, registry=registry_id, resource=check.resource, column=check.column
            )


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
        report.add(check, message, rows, registry="core", resource=CORE_SESSIONS)


def _resolve_column(spec: Mapping[str, Any]) -> str | None:
    """Return the column a paired value joins to, or None where the resource is not namable.

    Part 02 §8.3 requires a single-column key, since a paired value holds one identifier. Which
    column it *matches* follows from the key's identity: an `assigned` key is a number this format
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
    Core's absent tables get empty stand-ins in `run_rules`, so all of them can be joined; an
    extension's do not, so only what the packet carries can be.
    """
    tables = dict(declared_tables(registry))
    carried = {resource.resource_id for resource in packet.resources(kind="table")}
    for document in extensions:
        if isinstance(declared_tables(document), Mapping):
            tables.update({n: t for n, t in declared_tables(document).items() if n in carried})
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
    tables = dict(declared_tables(registry))
    carried = {resource.resource_id for resource in packet.resources(kind="table")}
    for document in extensions:
        if isinstance(declared_tables(document), Mapping):
            tables.update({n: t for n, t in declared_tables(document).items() if n in carried})
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

    Nothing here is per-extension: the same `generate` produces an
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
        declared = set(declared_tables(document))
        # What the *packet* declares, not what the core registry knows: an extension's tables are
        # by definition absent from core's, and `present` is built from core's.
        carried = declared & {r.resource_id for r in packet.resources(kind="table")}
        if absent := sorted(declared - carried):
            report.add(
                check_table.EXTENSION_TABLE_ABSENT,
                f"{extension_id}: declares {len(absent)} table(s) this packet does not carry",
                [(name,) for name in absent],
                registry=extension_id,
                counts={"absent": len(absent)},
            )
        tier1 = generate(
            extension_context,
            only=carried,
            advisory=advisory,
            aggregate=unsound or set(),
            resolvable=set(declared_tables(registry)),
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
            counts={"checks": len(checks), "tables": len(carried)},
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


__all__: list[str] = []
