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
| 1 | [A build records a recipe without its credentials](a-build-records-a-recipe-without-its-credentials.md) | 2239 | Promoted 2026-10-01 and appraised on `fca9482`, the bootstrap that anchors Part 05 §3.2; the commit after it regenerated the heading index and the combined rendering. Rerun at the baseline: Part 05 §3.5 lists no refusal for a credential, the recipe schema leaves `storage_options` unconstrained, and the reference build refuses a recognized member and records `[redacted]`. Material finding: a source root reaches the packet root at four places, not the two the proposal counted, since an external manifest entry (Part 12 §5) and a source resolution document (Part 04 §5.5) each carry a URI derived from it. Three choices were made in drafting and are the reviewer's to confirm: the rule covers everything a build composes and not only the recorded recipe and the source-file row; the marker is the fixed string `[redacted]`; and an adapter's delivery and a command's output are outside the rule. Revised 2026-10-02 and rechecked on `6be2fcf`, where Part 05 §§3.2 and 7 read as at the baseline and §3.5 has gained no refusal for a credential. Material finding of the revision: §3.2 put the marker in place of every recognized value in the recorded recipe, a component of a root among them, while §3.3 had a root written without the component wherever a build writes it, so the two disagreed over the root inside the recorded recipe. §3.3 now excepts the recorded recipe, where the marker stands in the component's place; the alternative is to write the root there without the component as everywhere else. The change alters a Decision clause, so it needs acceptance anew. One open proposal, `a-recipe-accepts-a-discarded-value-by-naming-its-column.md`, also extends the refusals of Part 05 §3.5, in a different item, and either order incorporates. | structural: in place at Part 05 §§3.2, 3.5 and 7; notes on R111 §3.5, R135 §3.4 and R150 §3.7 |
| 2 | [Core declares a catalog of sidecars](core-declares-a-catalog-of-sidecars.md) | 5891 | Redrafted 2026-10-02 on the design settled after the first appraisal and appraised on `53ef6d3`, the bootstrap that anchors Part 02 §§5.3 and 12; the commit after it regenerated the heading index and the combined rendering. Independent of the one above: that draft amends Part 05 §§3.2, 3.5 and 7, and this one amends none of them. Three open proposals advance the same core `registry_version`; §3.8 names no target, so any order incorporates. Rerun at the baseline: the core registry holds 48 declarations, none of class `documentation`; 17 of its 45 tables have a one-column key; `docs/` and `sidecar` occur in six statements of the parts; the corpus holds 120 packets. A probe of the registry sources shows the three declarations pass every Part 02 §9.4 invariant with a carried string key and no meta-schema change. Material findings: Part 02 §5.3, like §4, excepts only the catalog's own `resource_id` from the integer rule, so both are amended for the scope table's referencing column; an amending build refuses a delivered row of a documentation table the manifest already names, which §3.7 changes; and the reference validator's forward check admits a core table the packet does not carry, where Part 02 §8.3 has it report one. Choices made in drafting that are the reviewer's to confirm: the additive amending-build rule of §3.7; `sidecar_type` names no authority and reserves no value; the scope and consumer rules land in a new subsection of Part 02 §12; the `resource_id` exceptions cover every column of that name; `core.sidecar_scopes` declares no `metadata`; `media_type` is `type/subtype` without parameters; and `registry_version` takes the next minor version at incorporation. | structural: in place at Part 02 §§2.2, 2.6, 4, 5.3, 9.2 and 13, Part 03 §§3.1 and 7, Part 05 §4.3, Part 08 §§2 and 3 and Part 09 §§2 and 3, new subsections of Part 02 §§11 and 12, and three registry declarations; notes on R128 §§3.2 and 3.6, R140 §3.3 and R150 §3.6 |
