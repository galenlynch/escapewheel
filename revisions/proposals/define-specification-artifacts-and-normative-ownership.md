# Define specification artifacts and normative ownership

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-17 |
| **Based on** | `a201ef8344844bee0116c84c587c6776c30b268a` |
| **Affects** | Specification README; Part 00; Part 01 §3.13; Part 02 §§1, 9–12; Parts 03–05 and Part 09; registry and packet schemas; extension registries; specification publication and generation |

## 1. Problem

The generated v0.2 specification is the current authority, but its publication structure does not
make the boundaries of that authority easy to determine. Several different questions are presently
collapsed into one:

- which files form a versioned specification release;
- which artifact owns a particular kind of fact;
- whether an artifact is normative or informative;
- whether it is an authoring source or a generated result; and
- whether it is prose, declarative data, executable logic, or implementation code.

The specification README currently supplies scope, conformance, normative-language, organization,
and version clauses. `combine.py` consequently prepends it to the numbered parts. That gives a file
normally read as publication guidance the role of an unnumbered normative preamble. Part 00 then
repeats the part-status and actor models while also mixing architecture with exact logical facts,
reader behavior, measured performance, and implementation description.

The machine-readable side has the same ambiguity. Part 02 §1 expressly makes
`registry/logical_schemas.json` normative for current declarations, but the status of
`registry/registry.schema.json` and the packet-related JSON Schemas is less explicit. The prose,
meta-schema, registry, generated tables, validation predicates, and implementations can therefore
appear to compete as alternative versions of one contract.

The word *layer* also names two different axes. Part 00 §§2.1–2.3 describe semantic, logical, and
physical abstraction levels. Part 00 §3 calls core, extensions, analysis, and the deferred NWB
projection layers. These classifications are useful, but they are orthogonal: a core declaration
can have semantic, logical, and physical aspects, while an extension can use the same three
abstraction levels. Treating both as one hierarchy obscures which part is allowed to state which
kind of rule.

Unit identity exposes the practical consequence. R81 §2.1 and Part 02 §12.1 establish a
packet-assigned, packet-unique `unit_id`; the registry gives `core.units` the primary key
`["unit_id"]`. Part 00 §4.3 and Part 01 §3.13 retain the superseded composite identity. This is not
an unsettled identity design. It is a placement and ownership defect: logical key structure was
stated at the architectural and semantic levels, then survived after its logical owner changed.

Without an explicit publication and ownership model, an independent implementer cannot always
answer which artifact to follow, and a maintainer cannot reliably tell whether a disagreement is a
precedence case, a stale rendering, or a release-blocking defect.

## 2. Evidence

### 2.1 Current repository

The following observations are against the generated v0.2 material at commit
`a201ef8344844bee0116c84c587c6776c30b268a`:

- The specification README contains the only top-level conformance and normative-language
  clauses. `combine.py` says that README is first because it carries the conformance clauses and
  version identifiers.
- The README and Part 00 §9 both classify parts. They already disagree in presentation: the README
  says there are eleven parts but its table ends at Part 09, while Part 00 also lists Part 10 and
  records the section-level exceptions in Part 06.
- Part 00 §1 says that Part 00 defines no schema or file format. The same part later fixes a unit's
  key, reports exact table counts, prescribes reader behavior, gives a measured join cost, and
  describes the first implementation.
- Part 02 §1 distinguishes rules for registries from current declarations and explicitly calls
  `registry/logical_schemas.json` normative. It also calls `registry/tables.md` a generated
  human-readable listing. This is already a partial authority-by-concern model.
- R2 §9, R2 §10, and R2 §11 intended a published meta-schema, a manifest JSON Schema, and a single
  machine-readable registry statement. The current Part 02 does not clearly incorporate every
  corresponding repository schema into the released normative set.
- The current registry build reconstructs present declarations by replaying Python associated with
  the revision history. That preserves provenance, but makes historical mutation code part of the
  practical authoring path for current declarative state.
- R81 §2 and Part 02 §12.1 agree on unit identity, as does the current registry. The conflicting
  text is confined to higher abstraction levels that do not own a logical primary key.

No other proposal or draft was open at appraisal. An explicit reverse-citation query over Part 00
§4.3, Part 01 §3.13, and Part 02 §12.1 found the two stale higher-level statements cited only by
this proposal. The writer and its sorter tests cite Part 02 §12.1 and already implement the
packet-assigned single-column identity. The placement repair therefore has downstream prose to
remove but no competing implementation behavior to migrate.

These observations show more than duplicated prose. They show that the specification has no single
machine-checkable inventory of its released artifacts, their roles, and the subjects each owns.

### 2.2 Established publication patterns

