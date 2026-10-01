"""Generate Tier 1 validation checks from a registry's structure (Part 02 §10.1).

- :func:`generate` -- every check a checked registry implies, followed by its Tier 2 rules.
- :class:`Check` -- one check: SQL returning offending rows, so an empty result is a pass.
- :class:`Specialisation` -- one specialising reference, resolved against the packet's tables.
- :func:`concerns` -- whether an amendment writing some resources obliges a check to run.
- :func:`adjacency_settles_uniqueness` -- whether a table's sort order puts duplicate primary
  keys next to each other, so the ordering scan decides uniqueness.

No check is written by hand for a table. The checks for required columns, primary keys, foreign
keys, closed vocabularies and finite values follow from a registry's structure, and its Tier 2
rules pass through unchanged.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from escapewheel_reader import quote, sql_name
from escapewheel_reader.ordering import stored_order

from .registry_document import CheckedRegistryContext, RegistryRejected
from .vocabulary import Level, RegistryState


@dataclass(frozen=True)
class Check:
    """One validation check.

    Attributes
    ----------
    id : str
        Stable identifier, e.g. ``core.trials.primary_key_unique``.
    level : str
        ``error``, ``warning``, or ``info``.
    message : str
        What a non-empty result means.
    sql : str
        A query returning offending rows.
    resource : str
        The resource the check is declared on. Not necessarily the only one its query reads.
    optional_columns : frozenset of str
        The `optional` columns the query reads. A table omitting one leaves nothing to check, so the
        runner skips the check rather than reporting a query that cannot bind (Part 02 §§6, 10.1).
    """

    id: str
    level: str
    message: str
    sql: str
    resource: str
    tier: int = 1
    dependencies: frozenset[str] = frozenset()
    optional_columns: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        """Default a generated check's inputs to its attached resource."""
        if not self.dependencies:
            object.__setattr__(self, "dependencies", frozenset({self.resource}))


@dataclass(frozen=True)
class Specialisation:
    """One specialising reference (Part 02 §8.3), resolved against every table the packet declares.

    Attributes
    ----------
    detail : str
        The detail table declaring the reference.
    target : str
        The table the discriminator specialises, which the reference targets.
    on : tuple of (str, str)
        Each detail column with the target column it references.
    holder : str
        The table carrying the discriminator.
    column : str
        The discriminator column.
    via : tuple of (str, str), optional
        Where the discriminator is on another table, each column of the target's reference to it
        with the holder column it references.
    """

    detail: str
    target: str
    on: tuple[tuple[str, str], ...]
    holder: str
    column: str
    via: tuple[tuple[str, str], ...] | None = None


def concerns(check: Check, written: Collection[str]) -> bool:
    """Whether Part 05 §15.4 obliges `check` to run when `written` are the resources just written.

    Generated Tier 1 checks carry dependencies derived from registry structure, while Tier 2
    checks carry base relations returned by the Part 11 parser. Anything else reads only files an
    amendment may not modify (Part 05 §15.1) and Part 03 §8.1 declares immutable, so it can only
    reach the verdict it reached before.
    """
    return bool(check.dependencies & set(written))


def adjacency_settles_uniqueness(resource: str, table: Mapping[str, Any]) -> bool:
    """Whether a table's sort order puts duplicate primary keys next to each other.

    Two rows sharing a key are neighbours when nothing in the sort can order between them. That
    holds when every sort column up to and including the last key column is either a key column
    itself, or one the registry declares `determined_by` a subset of the key: a column that is a
    function of the key takes the same value in both rows, so it cannot separate them.

    `analysis.spike_events` is the case that needs the second clause. Part 03 §5.4 sorts it by
    `(session_id, clock_id, time_bucket_tick, …)` so a time filter and a unit filter both prune,
    which puts two non-key columns ahead of the key — but `clock_id` is the session's reference
    clock and `time_bucket_tick` is a function of `t_tick`, so neither varies between rows that
    share a key. Without the declaration a `GROUP BY` over every spike runs, and spills, to
    settle what one comparison per row already answers.

    False where a sort column genuinely varies within a key: a sort of `(a, x, b)` with key
    `(a, b)` lets `x` order duplicates apart, so neighbours are not enough and the aggregate is
    the only correct check.
    """
    key = table.get("primary_key")
    # Part 03 §5.3: a table the descriptor does not override is in its primary key's order.
    sort = stored_order(resource, table)
    if not key or not sort:
        return False
    determined = {c["name"]: set(c["determined_by"]) for c in table.get("columns", []) if "determined_by" in c}
    positions = [sort.index(k) for k in key if k in sort]
    if len(positions) != len(key):
        return False
    return all(column in key or determined.get(column, {object()}) <= set(key) for column in sort[: max(positions) + 1])


