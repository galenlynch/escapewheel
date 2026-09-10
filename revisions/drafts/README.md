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
| 1 | `a-requirement-is-cited-where-it-is-stated` | rests on R93 §3.6 and R93 §4 for where a clause belongs, and on R111 §3.3 for what a requirement may be |
| 2 | `an-extension-declares-the-core-it-was-authored-against` | rests on R17 §5 for what an extension declares and on R109 §3.1 for a writer requiring no code, which is what puts an extension somewhere else |
| 3 | `a-writer-requires-no-knowledge-of-a-particular-source` | takes R109 §2.3's argument about a dependency closure and applies it to an adapter, so it reads after the draft that puts an extension elsewhere |

**None moves a count in the generated block.** No core table, column, reference, rule or vocabulary
changes: #1 adds a section to `00` and a sentence to `07` §2, #2 adds one field to an extension's
registry document and a clause to `02` §3, and #3 adds a preference table to `05` §3 and moves four
tables out of the reference implementation. Every number in each is measured against the parts, the
registries and the three distributions as they stood when it was drafted and is re-measured at
acceptance, which the pre-acceptance checks in `../CLAUDE.md` require anyway.
