# Define specification authority and abstraction ownership

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-17 |
| **Based on** | `8d3a9c8598dd0152930ee0aab4de9a19a5496f22` |
| **Affects** | Root authority guidance; specification README; Parts 00, 02–05, and 09; part-status projections and terminology citations; specification-framework checks; combined-specification generation; developer documentation |

## 1. Problem

The generated v0.2 specification is the current authority, but the specification does not give an
independent implementer one clear framework for locating that authority. Several separate
properties are conflated:

- whether an artifact is normative or informative;
- which subject an artifact owns;
- whether it is an edited source or a generated result;
- whether it is prose, declarative data, executable logic, or implementation code; and
- whether the repository state is a development candidate or an immutable release.

The specification README currently supplies scope, conformance, normative-language,
normative-reference, organization, and version clauses. `combine.py` prepends it to the numbered
parts because it carries those clauses. A file normally read as navigation and publication
guidance therefore acts as an unnumbered normative preamble. Part 00 repeats parts of the status
and actor models without taking clear ownership of the complete specification framework.

Part 00 also uses *layer* for two orthogonal classifications. Sections 2.1–2.3 describe semantic,
logical, and physical abstraction levels. Section 3 uses the same word for the architectural
relationship of core, extension, analysis, and projection content to a packet. A core, extension,
or analysis resource can have semantic, logical, and physical aspects, so neither classification
is a refinement of the other. The shared term makes statements such as “logical layer” and
“analysis layer” appear to occupy the same hierarchy.

The unclear framework has allowed lower-level facts to remain in overview sections after their
owners changed. Part 00 contains exact table counts, a logical unit key, reader behavior,
performance evidence, and implementation description. Other current disagreements involve unit
identity, packet resource classification, publication order, lineage, and integrity. This proposal
does not resolve those contracts. It establishes the ownership and abstraction vocabulary needed
to resolve them without adding another precedence rule.

The present ambiguity has two practical effects. An implementer cannot always determine whether a
statement is binding or where to find the detailed owner. A maintainer cannot consistently
distinguish an actual disagreement among owners from a stale summary, generated projection, or
implementation defect.

## 2. Evidence

### 2.1 Current repository

The following observations are against the generated v0.2 material at commit
`8d3a9c8598dd0152930ee0aab4de9a19a5496f22`. The working tree was clean when this baseline was
established, and `uv run --project escapewheel-writer python verify.py --quick` passed all 24
stages.

- The specification README contains the only top-level conformance, normative-language, and
  normative-reference clauses. `combine.py` says that the README is first because it carries the
  conformance clauses and version identifiers.
- The README and Part 00 §9 both classify parts. The README says there are eleven parts but its
  table ends at Part 09. Part 00 lists Part 10 and records section-level exceptions for Part 06.
- Part 00 §1 says that Part 00 defines no schema or file format. Later sections nevertheless fix a
  unit key, report exact registry counts, prescribe reader behavior, give a measured join cost, and
  describe the first implementation.
- Part 00 §2.4 says that 33 of 35 core and analysis tables are session-scoped and that eight reach
  `core.sessions` without carrying `session_id`. The baseline registry check instead reports 41 of
  43 session-scoped tables and none lacking the column. The copied measurement drifted after the
  registry changed.
- Part 02 §1 already distinguishes registry rules from current declarations. It identifies
  `registry/logical_schemas.json` as normative for exact current declarations and
  `registry/tables.md` as an informative generated listing. This is an existing example of
  authority divided by concern rather than by file format.
- R81 §2 and Part 02 §12.1 agree that `unit_id` is packet-assigned and packet-unique, and the core
  registry gives `core.units` the primary key `['unit_id']`. Part 00 §4.3 and Part 01 §3.13 retain
  the superseded composite identity. The contradiction demonstrates the effect of duplicated
  ownership, but its full repair is a separate proposal.
- Part 04, `registry/manifest.schema.json`, Part 00, and the implementations disagree on the
  `layer` and `canonical` resource fields. That is a packet-contract decision rather than a reason
  to leave the two architectural axes unnamed.

The repository contains a tracked `RELEASE.json` generated by the current `release.py` prototype.
At the baseline it records commit `2a3a05ea10604e037016ae426054cab3955fa2db`, while the proposal
baseline is later. Its membership comes from Python constants and globs, includes the combined
specification, generated tables, lab-specific extension registries, conformance programs, and the
revision ledger, and excludes the numbered specification sources. `verify.py` does not establish
that file as a current authority. This is evidence that candidate and released state need distinct
concepts; deciding the final release manifest and publication procedure is deferred.

