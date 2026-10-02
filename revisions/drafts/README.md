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
| 1 | [A rule means what Part 11 defines on any engine](a-rule-means-what-part-11-defines-on-any-engine.md) | 3907 | Promoted 2026-10-02, appraised and revised 2026-10-02 on `5a1c47b`, whose code, specification and conformance files equal those of `0d8285f`; every amended section already carries a canonical anchor, so no bootstrap precedes it. Depends on no draft or unincorporated revision. Rerun at the baseline: the five shipped registries declare 140 Tier 2 rules, four of them using `BETWEEN` six times and none `IN`, and the validator marks none incomplete; every case of §§2.1, 2.2 and 2.4 made an execution vector returns its engine column when given to the engine as authored. Material findings, resolved in the revision: §3.3 now compares a list of exact members with `x` member by member by value, as the engine and the basis do; §2.5 cited an unreadable Parquet footer as an incomplete evaluation where the reference validator recorded none, and now cites the evaluations that do, the footer defect being corrected at incorporation; §3.4 no longer claims a vector checks the prohibition in general; the ledger plan adds R149 §3.2's note. Choices that are the reviewer's: Part 05 §9.4 keeps a list for evaluations other than rules; the language ID stays `escapewheel-rule-sql-v0.2`, with the 2023 ISO basis unverified (§2.3). | structural: in place at Part 11 §§1, 4 and 8 and Part 05 §9.4; notes on R125 §§3.2, 3.3, 3.4 and 3.8 and R149 §3.2 |
