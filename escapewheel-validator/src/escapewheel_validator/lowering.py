"""Lower a Tier 2 query to the SQL DuckDB executes (Part 11 §4).

- :func:`lower` -- a query as DuckDB must be given it to evaluate it as Part 11 defines it.

A rule runs as authored except where DuckDB's own semantics differ from the language's. Each
difference is spliced into the authored text at token boundaries: regenerating a query from its
parse tree would respell its routines and its null ordering, and change what the engine is asked.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from sqlglot import Token, Tokenizer, TokenType

_CALL = [(TokenType.VAR, "PERCENTILE_CONT"), (TokenType.L_PAREN, "")]
_WITHIN_GROUP = [(TokenType.VAR, "WITHIN"), (TokenType.VAR, "GROUP"), (TokenType.L_PAREN, ""), (TokenType.ORDER_BY, "")]
_SORT_KEY_END = frozenset({TokenType.COMMA, TokenType.ASC, TokenType.DESC})


def _shapes(tokens: Sequence[Token]) -> list[tuple[TokenType, str]]:
    """Return each token's kind and, for a bare word, its spelling in upper case."""
    return [(token.token_type, token.text.upper() if token.token_type == TokenType.VAR else "") for token in tokens]


def _end(tokens: Sequence[Token], start: int, stops: Collection[TokenType] = ()) -> int:
    """Return where the parenthesized span holding the token at `start` ends.

    That is the index of the parenthesis closing it or, sooner, of a token of a kind in `stops`
    outside every parenthesis opened since `start`; `len(tokens)` where neither occurs.
    """
    depth = 0
    for index in range(start, len(tokens)):
        kind = tokens[index].token_type
        if kind == TokenType.L_PAREN:
            depth += 1
        elif kind == TokenType.R_PAREN:
            if depth == 0:
                return index
            depth -= 1
        elif depth == 0 and kind in stops:
            return index
    return len(tokens)


def _ordering_value(tokens: Sequence[Token], routine: int) -> tuple[int, int] | None:
    """Return the first and last token of the ordering value of the `PERCENTILE_CONT` at `routine`.

    None where the tokens from `routine` do not begin
    ``PERCENTILE_CONT(...) WITHIN GROUP (ORDER BY value``.
    """
    if _shapes(tokens[routine : routine + 2]) != _CALL:
        return None
    within = _end(tokens, routine + 2) + 1
    if _shapes(tokens[within : within + 4]) != _WITHIN_GROUP:
        return None
    first = within + 4
    last = _end(tokens, first, _SORT_KEY_END) - 1
    return (first, last) if first <= last else None


def lower(sql: str) -> str:
    """Return `sql` as DuckDB must be given it to evaluate it as Part 11 defines it.

    DuckDB interpolates `PERCENTILE_CONT` in its ordering value's own domain and returns that
    domain for `DECIMAL` and `REAL`, where Part 11 §5 converts the value to binary64 first. Each
    ordering value is therefore cast to `DOUBLE PRECISION`, by the engine's own conversion.

    Parameters
    ----------
    sql : str
        A query the static profile check admits.
    """
    tokens = Tokenizer().tokenize(sql)
    insertions: list[tuple[int, str]] = []
    for routine in range(len(tokens)):
        if (span := _ordering_value(tokens, routine)) is not None:
            first, last = span
            insertions += [(tokens[first].start, "CAST("), (tokens[last].end + 1, " AS DOUBLE PRECISION)")]
    # From the right, so that an insertion leaves the offsets before it standing.
    for offset, text in sorted(insertions, reverse=True):
        sql = sql[:offset] + text + sql[offset:]
    return sql


__all__ = ["lower"]
