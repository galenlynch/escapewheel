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

Dependencies run downward: a draft may depend on the ones above it and on nothing below.

| # | draft | why here |
|---|---|---|
| 1 | `a-preference-discards-no-stated-fact` | rests on R98 §3.3 having spent a preference to buy silence about a discarded row, which is the premise it checks |

**It moves no count in the generated block.** No table, column, reference, rule or vocabulary
changes; `recipe.PREFERRED` loses one stale entry and a build gains one refusal. Every number in it
is measured against the registry as it stood when it was drafted and is re-measured at acceptance,
which the pre-acceptance checks in `../CLAUDE.md` require of every number anyway.
