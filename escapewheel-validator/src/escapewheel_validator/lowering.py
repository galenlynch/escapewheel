"""Lower a Tier 2 query to the SQL DuckDB executes (Part 11 §4).

- :func:`lower` -- a query as DuckDB must be given it to evaluate it as Part 11 defines it.

A rule runs as authored except where DuckDB's own semantics differ from the language's. Each
difference is spliced into the authored text at token boundaries: regenerating a query from its
parse tree would respell its routines and its null ordering, and change what the engine is asked.

Four differences are lowered. DuckDB interpolates `PERCENTILE_CONT` in its ordering value's own
domain, where Part 11 §5 converts the value to binary64 first. It converts a `DECIMAL` or a
`HUGEINT` to an approximate domain through an intermediate that is itself rounded, where Part 11 §4
rounds every exact-to-approximate conversion once, to nearest with ties to even; its conversion from
text rounds once, so each such conversion is made through text. It gives the three operands of
`BETWEEN` one common domain, where Part 11 §4 makes `BETWEEN` two comparisons, so a `BETWEEN` whose
comparisons would take different domains is written as the two. And it brings an `IN` list's members
into the domain they share with the left operand, where Part 11 §4 types the list first, so an exact
member of a `REAL` list compared with a `DOUBLE PRECISION` operand is converted to `REAL` first.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

from sqlglot import Token, Tokenizer, TokenType, exp, parse_one
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, build_scope

from .errors import LoweringFailed


class _Domain(Enum):
    """The SQL domain of an expression, as far as a conversion depends on it."""

    #: `INTEGER` or `BIGINT`, which the engine converts to an approximate domain correctly.
    INTEGER = "integer"
    #: `DECIMAL`, or an integer literal beyond `BIGINT`, which the engine holds as `HUGEINT`.
    DECIMAL = "decimal"
    REAL = "real"
    DOUBLE = "double"
    #: No numeric domain.
    OTHER = "other"
    #: A bare `NULL`, or a recursive reference being resolved: it takes the domain it meets.
    NULL = "null"


_APPROXIMATE = {_Domain.REAL: "REAL", _Domain.DOUBLE: "DOUBLE PRECISION"}
_STORED = {
    "int32": _Domain.INTEGER,
    "int64": _Domain.INTEGER,
    "float32": _Domain.REAL,
    "float64": _Domain.DOUBLE,
}
_CAST_TARGETS = {
    exp.DataType.Type.INT: _Domain.INTEGER,
    exp.DataType.Type.BIGINT: _Domain.INTEGER,
    exp.DataType.Type.DECIMAL: _Domain.DECIMAL,
    exp.DataType.Type.FLOAT: _Domain.REAL,
    exp.DataType.Type.DOUBLE: _Domain.DOUBLE,
}
_BIGINT_MAX = 2**63 - 1
_ARGUMENT_DOMAIN = (exp.Paren, exp.Neg, exp.Alias, exp.Abs, exp.Min, exp.Max, exp.Lag, exp.Window, exp.Filter)
_BIGINT_ROUTINES = (exp.Count, exp.RowNumber, exp.DenseRank, exp.Length)
_NOT_NUMERIC = (exp.Predicate, exp.Connector, exp.Not, exp.Boolean, exp.IsNan, exp.Anonymous, exp.Interval)
#: Operators whose two operands take their common domain.
_PAIRS = (exp.EQ, exp.NEQ, exp.LT, exp.LTE, exp.GT, exp.GTE, exp.NullSafeEQ, exp.NullSafeNEQ)
_ARITHMETIC = (exp.Add, exp.Sub, exp.Mul, exp.Div)
#: What a source exposing no column of a name answers.
_ABSENT = object()
#: Where a node of the parse tree was authored: its key in each node's `meta`.
_AUTHORED = "authored"
#: How many tokens beyond its outermost positioned leaves an expression's text is searched for.
_REACH = 12
#: How many `BETWEEN`s one query may need written as two comparisons, counting each copy made.
_BETWEEN_LIMIT = 64
#: Operands whose text stays one operand beside a comparison operator without parentheses.
_ATOMIC = (exp.Column, exp.Literal, exp.Null, exp.Func, exp.Paren)

if TYPE_CHECKING:
    _Member = tuple[exp.Expr | None, _Domain | None]


def _common(domains: Iterable[_Domain | None]) -> _Domain | None:
    """Return the common domain Part 11 §4 gives these, or None where one of them is unknown."""
    met = [domain for domain in domains if domain is not _Domain.NULL]
    if not met:
        return _Domain.NULL
    if None in met:
        return None
    for domain in (_Domain.OTHER, _Domain.DOUBLE, _Domain.REAL, _Domain.DECIMAL):
        if domain in met:
            return domain
    return _Domain.INTEGER


def _literal(literal: exp.Literal) -> _Domain | None:
    """Return the domain the engine gives a literal."""
    if literal.is_string:
        return _Domain.OTHER
    text = literal.name.lower()
    if "e" in text:
        return _Domain.DOUBLE
    if "." in text:
        return _Domain.DECIMAL
    if not text.isdecimal():
        return None
    return _Domain.INTEGER if int(text) <= _BIGINT_MAX else _Domain.DECIMAL


def _results(case: exp.Case) -> list[exp.Expr]:
    """Return the result expressions of a `CASE`."""
    results = [branch.args["true"] for branch in case.args["ifs"]]
    return [*results, case.args["default"]] if case.args.get("default") is not None else results


def _query(node: exp.Expr) -> exp.Expr:
    """Return the query a parenthesized or subquery node holds."""
    while isinstance(node, (exp.Subquery, exp.Paren)):
        node = node.this
    return node


class _Binding:
    """The domain of each expression of a qualified query, from the declarations it binds to."""

    def __init__(self, qualified: exp.Expr, tables: Mapping[str, Mapping[str, Any]]) -> None:
        self._tables = tables
        self._scopes: dict[int, Scope] = {}
        self._queries: dict[int, Scope] = {}
        self._resolving: set[tuple[int, int]] = set()
        root = build_scope(qualified)
        # A scope is yielded after those nested in it, so the first to claim a column is the innermost.
        for scope in root.traverse() if root is not None else ():
            self._queries[id(scope.expression)] = scope
            for column in scope.columns:
                self._scopes.setdefault(id(column), scope)

    def domain(self, node: exp.Expr) -> _Domain | None:
        """Return the domain of an expression, or None where it cannot be told."""
        if isinstance(node, _ARGUMENT_DOMAIN):
            return self.domain(node.this)
        if isinstance(node, exp.Literal):
            return _literal(node)
        if isinstance(node, exp.Null):
            return _Domain.NULL
        if isinstance(node, exp.Column):
            return self._column(node)
        if isinstance(node, exp.Cast):
            return _CAST_TARGETS.get(node.to.this)
        if isinstance(node, exp.Div):
            operands = _common([self.domain(node.this), self.domain(node.expression)])
            return operands if operands in (None, _Domain.REAL, _Domain.OTHER) else _Domain.DOUBLE
        if isinstance(node, _ARITHMETIC):
            return _common([self.domain(node.this), self.domain(node.expression)])
        if isinstance(node, exp.Coalesce):
            return _common(self.domain(argument) for argument in (node.this, *node.expressions))
        if isinstance(node, exp.Case):
            return _common(self.domain(result) for result in _results(node))
        if isinstance(node, _BIGINT_ROUTINES):
            return _Domain.INTEGER
        if isinstance(node, (exp.PercentileCont, exp.WithinGroup)):
            return _Domain.DOUBLE
        if isinstance(node, exp.Subquery):
            return self.projected(node, 0)
        if isinstance(node, _NOT_NUMERIC):
            return _Domain.OTHER
        return None

    def projected(self, query: exp.Expr, index: int) -> _Domain | None:
        """Return the domain of the result column of a query at an index."""
        query = _query(query)
        key = (id(query), index)
        if key in self._resolving:
            return _Domain.NULL
        self._resolving.add(key)
        try:
            if isinstance(query, exp.SetOperation):
                return _common([self.projected(query.this, index), self.projected(query.expression, index)])
            if isinstance(query, exp.Select) and index < len(query.selects):
                return self.domain(query.selects[index])
            return None
        finally:
            self._resolving.discard(key)

    def _column(self, column: exp.Column) -> _Domain | None:
        if column.table:
            scope: Scope | None = self._scopes.get(id(column))
            while scope is not None and column.table not in scope.selected_sources:
                scope = scope.parent
            exposed = [self._exposed(scope.selected_sources[column.table][1], column.name)] if scope else []
        else:
            # Qualification leaves a name bare where it may be a result name of its own query.
            scope = self._queries.get(id(column.find_ancestor(exp.Select)))
            exposed = (
                [self._exposed(source, column.name) for _, source in scope.selected_sources.values()] if scope else []
            )
        found = [domain for domain in exposed if domain is not _ABSENT]
        if found:
            return cast("_Domain | None", found[0]) if len(found) == 1 else None
        return self._result_name(column)

    def _exposed(self, source: exp.Table | Scope, name: str) -> _Domain | object | None:
        """Return the domain of a source's column, or `_ABSENT` where it exposes no column of the name."""
        if isinstance(source, exp.Table):
            declared = self._tables.get(f"{source.db}.{source.name}")
            if declared is None:
                return None
            types = {declaration["name"]: declaration["type"] for declaration in declared["columns"]}
            return _STORED.get(types[name], _Domain.OTHER) if name in types else _ABSENT
        query = cast("exp.Query", source.expression)
        return self.projected(query, query.named_selects.index(name)) if name in query.named_selects else _ABSENT

    def _result_name(self, column: exp.Column) -> _Domain | None:
        """Return the domain of a reference to a result name of the query it stands in."""
        query = column.find_ancestor(exp.Select)
        named = [s for s in query.selects if _AUTHORED in s.meta and s.alias == column.name] if query else []
        key = (id(column), -1)
        if len(named) != 1 or key in self._resolving:
            return None
        self._resolving.add(key)
        try:
            return self.domain(named[0])
        finally:
            self._resolving.discard(key)

    def _operands(self, query: exp.Expr, index: int, distinct: bool) -> list[_Member]:
        """Return the result expressions at an index that a set operation's operand contributes.

        An exact operand that is itself a set operation contributes those of its own operands, since
        converting its result is converting each of them. That holds where it keeps duplicates or
        the operation taking it removes them; elsewhere it contributes its domain and no expression.
        """
        query = _query(query)
        if isinstance(query, exp.Select) and index < len(query.selects):
            return [(query.selects[index], self.domain(query.selects[index]))]
        domain = self.projected(query, index)
        nested = isinstance(query, exp.SetOperation) and (distinct or not query.args.get("distinct"))
        if domain is not _Domain.DECIMAL or not nested:
            return [(None, domain)]
        return [*self._operands(query.this, index, distinct), *self._operands(query.expression, index, distinct)]

    def _convert(self, members: Sequence[_Member]) -> Iterator[tuple[exp.Expr, str, str]]:
        """Yield what each member of a common-domain group is wrapped in to convert through text."""
        domains = [domain for _, domain in members]
        common = _common(domains)
        if common is None and any(domain in (_Domain.DECIMAL, *_APPROXIMATE) for domain in domains):
            raise LoweringFailed("an operand of an exact or approximate numeric has no domain that can be told")
        if common not in _APPROXIMATE:
            return
        for node, domain in members:
            if domain is not _Domain.DECIMAL:
                continue
            if node is None:
                raise LoweringFailed("a set operation's exact result converts to an approximate domain")
            value = node.unalias()
            # A result column a wrapped reference no longer names keeps its name.
            named = isinstance(node, exp.Alias) and _AUTHORED not in node.meta and isinstance(value, exp.Column)
            suffix = f" AS VARCHAR) AS {_APPROXIMATE[common]})"
            yield value, "CAST(CAST(", suffix + (f" AS {node.alias}" if named else "")

    def _in(self, node: exp.In) -> Iterator[tuple[exp.Expr, str, str]]:
        """Yield the conversions of an `IN`, whose list is typed before its left operand meets it."""
        compared: _Member = (node.this, self.domain(node.this))
        query = node.args.get("query")
        if query is not None:
            listed = self.projected(query, 0)
            # A set operation in the subquery converts its own members to the list's domain.
            members = [] if listed in _APPROXIMATE else self._operands(query, 0, True)
        else:
            members = [(value, self.domain(value)) for value in node.expressions]
            listed = _common(domain for _, domain in members)
        if listed not in _APPROXIMATE:
            yield from self._convert([compared, *members])
            return
        yield from self._convert(members)
        if listed is _Domain.REAL and _common([compared[1], listed]) is _Domain.DOUBLE:
            for member, domain in members:
                if member is not None and domain is _Domain.INTEGER:
                    yield member.unalias(), "CAST(", " AS REAL)"
        yield from self._convert([compared, (None, listed)])

    def conversions(self, qualified: exp.Expr) -> Iterator[tuple[exp.Expr, str, str]]:  # noqa: C901
        """Yield each expression the lowering wraps, with the text put before and after it."""
        for node in qualified.walk():
            if isinstance(node, (*_PAIRS, *_ARITHMETIC)):
                yield from self._convert([(side, self.domain(side)) for side in (node.this, node.expression)])
            elif isinstance(node, exp.Between):
                # One remains only where its two comparisons share the domain of all three operands.
                operands = (node.this, node.args["low"], node.args["high"])
                yield from self._convert([(operand, self.domain(operand)) for operand in operands])
            elif isinstance(node, exp.In):
                yield from self._in(node)
            elif isinstance(node, exp.Coalesce):
                yield from self._convert([(value, self.domain(value)) for value in (node.this, *node.expressions)])
            elif isinstance(node, exp.Case):
                yield from self._convert([(result, self.domain(result)) for result in _results(node)])
                if node.args.get("this") is not None:
                    compared = (node.this, *(branch.this for branch in node.args["ifs"]))
                    yield from self._convert([(value, self.domain(value)) for value in compared])
            elif isinstance(node, exp.SetOperation):
                distinct = bool(node.args.get("distinct"))
                for index in range(len(node.named_selects)):
                    sides = (node.this, node.expression)
                    yield from self._convert([m for side in sides for m in self._operands(side, index, distinct)])
            elif isinstance(node, exp.Cast) and _CAST_TARGETS.get(node.to.this) in _APPROXIMATE:
                operand = self.domain(node.this)
                if operand is None:
                    raise LoweringFailed("a cast's operand has no domain that can be told", expression=node.sql())
                if operand is _Domain.DECIMAL:
                    yield node.this, "CAST(", " AS VARCHAR)"
            elif isinstance(node, exp.WithinGroup) and isinstance(node.this, exp.PercentileCont):
                for ordered in node.expression.expressions:
                    value = ordered.this if isinstance(ordered, exp.Ordered) else ordered
                    ordering = self.domain(value)
                    if ordering is None:
                        raise LoweringFailed("an ordering value has no domain that can be told", expression=value.sql())
                    text = " AS VARCHAR)" if ordering is _Domain.DECIMAL else ""
                    yield value, "CAST(" * (2 if text else 1), f"{text} AS DOUBLE PRECISION)"


