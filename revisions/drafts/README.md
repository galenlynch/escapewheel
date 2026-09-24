# Drafts

A draft is candidate normative text for a problem whose scope and intended direction have already
been settled. Exploratory work belongs in `../proposals/`; start a draft from
`../templates/draft.md`.

A draft has no number. It gets one only after acceptance is authorized, taken from the end of the
accepted range, so the numbered space reads in the order revisions were **applied**
rather than the order they were written. Nothing outside this directory may cite a draft by number,
because it has none, and a draft does not change the authoritative generated v0.2 specification.

Why: an `R<N>` is permanent once accepted: it identifies the accepted record, its clause-ledger
entries, and its evidence manifest. Git preserves the earlier stages. Assigning a number at drafting
time would force application order to match drafting order or require those permanent references to
be renumbered.

A draft cites another draft by its file name in backticks. At acceptance those citations become
`R<N> §<x>`, which is a step in the acceptance sequence in `../CONTRIBUTING.md`.

## Application order

Dependencies run downward, so a draft may depend on the ones above it and on nothing below.

| order | draft | words | appraisal | placement |
|---:|---|---:|---|---|
| 1 | [A Packet Passes Only When Its Manifest, Core, and Every Bound Extension Pass](a-packet-passes-only-when-its-manifest-core-and-every-bound-extension-pass.md) | 2758 | Not yet appraised; promoted 2026-09-23 from the exact proposal at `d9b6686`. | Part 05 section 9.5 added; Part 00 §4.1, Part 04 §§9–10, Part 05 §§5.3, 5.4, 9.2, 10, and 14.5, and Part 09 §5.4 in place |