#: A dotted resource ID: two lowercase snake_case names. Part 02 §8.3 makes this checkable without
#: knowing which resources exist, so a discriminator holding an empty string is reported whatever
#: the packet declares.
RESOURCE_ID = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"


def _discriminator(
    resource: str,
    name: str,
    table: Mapping[str, Any],
    column: Mapping[str, Any],
    kinds: Mapping[str, str | None] | None,
    included: Collection[str],
    specialises: Mapping[str, Collection[Specialisation]] | None = None,
    specs: Mapping[str, Any] | None = None,
    keys: Mapping[str, Mapping[str, Any] | None] | None = None,
) -> list[Check]:
    """Build the checks one discriminator column implies (Part 02 §8.3).

    Three, and they fail for different reasons: the value is not a resource ID at all, it names a
    resource the packet does not declare, or it names one that exists and holds no such row.
    `resolves` sets the second's severity and whether the third is generated: R49's scope may
    legitimately name a rig the packet does not hold, where R54's interval kind naming nothing
    leaves the row uninterpretable.
    """
    col = quote(column["name"])
    checks = [
        Check(
            f"{resource}.{column['name']}.is_a_resource_id",
            Level.ERROR,
            f"{column['name']} holds a value that is not a dotted resource ID",
            f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL AND NOT regexp_matches({col}, '{RESOURCE_ID}')",
            resource,
        )
    ]
    if not kinds:
        return checks

    declared = ", ".join(f"'{k}'" for k in sorted(kinds))
    checks.append(
        Check(
            f"{resource}.{column['name']}.kind_declared",
            # Part 02 §8.3. Where an unresolvable kind is a fact rather than a defect it is still
            # reported: passed in silence, an extension kind would go unchecked without anything
            # saying so.
            Level.ERROR if column.get("resolves") == "required" else Level.INFO,
            f"{column['name']} names a resource this packet does not declare",
            f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL AND {col} NOT IN ({declared})",
            resource,
        )
    )

    # A paired value lives in the named table's key space (Part 02 §8.3), so it resolves value-to-key.
    paired = column.get("discriminates")
    if paired is None:
        # A shared-key discriminator: Part 02 §8.3 adds the direction a foreign key cannot point --
        # a row naming a kind with no counterpart in it, whose kind is then only a name, and which
        # every other check passes. Only where `resolves` is required: an optional kind naming
        # nothing is a fact (R49), not a defect.
        if column.get("resolves") != "required" or not table.get("primary_key"):
            return checks
        key = ", ".join(quote(c) for c in table["primary_key"])
        details = {s.detail: s for s in (specialises or {}).get(f"{resource}.{column['name']}", ())}
        for kind in sorted(kinds):
            found = details.get(kind)
            if found is None:
                # A kind declaring no specialising reference naming this discriminator holds no
                # counterpart, so every row naming it is reported.
                message = (
                    f"a row names {kind}, which declares no specialising reference naming "
                    f"{resource}.{column['name']} (Part 02 §8.3)"
                )
                sql = f"SELECT {key} FROM {name} d WHERE d.{col} = '{kind}'"
            else:
                on = " AND ".join(f"s.{quote(a)} = d.{quote(b)}" for a, b in found.on)
                message = f"a row names {kind} and has no counterpart there (Part 02 §8.3)"
                sql = (
                    f"SELECT {key} FROM {name} d WHERE d.{col} = '{kind}' "
                    f"AND NOT EXISTS (SELECT 1 FROM {kind} s WHERE {on})"
                )
            checks.append(
                Check(
                    f"{resource}.{column['name']}.{sql_name(kind)}_is_specialised",
                    Level.ERROR,
                    message,
                    sql,
                    resource,
                    dependencies=frozenset({resource, kind}),
                )
            )
        return checks
    return checks + _paired_value(resource, name, column, paired, kinds, included, specs or {}, keys)