def _authored(node: exp.Expr, authored: Sequence[exp.Expr]) -> exp.Expr | None:
    """Return the authored node a qualified one stands for, or None where qualification made or moved it."""
    index = node.meta.get(_AUTHORED)
    parent = node.parent
    while parent is not None and _AUTHORED not in parent.meta:
        parent = parent.parent
    if index is None or parent is None:
        return None
    original = authored[index]
    return original if original.parent is authored[parent.meta[_AUTHORED]] else None


def _span(node: exp.Expr, sql: str, tokens: Sequence[Token]) -> tuple[int, int] | None:
    """Return the offsets at which an authored expression's text starts and stops, or None.

    The parser positions leaves and routine names alone. The text is the shortest run of tokens
    around them that parses to the expression.
    """
    positioned = [part.meta for part in node.walk() if "start" in part.meta]
    if not positioned:
        return None
    starts = {token.start: index for index, token in enumerate(tokens)}
    ends = {token.end: index for index, token in enumerate(tokens)}
    first = starts.get(min(meta["start"] for meta in positioned))
    last = ends.get(max(meta["end"] for meta in positioned))
    if first is None or last is None:
        return None
    for reach in range(2 * _REACH + 1):
        for before in range(max(0, reach - _REACH), min(reach, _REACH, first) + 1):
            after = reach - before
            if last + after >= len(tokens):
                continue
            depth = 0
            for token in tokens[first - before : last + after + 1]:
                depth += (token.token_type == TokenType.L_PAREN) - (token.token_type == TokenType.R_PAREN)
                if depth < 0:
                    break
            if depth != 0:
                continue
            start, stop = tokens[first - before].start, tokens[last + after].end + 1
            try:
                if parse_one(sql[start:stop]) == node:
                    return start, stop
            except SqlglotError:
                continue
    return None


