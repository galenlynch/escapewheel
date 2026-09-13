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

A draft takes a row naming its word count, when it was appraised, and why it sits where it does:
dependencies run downward, so a draft may depend on the ones above it and on nothing below.

| draft | words | appraised | why here |
|---|---|---|---|
| `a-build-supplies-the-electrode-identifiers-it-assigned` | 1,655 | not yet | Only one open, and it depends on R115 alone. |

The last to leave was `a-build-reaches-a-source-through-declarations`, accepted as **R115** on
2026-09-11 at 12,038 words. It was two drafts merged — a writer requiring no knowledge of a
particular source, and an adapter's rows crossing a process boundary — split at 3,801 words for
length and unacceptable apart, since each carried a mechanism the other's rules stood on. The
split also hid a contradiction between them for a day.
