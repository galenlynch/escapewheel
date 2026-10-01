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
| 1 | [The reader floor bounds an array's byte order](the-reader-floor-bounds-an-arrays-byte-order.md) | 2658 | Promoted 2026-10-01 and appraised on `5117217`. Every affected section already carried an anchor, so no bootstrap was needed. Rerun at `5117217`: no part mentions `endian` or `fill_value`, and the ledger places R3 §7.1 at Part 03 §6.1. The reader matrix is the probe run of 2026-10-01, not repeated since, and no probed library or array has changed. The schema of §3.3 was evaluated against the descriptor: it accepts the v2 floor of §3.2 and refuses the current descriptor, an absent, empty or unknown `dtype_byte_orders`, and the member on the v3 floor. Three choices were made in drafting and are the reviewer's to confirm: the member lists the type string's own characters, it is required, and the two withdrawn sentences land as a writer permission and an instance of upstream invalidity in Part 03 §6.4. No other draft is open and no open proposal touches Part 03 §6.4 or Part 05 §5.3. | structural: in place at Part 03 §§1 and 6.4 and Part 05 §5.3, an informative table in Part 10 §5; notes on R3 §7.1, R129 §3.4, R137 §§3.3 and 3.5, and R154 §3.5 |
| 2 | [A build records a recipe without its credentials](a-build-records-a-recipe-without-its-credentials.md) | 2199 | Promoted 2026-10-01 and appraised on `fca9482`, the bootstrap that anchors Part 05 §3.2; the commit after it regenerated the heading index and the combined rendering. Independent of the draft above: neither touches a section the other does. Rerun at the baseline: Part 05 §3.5 lists no refusal for a credential, the recipe schema leaves `storage_options` unconstrained, and the reference build refuses a recognized member and records `[redacted]`. Material finding: a source root reaches the packet root at four places, not the two the proposal counted, since an external manifest entry (Part 12 §5) and a source resolution document (Part 04 §5.5) each carry a URI derived from it. Three choices were made in drafting and are the reviewer's to confirm: the rule covers everything a build composes and not only the recorded recipe and the source-file row; the marker is the fixed string `[redacted]`; and an adapter's delivery and a command's output are outside the rule. No open proposal touches Part 05 §§3.2, 3.5 or 7. | structural: in place at Part 05 §§3.2, 3.5 and 7; notes on R111 §3.5, R135 §3.4 and R150 §3.7 |
