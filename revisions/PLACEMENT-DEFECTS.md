# Specification placement-defect inventory

| | |
|---|---|
| **Status** | Non-authoritative maintenance inventory |
| **Updated** | 2026-09-27 |
| **Review baseline** | `e7a923cab7ad6db2d880e07ea2334349b8ca641f` |

This document tracks statements that appear to occupy the wrong specification abstraction or to
duplicate a rule owned elsewhere. It is deliberately separate from both the normative
specification and the higher-level [reconciliation roadmap](proposals/ROADMAP.md). The generated
v0.2 specification remains authoritative while an entry is open; this inventory neither overrides
that text nor decides the replacement rule.

The initial entries come from the
[project sanity check](../Escapewheel_Project_Sanity_Check_2026-09-17.md) and the appraisal of the
[R122](accepted/R122-define-specification-artifacts-and-normative-ownership.md). A
candidate destination identifies where appraisal should begin, not an accepted ownership decision.

## Maintaining the inventory

Give each observation a stable `PD-<number>` identifier. Use one of four states:

- **Open:** reproduced, but not yet covered by an active proposal or ordinary maintenance change.
- **Tracked:** assigned to a roadmap work item or active lifecycle artifact.
- **Resolved:** incorporated or repaired without changing the contract; record the revision or
  commit and final owner.
- **Dismissed:** appraisal showed that the present placement is intentional; record why.

Do not delete resolved or dismissed entries. Split an entry when appraisal finds independent
decisions, and add newly discovered locations rather than expanding an entry into a general topic.
The roadmap owns sequencing among work items; this file owns the observation-level audit trail.

## Current inventory

