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
| 1 | [`define-specification-artifacts-and-normative-ownership`](define-specification-artifacts-and-normative-ownership.md) | 6,796 | Appraised 2026-09-20 against `41da62e3fd4924e5526f8f812492e90607d14d97`: ready for acceptance authorization. The R121 rebase, exact structural and README crosswalks, authority and bibliography corrections, 22-section impact inventory, 11 semantic citation dispositions, owner/evidence plan, roadmap-alignment pass, and all pre-acceptance gates are complete. `stages.py`, citation and repointing checks, `headings.py --check`, and all 25 quick-verifier stages pass. | No blocker remains. Preserve these exact bytes in Git before authorization; after authorization, follow the atomic acceptance and incorporation sequence. |
