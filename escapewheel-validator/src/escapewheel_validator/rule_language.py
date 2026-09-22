"""Static boundary for the Escapewheel Tier 2 SQL profile.

The registry carries SQL text, but an engine's parser is intentionally broader than the
language the specification admits.  This module parses every rule before execution, rejects
non-query and environment-dependent surfaces, resolves exact registry relation names, and
returns the dependencies used for incremental validation.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from sqlglot import exp, parse
from sqlglot.errors import ParseError
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.qualify_columns import OptimizeError
from sqlglot.optimizer.scope import build_scope

PROFILE_ID = "escapewheel-rule-sql-v0.1"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
BRACKETED_COMMENT = re.compile(r"/\*")
EXPLICIT_NULL_ORDER = re.compile(r"\bNULLS\s+(?:FIRST|LAST)\b", re.IGNORECASE)
NONSTANDARD_NOT_EQUAL = re.compile(r"!=")
DERIVED_ALIAS_WITHOUT_AS = re.compile(
    r"\)\s+(?!AS\b|WITHIN\b|OVER\b|FILTER\b)([a-z][a-z0-9_]*)\s+(?=WHERE\b|JOIN\b|LEFT\b|INNER\b|ON\b|GROUP\b|HAVING\b|UNION\b|$)",
    re.IGNORECASE,
)


class RuleProfileError(ValueError):
    """A rule is not in the selected portable profile."""


@dataclass(frozen=True)
class CheckedRule:
    """The facts established by static profile validation."""

    sql: str
    resources: frozenset[str]
    result_names: tuple[str, ...]


_FORBIDDEN_NODES = tuple(
    node
    for name in (
        "Alter",
        "Attach",
        "Cache",
        "Command",
        "Copy",
        "Create",
        "Delete",
        "Describe",
        "Detach",
        "Drop",
        "Execute",
        "Grant",
        "Insert",
        "LoadData",
        "Merge",
        "Pragma",
        "Set",
        "Show",
        "Transaction",
        "TruncateTable",
        "Update",
        "Use",
    )
    if (node := getattr(exp, name, None)) is not None
)

# SQLGlot represents standardized routines with dedicated nodes and leaves extensions as
# Anonymous.  Only the two Part 11 extensions are allowed through that generic node.
_ANONYMOUS_ROUTINES = frozenset({"isfinite", "isnan"})
_ALLOWED_FUNCTION_NODES = tuple(
    node
    for name in (
        "Abs",
        "Coalesce",
        "Count",
        "DenseRank",
        "IsNan",
        "Lag",
        "Max",
        "Min",
        "PercentileCont",
        "RowNumber",
    )
    if (node := getattr(exp, name, None)) is not None
)
_STRUCTURAL_FUNCTION_NODES = tuple(
    node for name in ("And", "Case", "Cast", "Exists", "If", "Or") if (node := getattr(exp, name, None)) is not None
)


def _identifier(value: str, subject: str) -> None:
    if not IDENTIFIER.fullmatch(value):
        raise RuleProfileError(f"{subject} {value!r} is not exact lowercase snake case")


def _base_tables(expression: exp.Expression, visible: set[str]) -> frozenset[str]:
    ctes = {cte.alias for cte in expression.find_all(exp.CTE)}
    resources: set[str] = set()
    for table in expression.find_all(exp.Table):
        # A table function has an expression rather than an identifier as its name.
        if not isinstance(table.this, exp.Identifier):
            raise RuleProfileError("table functions are outside the profile")
        name = table.name
        if not table.db and name in ctes:
            _identifier(name, "common-table-expression name")
            continue
        if not table.db:
            raise RuleProfileError(f"base relation {name!r} is not a qualified registry resource")
        namespace = table.db
        _identifier(namespace, "resource namespace")
        _identifier(name, "resource name")
        resource = f"{namespace}.{name}"
        if resource not in visible:
            raise RuleProfileError(f"relation {resource!r} is not visible to this registry")
        resources.add(resource)
    return frozenset(resources)


def _check_identifiers(expression: exp.Expression) -> None:
    for identifier in expression.find_all(exp.Identifier):
        _identifier(identifier.name, "identifier")
    for subquery in expression.find_all(exp.Subquery):
        if isinstance(subquery.parent, (exp.From, exp.Join)) and not subquery.alias:
            raise RuleProfileError("a derived table needs an explicit AS correlation name")


def _check_binding(expression: exp.Expression, tables: Mapping[str, Any]) -> None:
    """Resolve every column against the declared relations before execution."""
    nested_schema: dict[str, dict[str, dict[str, str]]] = {}
    for resource, table in tables.items():
        namespace, name = resource.split(".", 1)
        nested_schema.setdefault(namespace, {})[name] = {column["name"]: column["type"] for column in table["columns"]}
    schema = cast(dict[str, object], nested_schema)
    try:
        qualified = qualify(
            expression.copy(),
            schema=schema,
            validate_qualify_columns=True,
            identify=False,
            quote_identifiers=False,
        )
    except OptimizeError as exc:
        raise RuleProfileError(f"query does not bind to its registry declarations: {exc}") from exc
    if build_scope(qualified) is None:
        raise RuleProfileError("query has no resolvable scope")


def _check_surface(expression: exp.Expression, sql: str) -> None:  # noqa: C901
    if BRACKETED_COMMENT.search(sql):
        raise RuleProfileError("bracketed comments are outside the profile")
    if EXPLICIT_NULL_ORDER.search(sql):
        raise RuleProfileError("explicit NULLS FIRST or NULLS LAST is outside the profile")
    if NONSTANDARD_NOT_EQUAL.search(sql):
        raise RuleProfileError("!= is outside the profile; use <>")
    if DERIVED_ALIAS_WITHOUT_AS.search(sql):
        raise RuleProfileError("a derived-table correlation name must be introduced by AS")
    if _FORBIDDEN_NODES and any(expression.find_all(*_FORBIDDEN_NODES)):
        raise RuleProfileError("the rule contains a non-query or state-changing construct")
    if expression.args.get("order") is not None:
        raise RuleProfileError("a top-level result ORDER BY is outside the profile")
    for query in expression.find_all(exp.Query):
        if query is not expression and query.args.get("with_") is not None:
            raise RuleProfileError("a nested WITH is outside the profile")
    for order in expression.find_all(exp.Ordered):
        if order.args.get("desc"):
            raise RuleProfileError("DESC is outside the profile")
    for window in expression.find_all(exp.Window):
        if window.args.get("order") is None or not window.args["order"].expressions:
            raise RuleProfileError("every window invocation needs ORDER BY")
        if window.args.get("spec") is not None:
            raise RuleProfileError("window frames are outside the profile")
    for join in expression.find_all(exp.Join):
        side = (join.args.get("side") or "").upper()
        kind = (join.args.get("kind") or "").upper()
        if side in {"RIGHT", "FULL"} or kind in {"CROSS", "NATURAL"}:
            raise RuleProfileError(f"{(side or kind).lower()} join is outside the profile")
        if join.args.get("on") is None and join.args.get("using") is None:
            raise RuleProfileError("a join needs ON or USING")
    for function in expression.find_all(exp.Func):
        if isinstance(function, exp.Anonymous):
            if function.name.lower() not in _ANONYMOUS_ROUTINES:
                raise RuleProfileError(f"routine {function.name!r} is outside the profile")
        elif not isinstance(function, (*_ALLOWED_FUNCTION_NODES, *_STRUCTURAL_FUNCTION_NODES)):
            # CAST, CASE, FILTER and window syntax are expression nodes rather than Func.
            raise RuleProfileError(f"routine {function.sql_name()} is outside the profile")
    for conversion in expression.find_all(exp.Cast):
        target = conversion.to.sql().upper()
        if target not in {"DOUBLE", "DOUBLE PRECISION", "DECIMAL(38, 0)", "DECIMAL(38,0)"}:
            raise RuleProfileError(f"cast target {target!r} is outside the profile")
    for division in expression.find_all(exp.Div):
        if not any(
            isinstance(side, exp.Cast) and "DOUBLE" in side.to.sql().upper()
            for side in (division.this, division.expression)
        ):
            raise RuleProfileError("division needs an operand explicitly cast to DOUBLE PRECISION")


def _check_recursion(expression: exp.Expression, sql: str) -> None:
    with_clause = expression.args.get("with_")
    if with_clause is None or not with_clause.args.get("recursive"):
        return
    # The admitted form is deliberately small.  This structural test is independent of the
    # execution engine and recognizes the depth-counter form used by the registry.
    normalized = " ".join(sql.lower().split())
    required = (" union all ", "depth", ".depth + ", ".depth < ")
    if any(piece not in normalized for piece in required):
        raise RuleProfileError("recursive CTE is not the bounded depth-counter form")
    for cte in expression.find_all(exp.CTE):
        name = cte.alias
        references = [table for table in cte.this.find_all(exp.Table) if not table.db and table.name == name]
        if len(references) != 1:
            raise RuleProfileError("a recursive CTE needs exactly one self-reference")


def _check_window_keys(
    expression: exp.Expression,
    resources: frozenset[str],
    tables: Mapping[str, Any],
) -> None:
    """Establish deterministic input identity for LAG and ROW_NUMBER windows."""
    keys = [set(tables[name].get("primary_key") or ()) for name in resources if name in tables]
    for window in expression.find_all(exp.Window):
        if not isinstance(window.this, (exp.Lag, exp.RowNumber)):
            continue
        columns = {
            column.name
            for item in [*window.args.get("partition_by", []), *window.args["order"].expressions]
            for column in item.find_all(exp.Column)
        }
        if not any(key and key <= columns for key in keys):
            raise RuleProfileError("LAG or ROW_NUMBER partition and order do not establish an input key")


def _check_exact_overflow(expression: exp.Expression) -> None:
    """Reject the unambiguously unsafe stored-integer arithmetic shape."""
    for operation in expression.find_all(exp.Add, exp.Sub, exp.Mul):
        if any(operation.find_all(exp.Case)):
            continue
        if isinstance(operation.parent, exp.Cast) and "DECIMAL(38" in operation.parent.to.sql().upper():
            continue
        left_columns = list(operation.this.find_all(exp.Column))
        right_columns = list(operation.expression.find_all(exp.Column))
        if left_columns and right_columns and not any(operation.find_all(exp.Cast)):
            raise RuleProfileError("stored exact operands need DECIMAL(38,0) widening before arithmetic")


def _result_names(expression: Any) -> tuple[str, ...]:
    selects = expression.selects
    names: list[str] = []
    for selected in selects:
        if isinstance(selected, exp.Star):
            raise RuleProfileError("a final result cannot project *")
        alias = selected.alias
        if alias:
            name = alias
        elif isinstance(selected, exp.Column):
            name = selected.name
        else:
            raise RuleProfileError("a final result expression needs an explicit alias")
        _identifier(name, "result name")
        names.append(name)
    if len(names) != len(set(names)):
        raise RuleProfileError("final result names must be unique")
    return tuple(names)


def check_rule(
    sql: str,
    registry: Mapping[str, Any],
    *,
    core_resources: set[str] | Mapping[str, Any] | None = None,
) -> CheckedRule:
    """Parse and statically validate one Tier 2 query.

    Parameters
    ----------
    sql : str
        The authored query.
    registry : mapping
        The registry document that owns the rule.
    core_resources : set of str or mapping, optional
        Core and analysis resources visible to an extension registry. A registry mapping also
        supplies their declarations for pre-execution column binding and window-key checks.
    """
    try:
        statements = parse(sql)
    except ParseError as exc:
        raise RuleProfileError(str(exc).splitlines()[0]) from exc
    if len(statements) != 1 or statements[0] is None:
        raise RuleProfileError("a rule must contain exactly one query expression")
    parsed = statements[0]
    if not isinstance(parsed, exp.Query):
        raise RuleProfileError("a rule must be a query expression")
    expression: Any = parsed
    own = set(registry.get("tables", {}))
    extension = registry.get("extension_id")
    core_tables = dict(core_resources.get("tables", {})) if isinstance(core_resources, Mapping) else {}
    core_names = set(core_tables) if core_tables else set(core_resources or ())
    visible = own if extension is None else own | core_names
    _check_surface(expression, sql)
    _check_identifiers(expression)
    resources = _base_tables(expression, visible)
    tables = core_tables | dict(registry.get("tables", {}))
    _check_binding(expression, tables)
    _check_window_keys(expression, resources, tables)
    _check_exact_overflow(expression)
    _check_recursion(expression, sql)
    names = _result_names(expression)
    return CheckedRule(sql=sql, resources=resources, result_names=names)


__all__ = ["PROFILE_ID", "CheckedRule", "RuleProfileError", "check_rule"]
