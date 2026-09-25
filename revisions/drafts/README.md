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
| 1 | [The Core Vocabulary Targets Extracellular Electrophysiology](the-core-vocabulary-targets-extracellular-electrophysiology.md) | 2295 | Not yet appraised; promoted 2026-09-24 from the proposal as committed at `782dbf8`, which stays open for the relocation of Part 03 §11 and records the split among its open questions. The draft is structural in form because it replaces text in place; no anchor bootstrap is needed. | Part 00 §§1 and 3.2 and Part 02 §2.2 in place |
| 2 | [A Build Supplies an Adapter a Persistent Source Cache Keyed by URI and Entity Tag](a-build-supplies-an-adapter-a-persistent-source-cache.md) | 4339 | Not yet appraised; promoted 2026-09-24 from the exact proposal at `65f59cd`. The draft is structural in form because it adds a subsection; no anchor bootstrap is needed. | Part 03 §§11, 11.2, and 11.5, Part 05 §§3.4 and 3.5, and Part 07 §4 in place; a subsection added at the end of Part 03 §11 |
