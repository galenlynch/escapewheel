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
| 1 | [Every Packet Resource Instantiates a Logical Declaration](every-packet-resource-instantiates-a-logical-declaration.md) | 6,950 | Ready for acceptance on 2026-09-22 against `c33d60a102b3b4b4cc0a44cf2809abbc80a64c6a`: the separate 21-heading anchor bootstrap and informational projection refresh are complete; ownership, decision, structural, feasibility, compatibility, traceability, and evidence review found no blocker after revising the closed kind vocabulary to `table`, `dense_array`, and `opaque`; the 42-section impact inventory is current; and lifecycle, citation, repointing, heading, publication, and all 31 quick-verifier stages pass. | Structural reconciliation across Parts 00–06 and 09; generalized logical registry, packet declaration binding, catalog identity, dense-array axes binding, opaque payloads, and declaration-driven lineage. |