def _parsed(sql: str) -> exp.Expr:
    """Return the parse tree of `sql`, each node keyed by its position in the authored tree."""
    try:
        parsed = parse_one(sql)
    except SqlglotError as error:
        raise LoweringFailed(f"the query does not parse: {str(error).splitlines()[0]}") from error
    for index, node in enumerate(parsed.walk()):
        node.meta[_AUTHORED] = index
    return parsed


def _qualified(parsed: exp.Expr, tables: Mapping[str, Mapping[str, Any]]) -> exp.Expr:
    """Return a copy of the parse tree with every column bound to the source it names."""
    schema: dict[str, dict[str, dict[str, str]]] = {}
    for table in parsed.find_all(exp.Table):
        declared = tables.get(f"{table.db}.{table.name}")
        if declared is not None:
            schema.setdefault(table.db, {})[table.name] = {c["name"]: c["type"] for c in declared["columns"]}
    try:
        return qualify(
            parsed.copy(),
            schema=cast(dict[str, object], schema),
            # A reference to a result name stays where it was authored.
            expand_alias_refs=False,
            validate_qualify_columns=False,
            identify=False,
            quote_identifiers=False,
        )
    except SqlglotError as error:
        raise LoweringFailed(f"the query does not bind: {str(error).splitlines()[0]}") from error


