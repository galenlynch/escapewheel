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
| 1 | [Registry documents are checked at conformance boundaries](check-registry-documents-at-conformance-boundaries.md) | 3,180 | Ready for acceptance; appraised 2026-09-22 at `3ba8b7f16e198c9ea077a4cdfd6c3f26acf6441b`. The R126 non-object-root checker gap found during appraisal was fixed at that baseline; no decision blocker remains. | New registry-result subsection in Part 02, new final conformance-boundary section in Part 05, and incorporated `registry/registry_result.schema.json`. |
