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
| 1 | [An Adapter Declares Its Whole Contract and Delivers Only Where a Build Points It](an-adapter-declares-its-whole-contract-and-delivers-only-where-a-build-points-it.md) | 6361 | Re-appraised 2026-09-24 against `89e2d60`; ready for acceptance. Incorporation found that a class of an adapter a build ships declares no protocol, so §3.2 exempts only such a class from `protocols`, and the writer refuses an independently released adapter run in process that declares none, as Part 03 §11.1 already requires. `protocols` replaces the single `protocol`, and a build reaches an adapter out of process by the declared protocol its recipe names, or any it declares. A coherence review settled the rest against the specification: Part 05 §3.9 lets a build serve an adapter it ships over a protocol where its recipe entry gives it a delivery, as Part 03 §11.1 already does; Part 03 §11.1 describes a `files-v0.1` delivery as one Parquet file per resource under `delivery_root`, as the writer reads it; Part 03 §11.3 keeps R117's in-process handover of an array's values; and the writer's `array_location` moves under its staging area. A build owns its delivery locations, may point an adapter at the place its bytes will stay, and supplies `delivery_root` empty, since under `files-v0.1` its contents are the only record of a delivery. The resolution schema's source-name pattern loosens to the manifest's, and R80 §2.2's version rule is restated. | Part 03 §§11, 11.1, 11.2, 11.3, and 11.5, Part 04 §5.5, Part 05 §§2, 3.5, and 3.9, and Part 07 §4 in place; `registry/adapter.schema.json` and `registry/sources.schema.json` incorporated |
