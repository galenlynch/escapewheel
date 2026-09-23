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
| 1 | [A Portable Profile Declares Its Interfaces and Reader Floor](a-portable-profile-declares-its-interfaces-and-reader-floor.md) | 5,177 | Acceptance appraisal passed 2026-09-23 at `a52e4fc56dbbf7dd6be4d7d64145404b1c838b5d`: the 19-section, 246-citation impact review is complete; current Parquet output and V2-reader feasibility were reprobed; and every draft gate passes with no remaining blocker. | Structural reconciliation across Parts 00, 03, 04, and 05; physical descriptor, interface derivation, packet-field retirement, and reader floor. |
