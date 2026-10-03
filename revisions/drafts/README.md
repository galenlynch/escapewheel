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
| 1 | [An amendment drops a held column only where its recipe names it](an-amendment-drops-a-held-column-only-where-its-recipe-names-it.md) | 5050 | Appraised 2026-10-02 at `90994366`, 4744 words. Feasible: the build reads held footers before any source. Material: §3.3's binding remedy fails where the packet's own registry already lacks the column (the R163 `transform_to_parent` packets); a non-canonical table's undeclared column fails only at validation, and its remedy needs naming; Part 02 §6 has no anchor, so a bootstrap is likely; §2.7 counts are stale (27 packets, 1,083 files, none affected). Revised the same day on `18d05c61`, the Part 02 §6 anchor bootstrap: the build refuses over every held table it does not derive again, the binding remedy is named only where it works, and the counts are refreshed. | structural: a new subsection at the end of Part 02 §6; in place at Part 05 §§3.1, 3.5, 4.3, 5.3 and 15.2; no existing ledger entry changes |
| 2 | [A change is one document from Open to Accepted](a-change-is-one-document-from-open-to-accepted.md) | 2810 | Opened 2026-10-02 as a draft, with no proposal; not yet appraised. | process, ordinary: in place at fifteen anchored sections of the revision guide, from §1 to §14; no existing ledger entry changes |