def _text(node: exp.Expr, sql: str, tokens: Sequence[Token]) -> str:
    """Return an authored operand's text, parenthesized where an operator beside it could take part of it."""
    span = _span(node, sql, tokens)
    if span is None:
        raise LoweringFailed("a BETWEEN cannot be written as two comparisons", expression=node.sql())
    text = sql[span[0] : span[1]]
    return text if isinstance(node, _ATOMIC) else f"({text})"


def _two_comparisons(sql: str, tables: Mapping[str, Mapping[str, Any]]) -> str:
    """Return `sql` with each `BETWEEN` whose two comparisons take different domains written as both.

    The engine converts the three operands of a `BETWEEN` to one common domain, which equals each
    comparison's own only where all three agree; elsewhere it would convert an operand Part 11 §4
    compares without converting.
    """
    for _ in range(_BETWEEN_LIMIT):
        parsed = _parsed(sql)
        authored = list(parsed.walk())
        qualified = _qualified(parsed, tables)
        binding = _Binding(qualified, tables)
        for node in qualified.find_all(exp.Between):
            domains = [binding.domain(node.args[name]) for name in ("this", "low", "high")]
            joint = _common(domains)
            if joint is not None and _common(domains[:2]) == joint == _common(domains[::2]):
                continue
            original = _authored(node, authored)
            if original is None:
                raise LoweringFailed("a BETWEEN cannot be written as two comparisons", expression=node.sql())
            negated = isinstance(original.parent, exp.Not)
            replaced = original.parent if negated else original
            tokens = Tokenizer().tokenize(sql)
            span = _span(replaced, sql, tokens) if replaced is not None else None
            if span is None:
                raise LoweringFailed("a BETWEEN cannot be written as two comparisons", expression=node.sql())
            value, low, high = (_text(original.args[name], sql, tokens) for name in ("this", "low", "high"))
            comparisons = f"{'NOT ' if negated else ''}({value} >= {low} AND {value} <= {high})"
            sql = sql[: span[0]] + comparisons + sql[span[1] :]
            break
        else:
            return sql
    raise LoweringFailed("the query nests more BETWEENs than can be written as comparisons")


