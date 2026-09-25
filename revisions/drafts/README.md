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
| 1 | [A Packet-Owned Opaque Resource Crosses as Its Bytes, in a Directory Named by Its Resource ID](a-packet-owned-opaque-resource-crosses-as-its-bytes-in-a-directory-named-by-its-resource-id.md) | 6612 | Revised 2026-09-25 after a critical review, on `c5b8e50`: a payload binds to an opaque singleton declaration as well as a catalog row, and a singleton payload follows Part 05 §3.4's ownership; every manifest `uri` not beginning `scheme://`, packet-owned or external, is a relative reference of nonempty, representable, percent-encoded segments in one form, which readers and validators resolve by appending decoded names and `packet.resource.uri_form` checks, so `..` and RFC 3986 §5 merging are excluded and a resource outside the root uses `source`; a prefix listing's keys, and members' keys, are unencoded paths written in UTF-8 under RFC 8785; the name warning, `physical.opaque_name_portability`, also covers names Windows cannot hold; and §3.7 restates R117 §3.2's rule that a build records every resource-document entry as external, refusing only `external: false`, rather than requiring adapters to declare it. The Unicode reference is Version 15.0.0, the edition of the oldest supported Python, whose stability policies keep D145 for every code point it assigns. Re-appraised the same day: `stages.py`, `check_citations.py`, `repoint.py`, and `verify.py --quick` pass; the 1,546 relative URIs, 8 members, and 572 citations were recounted, RFC 8785 §3.2.2.2 and Microsoft's naming rules were checked against their texts; ready. It follows R142 and shares no section with R141; the later relocation of Part 03 §11 carries its rules and R142's. | Part 03 §§2, 3.1, 4, 10, 11, 11.2, and 11.3, Part 04 §§4.3, 5.4, 5.5, 10, and 11, Part 05 §§2, 5.3, and 15, and Part 07 §4 in place |
