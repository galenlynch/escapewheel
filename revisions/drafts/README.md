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
| 1 | [Each Statement Sits in the Part That Owns Its Subject](each-statement-sits-in-the-part-that-owns-its-subject.md) | 5329 | Appraised 2026-09-27 on `9bc97b6`, the anchor bootstrap for the 22 structurally affected sections that had no anchor. No other proposal or draft is open. Registry counts and the example packet's spike tables rechecked at the baseline. Findings closed in the draft: Part 01 §3.8 requires a value on every axis where R105 §3.3 permits fewer, which §3.6 settles for R105; the reference validator maps an origin only through anchors onto the parent and takes the packet's first reference clock, which §3.4 and the impact inventory correct. | structural: Part 03 §§9.1–9.6 to a new Part 05 section on amendment; Part 05 §1 replaced by a scope section; new last subsections of Part 02 §12 and Part 05 §13 and a new last section of Part 10; retires Part 00 §§4.2, 5.2 and 8, Part 06 §6, Part 07 §5 and Part 08 §5; renumbers Part 00 §§9–10, Part 05 §15, Part 06 §§7–8 and Part 07 §§6–7 |
