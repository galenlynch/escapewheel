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
| 1 | [Every Array Axis Declares What Each Position Is](every-array-axis-declares-what-each-position-is.md) | 6293 | Appraised 2026-09-28 on `0b98d31`, the anchor bootstrap for Part 10 §2.9. The one other open draft, below, advances the core registry version this one assigns and revises another paragraph of Part 02 §8.3. Label rows, bytes, check timings and the channel orders were measured on the `packet-wf` builds of both session packets; the five declared rules and their analysis mirrors pass the Part 11 static check. Findings closed in the draft: `core.array_dimensions.coordinate_resource_is_core` has had no prose owner since R145 superseded R20 §5.1, and §3.2 states it with its reason; `analysis.array_dimensions` lacked the form rules its core twin carries, and §3.7 adds the mirrors; Part 02 §1 incorporates a v0.2 registry-contract descriptor the repository does not hold, and §3.8 names the v0.6 file; the reference validator compares an axis's length with its coordinate table's row count, which no part states and a label table's padding breaks, and §3.6's range checks replace it; no label holds free text, and a packet-owned array carries `dimension_names` (user's direction). | structural: in place at Part 02 §§1, 3, 8.3, 9.2, 9.4, 11.6 and 11.8, Part 03 §§6.3 and 6.5 and Part 05 §5.3; retires Part 02 §8.3's by-position shape; supersedes R20 §§2.4 and 3 and R100 §§2.1–2.3 |
| 2 | [An Interval Is Numbered by Its Packet](an-interval-is-numbered-by-its-packet.md) | 2861 | Appraised 2026-09-28 on `b773b21`, the projection refresh after the Part 10 §2.9 bootstrap, and re-appraised the same day after the label left the numbering order (user's direction), so that Part 02 states one label order, the unit proposal's. Depends on the draft above for the core registry version it advances from; the two revise different paragraphs of Part 02 §8.3 and advance Part 02 §9.2's version in turn. The numbering rule and the revised `contains_its_trials` were run on both session packets' `packet-wf` builds with injected defects and a tie numbered both ways, and the 17 `vr_foraging.sites` rules statically checked against the revised declarations. Findings closed in the draft: numbering by kind and time reproduces all 450 and 708 existing identifiers; seven `vr_foraging.sites` rules rely on how sites are numbered and hold under §3.2's order; `contains_its_trials` joined on the struck constant column, and §3.3 rewrites it; R54 §2.2 is superseded; `dup_pk` also draws the numbering rule. Part 02 §12.1's unit order, which compares a string the reference writer reads as a number, is left to its own proposal; intervals of one kind with equal bounds, of which neither packet has any, may be numbered in either order. | structural: in place at Part 02 §§8.3 and 9.2; a new last subsection of Part 02 §12, *Interval identity*; supersedes R54 §2.2 |