No other lifecycle proposal or draft was open when the initial appraisal began. The narrowed
reverse-citation query covers Part 00 §§1, 2, 2.1–2.3, 2.8, 3, 9, and 10; its current result is
recorded for remeasurement in §6.3. Part 00 §3 alone is cited by Parts 03 and 09, registry
generation and checking, conformance tooling, and R71. Changes to the framework therefore require
a citation sweep even though they do not change packet bytes.

Four accepted revisions overlap the narrowed boundary. R93 §3.6 makes Part 00 list every part but
says a local part header governs a disagreement. R111 §§3.1–3.2 establishes the actor definitions
Part 00 already carries. R112 §3.1 and §3.4 place current requirements in parts and preserve
section identifiers, and R113 §3.1 standardizes their citation spelling. This proposal preserves
the actor and citation decisions and expressly reverses only R93's status-precedence rule.

This project has no published remote, external consumers, or released packets. Backward packet
compatibility is not a constraint on later design proposals. This proposal introduces no new packet
shape or behavior, but it does change how a reader classifies conflicts in the current contract:
they become candidate defects rather than questions settled by an informal precedence rule.

### 2.2 Established specification patterns

Mature specifications commonly divide authority by concern instead of giving all prose or all
machine-readable data blanket precedence:

- [JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core) distinguishes a
  vocabulary, which defines keyword syntax and semantics, from a meta-schema, which validates
  schema structure.
