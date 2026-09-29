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
| 1 | [An Interval Is Numbered by Its Packet](an-interval-is-numbered-by-its-packet.md) | 2861 | Appraised 2026-09-28 on `b773b21`, the projection refresh after the Part 10 §2.9 bootstrap, and re-appraised the same day after the label left the numbering order (user's direction), so that Part 02 states one label order, the unit proposal's. Depends on R147 for the core registry version it advances from; the two revise different paragraphs of Part 02 §8.3 and advance Part 02 §9.2's version in turn. The numbering rule and the revised `contains_its_trials` were run on both session packets' `packet-wf` builds with injected defects and a tie numbered both ways, and the 17 `vr_foraging.sites` rules statically checked against the revised declarations. Findings closed in the draft: numbering by kind and time reproduces all 450 and 708 existing identifiers; seven `vr_foraging.sites` rules rely on how sites are numbered and hold under §3.2's order; `contains_its_trials` joined on the struck constant column, and §3.3 rewrites it; R54 §2.2 is superseded; `dup_pk` also draws the numbering rule. Part 02 §12.1's unit order, which compares a string the reference writer reads as a number, is left to the draft below; intervals of one kind with equal bounds, of which neither packet has any, may be numbered in either order. | structural: in place at Part 02 §§8.3 and 9.2; a new last subsection of Part 02 §12, *Interval identity*; supersedes R54 §2.2 |
| 2 | [Unit Labels Order by Length, Then by Unicode Scalar Value](unit-labels-order-by-length-then-by-unicode-scalar-value.md) | 2748 | Appraised 2026-09-28 on `f2131f9`, the last note to its proposal. Depends on the draft above and on R147: it advances the core registry version from the interval draft's 0.10.0 and the registry-contract descriptor from R147's v0.6, so the three advance Part 02 §9.2 in turn. The numbering rule ran on both session packets' `packet-wf` builds as built, renumbered by scalar-value order and numbered from 1, and on the 61 fixture packets carrying units; with the routine admitted in a probe it passes the Part 11 static check, and DuckDB 1.5.5's count and SQLGlot 30.18.0's parse of the three spellings were probed. Findings closed in the draft: ordering by length, then by scalar value reproduces every `unit_id` in both packets; Part 02 §12.1 omits R81 §2.2's start at zero; `CHARACTER_LENGTH` is admitted in one spelling and without `USING`; the new descriptor is R125 §3.2's exact data with a new ID and E021-04; an extension migrated to the new language changes its version, unchecked. Its proposal's one open question, whether `escapewheel-rule-sql-v0.1` retires or stays beside the new language, was unanswered at promotion, and the draft takes the preferred direction: one language, with the four extension registries advancing their versions. | structural: in place at Part 02 §§1, 9.2, 9.4 and 12.1 and Part 11 §§1, 2 and 5; retires `escapewheel-rule-sql-v0.1`; notes on R81 §2.2, R125 §3.1, R125 §3.2 and R125 §3.11 |
