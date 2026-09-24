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
| 1 | [A Build Owns Its Staging Area and Validates Everything It Stages Before Publishing](a-build-owns-its-staging-area-and-validates-everything-it-stages-before-publishing.md) | 4055 | Appraised 2026-09-24 against `3ac0410`, the metadata-only anchor bootstrap that gave Part 05 §§4, 4.2, 5, 6, 7, and 8, Part 03 §9.5, and Part 00 §8 canonical anchors; ready for acceptance. The draft is structural, since it replaces rules inside existing sections, and its Decision states each rule directly, with the crosswalk placing it. The appraisal found that `amend` writes a newly bound registry document at its final path before validating, so the draft has it stage the document under `staging/`, and that the staging area must be an amendment's as well as a build's. Part 00 §§2.4 and 8 already agree with the order and are left unchanged. The stray clause narrows R61 §2.1 and R32 §6, whose ledger entries move to anchors. The recorded `uri` is the recipe's root as written, so Part 05 §11's determinism holds. | Part 03 §§9.5, 11.2, and 11.3 and Part 05 §§1, 2, 4, 4.2, 5, 6, 7, and 8 in place; a subsection added at the end of Part 03 §3 |
| 2 | [Every Packet-Owned Resource Records a Named Whole-Object Digest](every-packet-owned-resource-records-a-named-whole-object-digest.md) | 4095 | Appraised 2026-09-24 against `96f5e58`; awaiting a metadata-only anchor bootstrap for Part 03 §10, Part 04 §§5.2 and 5.4, Part 05 §11, and Part 08 §5, after which `Based on` moves to that commit and the gates are rerun. The draft is structural: it replaces rules inside Part 03 §10 and Part 04 §§5.3, 5.4, and 10, moves the digest definition to a new last subsection of Part 04 §4, and moves RFC 1952's entry to Part 00 §10. The appraisal found that all four built packets already fail the current manifest schema, so the `digest` object adds no migration beyond R130's rebuild, and that a CRC prefix's value is a 64-digit SHA-256 of its listing, so the schema admits either width under a CRC. It states the approved all-or-none member rule as a schema condition tied to the entry's `digest`, which also carries the writer's duty to record external member digests. Throughputs and check values were rerun. It commutes with the reader-floor draft, which also edits Part 03 §12. | Part 00 §10, Part 03 §§1, 10, 11.3, and 12, Part 04 §§1, 4.1, 5.2, 5.3, 5.4, 10, and 11, Part 05 §11, and Part 08 §§3 and 5 in place; a subsection added at the end of Part 04 §4; the RFC 1952 entry moved from Part 03 §12 to Part 00 §10 |
| 3 | [The Zarr Floor Admits Blosc-Zstd and Sharding, and a Feature Outside a Floor Is a Resource Finding](the-zarr-floor-admits-blosc-zstd-and-sharding-and-a-feature-outside-a-floor-is-a-resource-finding.md) | 3408 | Appraised 2026-09-24 against `96f5e58`; the final appraisal awaits a metadata-only bootstrap giving Part 10 §5 a canonical anchor. The draft is structural, since it replaces the v3 floor paragraph of Part 03 §6.4 and two sentences of Part 05 §5.3. It adopts the promoted proposal's preferred answers: a shard index only at `end`, with an absent `index_location` read as `end`; Blosc discriminated by `cname` alone; `info` for a valid feature outside a reader-only floor and `warning` for a packet-owned table outside the Parquet writer floor; one `external.physical_unassessed` finding per resource; data-page types reported unassessed; and the descriptor schema's `$id` at 0.2.0. The appraisal found that raising the floor adds reader obligations, which the proposal had marked unchanged, and that the numeric ledger destinations of 14 clauses in Part 03 §§5.5 and 6.4 move to anchors. The writer output of §2.1 was rerun at the baseline; the five-reader matrix is the same day's probe. | Part 03 §§5.5 and 6.4, Part 05 §5.3, and Part 10 §5 in place |
