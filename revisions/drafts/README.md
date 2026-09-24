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
| 1 | [A Build Owns Its Staging Area and Validates Everything It Stages Before Publishing](a-build-owns-its-staging-area-and-validates-everything-it-stages-before-publishing.md) | 5980 | Appraised 2026-09-24 against `f5f3364`; not ready for acceptance until its anchor bootstrap. The draft is structural, since it replaces rules inside existing sections, and Part 05 §§4, 4.2, 5, 6, 7, and 8, Part 03 §9.5, and Part 00 §8 lack canonical anchors, so a metadata-only bootstrap commit must add them and become `Based on`. The appraisal found that `amend` writes a newly bound registry document at its final path before validating and removes it on refusal, so the draft has it stage the document under `staging/`; that the verdict test and the rule against promoting were stated in both Part 05 §2 and §6, so Part 05 §6 now cites Part 05 §2; and that the staging area must be an amendment's as well as a build's. The stray clause narrows R61 §2.1 and R32 §6, whose ledger entries move to anchors. The recorded `uri` is the recipe's root as written, so Part 05 §11's determinism holds. Two later proposals amend other sentences of Part 03 §11.3 and Part 05 §5.3 and follow this draft. | Part 00 §§2.4 and 8, Part 03 §§9.5, 11.2, and 11.3, and Part 05 §§1, 2, 4, 4.2, 5, 6, 7, and 8 in place; a subsection added at the end of Part 03 §3 |
