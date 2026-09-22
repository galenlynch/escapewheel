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
| 1 | `locate-normative-references-with-their-subjects.md` | 2,959 | 2026-09-21 — ready for acceptance on `3769082d29514ea9eeabe81c0931f98171faf8ea`; appraisal distinguished direct external invocation from reliance on another part's contract and allowed one invocation statement to govern a defined requirement group; all 28 quick-verifier stages pass | structural; no anchor bootstrap required; all 16 baseline citation surfaces read |
| 2 | `define-a-portable-tier-2-rule-language.md` | 7,226 | revise after P2.1; the detailed language contract and its SQL/IEEE references move to Part 11 without reopening the approved language semantics | structural; five-anchor bootstrap verified before the Part 11 destination was selected |
