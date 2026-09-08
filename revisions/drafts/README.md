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

Dependencies run downward: a draft depends on the ones above it and on nothing below.

| # | draft | why here |
|---|---|---|
| 1 | `columns-that-hold-one-value` | strikes seven duplicated names, makes the two clock-rate forms exclusive |
| 2 | `a-sorted-unit-declares-its-spikes-context` | moves `amplitude_unit` and `clock_id` to `core.units` |
| 3 | `the-free-form-metadata-column` | which tables declare `metadata`, and what may go in one; strikes `core.events.payload`; R94 §3 leaves it the rule that `metadata` is optional |
| 4 | `the-alignment-keys-in-a-runs-parameters` | three keys a reader reads and no document states |
| 5 | `checking-the-tables-an-array-axis-names` | `coordinate_resource` becomes a discriminator, resolving by R90 §3.5's third shape |
| — | `what-a-reserved-value-is-for` | outside the order; it amends R11 §4 alone and depends on nothing here |

These five are independent of each other; the order is a convenience, not a constraint.

Three of them change the registry's column count, each measured against the registry as it stood
when it was drafted. Whichever is accepted second re-measures — which the pre-acceptance checks in
`../CLAUDE.md` require of every number anyway.
