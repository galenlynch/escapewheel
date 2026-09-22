# Specification placement-defect inventory

| | |
|---|---|
| **Status** | Non-authoritative maintenance inventory |
| **Updated** | 2026-09-22 |
| **Review baseline** | `8d3a9c8598dd0152930ee0aab4de9a19a5496f22` |

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
| PD-007 | Part 00 §§3.2–4 | Packet content classification, namespace ownership, exact resource declarations, and canonicality remain interleaved; several statements duplicate Parts 02, 04, 06, and 09 or the registry. | R122 named the independent axes; P5 appraises classification and canonicality, after which placement-only cleanup follows the selected owners. | Tracked: P5 |
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
| PD-019 | Part 09 | The core/extension placement boundary repeats Part 00, while adapter and report-delivery behavior belongs with the build interface. | R122 established the architectural owner; P8 reconciles adapter behavior and makes Part 09 reference rather than restate it. | Tracked: P8 |
| PD-020 | Part 10 §3 | An informative performance part states an uppercase `SHOULD` about time-bucket row groups. | Move the storage obligation to Part 03 and retain its measurement and rationale in Part 10. | Tracked: P9 |
| PD-021 | Part 00 §§2 and 10 | The complete central bibliography places external authorities used only by one numbered part in the framework rather than beside the subject that invokes them. | R124 retained policy and shared references in Part 00, moved portable-profile references to Part 03 and SHA-256 to Part 04, and established the rule that lets future Part 11 own its SQL and floating-point references. | Resolved: R124 |
| PD-022 | Part 01 §§3.17–3.18 and the `core.array_assets`, `analysis.array_assets`, and `core.media_assets` declarations | Semantic concept definitions own URI, encoding, and manifest-provenance rules, while logical asset tables duplicate URI and format fields already owned by the packet catalog and physical profile. | The active logical-resource proposal keeps concept meaning in Part 01, gives Part 02 declaration and lineage policy, binds packet locations in Part 04, leaves encodings with Part 03, and removes the duplicated logical columns. | Tracked: logical-resource proposal |
| PD-023 | Part 01 §3.3 and `core.sessions.reference_clock_id` in Part 02's incorporated registry | The semantic Session requires the clock its times are reported on, but the logical column is nullable and the declared rule rejects a missing reference only when more than one clock exists. A one-clock packet can therefore omit the explicit reference even though the semantic statement is unconditional. | Appraise whether the one-clock implicit default was intentional. If the semantic requirement stands, make the logical declaration and conformance checks require the reference; otherwise narrow the semantic statement. Keep this independent of resource-family requiredness. | Open |

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