Several mature specifications separate prose semantics from exact machine-readable assignments
without giving either blanket precedence:

- [JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core) distinguishes a
  vocabulary, which defines keyword syntax and semantics, from a meta-schema, which declares
  vocabularies and validates schema syntax. A meta-schema is not a substitute for the prose
  semantics of those keywords.
- [Unicode Standard Annex #44](https://www.unicode.org/reports/tr44/) treats the Unicode Character
  Database as an integral part of the standard. Algorithm specifications define how properties
  mean and behave; published data files carry exact property assignments.
- [IANA's protocol-registration guidance](https://www.iana.org/help/protocol-registration)
  separates the specification of a registry's fields and allocation procedure from the registry's
  exact assignments and references.
- [Apache Arrow's columnar format](https://arrow.apache.org/docs/format/Columnar.html) publishes
  machine-readable schema definitions alongside prose and identifies generated tables as a
  convenience rather than a second definition.
- The [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html)
  makes normative status the default and marks informative text, examples, and notes explicitly.

The useful common pattern is a versioned normative bundle with authority divided by concern. It is
not “prose always wins” or “the machine-readable file always wins.” A disagreement between two
artifacts that were assigned different concerns is a defect to repair before publication, not a
precedence mechanism to invoke afterward.

## 3. Desired outcome and constraints

### 3.1 A versioned, role-partitioned specification bundle

The preferred model is a release whose manifest identifies every included artifact, its role, its
version or stable identifier, and its digest. Part 00 would define what those roles mean. The
release manifest would record which concrete files fill them for one release.

Authority would be assigned by concern:

| artifact class | subject it would own |
|---|---|
| numbered prose | terms, meanings, processing semantics, actor obligations, conformance, and relationships that cannot be expressed faithfully as structural data |
| registry meta-schema | the valid JSON structure of a registry document |
| core registry | the exact current resource, table, column, key, reference, vocabulary, and declared-rule entries in core |
| extension registry | the same exact declarations within its own namespace, when a packet invokes that extension |
| incorporated packet schemas | the exact JSON structure of manifests and other contract documents they cover |
| incorporated declarative rules | the exact predicate and severity of checks whose execution semantics the prose defines |
| specification release manifest | release identity, membership, artifact roles, versions, and digests |
| revisions | historical decision, evidence, rejected alternatives, and provenance; not the current packet contract |
| implementations, generators, adapters, and code generators | no independent normative subject |

This division would not turn every repository JSON file into an authority. A schema or registry
would become part of the normative bundle only after it had been reconciled with the prose and
listed in a release manifest with a defined role. Until then, its current status would remain
explicit rather than inferred from its file extension or location.

Each fact would have one owner. Cross-artifact checks could repeat a fact only as a verifiable
projection or consistency condition. There would be no general prose-wins or JSON-wins rule. Two
owning artifacts that conflict, an owning artifact that fails its meta-schema, or a generated view
that does not reproduce its owner would make the candidate release invalid.

“Generated” would remain independent of “normative.” A generated artifact could be normative for
an assigned concern if the release manifest says so. Conversely, a generated Markdown table could
remain an informative view of a normative registry. The combined specification could reproduce
normative clauses without becoming a second, independently editable owner. Generation would
neither add nor remove normativity.

### 3.2 Part 00 as the specification framework

Part 00 would become the formal specification framework and architectural map. Its subject would
include:

- the identity and composition of an Escapewheel specification release;
- conformance targets and normative-language conventions;
- the artifact roles and authority-by-concern rule;
- informative and normative status markers;
- the semantic, logical, and physical abstraction levels and their dependency direction;
- the separate content classification of core, extensions, analysis products, and projections;
- actors and the terms that resolve to them;
- the subject owned by each numbered part and the allowed dependencies between parts; and
- stable citation and publication conventions.

The semantic/logical/physical levels would be named as abstraction levels. Core, extension,
analysis, and projection would be named as content classes or namespaces rather than as a second
use of the same layer hierarchy. Part 00 would explain how the two axes intersect.

Exact resource counts, current keys, individual table declarations, profile-specific storage
rules, performance measurements, and implementation plans would move to the artifact or part that
owns them. Part 00 could point to those owners without repeating their facts.

Normative prose would be the default within a normative part. A clearly marked informative
section, example, note, or appendix would be the exception. Every standalone part would carry a
standardized status declaration at its head, and publication checks would compare those
declarations with the release manifest. Mixed-status material such as Part 06 would receive
explicit section markers or be separated so that its status is locally decidable.

### 3.3 An informational specification README

The specification README would become an informational entry point. It could give navigation,
release status, a short architectural summary, build instructions, and links to the owning
artifacts. Its release inventory and status table could be rendered from the release manifest.

The README would carry no unique conformance rule. Its current conformance, normative-language,
artifact-authority, and versioning clauses would move to Part 00 or to the release manifest as
appropriate. A summary in the README could remain useful, provided it is identified as a summary
and links to the owner.

### 3.4 A data-driven registry model

The registry system would follow the same separation JSON Schema makes between vocabulary,
meta-schema, and instance:

- Part 02 defines the meanings and processing semantics of registry fields.
- `registry/registry.schema.json` defines the permitted structure of registry documents.
- `registry/logical_schemas.json` contains the exact core declarations for a release.
- extension registries are instances of the same contract, restricted to their declared
  namespaces and unable to redefine core.
- readers, writers, validators, code generators, and adapters consume those declarations rather
  than reproducing them in program logic.

After the current v0.2 state has been reconciled and frozen as a baseline, the present registry
would be maintained as declarative state: either one reviewed JSON document or reviewed fragments
compiled deterministically into one document. A declaration's `since` field would retain the
accepted revision that introduced or last changed it. Accepted revisions would remain decision
records rather than executable migrations that have to be replayed to discover the current
contract.

The generator would validate, assemble, and render declarations; it would not decide their
meaning. A migration to this authoring model would first prove that it emits the same normative
registry bytes or the same defined canonical form as the reconciled baseline.

### 3.5 Packets, extensions, and adapters

A packet's embedded core registry would be a copy of an identified released contract, not a place
for the packet to redefine core. The long-term packet contract would identify that registry by a
stable identifier, version, and digest; an embedded copy would match the identified released
artifact. Extension registries would be identified separately, carry their own digests, and remain
confined to their namespaces.

The release-manifest model and the packet-manifest model are distinct. A specification release
manifest says which artifacts constitute the standard. A packet manifest says which released
contract and extensions a dataset was built against and where that packet's resources live.

Adapters would remain non-normative ingestion components. They translate particular source files
into resources declared by the selected registry; they do not define tables or relax registry
rules. This preserves the intended data flow:

```text
specification prose + meta-schema + released registries
                         |
                         v
                 data-driven contract
                         |
source files -> adapter -> writer -> validated packet
                                      |
                                      v
                              reader / consumer
```

Lab- and task-specific facts enter through extension registries. Lab- and task-specific source
formats enter through adapters. Keeping those mechanisms separate prevents an adapter's source
assumptions from becoming an implicit extension to the packet contract.

### 3.6 Unit identity is a placement correction

The authority work would not reopen unit identity. Part 02 §12.1 and the exact registry declaration
would remain the owners of the R81 design: `unit_id` is assigned by the packet, is packet-unique,
and is the sole primary-key column of `core.units`.

Part 00 §4.3 would lose the duplicate logical-key statement. Part 01 §3.13 would retain the
semantic facts that a unit is a sorted or curated spiking entity belonging to one sorting run and
one curation version, without prescribing its row key. This is intended to change placement and
consistency, not packet bytes or behavior.

### 3.7 Change and publication discipline

A change to the normative contract would update all owners and projections in one reviewable
unit: relevant prose, incorporated registry or schema declarations, declarative rules, generated
views, conformance fixtures, and the candidate release manifest. Publication checks would reject
drift between them.

The revision process would remain limited to changes in conformance or normative interpretation.
README navigation, generator refactoring, declarative-file organization, and other
meaning-preserving maintenance could use the ordinary repository workflow. If one of those changes
altered an artifact's normative role or packet contract, that decision would return to the
revision process.

The initial authority revision should preserve the current v0.2 packet contract except for
resolving contradictory placement. Adding packet registry-digest fields, declaring currently
unreconciled JSON Schemas normative, and changing registry authoring machinery are separable
follow-up changes rather than hidden consequences of reorganizing Part 00.

## 4. Options and tradeoffs

### 4.1 Prose is the sole authority

Under this option, every machine-readable artifact is an implementation aid and prose wins every
conflict. It is simple to describe, but it makes exact keys, column types, references, and
vocabularies duplicated prose or non-normative implementation detail. It also weakens the stated
data-driven design: independent tools cannot derive the complete contract from the registry.

### 4.2 Machine-readable artifacts are the sole authority

Under this option, prose explains machine-readable contracts but never binds. It supports code
generation, but JSON Schema and registry data do not naturally express semantic meaning,
cross-resource algorithms, actor obligations, error handling, or all physical-profile rules.
Encoding those subjects as annotations would make prose semantics implicit rather than eliminate
them.

### 4.3 One format has blanket precedence

A prose-wins or data-wins rule gives a deterministic answer after publication, but it permits a
known inconsistent bundle to call itself a release. Consumers written against different surfaces
can still diverge before anyone notices the conflict. Blanket precedence also ignores the reason
for publishing multiple forms: each is stronger for a different subject.

### 4.4 A role-partitioned normative bundle

This is the preferred option. It follows the JSON Schema, Unicode, IANA, and Arrow pattern: prose
defines meaning and procedure; machine-readable artifacts carry exact structures and assignments;
a release index binds the set. Its cost is stronger publication tooling and a one-time
reconciliation of artifacts. Its benefit is that both people and programs can find an exact owner,
and conflict becomes a testable release failure rather than an interpretive rule.

### 4.5 Registry state reconstructed from revisions

Keeping the current replay model makes every historical mutation reproducible and centralizes
application order. Its cost grows with the revision history, retains obsolete intermediate states
in the main authoring path, and asks executable code to stand between reviewers and current
declarations.

### 4.6 Direct declarative state, whole or compiled from fragments

Maintaining the released state directly is preferred after the baseline is frozen. One document is
easy to identify and hash but can become unwieldy. Validated fragments are easier to review and
delegate, but introduce an assembly order and compiler that need deterministic rules. Either form
can preserve revision provenance in data and produce one canonical release artifact; choosing
between them is a repository-maintenance decision unless it changes the published registry form.

## 5. Impact sketch

| area | likely effect |
|---|---|
| semantic standard | Part 01 would keep concept meanings and lose logical key declarations, beginning with the stale composite unit identity in Part 01 §3.13. |
| architecture | Part 00 would become the normative framework, distinguish the two classification axes, and shed lower-level facts. |
| logical resources | Part 02 would define registry vocabulary semantics and clearly incorporate the reconciled meta-schema and core registry by role. |
| physical profiles | Part 03 would continue to own storage bindings and would refer to logical resources without redefining them. |
| packet catalog | Part 04 would eventually identify released core and extension registries precisely; new digest fields, if any, need a separate packet-contract decision. |
| validation and import | Part 05 would define validation stages and failure behavior while generated checks consume the registry. Publication validation would be separate from packet validation. |
| reference APIs | APIs would consume the released contract but remain non-normative. Generated bindings would inherit declarations, not authority. |
| registries | Core and extension declarations would become directly reviewable release artifacts validated by one incorporated meta-schema. Historical `since` provenance would remain. |
| extensions | Part 09 would define namespace and extension semantics; each invoked extension registry would own its exact declarations without redefining core. |
| adapters | No immediate behavior change. Their declared products would be checked against registries rather than becoming schema by convention. |
| existing packets | The framework and unit-placement correction would not change packet bytes. Later registry digest or release-identifier fields could require regeneration and need their own decision. |
| conformance fixtures | New publication fixtures would exercise missing artifacts, bad digests, invalid registry instances, stale generated views, and contradictory role declarations. Existing packet fixtures would remain unchanged for the first revision. |
| documentation | The specification README would become informational; developer-facing build guidance would remain outside the normative bundle. The combined rendering would identify its source release and preserve local status markers. |

## 6. Open questions

### 6.1 Boundary of the first revision draft

The recommended first draft covers the framework in Part 00, the informational README boundary,
standard status declarations, a machine-readable specification release manifest, the two
classification axes, and the unit-identity placement repair. It would identify the artifact roles
without silently declaring every existing JSON Schema reconciled and normative.

An alternative is to reconcile all registry and packet schemas in the same revision. That would
produce a complete first bundle sooner, but combines the architectural decision with several
independent schema audits and makes the authority change harder to review.

### 6.2 Initial incorporated machine-readable artifacts

`registry/logical_schemas.json` already has an explicit normative status. The registry meta-schema
is the natural next incorporated artifact, but its current agreement with every registry feature
needs verification. The manifest, resource, source, and adapter schemas should each be classified
only after comparing them with their owning prose and fixtures.

The draft needs a precise transitional rule: either the first release manifest lists only the
already reconciled artifacts, or the authority revision waits until a defined larger set has been
reconciled. The former is the recommended staged path.

### 6.3 Release-manifest authoring

The release manifest is naturally JSON because it is the machine-readable inventory of a
data-driven standard. The remaining design choice is whether maintainers edit its artifact roles
and paths directly and release tooling fills digests, or maintain a smaller source document from
which the complete manifest is generated. In either case the published manifest, not the program
that assembled it, would own release membership.

The format also needs to avoid a self-digest cycle and distinguish working-tree validation from a
frozen release. These are publication-format details to settle before the revision draft states an
exact artifact.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The user has agreed that the work should advance to a revision draft.