def _kind_matches(found: Specialisation, reachable: Collection[str]) -> list[Check]:
    """Build the check that each detail row's specialised row names the detail table (Part 02 §8.3).

    Generated whatever the discriminator declares for `resolves`: the check compares two rows the
    packet holds, where `resolves` governs a kind naming a resource the packet lacks. The inner
    join leaves a detail row naming no row to its reference's anti-join.
    """
    if found.target not in reachable or found.holder not in reachable:
        return []
    detail = ", ".join(f"t.{quote(c)}" for c, _ in found.on)
    on = " AND ".join(f"t.{quote(a)} = s.{quote(b)}" for a, b in found.on)
    col = quote(found.column)
    if found.via is None:
        joins, value = f"JOIN {found.target} s ON {on}", f"s.{col}"
    else:
        via = " AND ".join(f"s.{quote(a)} = h.{quote(b)}" for a, b in found.via)
        joins, value = f"JOIN {found.target} s ON {on} LEFT JOIN {found.holder} h ON {via}", f"h.{col}"
    return [
        Check(
            f"{found.detail}.{'_'.join(c for c, _ in found.on)}.names_a_row_of_its_kind",
            Level.ERROR,
            f"a row specialises a {found.target} row whose {found.column} does not name {found.detail} (Part 02 §8.3)",
            f"SELECT {detail} FROM {found.detail} t {joins} WHERE {value} IS NULL OR {value} <> '{found.detail}'",
            found.detail,
            dependencies=frozenset({found.detail, found.target, found.holder}),
        )
    ]


def _key_column(kind: str, specs: Mapping[str, Any], keys: Mapping[str, Mapping[str, Any] | None] | None) -> Any:
    """Return a named resource's one key column, or None where its key is not one column."""
    if keys is not None and kind in keys:
        return keys[kind]
    key = (specs.get(kind) or {}).get("primary_key") or []
    if len(key) != 1:
        return None
    return next((c for c in specs[kind]["columns"] if c["name"] == key[0]), None)


def _paired_value(
    resource: str,
    name: str,
    column: Mapping[str, Any],
    paired: str,
    kinds: Mapping[str, str | None],
    included: Collection[str],
    specs: Mapping[str, Any],
    keys: Mapping[str, Mapping[str, Any] | None] | None,
) -> list[Check]:
    """Build a paired value's checks: its named keys' shape, one anti-join per kind, and its kind.

    None is generated unless the discriminator resolves `required`.

    The value sits on the discriminator's own table, or on the specialised table that
    `discriminates_via` names, which reaches the discriminator's row through its one reference
    (Part 02 §8.3). A `string` value matches the named key, or its `*_name` where the key is
    assigned; an `identifier` value holds the key's own value, so both sides share a type.
    """
    if column.get("resolves") != "required":
        return []
    col = quote(column["name"])
    via = column.get("discriminates_via")
    holder = resource if via is None else str(via).rsplit(".", 1)[0]
    value = next((c for c in (specs.get(holder) or {}).get("columns", []) if c["name"] == paired), None)
    if value is None:
        return []
    identifier = value.get("role") == "identifier"

    fits: dict[str, str] = {}
    misfits: list[str] = []
    for kind in sorted(kinds):
        key = _key_column(kind, specs, keys)
        if identifier:
            ok = key is not None and all(key.get(field) == value.get(field) for field in ("type", "identity"))
            if ok:
                fits[kind] = key["name"]
        else:
            ok = kinds[kind] is not None
            if ok:
                fits[kind] = str(kinds[kind])
        if not ok:
            misfits.append(kind)

    checks: list[Check] = []
    if misfits:
        checks.append(
            Check(
                f"{resource}.{column['name']}.key_fits_paired_value",
                Level.ERROR,
                f"{column['name']} names a resource whose primary key is not one column {paired} can hold "
                "(Part 02 §8.3)",
                f"SELECT DISTINCT {col} FROM {name} WHERE {col} IN ({', '.join(repr(k) for k in misfits)})",
                resource,
            )
        )
    if via is None:
        rows, join, kind_of = f"{name} r", "", f"r.{col}"
        selected = f"r.{col}, r.{quote(paired)}"
    else:
        spec = specs[holder]
        via_column = str(via).rsplit(".", 1)[1]
        reference = next(
            (ref for ref in spec.get("references", []) if ref["resource"] == resource and via_column in ref["columns"]),
            None,
        )
        # A via table that does not reach its discriminator, or that the packet does not carry,
        # has no value to check; the registry check reports the first.
        if reference is None or holder not in included:
            return checks
        pairs = zip(reference["columns"], reference["resource_columns"], strict=True)
        on = " AND ".join(f"r.{quote(a)} = d.{quote(b)}" for a, b in pairs)
        rows, join, kind_of = f"{holder} r", f" JOIN {name} d ON {on}", f"d.{col}"
        selected = ", ".join([*(f"r.{quote(c)}" for c in spec.get("primary_key") or []), f"r.{quote(paired)}"])
    for kind, target in sorted(fits.items()):
        if kind not in included:
            continue
        # Per kind, so an identifier value compares with its key in the key's own type. A string
        # value is cast on both sides: a carried key may be a number, and DuckDB raises on a string
        # it cannot coerce rather than reporting it.
        match = (
            f"t.{quote(target)} = r.{quote(paired)}"
            if identifier
            else f"CAST(t.{quote(target)} AS VARCHAR) = CAST(r.{quote(paired)} AS VARCHAR)"
        )
        checks.append(
            Check(
                f"{resource}.{column['name']}.{sql_name(kind)}_resolves",
                Level.ERROR,
                f"{paired} names no row of {kind}, which {column['name']} names (Part 02 §8.3)",
                f"SELECT DISTINCT {selected} FROM {rows}{join} "
                f"WHERE {kind_of} = '{kind}' AND r.{quote(paired)} IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM {kind} t WHERE {match})",
                resource,
                dependencies=frozenset({resource, holder, kind}),
            )
        )
    if via is not None:
        checks.append(
            Check(
                f"{resource}.{column['name']}.specialised_row_has_kind",
                Level.ERROR,
                f"a {holder} row pairs {paired} with no kind, since its {column['name']} is null (Part 02 §8.3)",
                f"SELECT {selected} FROM {rows}{join} WHERE {kind_of} IS NULL",
                resource,
                dependencies=frozenset({resource, holder}),
            )
        )
    return checks