def lower(sql: str, tables: Mapping[str, Mapping[str, Any]]) -> str:
    """Return `sql` as DuckDB must be given it to evaluate it as Part 11 defines it.

    The ordering value of each `PERCENTILE_CONT` is cast to `DOUBLE PRECISION` (Part 11 §5). An
    exact value the engine holds as `DECIMAL` or `HUGEINT` is cast to text before it converts to an
    approximate domain, whether a cast, an operator, a routine or a set operation converts it, so
    that it is rounded once (Part 11 §4). `INTEGER` and `BIGINT` convert as the engine converts them.
    A `BETWEEN` whose comparisons take different domains is written as the two comparisons, and an
    exact member of an `IN` list is converted to the list's domain before the left operand meets it.

    Parameters
    ----------
    sql : str
        A query the static profile check admits.
    tables : Mapping
        The declaration of each table the query may name, by resource ID.

    Raises
    ------
    LoweringFailed
        Where a conversion cannot be placed in the authored text, or a domain it depends on cannot
        be told. The rule is then incomplete (Part 11 §8).
    """
    sql = _two_comparisons(sql, tables)
    parsed = _parsed(sql)
    authored = list(parsed.walk())
    qualified = _qualified(parsed, tables)
    tokens = Tokenizer().tokenize(sql)
    wraps: dict[tuple[int, int], tuple[str, str]] = {}
    for node, before, after in _Binding(qualified, tables).conversions(qualified):
        original = _authored(node, authored)
        span = _span(original, sql, tokens) if original is not None else None
        if span is None or wraps.setdefault(span, (before, after)) != (before, after):
            raise LoweringFailed("a conversion cannot be placed in the authored text", expression=node.sql())
    edits: list[tuple[int, int, int, str]] = []
    for (start, stop), (before, after) in wraps.items():
        # At one offset a wrap closes before another opens, the outer opens first and the inner closes first.
        edits += [(start, 1, start - stop, before), (stop, 0, stop - start, after)]
    lowered: list[str] = []
    done = 0
    for offset, _, _, text in sorted(edits):
        lowered += [sql[done:offset], text]
        done = offset
    return "".join([*lowered, sql[done:]])


__all__ = ["lower"]
