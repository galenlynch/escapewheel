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
| 1 | [The Adapter Interface Is Its Own Part at the Physical Level](the-adapter-interface-is-its-own-part-at-the-physical-level.md) | 5463 | Drafted 2026-09-25 on `9bac392`, the anchor bootstrap for Part 00 §7.3, after `be9d1a1` anchored Part 03 §§11.4 and 11.6 and Part 09 §5.8. Appraised three times on 2026-09-25; the revisions place Part 12 under Part 00 §7.3's binding and dependency rules, keep a payload's shape and the names it keeps in Part 03 as a new §11, "Opaque storage", state that the report rules bind under the portable profile, keep one incorporation statement per schema, name JSON Schema among Parts 03 and 12's authorities, restore Part 09 §5.8's validation terms, migrate both numeric Part 00 §7.3 ledger destinations, and add the framework and probe cases. No other proposal or draft is open, and R142 and R143, which amended the moved text, are incorporated. | Part 03 §11 and Part 09 §5.8 move to a new Part 12, except a payload's shape and names, which become Part 03 §11; Part 00 §§1, 3.1.3, 7.3, 9, and 10 and Part 03 §§1 and 12 in place |
