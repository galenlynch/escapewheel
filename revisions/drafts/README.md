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
| 1 | [A Build Decides Ownership Only From the Recipe and Adapter Declarations](a-build-decides-ownership-only-from-the-recipe-and-adapter-declarations.md) | 3317 | Ready for acceptance; appraised 2026-09-23 against `18c6ba6`, the anchor bootstrap after `8b0f067`. Depends on R63 §2.2, R98 §3.2, R108 §§3.1 and 3.4, R115 §3.2, and R119 §3.4; a later adapter-contract decision would depend on it. Material findings: a preference declares ownership, so a build refuses one naming an unlisted kind, a source whose adapter cannot supply the resource, or a resource another entry declares under `owns` or `contributes`; a defaulted entry's own `contributes` is contributed and not owned, where the writer now reads it as both; the recipe schema admits `delivery`'s four keys; ledger destinations in the six sections move to anchors, and only the applied notes of R98 §3.2 and R108 §3.4 are rewritten. The re-run probes reproduce the ignored preference, the AIND `core.subjects` refusal, the repeated kind, and the producer table. No accepted clause is superseded. | Part 03 §11.5, Part 05 §§3.1 and 3.3–3.5, and Part 07 §4 in place; `registry/recipe.schema.json` added |
