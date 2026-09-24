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
| 1 | [A Recipe Names Each Extension Registry Once](a-recipe-names-each-extension-registry-once.md) | 1663 | Appraised for acceptance 2026-09-24 against `06b11fb`: ready. The draft is structural in form, extending Part 05 §3.1 in place beside the one-source-kind rule; no anchor bootstrap is needed. The duplicate-entry probes were rerun after the writer's recipe-prefix check and still pass with no finding, the writer keeping the later document. No other draft amends Part 05 §3.1. | Part 05 §3.1 in place |
| 2 | [A Float Column Declares Whether It Admits Non-Finite Values](a-float-column-declares-whether-it-admits-non-finite-values.md) | 3487 | Appraised for acceptance 2026-09-24 against `06b11fb`, the anchor bootstrap for Part 02 §10.1, Part 03 §5.6, and Part 05 §5.1: ready. Meta-schema 0.7.0, descriptor `escapewheel-registry-contract-v0.4`, and core registry 0.7.0 advance together and collide with no other draft's identifiers. The appraisal replaced a fixture scan that counted stale directories with the 30 packets the generator writes (901 files, 571 float columns), corrected the session-packet description to two extracellular sessions, one built twice, counted seven numeric ledger destinations, and added the validator's descriptor selection, the tests pinning 0.6.0, and the other files naming the old identifiers to the impact inventory. Registry counts, rule probes, and the `isfinite` checks were rerun and hold. It commutes with R136 in Part 08 §3. | Part 02 §§3, 9.2, 9.4, and 10.1, Part 03 §5.6, Part 05 §5.1, and Part 08 §§2 and 3 in place; a subsection added at the end of Part 02 §5 |
| 3 | [A Nomenclature That Governs an Open Core Column Has a Reference Entry](a-nomenclature-that-governs-an-open-core-column-has-a-reference-entry.md) | 2739 | Appraised for acceptance 2026-09-24 against `06b11fb`: ready. No anchor bootstrap is needed. The authority walk, Part 02 §13's current list, and the framework allocation were rerun and hold. It commutes with R136, which also edits Part 00 §10, the framework reference allocation, and the specification README's reference paragraph; applied after it, the Part 00 §10 and README edits merge by hand. | Part 00 §10 and Part 02 §§9.3 and 13 in place |
