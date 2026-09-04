# R12 — Physical Order Is Not a SQL Rule

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | R2 §7.1, R5 §7, R10 §5 |
| **Depends on** | R10 (declared sort order) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Building the Phase 0 fixture surfaced a defect in three accepted revisions.

R2 §7.1 lists "physical order matches `sort`" among the checks Tier 1 generates from
structure. R5 §7 specifies `core.spike_events.ticks_sorted_within_unit` as a Tier 2 SQL rule.
R10 §5 states that R2 §7.1's ordering check applies to every table with a declared `sort`.

**A SQL query has no access to physical row order.** That is what the relational model
abstracts away: a result set is unordered unless an `ORDER BY` imposes one, and no expression
refers to the order rows occupy in a file.

R5 §7's rule attempted it with `LAG(t_tick) OVER (PARTITION BY ... ORDER BY (SELECT NULL))`.
A constant `ORDER BY` does not preserve file order; it leaves the window order unspecified, so
`LAG` compares against an arbitrary neighbour. Run against a fixture whose spike file was
verified sorted, the rule reported four violations. It is not merely unreliable — it cannot
be made to work, because the information it needs is absent from the query layer.

## 2. Resolution

Physical ordering is checked by the shim (R2 §7.4), not by SQL.

`core.spike_events.ticks_sorted_within_unit` is withdrawn as a Tier 2 rule. R2 §7.1's list of
generated checks no longer includes physical ordering.

A validator MUST check declared ordering by reading each resource in written order and
verifying rows are non-decreasing under the table's `sort` key. Findings are `warning` level,
per R10 §2: ordering is a performance property and a packet in the wrong order conforms.

## 3. Consequence

The check gets broader, not narrower. R5 §7's rule covered one table; the shim check covers
every table declaring a `sort`, which after R10 is 19 of 22. It also gains what the SQL rule
could not have: it compares against the declared key rather than a single hard-coded column.

Nothing else moves. Every other Tier 1 and Tier 2 check operates on values rather than
layout, and SQL expresses those correctly.

## 4. The general rule this implies

A check belongs in SQL when it concerns *what the data says* — values, keys, references,
vocabularies, cross-table agreement. It belongs in the shim when it concerns *how the data
is stored* — physical order, file presence, Parquet types, Zarr rank and codecs, checksums.

The boundary is not a matter of convenience. Storage-layer facts are invisible to a query,
and a rule written in SQL against one of them fails silently rather than loudly, which is the
worse failure. R2 §7.4's list of shim responsibilities is amended to name physical ordering
alongside manifest parsing, URI resolution, array metadata, and checksums.

## 5. How this was found

The Phase 0 fixture (`fixtures/`) was built to exercise the registry, and the conforming
packet reported an ordering violation against a file that was demonstrably sorted. No amount
of reading the rule would have shown this; only running it against known-good data did.

That is the argument for the conformance corpus as a standing artifact rather than a
one-time exercise: a rule can be valid SQL, execute without error, and still be incapable of
checking what it claims.
