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
| 1 | [A Packet-Owned Opaque Resource Crosses as Its Bytes, Bound by Its Catalog Row](a-packet-owned-opaque-resource-crosses-as-its-bytes-bound-by-its-catalog-row.md) | 4568 | Appraised for acceptance 2026-09-25 against `b8bf7c1`, the anchor bootstrap that gives Part 03 §4 its canonical anchor, which no later commit changes in the parts the draft amends: ready. Revised the same day to follow packaging practice on names (BagIt, OCFL, Git): a build refuses only a name a packet cannot hold (not UTF-8, empty, NUL or `/`, `.` or `..`), publishes every other name unchanged, and a validator reports names in one payload directory that are a canonical caseless match under Unicode 16.0.0 §3.13 D145 as the warning `physical.opaque_name_collision`, which adds Part 05 §§5.3 and 15 (both anchored) to the amended sections. D145 was checked against the Unicode 16.0.0 text, and Python 3.14's `unicodedata` implements that edition. The draft is structural in form because it replaces Part 03 §11's route list, Part 03 §3.1's `media/` line, Part 04 §5.4's list of prefix resources, and a sentence of Part 05 §2 in place. The media, payload, and fixture measurements of §2 were rerun and hold, and no current packet-owned URI needs percent-encoding. The one-to-one refusal covers referenced resources handed over in process as well as resource-document entries, §3.3 states that no validator checks name preservation, and §2.4 records that the reader and validator decode a `file` URI but not a relative one. Every other MUST is checked by writer tests, the corpus fixtures §5 lists, or the existing owned-resource rules. Refreshed the same day against `d1d10ee`, which incorporated R142: R142 changed none of the text the draft amends apart from appending a row to Part 03 §11.2's table, which this draft's row follows, and no registry declaration or packet changed, so §2's counts hold; the reverse-citation query was rerun. It shares no section with R141; the later relocation of Part 03 §11 carries its rules and R142's. | Part 03 §§2, 3.1, 4, 10, 11, 11.2, and 11.3, Part 04 §5.4, Part 05 §§2, 5.3, and 15, and Part 07 §4 in place |
