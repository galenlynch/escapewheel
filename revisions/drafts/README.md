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
| 1 | [The Profile Descriptor Declares the Overriding Orders](the-profile-descriptor-declares-the-overriding-orders.md) | 2550 | Promoted 2026-09-30 and appraised on `b548bd0`, the metadata-only bootstrap adding `ew-overriding-orders` to Part 03 §5.4; `e512bc6` regenerated the projections. Rerun against the core registry at `b548bd0`: `analysis.spike_events`'s override satisfies §3.3, and the condition refuses an undeclared resource, an undeclared column, a missing key column, `amplitude` ahead of `core.spike_events`'s key, and an order equal to the key's own. Choices beyond the proposal, awaiting decision: the declaration is a member of the interface `kind_interfaces` maps `table` to, and the checker refuses it elsewhere; an override must differ from its key's order; the schema identifier moves from Part 03 §6.4 to §1; and a bound registry lacking an override's column draws a departure. Part 03 states neither the direction nor the value comparison of a stored order, which this draft leaves as it found. It depends on R93 §3.3, whose check it restores, and advances the physical-profile schema from R137 §3.3's 0.2.0 to 0.3.0. | structural: in place at Part 03 §§1, 5.3, 5.4 and 6.4, Part 06 §4 and Part 09 §5.1; notes on R93 §3.3, R30 §3.2, R81 §2.4 and R137 §3.3 |
