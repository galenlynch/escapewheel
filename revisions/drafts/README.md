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
| 1 | `an-array-declares-which-band-it-holds` | amends R101 §3.8's reserved set and R8 §4; renames a column and changes its presence, so it moves the counts R101 §5 records |
| 2 | `a-coordinate-frame-declares-what-its-axes-mean` | adds a table whose six string columns need R101 §3.1's declaration, and gives `coordinate_frame` the reference R101 §6 records it lacking |
| 3 | `a-coded-value-is-stored-decoded` | rests on R101 §3.1 having forbidden a vocabulary on an integer, which is what left the column unable to say what its codes mean |

Either order works between the two — neither touches the other's tables — but both must follow
R101, whose classification their new and renamed columns are measured against. Their numbers were
measured when they were drafted and are re-measured at acceptance, which the pre-acceptance checks
in `../CLAUDE.md` require of every number anyway.
