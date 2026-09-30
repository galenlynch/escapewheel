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
| 1 | [The Specification Is a Self-Contained Tree](the-specification-is-a-self-contained-tree.md) | 4493 | Promoted 2026-09-30 and appraised on `a110521`, the committed proposal; every affected section already carried an anchor, so no bootstrap was needed. Counts rerun at `a110521`: 95 files under `registry/`, 14 incorporated; 172 files naming the old paths, 107 of them accepted records or evidence; 26 uses of "checker" in six parts, 11 of them the unchecked label. The tree and the checker actor are independent decisions, kept in one draft by the promotion decision because the tree's tools are the checkers the actor defines. The packages and the frozen documents stay where they are, since no clause places them. The rules for the tree's tools, that they regenerate its content from it alone, what they import and which checks the tree holds, go to the root contributing guide rather than Part 00, since no actor can comply with them. It depends on R122 §3.1, which it locates, and R111 §3.3, whose roster it extends. | structural: in place at Part 00 §§2.1 and 2.4, and path, actor and generated-region revisions in Parts 02, 03, 04, 05, 08, 10, 11 and 12; a note on R111 §3.3 |
