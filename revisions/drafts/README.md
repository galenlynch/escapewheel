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
| 1 | `every-clock-declares-when-it-was-observing` | a clock declares its own observation window, which nothing required and one packet in every thirteen clocks carries |
| 2 | `a-packet-records-its-clock-alignment-in-columns` | three facts a reader needs to place a tick leave `core.processing_runs.parameters` for columns and a table |
| 3 | `checking-the-tables-an-array-axis-names` | `coordinate_resource` becomes a discriminator, resolving by R90 §3.5's third shape |
| — | `what-a-reserved-value-is-for` | outside the order; it amends R11 §4 alone and depends on nothing here |

The first two are ordered rather than independent: the alignment bound cannot be measured until
every clock declares a window, so accepting the second first would add a column no writer can fill
for a reason the packet does not record.

Two of them change a registry count — the first a rule, the second columns, references and a table
— each measured against the registry as it stood when it was drafted. Whichever is accepted second
re-measures, which the pre-acceptance checks in `../CLAUDE.md` require of every number anyway.
