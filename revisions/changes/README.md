# Changes

A change document carries one specification change from Open to Accepted. Start it from
`../templates/change.md`; the statuses and what each requires are in `../CONTRIBUTING.md`.

A change document has no number. It gets one only after acceptance is authorized, taken from the
end of the accepted range, so the numbered space reads in the order revisions were **applied**
rather than the order they were written. Nothing outside this directory may cite a change document
by number, because it has none, and a change document does not change the authoritative generated
v0.2 specification.

Why: an `R<N>` is permanent once accepted: it identifies the accepted record, its clause-ledger
entries, and its evidence manifest. Git preserves the earlier states. Assigning a number while a
change is open would force application order to match writing order or require those permanent
references to be renumbered.

A change document cites another by its file name in backticks. At acceptance those citations become
`R<N> §<x>`, which is a step in the acceptance sequence in `../CONTRIBUTING.md`.

## Application order

Dependencies run downward, so a document may depend on the ones above it and on nothing below.

| order | document | status | placement |
|---:|---|---|---|
| 1 | `a-source-entry-names-one-route.md` | Open | Part 05 §3.9 |
