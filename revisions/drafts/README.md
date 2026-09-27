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
| 1 | [Each Rule Is Stated by Its Owner, and a Canonical Resource Depends Only on Canonical Resources](each-rule-is-stated-by-its-owner-and-a-canonical-resource-depends-only-on-canonical-resources.md) | 4664 | Appraised 2026-09-26 on `a0f7d8b`, the anchor bootstrap for Part 01 §§2.1, 3.3 and 3.9 and Part 02 §12.6; re-appraised the same day, and again 2026-09-27 after its first acceptance was withdrawn to widen §3.4 (user's direction). No other proposal or draft is open. Registry, identifier and corpus counts rerun at the baseline. Findings closed in the draft: the reference writer accepts a recipe option mapping `analysis.spike_events` onto a non-reference clock, which §3.7 withdraws; R20 §5.1 is the source of Part 00 §3.2's direction rule, and §3.4 supersedes it in part, as Part 02 §2.7 already does for lineage; Part 01 §2.1's meaning and position bans fail on carried identifiers, so §3.2 scopes them to assigned identifiers (user's direction); every MUST no checker verifies says so; Part 06 §4's restated sort order cites Part 03 §5.4; §3.4 covered only `analysis` targets, and now covers every non-canonical class, matching its heading and Part 02 §2.7. | in place: Part 00 §§3.2, 5.1 and 9; Part 01 §§2.1, 3.3 and 3.9; Part 02 §§2.2, 9.2, 9.4 and 12.6; Part 05 §5.3; Part 06's status line and §4 |
