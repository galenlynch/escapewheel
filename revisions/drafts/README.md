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
| `an-adapter-delivers-an-array-by-writing-it` | 2,246 | 2026-09-14 | Depends on R115 and on R116, which it uses as it stands: the two amend different clauses — one what a build supplies, the other what an adapter returns — so accepting R116 first changed nothing here. |

A draft withdrawn before acceptance is **deleted rather than numbered**, since the `R<N>` space
records what bound something and a draft never did. Git holds the document, and whatever the
appraisal found goes wherever the work went. `a-build-supplies-the-electrode-identifiers-it-assigned`
went that way on 2026-09-12 at commit `aa230d7`: it proposed a ninth term for Part 03 §11.2's supply
vocabulary, and the appraisal found the boundary already carried the value, `PacketWriter._preassign`
resolving a name to an assigned number packet-wide before any table is built (Part 05 §8). What the
adapters needed was to compose the name the owning adapter composes, which deleted the mapping
instead of declaring it — recorded in `TODO.md` §1d.

The last to leave was `a-build-supplies-a-source-on-standard-input`, accepted as **R116** on
2026-09-14 at 1,283 words: the object a build supplies crosses on standard input, because the
argument list it crossed by caps one argument at 131,072 bytes on Linux and a whole command line at
32,767 characters on Windows, where the NWB adapter's object for one real session is 322,799.

Before it, `a-build-reaches-a-source-through-declarations`, accepted as **R115** on
2026-09-11 at 12,038 words. It was two drafts merged — a writer requiring no knowledge of a
particular source, and an adapter's rows crossing a process boundary — split at 3,801 words for
length and unacceptable apart, since each carried a mechanism the other's rules stood on. The
split also hid a contradiction between them for a day.