| ID | Current location | Observed placement or duplication defect | Candidate disposition | State |
|---|---|---|---|---|
| PD-001 | Specification README §§1–5 | Scope, conformance, normative-language, organization, and version statements made an informational entry point an unnumbered normative preamble and duplicated several numbered parts. | R122 relocated each binding statement to Part 00 or the subject-owning part and left linked summaries in the README. | Resolved: R122 |
| PD-002 | Specification README §§6–7 | The only normative bibliography was in the README even though that file was to become informational. | R122 moved reference authority into the numbered specification; R124 retained policy and shared references in Part 00 and placed single-part references with their subject owners. The README retains only informative navigation. | Resolved: R122/R124 |
| PD-003 | Specification README §4, Part 00 §9, and each part header | Part status was maintained in overlapping lists, and the README omitted Part 10. The local-header precedence rule permitted drift instead of rejecting it. | R122 made Part 00 the owner, made local headers checked projections, and added a framework check. | Resolved: R122 |
| PD-004 | Part 00 §3.3 | Exact session-scope table counts, named columns, and copied registry measurements were logical facts or generated evidence rather than architecture. Several counts were stale. | R123 removed the counts and left logical session scope with Part 02 §7.1. | Resolved: R123 |
| PD-005 | Part 00 §3.3 | Reader projection behavior, session discriminators, join-key instructions, and a measured join cost combined logical identity, reader operation, and performance evidence in the architecture. | R123 moved reader presentation and correlation to Part 05 §13, retained logical scope in Part 02, and removed the unrefreshed ratio. | Resolved: R123 |
| PD-006 | Part 00 §4.3 and Part 01 §3.13 | The composite unit-identity statements were misplaced duplicates and contradicted the Part 02 and registry `unit_id` identity. | R123 retained Unit meaning in Part 01, made Part 02 §12.1 the logical owner, and corrected reader behavior and projections. | Resolved: R123 |
| PD-007 | Part 00 §§3.2–4 | Packet content classification, namespace ownership, exact resource declarations, and canonicality remain interleaved; several statements duplicate Parts 02, 04, 06, and 09 or the registry. | R128 removed the exact resource declarations and made the catalog classification defer to the declaration. Remaining, placement only: Part 00 §3.2's serialized content-class table duplicates Part 02 §2.2, Part 00 §4.1's grain statements duplicate Part 02, and Part 00 §4.2 restates the `core.units` spike-summary columns and rule beside v0.1 history. The reference-direction rule is split to PD-024. | Open |
| PD-008 | Part 00 §5 | Analysis lineage, materialization policy, the exact `analysis.spike_events` declaration, and performance rationale duplicate or compete with Parts 02, 06, and 10. | R128 and R130 gave lineage, realization and promotion to Part 06 and the declaration to the registry. R145 removed Part 00 §5.1's restatement of disposability, which now cites Part 06. The promotion rule was split to PD-025. | Resolved: R128/R130/R145 |
| PD-009 | Part 00 §7 | Portable encodings, external-resource behavior, profile requirements, and packet-version behavior are physical, manifest, or lifecycle rules rather than framework-level architecture. | R129 and R144 corrected Part 00 §§7.2–7.3. Maintenance on 2026-09-27 replaced Part 00 §7.1's serverless reading and §7.2's external-resource restatements with citations of Part 03 §1 and Part 04 §5. Remaining: Part 00 §7.3's `packet_version` rule (Part 03 §9.6). Part 03's copy binds only its own profile, so the copy to keep is one that binds every profile. | Open |
| PD-010 | Part 00 §8 | A mutable description of the first implementation is informative implementation planning, not normative architecture. | Unchanged at the review baseline, and drifting: its five components disagree with Part 07's distributions. Move it to Part 07 or developer documentation, keeping only the citation of Part 05 §1. | Open |
| PD-011 | Part 01 | Scalar types, `*_name` columns, table and column restrictions, nullability, manifest placement, and importer algorithms cross from semantic meaning into logical representation, manifest structure, and workflow. | R128 removed the manifest placement and R123 the composite unit key. Remaining, placement only: Part 01 §2.1's carried and assigned identity and `*_name` rule (Part 02 §8.2), table and column restrictions (Part 01 §3.8 and elsewhere), a restated nullability, and importer and consumer algorithms (Part 01 §3.9). Two disagreements with Part 02 are split to PD-027 and PD-028, and dataset measurements to PD-029. | Open |
| PD-012 | Part 02 | Reader and writer algorithms, validator reporting behavior, and Parquet/Zarr performance rationale sit beside logical declarations. | No revision moved Part 02's operational material. Remaining: Part 02 §8.6's dataset measurements and validator `info` reporting, Part 02 §8.3's reader resolution of a discriminator, and Part 02 §10.3's physical-order statement duplicating Part 05 §5.3. | Open |
| PD-013 | Part 03 | Amendment, retention, cleanup, recipes, adapter capabilities, delivery completeness, process lifecycle, and IPC transport are combined with the portable storage profile. | R144 moved recipes, adapter capabilities, delivery, the adapter lifecycle and transport to Part 12, and R135 gave the staging area to Part 05 §2. Remaining: Part 03 §9's amendment, versioning and revalidation rules are profile-independent. Part 03 binds only its profile, so moving them widens their scope and takes a placement revision. | Open |
| PD-014 | Part 04 | Logical resource kinds are described as Parquet tables and Zarr arrays, and catalog declarations are mixed with reader and validator operations. | R128 made Part 02 the owner of resource kinds and R130 removed the codec projection. Remaining, placement only: Part 04 §5.3's reader-access paragraph duplicates Part 05 §14.3. | Open |
| PD-015 | Part 05 | Packet validation and writer/process conformance are combined without an early, consistently applied actor boundary. | R132 and R135 changed verdict and lifecycle rules without the actor reorganization. Part 05 still opens with "Validation is importation", draws its actor boundary only at Part 05 §10, and says a writer conforms when it satisfies the part while also binding readers and validators; Part 00 §2.4 calls the writer the actor Part 05 binds throughout. | Open |
| PD-016 | Part 06 | Mixed normative and informative analysis policy repeats Part 00, embeds an exact table schema, and carries benchmarks. | The embedded schema is now a projection `columns.py` checks against the registry. Remaining, placement only: Part 06 §§3–4's benchmarks (Part 10) and Part 06 §6's record of v0.1 withdrawals. R145 replaced Part 06 §4's statement of Part 03 §5.4's order and row groups with a citation. Part 06 §4's MUSTs were split to PD-026. | Open |
| PD-017 | Part 07 | An informative implementation part uses normative keywords for comments, performance behavior, and document placement and embeds mutable phase status. | Unchanged at the review baseline, though no uppercase keyword remains: the defect is imperative developer policy (Part 07 §§6–7), a document-placement rule (Part 07 §7), and Part 07 §5's phase-status table. | Open |
| PD-018 | Part 08 | An informative example's acceptance checklist and SQL resemble an independent contract and preserve obsolete unit columns. | R123 corrected the unit columns, and `e7a923c` generates Part 08 §§2–3 from a writer-built packet and runs Part 08 §4's queries as tests. Remaining: Part 08 §5's acceptance checklist is a second, incomplete conformance definition beside Part 05, and Part 08 §1 misstates the spike tables' columns. | Open |
| PD-019 | Part 09 | The core/extension placement boundary repeats Part 00, while adapter and report-delivery behavior belongs with the build interface. | R144 moved report delivery to Part 12 §9. Remaining: Part 09 §5.7 restates Part 12 §§3 and 5, and says `files-v0.1` "remains the route every implementation supports" where Part 12 §3 obliges a build to support every protocol and an adapter one of them. Part 00's restatement is PD-007's and PD-024's. | Open |
| PD-020 | Part 10 §3 | An informative performance part states an uppercase `SHOULD` about time-bucket row groups. | Part 10 §3 restated Part 03 §5.4's SHOULD. Maintenance on 2026-09-27 rewrote it as an informative citation. | Resolved: maintenance |
| PD-021 | Part 00 §§2 and 10 | The complete central bibliography places external authorities used only by one numbered part in the framework rather than beside the subject that invokes them. | R124 retained policy and shared references in Part 00, moved portable-profile references to Part 03 and SHA-256 to Part 04, and established the rule that lets future Part 11 own its SQL and floating-point references. | Resolved: R124 |
| PD-022 | Part 01 §§3.17–3.18 and the `core.array_assets`, `analysis.array_assets`, and `core.media_assets` declarations | Semantic concept definitions own URI, encoding, and manifest-provenance rules, while logical asset tables duplicate URI and format fields already owned by the packet manifest and physical profile. | R128 removed `uri` and `format` from the three asset tables, bound catalog rows to manifest entries through `resource_id`, and left Part 01 with concept meaning and pointers to Parts 02–04. Part 01's remaining logical detail is PD-011's. | Resolved: R128 |
| PD-023 | Part 01 §3.3 and `core.sessions.reference_clock_id` in Part 02's incorporated registry | The semantic Session requires the clock its times are reported on, but the logical column is nullable and the declared rule rejects a missing reference only when more than one clock exists. A one-clock packet can therefore omit the explicit reference even though the semantic statement is unconditional. | Reproduced at the review baseline. Part 01 §3.3's unconditional MUST is stronger than accepted R27 §2 (SHOULD, and MUST with more than one clock), which the registry rule implements. The reference reader refuses to map a one-clock session with no reference rather than defaulting to its clock. Contract disagreement. R145 made Part 01 §3.3 require the reference clock only of a session declaring more than one clock, and recommend it otherwise, which the registry rule implements. | Resolved: R145 |
| PD-024 | Part 00 §3.2 and Part 09 §6.1 | Part 00 lets a content class reference only a class "beneath" it and says neither core nor analysis references an extension; Part 09 §6.1 lets any resource an extension registry declares, an analysis resource included, reference that extension. Nothing orders the classes. | Contract disagreement: a revision decides which rule holds and leaves it with one owner. R145 gave Part 02 §2.2 the rule that a canonical resource depends only on canonical resources, left the registry direction with Part 09 §§6.1–6.2, and made Part 00 §3.2 cite both. | Resolved: R145 |
| PD-025 | Part 00 §5.1 | An analysis resource "becomes canonical only through an explicit revision of this specification", where Part 02 §2.2 and Part 06 §8 also admit an extension-registry change. | Contract disagreement: R128 §3.2 chose the wider rule, so Part 00's narrower statement is the one out of step. R145 deleted Part 00 §5.1's narrower statement; Part 06 §8 owns promotion. | Resolved: R145 |
| PD-026 | Part 06 §4 | Part 06 §4 obliges a writer with MUSTs about omitted and colliding spikes, while Part 00 §9 lists that section as informative. | Which text binds is a contract question: move the obligations into a normative section or change the status row. R145 made Part 06 §4 normative except its measurement, in Part 00 §9's status row and Part 06's status line. | Resolved: R145 |
| PD-027 | Part 01 §2.1 | "An identifier is a signed 32-bit integer", where Part 02 §5.3 admits `int64` identifiers and a string catalog `resource_id`. | Contract disagreement: Part 02 owns identifier types. R145 replaced Part 01 §2.1's type statement with a citation of Part 02 §5.3 and Part 04 §4.1. | Resolved: R145 |
| PD-028 | Part 01 §3.9 and Part 02 §12.6 | Part 01 says a writer reaching past one median anchor interval MUST measure its error and MUST record the median, p95 and maximum; Part 02 says it SHOULD record them. | Contract disagreement. R145 kept the measurement in Part 01 §3.9 and gave the record to Part 02 §12.6, which recommends it and requires the three statistics together where it is made. | Resolved: R145 |
| PD-029 | Part 01 §§3.17, 3.23 and 3.24 | Normative concept text carries measurements from particular datasets: 22 of 25 arrays, 133 and 302 days, and 27,557 and 8,448 rows. | Leave evidence with the revisions that measured it or with Part 10; placement only. | Open |

