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
| 1 | [An Adapter Declares Its Whole Contract and Delivers Only Where a Build Points It](an-adapter-declares-its-whole-contract-and-delivers-only-where-a-build-points-it.md) | 5316 | Re-appraised 2026-09-24 against `cf0d686`; ready for acceptance. Incorporation found that a class of an adapter a build ships declares no protocol, so §3.2 exempts only such a class from `protocols`, and the writer refuses an independently released adapter run in process that declares none, as Part 03 §11.1 already requires. `protocols` replaces the single `protocol`, since Part 03 §11.1 has an adapter declare at least one, and a build reaches an adapter out of process by the declared protocol its recipe names, or any it declares. The schema audit loosens the resolution schema's source-name pattern to the manifest's and restates R80 §2.2's version rule; a build owns its delivery locations, may point an adapter at the place its bytes will stay, and reads nothing an earlier run left as this run's delivery. | Part 03 §§11, 11.1, 11.2, and 11.5, Part 04 §5.5, Part 05 §§2 and 3.5, and Part 07 §4 in place; `registry/adapter.schema.json` and `registry/sources.schema.json` incorporated |
