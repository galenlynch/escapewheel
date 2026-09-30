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
| 1 | [A Packet Names the Packet It Replaces](a-packet-names-the-packet-it-replaces.md) | 3570 | Promoted 2026-09-29 (decision 39) and appraised on `886ad3a`, the metadata-only bootstrap adding `ew-packet-owned-bytes` to Part 03 §8.1 and `ew-prior-packet-comparison` to Part 05 §9.3; `ac347ee` regenerated the projections. Rerun over every build with a manifest, eight of the first session and seven of the second: each is still `0.1.0`, each manifest's SHA-256 differs, `packet-wf` and `packet-r146` share their core registry version too, and three new consecutive pairs change 4, 1 and 1 resources. `core.units` keeps one digest throughout; `core.intervals` changes digest at `packet-r148`, where R148 renamed a column, and matched by bounds and clock every interval keeps its identifier, correcting the proposal. The first session's amended build retains a superseded manifest byte-identical to `packet-r150`'s. The external repository precedents are dropped, so no normative-reference section gains an entry (Part 00 §9). Choices beyond the proposal, each agreed on 2026-09-30: a replacement keeping its `packet_id` takes any greater major version rather than exactly the next; a mismatched link is a warning, since a validator cannot tell whether the link or the packet it was given is wrong; and Part 05 §6's refusal to promote over an existing path is left to keep a replacement off its predecessor's root, with no new rule. It depends on R150, whose amendment, comparison and recipe schema it extends, and advances the manifest schema to 0.6.0 and the recipe schema to 0.3.0. | structural: in place at Part 03 §8.1, Part 04 §§1, 3 and 10 and Part 05 §§3.1, 3.5, 9.3, 15.1, 15.2, 15.3 and 15.6; notes on R32 §2 and R150 §§3.4 and 3.5 |
