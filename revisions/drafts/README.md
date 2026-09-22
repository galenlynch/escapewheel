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
| 1 | [A Registry Document Has One Complete Conformance Contract](define-registry-document-conformance.md) | 6,301 | Ready for acceptance on 2026-09-22 against `8b22b501cec6d2b76a1f286d84d2c082055f62f6`: the separate anchor bootstrap and informational projection refresh are complete; ownership, decision, structural, feasibility, compatibility, traceability, and evidence review found no blocker; the 20-section impact inventory is current; and lifecycle, citation, repointing, heading, publication, and all 30 quick-verifier stages pass. | P4.1; commit this exact appraised draft and request acceptance authorization. |
