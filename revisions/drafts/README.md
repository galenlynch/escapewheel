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
| 1 | [A Float Column Declares Whether It Admits Non-Finite Values](a-float-column-declares-whether-it-admits-non-finite-values.md) | 3487 | Appraised for acceptance 2026-09-24 against `06b11fb`, the anchor bootstrap for Part 02 §10.1, Part 03 §5.6, and Part 05 §5.1: ready. Meta-schema 0.7.0, descriptor `escapewheel-registry-contract-v0.4`, and core registry 0.7.0 advance together and collide with no other draft's identifiers. The appraisal replaced a fixture scan that counted stale directories with the 30 packets the generator writes (901 files, 571 float columns), corrected the session-packet description to two extracellular sessions, one built twice, counted seven numeric ledger destinations, and added the validator's descriptor selection, the tests pinning 0.6.0, and the other files naming the old identifiers to the impact inventory. Registry counts, rule probes, and the `isfinite` checks were rerun and hold. It commutes with R136 in Part 08 §3. | Part 02 §§3, 9.2, 9.4, and 10.1, Part 03 §5.6, Part 05 §5.1, and Part 08 §§2 and 3 in place; a subsection added at the end of Part 02 §5 |
| 2 | [A Nomenclature That Governs an Open Core Column Has a Reference Entry](a-nomenclature-that-governs-an-open-core-column-has-a-reference-entry.md) | 3316 | Appraised for acceptance 2026-09-24 against `0526ab0`, after R136–R138: ready. No anchor bootstrap is needed. Since `fc3ab4e`, §3.1 is scoped to registered values: a writer spells a value of an open column as a named nomenclature does where that nomenclature registers what the value names, and otherwise writes it as the source states it; no validator checks either, a unit column's value staying a UCUM code under Part 02 §8.4. The scope, crosswalk, a new background subsection on the unregistered value, the alternatives, §3.3's application column for the three living registries, §3.2's timing sentence, the consequence, the impact inventory and §6 follow it. §6 records that the open-column rule has no negative case a tool can run and that no writer or adapter test checks a `species` or `strain` spelling, since neither maps one. R101 §3.5 keeps its `registry` disposition and, with R101 §§3.6 and 3.9, gains a note. R136 left the Part 00 §10 edition paragraph and the README's Part 02 sentence this draft replaces as they were, so its edits apply to the current text without merging. The overlap section cites R136–R138 by number and names the non-finite draft, ordered first, as the one open overlap; the two share no text. The authority walk (twelve columns naming five authorities, none in an extension registry), Part 02 §13's one-item list, the framework allocation, and the eleven numeric Part 02 §9.3 ledger destinations were rerun and hold. | Part 00 §10 and Part 02 §§9.3 and 13 in place |
