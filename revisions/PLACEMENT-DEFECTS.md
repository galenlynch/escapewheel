# Specification placement-defect inventory

| | |
|---|---|
| **Status** | Non-authoritative maintenance inventory |
| **Updated** | 2026-09-17 |
| **Review baseline** | `8d3a9c8598dd0152930ee0aab4de9a19a5496f22` |

This document tracks statements that appear to occupy the wrong specification abstraction or to
duplicate a rule owned elsewhere. It is deliberately separate from both the normative
specification and the higher-level [reconciliation roadmap](proposals/ROADMAP.md). The generated
v0.2 specification remains authoritative while an entry is open; this inventory neither overrides
that text nor decides the replacement rule.

The initial entries come from the
[project sanity check](../Escapewheel_Project_Sanity_Check_2026-09-17.md) and the appraisal of the
[authority proposal](proposals/define-specification-artifacts-and-normative-ownership.md). A
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
| PD-001 | Specification README §§1–5 | Scope, conformance, normative-language, organization, and version statements make an informational entry point an unnumbered normative preamble and duplicate several numbered parts. | P1 relocates each binding statement to Part 00 or the subject-owning part and leaves linked summaries in the README. | Tracked: P1 |
| PD-002 | Specification README §§6–7 | The only normative bibliography is in the README even though that file is to become informational. | P1 moves the complete normative bibliography and its applicability rule to Part 00; the README retains only informative references and links. | Tracked: P1 |
| PD-003 | Specification README §4, Part 00 §9, and each part header | Part status is maintained in overlapping lists, and the README omits Part 10. The present local-header precedence rule permits drift instead of rejecting it. | P1 makes Part 00 the owner, makes local headers checked projections, and adds a framework check. | Tracked: P1 |
| PD-004 | Part 00 §2.4 | Exact session-scope table counts, named columns, and copied registry measurements are logical facts or generated evidence rather than architecture. Several counts are stale. | P2 removes or replaces them with links to Part 02, the registry, or generated evidence. | Tracked: P2 |
| PD-005 | Part 00 §2.4 | Reader projection behavior, session discriminators, join-key instructions, and a measured join cost combine logical identity, reader operation, and performance evidence in the architecture. | P2 separates the logical and reader contracts from Part 10 evidence while reconciling unit identity. | Tracked: P2 |
| PD-006 | Part 00 §4.3 and Part 01 §3.13 | The composite unit-identity statements are misplaced duplicates and contradict the Part 02 and registry `unit_id` identity. | P2 treats Part 02 and the registry as the intended decision point, then updates examples, APIs, fixtures, and tests. | Tracked: P2 |
| PD-007 | Part 00 §§3–4 | Packet content classification, namespace ownership, exact resource declarations, and canonicality are interleaved; several statements duplicate Parts 02, 04, 06, and 09 or the registry. | P1 names the independent axes; P5 appraises classification and canonicality; placement-only cleanup follows the selected owners. | Tracked: P1/P5 |
| PD-008 | Part 00 §5 | Analysis lineage, materialization policy, the exact `analysis.spike_events` declaration, and performance rationale duplicate or compete with Parts 02, 06, and 10. | P5 owns the lineage and canonicality decision; subsequent placement work leaves exact declarations with Part 02 or the registry and evidence in Part 10. | Tracked: P5 |
| PD-009 | Part 00 §7 | Portable encodings, external-resource behavior, profile requirements, and packet-version behavior are physical, catalog, or lifecycle rules rather than framework-level architecture. | P9 reconciles the physical, integrity, and lifecycle rules after P5–P8 establish their owners. | Tracked: P9 |
| PD-010 | Part 00 §8 | A mutable description of the first implementation is informative implementation planning, not normative architecture. | Move it to Part 07 or developer documentation through placement cleanup or ordinary maintenance once P1 establishes the boundary. | Open |
| PD-011 | Part 01 | Scalar types, `*_name` columns, table and column restrictions, nullability, manifest placement, and importer algorithms cross from semantic meaning into logical representation, catalog structure, and workflow. | Preserve concept meaning in Part 01; appraise moves to Parts 02, 04, and 05 during placement cleanup. | Tracked: P2 |
| PD-012 | Part 02 | Reader and writer algorithms, validator reporting behavior, and Parquet/Zarr performance rationale sit beside logical declarations. | Retain logical invariants in Part 02; appraise operational placement in Part 05 and storage-dependent rules or evidence in Parts 03 and 10. | Tracked: P2/P9 |
| PD-013 | Part 03 | Amendment, retention, cleanup, recipes, adapter capabilities, delivery completeness, process lifecycle, and IPC transport are combined with the portable storage profile. | P8 separates adapter/build-interface semantics; P9 handles remaining lifecycle placement while Part 03 retains profile-dependent encodings. | Tracked: P8/P9 |
| PD-014 | Part 04 | Logical resource kinds are described as Parquet tables and Zarr arrays, and catalog declarations are mixed with reader and validator operations. | P6 separates logical kinds, profile-selected encodings, catalog state, and operational behavior. | Tracked: P6 |
| PD-015 | Part 05 | Packet validation and writer/process conformance are combined without an early, consistently applied actor boundary. | P7 and P9 appraise validity composition and lifecycle organization, including whether the distinction remains internal or becomes structural. | Tracked: P7/P9 |
| PD-016 | Part 06 | Mixed normative and informative analysis policy repeats Part 00, embeds an exact table schema, and carries benchmarks. | P5 selects the analysis contract owner; exact schema stays with Part 02 or the registry and evidence moves to Part 10. | Tracked: P5 |
| PD-017 | Part 07 | An informative implementation part uses normative keywords for comments, performance behavior, and document placement and embeds mutable phase status. | Relocate developer policy and status to developer documentation and retain only clearly informative implementation description. | Open |
| PD-018 | Part 08 | An informative example's acceptance checklist and SQL resemble an independent contract and preserve obsolete unit columns. | P2 reconciles unit examples; P10 generates and executes the example from current authoritative declarations. | Tracked: P2/P10 |
| PD-019 | Part 09 | The core/extension placement boundary repeats Part 00, while adapter and report-delivery behavior belongs with the build interface. | P1 establishes the architectural owner; P8 reconciles adapter behavior and Part 09 references rather than restates it. | Tracked: P1/P8 |
| PD-020 | Part 10 §3 | An informative performance part states an uppercase `SHOULD` about time-bucket row groups. | Move the storage obligation to Part 03 and retain its measurement and rationale in Part 10. | Tracked: P9 |

## Closure record

No entry has yet been resolved or dismissed against the review baseline.
