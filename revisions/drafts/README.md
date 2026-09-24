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
| 1 | [A Validator Checks Every Unit Value Against UCUM](a-validator-checks-every-unit-value-against-ucum.md) | 2110 | Ready for acceptance; appraised 2026-09-23 against `cd2a612`. Depends on no accepted clause or open draft, and precedes the verdict-composition proposal, whose extension parity carries the check to extension tables. Material finding: every unit column is an `open` vocabulary, so §3.2 also exempts unit codes from the open-vocabulary non-rejection rule; R101 §§3.1 and 3.6 and R107 §3.3 are narrowed, not superseded. Every `volts` row in the development packets comes from the LFP source. | Part 02 §§8.4, 9.3, and 13 and Part 05 §5.3, in place |
