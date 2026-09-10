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
| 1 | `a-coded-value-is-stored-decoded` | rests on R101 §3.1 having forbidden a vocabulary on an integer, which is what left the column unable to say what its codes mean |
| 2 | `a-description-states-what-the-column-declares` | corrects prose R101 §3.3 made wrong; touches no declaration, so it may land at any point after R101 |

The two are independent of each other; the numbering above is the order they would be applied
in, not a dependency between them.

**Neither moves the registry's counts.** #1 changes one extension column's type and #2 changes six
descriptions, so the order between them is free. Every number in each is measured against the
registry as it stood when it was drafted and is re-measured at acceptance, which the pre-acceptance
checks in `../CLAUDE.md` require of every number anyway.
