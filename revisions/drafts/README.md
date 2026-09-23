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
| 1 | [A Packet Binds the Exact Registries That Declare Its Resources](a-packet-binds-the-exact-registries-that-declare-its-resources.md) | 6,509 | Acceptance appraisal passed 2026-09-23 at `c459cf9f7b9c1737a8f42d2d7e0d9ea894aed6a9`: the impact review covers 34 sections; registry sizes, fixture identifiers, and timestamps were remeasured; the gzip storage rule has a planned Part 03 home, Part 04's binding checks are profile-neutral, an extension's binding failure withholds only its own declaration checks, the Decision clauses name no repository tooling, the manifest entry names no producing run, and a reader checks only what reading needs; every draft gate passes with no remaining blocker. | Structural reconciliation across Parts 00, 02, 03, 04, 05, 06, 08, and 09; registry binding, manifest-schema incorporation, manifest checks, and optional run provenance. |
