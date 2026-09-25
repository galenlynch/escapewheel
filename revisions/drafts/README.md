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
| 1 | [A Build Supplies an Adapter a Persistent Source Cache Keyed by URI and Entity Tag](a-build-supplies-an-adapter-a-persistent-source-cache.md) | 4365 | Appraised for acceptance 2026-09-24 against `782dbf8`, which no later commit changes in the parts the draft amends: ready. Trimmed 2026-09-25: the consequence table and one writer test no longer name reference-writer functions or fetch routes, which §2 keeps as observations; no clause changed. Revised 2026-09-25 at the user's direction so the first published entry wins: §3.4 now forbids replacing a readable entry, and a later writer discards its copy, since replacing a file under a reader fails on NFS and Windows. §2.7 records that on the workstation's FUSE-mounted NTFS data disk `link(2)` publishes without replacement while `RENAME_NOREPLACE` is unsupported, and its overlap text now cites R141. The draft is structural in form, replacing the `accepts`, unfillable-term, and declaration-refusal rules of Part 03 §§11.2 and 11.5 and Part 05 §3.5 in place and adding a last subsection to Part 03 §11; all six amended sections carry canonical anchors, so no bootstrap is needed. The cache contents, store responses, and `HeadObject` timings of §2 were re-measured and hold, and neither package changed since the proposal's measurements. The appraisal made §3.3's revalidation per object, stated in §3.4 the one replacement of a readable entry it permits, and added a writer test for a configured location inside the packet root. §§3.3–3.5 bind adapters to behavior no build or validator observes, and each rule says so; an adapter complies with §3.5 in every case by reading its source. It shares no section with R141; the opaque-delivery proposal also appends a row to Part 03 §11.2's table. | Part 03 §§11, 11.2, and 11.5, Part 05 §§3.4 and 3.5, and Part 07 §4 in place; a subsection added at the end of Part 03 §11 |
| 2 | [A Packet-Owned Opaque Resource Crosses as Its Bytes, Bound by Its Catalog Row](a-packet-owned-opaque-resource-crosses-as-its-bytes-bound-by-its-catalog-row.md) | 4568 | Appraised for acceptance 2026-09-25 against `b8bf7c1`, the anchor bootstrap that gives Part 03 §4 its canonical anchor, which no later commit changes in the parts the draft amends: ready. Revised the same day to follow packaging practice on names (BagIt, OCFL, Git): a build refuses only a name a packet cannot hold (not UTF-8, empty, NUL or `/`, `.` or `..`), publishes every other name unchanged, and a validator reports names in one payload directory that are a canonical caseless match under Unicode 16.0.0 §3.13 D145 as the warning `physical.opaque_name_collision`, which adds Part 05 §§5.3 and 15 (both anchored) to the amended sections. D145 was checked against the Unicode 16.0.0 text, and Python 3.14's `unicodedata` implements that edition. The draft is structural in form because it replaces Part 03 §11's route list, Part 03 §3.1's `media/` line, Part 04 §5.4's list of prefix resources, and a sentence of Part 05 §2 in place. The media, payload, and fixture measurements of §2 were rerun and hold, and no current packet-owned URI needs percent-encoding. The one-to-one refusal covers referenced resources handed over in process as well as resource-document entries, §3.3 states that no validator checks name preservation, and §2.4 records that the reader and validator decode a `file` URI but not a relative one. Every other MUST is checked by writer tests, the corpus fixtures §5 lists, or the existing owned-resource rules. It follows the source-cache draft, with which it shares only the rows of Part 03 §11.2's table; it adds no subsection, so their order fixes no number. It shares no section with R141; the later relocation of Part 03 §11 carries both drafts' rules. | Part 03 §§2, 3.1, 4, 10, 11, 11.2, and 11.3, Part 04 §5.4, Part 05 §§2, 5.3, and 15, and Part 07 §4 in place |
