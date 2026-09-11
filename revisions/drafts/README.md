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

| # | draft | words | appraised | why here |
|---|---|---|---|---|
| 1 | `a-build-reaches-a-source-through-declarations` | 7,370 | merged and appraised 2026-09-11, then appraised as merged | depends on nothing else open |

**#1 is `a-writer-requires-no-knowledge-of-a-particular-source` and
`an-adapters-rows-cross-a-process-boundary` merged.** They were split at 3,801 words for length and
could not be accepted apart: §3.8 has a build supply a staging location, which is §3.1's mechanism;
§3.3's work-saving rests on a build passing a wanted set, which §3.1 carries; and §3.1's rule that a
build passes what an adapter can use without importing the writer is motivated by an adapter running
elsewhere, which §3.3 establishes. The split also hid a contradiction between the two for a day, and
by the end they disagreed in text about whether they were independent.

Five findings were applied in the merge. §2.1 called five declared dependencies a closure where the
resolved one is **57 distributions**, understating its own argument; `Part 03 §1` and `Part 05 §3.5`
were amended in the body and absent from the status table; a passage about R109 §2.3 opened two
sections with the same two clauses; one draft said the two met at what a build passes and the other
said neither depended on the other; and a bullet still called the stream "the default" from before
the protocol group.

`conformance/adapter-boundary/` is the evidence it cites: the 271-byte input crossing with rows
identical, the two mappings that do not survive a round trip, `StagedArray`'s five fields of six,
three schemas over one pipe, and Arrow Flight over a Unix socket.
