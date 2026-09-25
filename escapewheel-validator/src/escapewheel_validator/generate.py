"""Generate Tier 1 validation checks from a registry.

Tier 1 follows from structure alone (Part 02 §10.1): required columns, primary keys, foreign
keys, closed vocabularies, finite values. Nothing here is written per table. Tier 2 rules carried
in the registry are passed through unchanged.

Every check is SQL returning offending rows; an empty result is a pass (R2 §7.3).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from escapewheel_reader import quote, sql_name
from escapewheel_reader.ordering import stored_order

from .registry_document import CheckedRegistryContext, RegistryRejected


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


def concerns(check: Check, written: Collection[str]) -> bool:
    """Whether Part 03 §9.4 obliges `check` to run when `written` are the resources just written.

    Generated Tier 1 checks carry dependencies derived from registry structure, while Tier 2
    checks carry base relations returned by the Part 11 parser. Anything else reads only files an
    amendment may not modify (Part 03 §9.2) and Part 04 §5.1 declares immutable, so it can only
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
    share a key. Without the declaration a 287 M-row `GROUP BY` runs and spills 27 GB to settle
    what one comparison per row already answers.

    False where a sort column genuinely varies within a key: a sort of `(a, x, b)` with key
    `(a, b)` lets `x` order duplicates apart, so neighbours are not enough and the aggregate is
    the only correct check.
    """
    key = table.get("primary_key")
    # Part 03 §5.3: a table with no override is in its primary key's order. R93 §3.3 removed the
    # registry field that used to say so, and Part 03 §5.4's list says it instead.
    sort = stored_order(resource, table)
    if not key or not sort:
        return False
    determined = {c["name"]: set(c["determined_by"]) for c in table.get("columns", []) if "determined_by" in c}
    positions = [sort.index(k) for k in key if k in sort]
    if len(positions) != len(key):
        return False
    return all(column in key or determined.get(column, {object()}) <= set(key) for column in sort[: max(positions) + 1])


#: A dotted resource ID: two lowercase snake_case names. Part 02 §8.3 makes this checkable without
#: knowing which resources exist, which is what nothing did -- `scope_kind` could hold an empty
#: string and no rule would see it.
RESOURCE_ID = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"


def _discriminator(
    resource: str,
    name: str,
    table: Mapping[str, Any],
    column: Mapping[str, Any],
    kinds: Mapping[str, str | None] | None,
    included: Collection[str],
    specialises: Mapping[str, Collection[tuple[str, Mapping[str, str]]]] | None = None,
    specs: Mapping[str, Any] | None = None,
) -> list[Check]:
    """Build the checks one discriminator column implies (Part 02 §8.3).

    Three, and they fail for different reasons: the value is not a resource ID at all, it names a
    resource the packet does not declare, or it names one that exists and holds no such row. Only
    the second is what `resolves` governs -- R49's scope may legitimately name a rig the packet
    does not hold, where R54's interval kind naming nothing leaves the row uninterpretable.
    """
    col = quote(column["name"])
    checks = [
        Check(
            f"{resource}.{column['name']}.is_a_resource_id",
            "error",
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
            # reported: R49 §2.5's union passed it in silence, which is what let an extension
            # kind go unchecked without anything saying so.
            "error" if column.get("resolves") == "required" else "info",
            f"{column['name']} names a resource this packet does not declare",
            f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL AND {col} NOT IN ({declared})",
            resource,
        )
    )

    # Part 02 §8.3: the third shape. The named resource's rows *are* the positions, so there is no key
    # correspondence and Part 02 §8.3's reverse check does not apply -- which R90 said twice and neither
    # sentence could be acted on, by-position and shared-key being indistinguishable until
    # `positions_in` declared the difference. What is checkable instead is that the column named
    # holds a position: the registry knows each resource's `structural_index` columns, so they
    # become literals here, as the declared resources do in `kind_declared`.
    if (positions := column.get("positions_in")) is not None:
        legal = {
            kind: sorted(
                c["name"] for c in (specs or {}).get(kind, {}).get("columns", []) if c.get("role") == "structural_index"
            )
            for kind in sorted(kinds)
        }
        branches = " OR ".join(
            f"({col} = '{kind}' AND {quote(positions)} NOT IN ({', '.join(repr(c) for c in cols)}))"
            for kind, cols in legal.items()
            if cols
        )
        unpositioned = [kind for kind, cols in legal.items() if not cols]
        if unpositioned:
            branches = " OR ".join(filter(None, [branches, f"{col} IN ({', '.join(repr(k) for k in unpositioned)})"]))
        if branches:
            checks.append(
                Check(
                    f"{resource}.{column['name']}.position_column_indexes",
                    "error",
                    f"{positions} does not name a structural_index column of the resource "
                    f"{column['name']} names (R100 §2.2)",
                    f"SELECT DISTINCT {col}, {quote(positions)} FROM {name} WHERE {branches}",
                    resource,
                )
            )
        return checks

    # A paired value lives in the named table's key space (Part 02 §8.3), so it resolves value-to-key.
    paired = column.get("discriminates")
    if paired is None:
        # A shared-key discriminator: the reference Part 02 §8.3 requires of the named table
        # generates the anti-join from detail to discriminated row. Part 02 §8.3 adds the direction a
        # foreign key cannot point -- a row naming a kind with no counterpart in it, which is
        # Part 01 §3.10a's "a kind that resolves to nothing is a name again" and which every other
        # check passes. Only where `resolves` is required: an optional kind naming nothing is a
        # fact (R49), not a defect.
        if column.get("resolves") != "required" or not table.get("primary_key"):
            return checks
        # Only a resource that could *be* a specialisation: one declaring a reference back over
        # the discriminated table's whole key, which is what Part 02 §8.3 requires of a named
        # resource. Without the filter this generates one check per declared resource, and 34 of
        # the 35 name a core table that could never carry the key (Part 02 §8.3).
        for kind, mapping in sorted((specialises or {}).get(resource, ()), key=lambda pair: pair[0]):
            on = " AND ".join(f"s.{quote(mapping[c])} = d.{quote(c)}" for c in table["primary_key"])
            checks.append(
                Check(
                    f"{resource}.{column['name']}.{sql_name(kind)}_is_specialised",
                    "error",
                    f"a row names {kind} and has no counterpart there (Part 02 §8.3)",
                    f"SELECT {', '.join(quote(c) for c in table['primary_key'])} FROM {name} d "
                    f"WHERE d.{col} = '{kind}' "
                    f"AND NOT EXISTS (SELECT 1 FROM {kind} s WHERE {on})",
                    resource,
                    dependencies=frozenset({resource, kind}),
                )
            )
        return checks
    # Only a resource a paired value can actually name: one with a single-column key, which is
    # what `_resolve_column` returns a column for (Part 02 §8.3).
    joinable = {k: key for k, key in kinds.items() if k in included and key is not None}
    if not joinable:
        return checks
    # CAST both sides. A paired value is a string, because one column resolves against several
    # kinds and a carried key is a number where an assigned one's name is not -- so the union
    # mixes types by construction. Uncast, DuckDB coerces the string and *raises* on one that is
    # not a number, turning a finding into a check that could not run.
    union = " UNION ALL ".join(
        f"SELECT '{k}' AS kind, CAST({quote(key)} AS VARCHAR) AS id FROM {k}" for k, key in sorted(joinable.items())
    )
    val = quote(paired)
    return checks + [
        Check(
            f"{resource}.{column['name']}.resolves",
            "error",
            f"{paired} names no row of the resource {column['name']} declares",
            f"WITH known AS ({union}) SELECT DISTINCT r.{col}, r.{val} FROM {name} r "
            f"WHERE r.{col} IN (SELECT DISTINCT kind FROM known) AND NOT EXISTS "
            f"(SELECT 1 FROM known k WHERE k.kind = r.{col} AND k.id = CAST(r.{val} AS VARCHAR))",
            resource,
            dependencies=frozenset({resource, *joinable}),
        )
    ]


def _generate(
    registry: Mapping[str, Any],
    *,
    only: set[str] | None = None,
    advisory: bool = False,
    aggregate: set[str] | None = None,
    resolvable: set[str] | None = None,
    kinds: Mapping[str, str | None] | None = None,
    specialises: Mapping[str, Collection[tuple[str, Mapping[str, str]]]] | None = None,
    declared: bool = True,
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
        extension registry needs core's tables here, since it declares none of them and Part 09 §2
        lets it reference them.
    kinds : Mapping, optional
        Every resource a discriminator may name (Part 02 §8.3), mapped to the column a paired value
        joins to -- the `*_name` where the key is assigned, the key where it is carried (R55
        §2.3.3). Supplied by the caller rather than read from this registry, because Part 02 §8.3
        requires the resolution to reach the packet's *extension* kinds -- the case Part 02 §8.3
        designed the mechanism for and whose hand-written union quietly matched no branch.

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
    # declares its own tables and references core's (Part 09 §2), so without this its foreign keys
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
                        "error",
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
                        "error",
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
                        "error",
                        f"{column['name']} carries a value outside its closed vocabulary",
                        f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL AND {col} NOT IN ({allowed})",
                        resource,
                        optional_columns=frozenset({column["name"]}) & optional,
                    )
                )

        for column in table["columns"]:
            if column.get("role") != "discriminator":
                continue
            checks.extend(_discriminator(resource, name, table, column, kinds, included, specialises, tables))

        by_scan = adjacency_settles_uniqueness(resource, table) and resource not in (aggregate or set())
        if (key := table.get("primary_key")) and not by_scan:
            columns = ", ".join(quote(k) for k in key)
            checks.append(
                Check(
                    f"{resource}.primary_key_unique",
                    "error",
                    "duplicate primary key",
                    f"SELECT {columns}, COUNT(*) AS n FROM {name} GROUP BY {columns} HAVING COUNT(*) > 1",
                    resource,
                )
            )

        for ref in table.get("references", []):
            if ref["resource"] not in reachable:
                continue
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
                    "error",
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
    specialises: Mapping[str, Collection[tuple[str, Mapping[str, str]]]] | None = None,
    declared: bool = True,
) -> list[Check]:
    """Build checks only from a valid context bound to the registry it checked."""
    if not isinstance(registry, CheckedRegistryContext):
        raise TypeError("generate() requires a CheckedRegistryContext")
    if registry.result.state != "valid":
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
    )
