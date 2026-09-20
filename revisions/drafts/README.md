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
| 1 | [`define-specification-artifacts-and-normative-ownership`](define-specification-artifacts-and-normative-ownership.md) | 4,227 | Appraised 2026-09-19 against `b4695ca087376fd85e998743f81401164b2a15c5`: not ready. R121 is incorporated, so this draft now needs a refreshed baseline, impact inventory, crosswalk, evidence, and appraisal. Its §§3.3–3.5, §3.8, and §3.9 also retain the recorded substantive defects. | Rebase on incorporated R121, revise the Decision defects, finish the crosswalk and anchor work, refresh the evidence, and repeat the full appraisal. |
