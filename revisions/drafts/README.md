# Drafts

A draft has no number. It gets one when the user accepts it, taken from the end of the accepted
range, so the numbered space reads in the order revisions were **applied** rather than the order
they were written. Nothing outside this directory may cite a draft by number, because it has none.

Why: an `R<N>` is permanent once accepted — `applied.toml` keys on it, `build.py` stamps it into
every column's `since`, the registry's `derived_from` lists it, and the compiled spec cites it. A
number assigned at drafting time forces the application order to match the drafting order, and
renumbering later would break all four.

A draft cites another draft by its file name in backticks. At acceptance those citations become
`R<N> §<x>`, which is a step in the acceptance sequence in `../CLAUDE.md`.

## Application order

Dependencies run downward: a draft may depend on the ones above it and on nothing below. These two
are independent, and the order is readiness.

| # | draft | why here |
|---|---|---|
| 1 | `an-encoding-follows-a-rule-and-its-exceptions` | rests on R68 §3 having put one encoding SHOULD in `03` §5.5, on R93 having built `10` for the readings, and on R109 §3.6 for what an extension states across the boundary; measured and exercised, so only re-measurement is left |
| 2 | `a-requirement-binds-a-named-actor` | touches no clause the other adds, and the other's two SHOULDs bind a writer either way. Later because it is newly drafted |

**Neither moves a count in the generated block.** No table, column, reference, rule or vocabulary
changes: #1 adds two SHOULDs to `03` §5.5 and four subsections to `10` §2, and #2 adds four
definitions to `00` §2 and gives ten clauses an actor. Every number in either is measured against
the packets and the parts as they stood when it was drafted and is re-measured at acceptance, which
the pre-acceptance checks in `../CLAUDE.md` require of every number anyway.