## Closure record

- R122 resolved PD-001 through PD-003 by making the specification README informational, assigning
  its binding statements to numbered owners, centralizing normative references in Part 00, and
  checking the README and local part-status lines as projections.
- R123 resolved PD-004 through PD-006 by removing stale architecture counts and implementation
  measurements, assigning reader composition to Part 05, and reconciling unit identity around the
  packet-assigned `unit_id` owned by Part 02.
- R124 resolved PD-021 and completed PD-002's ownership cleanup by distributing single-part
  normative references to their subject owners while retaining policy and shared references in
  Part 00.
- R128 resolved PD-022 by removing the asset tables' `uri` and `format` columns and binding catalog
  rows to manifest entries through `resource_id`. R128, R129, R130, R132, R135 and R144 resolved
  parts of PD-007 through PD-009, PD-011, PD-013, PD-014 and PD-019; each row records what remains.
  The re-appraisal at `e7a923c` split six observations out as PD-024 through PD-029, five of them
  disagreements between a summary in Part 00, 01 or 06 and the part that owns the rule.
- R145 resolved PD-023 through PD-028 and PD-008's remainder by stating each disputed rule once at
  its owner and citing it from the summary, and by making Part 06 §4 normative. It also removed
  the row-group statement from PD-016's remainder.