- [Unicode Standard Annex #44](https://www.unicode.org/reports/tr44/) treats published data as an
  integral part of the standard while prose defines how its properties behave.
- [IANA protocol-registration guidance](https://www.iana.org/help/protocol-registration)
  separates registry fields and allocation procedures from exact assignments and references.
- [Apache Arrow's columnar format](https://arrow.apache.org/docs/format/Columnar.html) publishes
  prose beside machine-readable schemas and treats generated tables as views rather than a second
  independently maintained definition.
- The [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html)
  makes normative status explicit and marks informative text, examples, and notes.

These patterns support a small framework in which prose owns meaning and procedure,
machine-readable artifacts can own exact structures or assignments when incorporated for that
purpose, and generated views remain projections. They do not support publishing known
inconsistencies and resolving them afterward through “prose wins” or “data wins.”

## 3. Desired outcome and constraints

### 3.1 Current authority and candidate status

Part 00 would identify the generated v0.2 specification material as authoritative for current
development and conformance at the commit being used. An artifact expressly incorporated by a
numbered part would participate in authority only for the subject and extent that part identifies.
The existing Part 02 incorporation of the core logical registry would remain in force; this
proposal would not incorporate another schema, registry, or rule language.

The frozen proof-of-concept document and accepted revisions would remain design history and
provenance. The combined specification would remain a generated convenience rendering rather than
a separately edited owner. Implementations, generators, adapters, tests, examples, and developer
documentation would remain non-normative.

The same authoritative working specification would be called a specification candidate until a
later publication decision identifies and freezes an exact release. *Authoritative* describes what
currently governs; *candidate* describes publication state. Candidate status would not make the
generated v0.2 material optional or allow an implementation to substitute the proof-of-concept,
revision history, or reference code. This proposal would define the distinction without selecting
final release members, formats, identifiers, or digests.

### 3.2 Authority divided by concern

Part 00 would define an authority-by-concern rule:

- numbered prose owns terms, meanings, processing semantics, actor obligations, conformance, and
  relationships that structural declarations cannot express faithfully;
- an expressly incorporated machine-readable artifact owns only the exact structures or
  assignments for which a numbered part incorporates it;
- historical revisions own rationale and provenance rather than current packet behavior; and
- implementations and evidence acquire no independent normative subject.

Each fact would have one owner. Another artifact could reproduce the fact only as a checked
projection, an informative explanation, or an explicit consistency condition. A disagreement
between owners, an unfaithful projection, or an incorporated artifact that violates its governing
contract would make the candidate inconsistent. No general precedence rule would convert that
state into a valid release.

The working candidate may temporarily contain an inventoried inconsistency while the revision
sequence repairs it. That state would remain authoritative in the limited sense that it is the
current text to inspect; it would not supply enough agreement for publication. The final release
could contain no unresolved ownership conflict.

Normativity, representation, and production would remain separate properties. Prose is not
automatically normative, JSON is not automatically declarative authority, and generated output is
not automatically informative. The owning part and the artifact's declared role determine its
subject.

### 3.3 Part 00 as the specification framework

Part 00 would own:

- specification identity and candidate/release terminology;
- conformance targets and normative-language conventions;
- the normative-reference policy and complete normative bibliography;
- actors and the terms that resolve to them;
- normative, informative, and mixed status;
- artifact roles and the authority-by-concern rule;
- abstraction levels and their dependency direction;
- packet content classes as a separate axis;
- the subject owned by every numbered part; and
- stable citation and publication conventions.

The semantic, logical, and physical classifications would be called **abstraction levels**. A
**packet content class** would classify a resource by its architectural relationship to the
packet's interoperable content rather than by its representation. The current architecture
distinguishes core content, extension content, derived analysis content, and a deferred
compatibility projection. A table and an array can belong to the same content class.

The term *namespace* would remain the ownership mechanism expressed in dotted identifiers, and
*resource kind* would continue to distinguish tables, arrays, media, documents, and views. A
document is therefore a resource kind, not a content class. This proposal would not equate packet
content class with the catalog's current `layer` field or decide whether a future packet declares
or derives that classification; P5 owns those decisions.

Part 00 would define the framework without carrying a changing list of defects. It would not claim
that the first revision had completed the placement pass. Exact keys, copied counts, measurements,
implementation descriptions, packet-classification rules, and lifecycle summaries that remain in
Part 00 are tracked in the non-authoritative
[placement-defect inventory](../PLACEMENT-DEFECTS.md). P2 would handle unit identity and the first
placement cleanup, P5 resource classification and canonicality, and P9 the remaining lifecycle and
physical reconciliations. This preserves a narrow first revision without pretending that its new
ownership rule is already satisfied everywhere.

### 3.4 Part 00 owns part status

Part 00 would own the normative, informative, or mixed status of every numbered part and the exact
section exceptions for a mixed part. Each part would continue to state its own status at its head,
but that line would become a checked projection. A disagreement would make the candidate
inconsistent rather than cause either representation to win.

This decision would supersede the final sentence of R93 §3.6 and the corresponding sentence in
Part 00 §9, which currently say the local part header governs a disagreement. It would not change
the current status assigned to any part or section.

### 3.5 Informational specification README

The specification README would become an informational entry point for navigation, candidate
status, an architectural summary, build guidance, informative references, and links to owning
artifacts. A concise summary could remain if it is identified as a summary and links to the owner.
Every current binding statement would move without changing meaning:

| current README subject | owning destination |
|---|---|
| purpose, applicability, conformance targets, actor summary, general composition of conformance, normative-language convention, normative-reference policy and bibliography, document organization, and specification candidate identity | Part 00 |
| registry document structure, embedding, compatibility, `registry_version` semantics, and the temporary version hold | Part 02 |
| portable-profile identifier and the profile-dependent meaning of that identifier | Part 03 |
| packet catalog fields and the obligation to record the applicable identifiers | Part 04 |
| validation and import consequences stated by the conformance summary | Part 05 |
| extension independence, namespace ownership, and extension-related reader or validator behavior | Part 09 |
| navigation, generated status summaries, informative references, and links to the normative bibliography | remain informative in the README |

Where one README sentence combines several subjects, incorporation would split it and place each
statement with its owner. Existing detailed clauses would be referenced rather than duplicated.
Part 00 would carry the complete normative bibliography, including RFC 2119, Zarr v3, Parquet, and
Arrow. A subject-owning part would cite a Part 00 bibliography entry when its requirements depend
on that external specification; it would not reproduce a second normative reference list. This
central bibliography would not move the subject rule itself into Part 00. The current
normative-keyword semantics would move unchanged; adopting a different keyword set or meaning is
outside this proposal.

The combined document could continue to prepend that README for orientation, but its generator
would not rely on the README to supply a normative preamble. Part 00 would make a standalone part
set intelligible without repository-specific developer documentation.

### 3.6 Scope boundary

This proposal would establish only the framework needed to place subsequent decisions. It would
not decide or incorporate:

- a final release-manifest schema, final `RELEASE.json` membership, hashes, or publication tooling;
- the registry meta-schema or the semantic invariants of registry documents;
- the dialect and execution semantics of Tier 2 rules;
- unit-identity cleanup across prose, examples, APIs, fixtures, types, and tests;
- packet resource requiredness, the serialized classification contract, `layer`, `canonical`, or
  lineage;
- packet identification of core or extension registries;
- packet, resource, source, adapter, or recipe JSON Schemas;
- validity composition, recipe arbitration, adapter capabilities, physical integrity, or codec
  capability; or
- final semantic, logical, profile, registry, schema, or rule-language identifiers.

Those subjects have independent decision boundaries and evidence requirements. None is a
prerequisite for naming its future owner, but all relevant ones are prerequisites for an immutable
v0.2 publication.

### 3.7 Conformance evidence for the framework

The resulting revision would add a focused specification-framework check and tests for it. The
check would parse the ownership table in Part 00 and the status line of every numbered part. It
would establish that:

- Parts 00–10 each appear exactly once and no unknown part appears;
- every local status agrees with Part 00, including Part 06's mixed-section exceptions;
- the complete normative bibliography is in Part 00 and no normative-reference section remains in
  the informational README;
- the informational README contains no normative-keyword obligation; and
- the combined specification remains a reproducible projection whose ordering no longer supplies
  a normative preamble.

Negative tests would cover a missing or duplicate ownership row, an unknown part, a conflicting
part header, a missing or conflicting mixed-section exception, a normative-reference section or
normative keyword introduced into the README, and a combined rendering that is stale or omits Part
00. Positive tests would cover all eleven current parts, Part 06's mixed status, and the normative
bibliography in Part 00.

A human relocation inventory would account for every current README paragraph because keyword
scanning cannot prove that informative prose contains no unique rule. Incorporation would also run
a citation sweep for changed Part 00 sections and every destination receiving README text. The
evidence manifest would record the ownership-table check, its positive and negative tests, the
relocation inventory, and verification that no registry declaration, packet schema, packet
fixture, implementation behavior, or version identifier changed.

The evidence would show that a reader can locate an owner and distinguish a candidate defect from
a precedence question. It would not claim that all known candidate defects have already been
repaired.

## 4. Options and tradeoffs

### 4.1 Keep the current split framework

The specification README could retain its normative preamble while Part 00 remains an overlapping
architecture overview. This avoids immediate edits, but it preserves two entry points for status
and organization and leaves the abstraction axes ambiguous. Later proposals would continue to
choose owners without a common rule.

### 4.2 Make prose the sole authority

Every machine-readable artifact could become an implementation aid, with prose deciding every
conflict. This is simple to explain but turns exact keys, column types, references, vocabularies,
and future declared resource conditions into duplicated prose or non-normative implementation
detail. It conflicts with the project's data-driven objective.

### 4.3 Make machine-readable artifacts the sole authority

Prose could become explanatory only. That supports code generation, but present JSON artifacts do
not naturally express semantic meaning, actor obligations, processing algorithms, error behavior,
or all physical-profile requirements. Encoding those subjects as annotations would hide semantics
rather than eliminate prose authority.

### 4.4 Give one representation blanket precedence

A prose-wins or data-wins rule gives a deterministic answer after a disagreement is published, but
it permits a known inconsistent bundle to call itself valid. It also ignores the reason for
publishing several forms: each can be stronger for a different subject.

### 4.5 Establish authority by concern before publication design

This is the preferred option. Part 00 would define roles, owners, abstractions, and candidate
status; the README would become informational; and later proposals would reconcile and incorporate
machine-readable contracts before an immutable publication binds them. The cost is that the
current authoritative specification remains an explicitly mutable and, in places, inconsistent
candidate through several revisions. The benefit is that final publication cannot freeze known
contradictions merely to complete the authority work.

## 5. Impact sketch

| surface | disposition |
|---|---|
| semantic prose | **Unchanged except citations or status projection.** Part 01 would retain its current content; unit identity is P2 work. |
| architecture | **Affected.** Part 00 would become the complete specification framework, own part status and the normative bibliography, distinguish abstraction levels from packet content classes, and receive the README's cross-cutting rules. Known placement defects would remain in a separate non-authoritative inventory until their owning work resolves them. |
| logical prose | **Affected without changing behavior.** Part 02 would receive the README's registry embedding, compatibility, version-semantics, and version-hold statements. Its existing incorporation of the core registry would remain; its meta-schema and rule-language gaps are deferred. |
| registry meta-schema | **Unchanged.** Structural and semantic registry conformance is a later proposal. |
| core and extension registries | **Unchanged.** No declarations, rule text, versions, or identifiers would change. |
| declarative rules | **Unchanged.** Their execution language is deferred rather than implicitly settled. |
| physical profiles | **Affected without changing behavior.** Part 03 would own any profile-identifier statement now unique to the README and would update terminology citations or status projection. No storage binding or capability would change. |
| packet catalog and packet schemas | **Prose affected without changing behavior.** Part 04 would own the README's obligations to record applicable identifiers. Resource classification, requiredness, registry binding, schema incorporation, and packet schemas are deferred. |
| validation and import | **Prose affected without changing behavior.** Part 05 would receive any validation/import consequence stated only by the README. Its procedures and packet verdicts would not change. |
| analysis and extensions | **Extension prose affected without changing behavior.** Part 09 would receive extension-independence and extension-behavior statements now unique to the README. Part 06 content rules remain for later reconciliation. |
| reader, writer, validator, adapters, and code generation | **Unchanged.** No packet behavior or source obligation is introduced. |
| release manifest and tooling | **Unchanged.** The tracked prototype remains non-authoritative pending the final publication proposal. |
| existing packets and migration | **No shape change.** No packet bytes need regeneration or migration. The revision changes how conflicting specification statements are classified but does not select new packet behavior. |
| packet conformance fixtures | **Unchanged.** The framework creates no new malformed-packet case. |
| framework checks | **Affected.** A focused check and positive and negative tests would cover Part 00 ownership, local status projections, normative-reference placement, README normative keywords, and combined-document generation. A reviewed inventory would cover semantic relocation from the README. |
| generated publications | **Affected.** The README and combined specification would reflect the new location of the framework without becoming independent owners. |
| developer documentation | **Affected.** Root authority summaries and contribution guidance would point to Part 00 and describe current candidate status. |
| release and packet versions | **Unchanged.** Final identifiers and immutable release identity are deferred. |

## 6. Resolved direction and deferred work

### 6.1 Preferred direction

The intended draft would use the authority-by-concern model in §3, make Part 00 the framework, make
the specification README informational by relocating each binding statement, name the two
architectural axes distinctly, make Part 00 the owner of part status, and define authority and
candidate/release state as independent properties. It would also move the complete normative
bibliography to Part 00 while leaving requirements that rely on those references with their
subject-owning parts. It would not introduce a release manifest or broaden the set of incorporated
machine-readable authorities.

### 6.2 Compatibility and migration

The change would alter how the specification describes its own authority and how a reader
classifies a contradiction. It would preserve the intended packet contract, packet shape, registry
declarations, validator results, and implementation APIs; it would not use P1 to select among the
substantive packet disagreements deferred in §3.6. It would require document regeneration and
citation review, not packet migration.

### 6.3 Dependency order

The revision-process foundation is complete, so this proposal has no unresolved normative
predecessor. It is the prerequisite for the subsequent placement, executable-rule, registry,
resource/profile, manifest, validity, recipe/adapter, reconciliation, identifier, and publication
proposals. Exact ordering and finding coverage are maintained outside this lifecycle artifact in
the proposal coordination record. The separate
[placement-defect inventory](../PLACEMENT-DEFECTS.md) records the observed misplaced and duplicate
statements without making either Part 00 or the roadmap a live defect list.

The narrowed impact query over Part 00 §§1, 2, 2.1–2.3, 2.8, 3, 9, and 10 found 32 citations to
read across nine sections at this appraisal. Incorporation would rerun that query against its then
current baseline and separately account for every README paragraph. R93 §3.6 is superseded only for
its local-header precedence sentence; R111's actor decisions and R112–R113's citation decisions
remain in force.

### 6.4 Deferred subjects

Unit identity and misplaced lower-level statements are the first follow-up because their intended
owners are already apparent. Rule-language semantics precede registry meta-schema incorporation.
Registry conformance precedes the resource/profile model; that model precedes the packet manifest,
validity, and recipe work. Final identifiers, declarative registry-source cleanup, and immutable
publication follow reconciliation of all packet-contract blockers.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [x] The exact proposal and its final appraisal state are tracked in the current commit.
- [x] The proposal has explicit approval to advance to a revision draft.