def _generate(  # noqa: C901
    registry: Mapping[str, Any],
    *,
    only: set[str] | None = None,
    advisory: bool = False,
    aggregate: set[str] | None = None,
    resolvable: set[str] | None = None,
    kinds: Mapping[str, str | None] | None = None,
    specialises: Mapping[str, Collection[Specialisation]] | None = None,
    declared: bool = True,
    keys: Mapping[str, Mapping[str, Any] | None] | None = None,
) -> list[Check]:
    """Build every check a registry implies.

    Parameters
    ----------
    registry : Mapping
        A parsed registry document.
    advisory : bool, default False
        Include rules marked ``advisory`` (Part 02 §10.2). They never carry ``error``, so
        enabling them cannot change whether a packet passed.
    only : set of str, optional
        Restrict to these resources. Checks referring to a resource outside the set are
        still generated if their own table is inside it; a packet need not carry every
        table, and a foreign key into an absent one cannot be evaluated.
    resolvable : set of str, optional
        Resources a reference may resolve against, beyond this registry's own tables. An
        extension registry needs core's tables here, since it declares none of them and Part 09 §6.1
        lets it reference them.
    kinds : Mapping, optional
        Every resource a discriminator may name (Part 02 §8.3), mapped to the column a paired value
        joins to -- the `*_name` where the key is assigned, the key where it is carried (R55
        §2.3.3). Supplied by the caller rather than read from this registry, because Part 02 §8.3
        requires the resolution to reach the packet's *extension* kinds -- the case the mechanism
        exists to cover, and one a check built over core alone passes in silence.
    keys : Mapping, optional
        Every resource a discriminator may name, mapped to its one key column's declaration, or
        None where its key is not one column. An identifier paired value must share that
        column's type and identity (Part 02 §8.3). Absent, this registry's own tables supply it.

    Returns
    -------
    list of Check
        Generated Tier 1 checks followed by the registry's Tier 2 rules.
    """
    checks: list[Check] = []
    tables: Mapping[str, Any] = {
        str(name): declaration["table"]
        for name, declaration in registry["resources"].items()
        if declaration["kind"] == "table"
    }
    included = set(tables) if only is None else set(only)
    # What a reference may point at, which is not the same as what gets checks. An extension
    # declares its own tables and references core's (Part 09 §6.1), so without this its foreign keys
    # generate nothing and an orphan validates clean -- the gap R46 closed for core.
    reachable = included if resolvable is None else set(resolvable) | included

    for resource, table in tables.items():
        if resource not in included:
            continue
        name = resource
        presence = {c["name"]: c["presence"] for c in table["columns"]}
        optional = {column for column, state in presence.items() if state == "optional"}

        for column in table["columns"]:
            if column["presence"] == "required":
                checks.append(
                    Check(
                        f"{resource}.{column['name']}.not_null",
                        Level.ERROR,
                        f"required column {column['name']} contains nulls",
                        f"SELECT * FROM {name} WHERE {quote(column['name'])} IS NULL",
                        resource,
                    )
                )
            if column.get("finite") is True:
                # `isfinite` is null for null, so a null stays presence's concern alone.
                checks.append(
                    Check(
                        f"{resource}.{column['name']}.finite",
                        Level.ERROR,
                        f"{column['name']} holds NaN or an infinity",
                        f"SELECT * FROM {name} WHERE NOT isfinite({quote(column['name'])})",
                        resource,
                        optional_columns=frozenset({column["name"]}) & optional,
                    )
                )
            if values := column.get("enum"):
                allowed = ", ".join(f"'{v}'" for v in values)
                col = quote(column["name"])
                checks.append(
                    Check(
                        f"{resource}.{column['name']}.in_vocabulary",
                        Level.ERROR,
                        f"{column['name']} carries a value outside its closed vocabulary",
                        f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL AND {col} NOT IN ({allowed})",
                        resource,
                        optional_columns=frozenset({column["name"]}) & optional,
                    )
                )

        for column in table["columns"]:
            if column.get("role") != "discriminator":
                continue
            checks.extend(_discriminator(resource, name, table, column, kinds, included, specialises, tables, keys))

        by_scan = adjacency_settles_uniqueness(resource, table) and resource not in (aggregate or set())
        if (key := table.get("primary_key")) and not by_scan:
            columns = ", ".join(quote(k) for k in key)
            checks.append(
                Check(
                    f"{resource}.primary_key_unique",
                    Level.ERROR,
                    "duplicate primary key",
                    f"SELECT {columns}, COUNT(*) AS n FROM {name} GROUP BY {columns} HAVING COUNT(*) > 1",
                    resource,
                )
            )

        for ref in table.get("references", []):
            if ref["resource"] not in reachable:
                continue
            if declared_discriminator := ref.get("specialises"):
                checks.extend(
                    check
                    for found in (specialises or {}).get(declared_discriminator, ())
                    if found.detail == resource
                    for check in _kind_matches(found, reachable)
                )
            parent = ref["resource"]
            on = " AND ".join(f"c.{quote(a)} = p.{quote(b)}" for a, b in zip(ref["columns"], ref["resource_columns"]))
            # A foreign key that may be null constrains only its non-null values; without this
            # guard every legitimately absent value reports as a violation.
            guards = [f"c.{quote(a)} IS NOT NULL" for a in ref["columns"] if presence.get(a) != "required"]
            where = " AND ".join([f"p.{quote(ref['resource_columns'][0])} IS NULL", *guards])
            selected = ", ".join("c." + quote(a) for a in ref["columns"])
            checks.append(
                Check(
                    f"{resource}.{'_'.join(ref['columns'])}_resolves",
                    Level.ERROR,
                    f"{', '.join(ref['columns'])} does not resolve to {ref['resource']}",
                    f"SELECT DISTINCT {selected} FROM {name} c LEFT JOIN {parent} p ON {on} WHERE {where}",
                    resource,
                    dependencies=frozenset({resource, ref["resource"]}),
                    optional_columns=frozenset(ref["columns"]) & optional,
                )
            )

        for rule in table.get("rules", []) if declared else []:
            if rule.get("advisory") and not advisory:
                continue
            checks.append(Check(rule["id"], rule["level"], rule["message"], rule["sql"], resource, tier=2))

    return checks


def generate(
    registry: CheckedRegistryContext,
    *,
    only: set[str] | None = None,
    advisory: bool = False,
    aggregate: set[str] | None = None,
    resolvable: set[str] | None = None,
    kinds: Mapping[str, str | None] | None = None,
    specialises: Mapping[str, Collection[Specialisation]] | None = None,
    declared: bool = True,
    keys: Mapping[str, Mapping[str, Any] | None] | None = None,
) -> list[Check]:
    """Build checks only from a valid context bound to the registry it checked."""
    if not isinstance(registry, CheckedRegistryContext):
        raise TypeError("generate() requires a CheckedRegistryContext")
    if registry.result.state != RegistryState.VALID:
        raise RegistryRejected("check generator", registry)
    document = registry.document
    if not isinstance(document, Mapping):  # guarded by a valid result; retained for type safety
        raise RegistryRejected("check generator", registry)
    return _generate(
        document,
        only=only,
        advisory=advisory,
        aggregate=aggregate,
        resolvable=resolvable,
        kinds=kinds,
        specialises=specialises,
        declared=declared,
        keys=keys,
    )
