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
| 1 | [A unit is identified outside its packet by its name](a-unit-is-identified-outside-its-packet-by-its-name.md) | 5067 | Promoted 2026-10-02 and appraised on `7201b2d`; every amended section already carries a canonical anchor, so no bootstrap precedes it. Independent of R159, R161, R162 and R163 in text: none amends Part 02 §§8.2, 10.1, 12.1 or 12.9 or Part 05 §5.1, or changes a declaration of a name. R161 §3.5 and R163 §3.3 advance the same core `registry_version`; §3.5 names no core target, so any order incorporates, and none of them declares a table that owns an assigned identifier. This draft alone advances the meta-schema `$id` and the registry-contract descriptor, to 0.12.0 and v0.10. Rerun at the baseline: 17 of the core registry's 47 tables own an assigned identifier, each with a one-column key, and nine of their names are `nullable`; one extension table owns one, `dynamic_foraging.blocks`, keyed by a session and the block, with a `nullable` name; the 132 corpus packets hold 3,044 names and the two session packets outside the tree 12,243 and 8,932, none null, with one name two rows share, in `dup_pk`; four corpus packets that pass hold units sharing `(sorting_run_id, local_unit_label)` and none shares a `unit_name`. A probe of a copy of `spec/` with the nine names `required` and a presence-checking `registry.identity.name` regenerates and passes the tree's check; under that checker the baseline core registry draws nine outcomes, and of the four extension registries only `dynamic_foraging` is invalid, on `dynamic_foraging.blocks`. Material finding: every repository extension names meta-schema 0.11.0 and migrates, and `dynamic_foraging` is also invalid on one declaration until its owner changes it. Choices made in drafting that are the reviewer's to confirm: the nine core declarations are a separate `registry` clause; §3.4's sentence covers anything outside the packet that holds a name; R152 §3.4 stays `applied` with a note, and a version clause another draft lands first becomes `superseded` by this one. Revised 2026-10-02 after a critical appraisal and rechecked on `0815350`, where R159 and R160 had landed and changed none of the sections this draft amends. §3.3 now says that two names are equal where their Unicode scalar sequences are, as Part 11 §5 compares characters, and that the check reports nothing for an `optional` name a table omits, as the `finite` check does; §3.4 drops the sentence on `core.intervals.label_unique_within_kind`, which Part 02 §12.9 keeps as a statement about labels; §3.5 is placed in Part 02 alone, as R152 §3.4 was, and Part 08 §§2 and 3 are a projection showing the core version and the four extension versions. The draft no longer states how `dynamic_foraging` changes its declaration: that registry is invalid under v0.10 until its owner changes it, and the repository's copy is made valid at incorporation. Consequence states as limits that a duplicated row draws two findings, that two conforming validators can disagree on a packet bound under an earlier descriptor, that a table has one instance, that an adapter's null name fails the non-null check, and that uniqueness is per identifier. R160 took core 0.15.0 and added two tables and a catalog, owning no assigned identifier. Material finding of the recheck: R160 §3.8, which assigns only the core version, becomes `superseded` by this draft where it lands first, and R152 §3.4 keeps its disposition with a note for the meta-schema and descriptor; §3.5's statement of the baseline core version now reads `0.15.0`, assigned by R160 §3.8; the rule it states is unchanged. §§3.3 and 3.4 changed, so the draft needs acceptance anew. | structural: in place at Part 02 §§1, 8.2, 9.2, 9.4, 10.1, 12.1 and 12.9 and Part 05 §5.1, the meta-schema `$id`, a new descriptor and nine registry declarations; notes on R81 §2.5, R85 §2.2, R123 §3.1, R148 §3.1 and R152 §3.4 |
