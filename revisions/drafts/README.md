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
| 1 | [A Packet-Owned Opaque Resource Crosses as Its Bytes, in a Directory Named by Its Resource ID](a-packet-owned-opaque-resource-crosses-as-its-bytes-in-a-directory-named-by-its-resource-id.md) | 6215 | Revised 2026-09-25 after a critical review, on `c5b8e50`: a payload binds to an opaque singleton declaration as well as a catalog row; every manifest `uri` without a scheme, packet-owned or external, is an RFC 3986 relative reference in one percent-encoded form, which readers and validators decode and `packet.resource.uri_form` checks; a prefix listing writes keys in UTF-8 under RFC 8785, adding Part 04 §§4.3, 5.5, 10, and 11 to the amended sections; and the name warning, now `physical.opaque_name_portability`, also covers names Windows cannot hold. Re-appraisal pending. It follows R142 and shares no section with R141; the later relocation of Part 03 §11 carries its rules and R142's. | Part 03 §§2, 3.1, 4, 10, 11, 11.2, and 11.3, Part 04 §§4.3, 5.4, 5.5, 10, and 11, Part 05 §§2, 5.3, and 15, and Part 07 §4 in place |
