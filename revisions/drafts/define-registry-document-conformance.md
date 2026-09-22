# A Registry Document Has One Complete Conformance Contract

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `35ee9bca2e532dd7d65aa95d734077ec535bdcda` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 sections 2–4, 7–10, and a new section 13; Part 09 sections 5.1, 5.2, and 6.1; `registry/registry.schema.json`; `registry/logical_schemas.json`; the four shipped extension registries; new registry-contract schema and descriptor artifacts |
| **Depends on** | R121 §§3.1–3.2; R122 §§3.2–3.3 and 3.6; R124 §§3.1–3.3; R125 §§3.1–3.8 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8; §3.9; §3.10 |

Section 3 is normative. Sections 1–2 and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision defines one complete, language-neutral conformance contract for core and extension
registry documents. It assigns local JSON shape to an incorporated registry meta-schema,
cross-declaration meaning to named prose invariants indexed by a small incorporated descriptor,
and exact declarations to incorporated registries. It also defines ordered validation phases and
the four possible document results.

This revision replaces incompatible or incomplete rules now spread across Part 02, Part 09, the
meta-schema, a shared Python checker, and repository-only checks. It does not decide where public
writer, validator, reader, or extension-author entry points invoke the result; roadmap P4.2 owns
that separate boundary decision.

This is a structural revision. The affected requirements already occur in the sections that own
tables, columns, references, semantics, and registry documents. Appending a second conformance
model would preserve contradictory rules, especially the direct-session-reference rule and the
current self-description fields. Incorporation therefore replaces rules in place and adds a
registry-conformance subsection and a subject-local normative reference.

### 1.1 Structural crosswalk

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02, “Table resource requirements” | revise in place | same section | makes the object member name the resource identifier and permits only the declared key forms | §§3.4, 3.6 |
| Part 02, “Column declaration” | revise in place | same section | makes local role-dependent fields schema constraints and prevents descriptions from overriding declarations | §§3.4, 3.8 |
| Part 02, “Naming” | replace in place | same section | retains declaration-backed naming as conformance and moves layout and prose heuristics to authoring guidance | §3.8 |
| Part 02, “References” | revise in place | same section | requires complete target keys, compatible pairs, and resolvable nonempty sides | §3.6 |
| [Part 02 §7.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-session-scope), direct `session_id` reference | replace in place | same anchor | permits a proven chain of session-preserving references without weakening row integrity | §3.7 |
| Part 02, “Identity” | revise in place | same section | states the assigned-name and carried/referenced-name invariant | §§3.5–3.6 |
| Part 02, “Discriminator” | split static declaration checks from row checks | same section and registry-conformance subsection | registry conformance proves that resolution is derivable; packet validation retains target-specific row obligations | §§3.5–3.6 |
| Part 02, “Unit and clock” | revise in place | same section and new normative-reference section | separates local source resolution from exact offline UCUM syntax | §§3.5, 3.9 |
| Part 02, “Functional dependence” and “Free-form metadata” | revise in place | same sections | states cross-declaration resolution and metadata eligibility invariants | §§3.5–3.6 |
| [Part 02 §9.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document), one registry shape | replace in place | same anchor | defines common root fields and disjoint core and extension classes | §§3.1–3.2 |
| [Part 02 §9.2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-self-description), current IDs and unknown-schema behavior | replace in place | same anchor | selects a local schema and contract without dereferencing and advances incompatible development versions | §§3.2–3.3, 3.10 |
| Part 02, “Vocabularies” | revise in place | same section | assigns local vocabulary combinations to shape and authority URI syntax to semantics | §§3.4–3.6 |
| no complete registry-conformance subsection | add | planned Part 02 section 9.4, `ew-registry-conformance` | owns artifacts, phases, results, and named semantic invariant algorithms | §§3.1–3.9 |
| Part 02, “Tier 2: declared” | revise in place | same section | adds rule identity, ownership, required-input, and phase integration requirements | §§3.5–3.6 |
| no Part 02 normative-reference section | add | planned Part 02 section 13, `ew-logical-schema-normative-references` | identifies UCUM 2.2 case-sensitive syntax locally | §3.9 |
| Part 09, “What an extension is” and “Namespacing” | revise in place | same sections | makes extension class, namespace ownership, and required core context exact | §§3.2–3.3 |
| Part 09, “Core does not reference an extension” | revise in place | same section | completes core and extension reference-direction restrictions | §§3.2, 3.5 |
| current meta-schema, core registry, and four extension registries | replace incompatible development identities and roots | same artifacts under the incorporated Part 02 contract | makes shape, selectors, and exact declarations agree | §§3.1–3.4, 3.10 |
| no machine-readable registry-contract index | add | `registry/registry_contract.schema.json` and `registry/registry_contracts/escapewheel-registry-contract-v0.1.json` | gives phases and prose invariants stable exact identities without duplicating algorithms | §§3.1, 3.5 |

The affected existing headings for Part 02 sections 2–4, 7, 8.2–8.6, 9.3, and 10.2 and Part 09
sections 5.1, 5.2, and 6.1 do not yet have canonical anchors. Before the final appraisal, the
structural procedure requires a separate metadata-only bootstrap commit adding an anchor to each.
The two new headings receive anchors during incorporation. After that bootstrap, this draft's
baseline, crosswalk links, measurements, and citation inventory must be refreshed.

## 2. Background

### 2.1 Current disagreement

At the baseline, the generated registry has 43 core and analysis tables, and four shipped
extension registries add 11 tables. The five documents carry 121 Tier 2 rules and 128 references.
All rule IDs are unique and begin with their owning resource ID; all references target a complete
declared primary key. Those valid declarations nevertheless sit behind three different partial
contracts:

1. `registry/registry.schema.json` checks JSON shape and some local conditional fields.
2. `escapewheel_validator.registry_document` performs 35 shared procedural checks.
3. `registry/check.py` adds 46 repository checks, including logical invariants absent from the
   shared checker and authoring conventions that are not conformance requirements.

Schema and shared-check probes accepted duplicate columns, duplicate rule IDs, identity on a
non-identifier, a discriminator without `resolves`, a missing root `$schema`, extension-only
fields on core, an arbitrary logical-standard value, and a rule naming an absent relation. The
shared checker rejected `primary_key: null`, which Part 02 expressly permits, and raised
`KeyError` after some shape defects instead of returning a conformance result.

The core document carries full semantic- and logical-standard identifiers. Each extension instead
carries the short value `0.1` in `logical_standard_version` and repeats the full value in
`extends`. The current meta-schema accepts both claims. The class of the document and which claim
matters consequently depend on caller context rather than on one document contract.

### 2.2 Public-boundary evidence and split from P4.2

Direct `PacketWriter` construction accepted a core or extension registry with duplicate column
declarations. Validation of an otherwise valid generated packet also passed when the supplied core
or embedded extension registry contained a duplicate rule ID. These are invocation defects, but
they demonstrate why every caller needs one result rather than selecting an ad hoc subset of
checks.

This revision defines that result. P4.2 will require it at trust boundaries and decide whether a
particular API returns, reports, or raises it. P7 will decide packet-level composition, missing
declared registries, extension table-byte checks, and partial reader access.

### 2.3 Selected architecture

The selected architecture has complementary owners:

- Part 02 and Part 09 define field meanings and language-neutral algorithms.
- An incorporated JSON Schema defines exact local shape.
- A small incorporated descriptor assigns exact contract IDs, ordered phases, invariant IDs,
  applicability classes, and owning prose anchors.
- Incorporated core and extension registries carry exact declarations.
- Informative positive and negative vectors establish implementation agreement.

This follows the hybrid already selected for the Tier 2 language. It avoids putting algorithms or
messages into JSON, but does not leave the invariant inventory hidden in one Python module.

### 2.4 Feasibility measurements

All 61 current literal-unit declarations, comprising 16 distinct expressions, parse under a
case-sensitive UCUM 2.2 grammar. All four current indirectly session-scoped extension tables have
a session-preserving path:

- `aind_opto.emissions` through `aind_opto.stimulations`;
- `dynamic_foraging.trials` through `core.intervals`;
- `vr_foraging.sites` through `core.intervals`; and
- `vr_foraging.site_odors` through `vr_foraging.sites` and `core.intervals`.

The nullable `dynamic_foraging.trials` reference through blocks is not itself sufficient, but its
required interval reference is. This distinction is why graph reachability alone is not the
selected session rule.

### 2.5 Alternatives

Keeping the schema plus two Python check layers preserves different public answers and hidden
applicability. Reconciling the prose and schema while retaining code-only semantic identities
could produce correct behavior, but independent implementations and fixture reports would have no
shared invariant index. A larger executable descriptor would duplicate prose algorithms and
create another rule language. The selected small descriptor is the narrowest data-driven form
that makes the contract enumerable without transferring semantic ownership from the specification.

## 3. Decision

### 3.1 Normative owners and incorporated artifacts

Part 02 **MUST** own the meaning and language-neutral algorithm of registry-document conformance.
Part 09 **MUST** own the additional namespace and reference-direction rules that distinguish an
extension. Part 02 **MUST** expressly incorporate these artifacts for the stated extents:

| artifact | incorporated extent |
|---|---|
| `registry/registry.schema.json` | exact local JSON structure and conditional shape constraints |
| `registry/registry_contract.schema.json` | exact structure of a registry-contract descriptor |
| `registry/registry_contracts/escapewheel-registry-contract-v0.1.json` | exact contract selector values, phase order, invariant IDs, applicability, and owning anchors |
| `registry/logical_schemas.json` | exact current core and analysis declarations |
| four registry documents under `registry/extensions/` | exact current declarations of the shipped extension identified by each document |

The registry-contract schema **MUST** have identifier
`https://escapewheel.org/schemas/registry-contract/0.1.0`. The initial descriptor **MUST** have ID
`escapewheel-registry-contract-v0.1`. Its closed object **MUST** contain `$schema`, `id`,
`registry_schema`, `semantic_standard`, `logical_standard`, `rule_languages`, `phases`, and
`invariants`. Each invariant entry **MUST** contain its stable ID, phase, applicable document
classes, and owning canonical specification anchors.

The descriptor **MUST NOT** contain an algorithm, executable expression, message, exception list,
or implementation selector. Prose remains the semantic owner. Conformance vectors **MUST** be
informative evidence and **MUST NOT** become a third owner.

### 3.2 Registry-document classes and selectors

Every registry document **MUST** carry `$schema`, `registry_version`,
`logical_standard_version`, `rule_language`, and `tables`. A core document **MUST** carry
`semantic_standard_version` and **MUST NOT** carry `extension_id` or `extends`. An extension
document **MUST** carry `extension_id` and **MUST NOT** carry `semantic_standard_version` or
`extends`. The presence of `extension_id` **MUST** determine the document class; caller context
**MUST NOT** redefine it.

The core document **MUST** own only the `core` and `analysis` table namespaces. An extension
document **MUST** own only the namespace equal to its `extension_id`; that identifier **MUST NOT**
be `core`, `analysis`, or `nwb`. A core registry reference **MUST** target the core document. An
extension registry reference **MUST** target either the conforming core context selected by its
full `logical_standard_version` or the same extension document, and **MUST NOT** target another
extension.

The meta-schema **MUST** check identifier syntax and the fields required for each class, but
**MUST NOT** hard-code the current contract selector values. The descriptor **MUST** assign the
exact supported registry-schema, semantic-standard, logical-standard, and rule-language IDs. A
checker **MUST** select only local contracts and **MUST NOT** dereference an identifier.

### 3.3 Ordered validation phases and result

A registry checker **MUST** evaluate these phases in order:

1. `json`;
2. `schema_selection`;
3. `shape`;
4. `contract_selection`;
5. `semantic`;
6. `rule_static`; and
7. `external_domain`.

A byte-oriented entry point **MUST** decode UTF-8 JSON and reject every duplicate object member.
A mapping-oriented entry point **MUST** begin after `json` and **MUST NOT** claim that the source
bytes had unique members.

After JSON decoding, the checker **MUST** inspect only root `$schema` to select a local
meta-schema. A missing or non-string `$schema` **MUST** make the document invalid; an unknown
schema ID **MUST** make evaluation unsupported. The selected meta-schema **MUST** validate the
whole shape. Semantic phases **MUST NOT** index into a shape-invalid document.

For a shape-valid document, the selected registry-schema ID **MUST** select one locally held
registry-contract descriptor. A core document's declared semantic, logical, and rule-language IDs
**MUST** match that descriptor. An extension document's declared logical and rule-language IDs
**MUST** match it, and the descriptor's semantic-standard ID **MUST** be supplied by the required
core context. An unknown required contract or selector **MUST** make evaluation unsupported. An
extension semantic evaluation **MUST** receive an already-conforming core registry with the
logical-standard ID it declares. An absent or unusable core context **MUST** make the extension
evaluation incomplete and **MUST NOT**, by itself, make the extension invalid.

Applicable semantic invariants **MUST** run in descriptor order. Tier 2 rules **MUST** then receive
Part 11 static validation under the selected rule language. External lexical domains **MUST** run
last and offline.

The complete result **MUST** be exactly one of `valid`, `invalid`, `unsupported`, or `incomplete`.
It **MUST** identify each finding's phase and stable schema, semantic-invariant, or rule-language
outcome ID. A definitive violation **MUST** dominate an unsupported or incomplete independent
phase; otherwise unsupported **MUST** dominate incomplete, incomplete **MUST** dominate valid, and
only completed passing phases **MUST** produce valid. A dependent phase skipped after an earlier
failure **MUST** be recorded with its reason.

### 3.4 Meta-schema boundary

The registry meta-schema **MUST** use closed root, table, column, reference, authority, and rule
objects. It **MUST** own required members, scalar types, enumerations, identifier syntax, unique
members within a declared key or reference side, and constraints determined from one object and
its local children.

The meta-schema **MUST** express these local conditionals:

- an identifier requires `identity`, and every other role forbids it;
- a discriminator is a string, requires `resolves`, and forbids `vocabulary`;
- every other string requires `vocabulary`, and every non-string forbids vocabulary fields;
- `closed` and `enum` occur together, `reserved_values` occurs only with `open`, and an open
  vocabulary has a nonempty description;
- `unit` and `unit_from` are mutually exclusive, and `clock_from` occurs only on a coordinate;
- `json_string` is optional;
- the declaration-backed name relations in §3.8 hold; and
- an advisory rule is not an error.

A schema finding **MUST** be identified by the selected meta-schema ID and its schema-location JSON
Pointer. A procedural checker **MUST NOT** give a second semantic-invariant identity to a
constraint owned by the meta-schema.

### 3.5 Semantic-invariant inventory

The initial descriptor **MUST** contain exactly these invariant assignments, in this order:

| invariant ID | phase | applies to | owned subject |
|---|---|---|---|
| `registry.namespace.owned` | semantic | core, extension | document-owned table identifiers |
| `registry.namespace.reference_direction` | semantic | core, extension | permitted reference targets |
| `registry.column.name_unique` | semantic | core, extension | local column identity |
| `registry.primary_key.resolves` | semantic | core, extension | key members and requiredness |
| `registry.reference.resolves` | semantic | core, extension | source and target resolution and arity |
| `registry.reference.target_key` | semantic | core, extension | complete ordered non-null target primary key |
| `registry.reference.compatible` | semantic | core, extension | paired type, role, and identity compatibility |
| `registry.session_scope.path` | semantic | core, extension | session-preserving path to `core.sessions` |
| `registry.identity.name` | semantic | core, extension | assigned-name ownership |
| `registry.metadata.eligibility` | semantic | core, extension | standard optional metadata eligibility |
| `registry.determined_by.resolves` | semantic | core, extension | local determinant resolution |
| `registry.discriminator.declaration` | semantic | core, extension | one complete discriminator shape |
| `registry.discriminator.path` | semantic | core, extension | one-hop declared resolution path |
| `registry.context_source.resolves` | semantic | core, extension | unit and clock source resolution |
| `registry.unit.ucum_2_2_cs` | external_domain | core, extension | case-sensitive UCUM 2.2 syntax |
| `registry.authority.uri` | semantic | core, extension | absolute authority URI syntax |
| `registry.rule.id_unique` | semantic | core, extension | document-local rule identity |
| `registry.rule.id_owner` | semantic | core, extension | resource-owned rule ID prefix |
| `registry.rule.required_inputs` | rule_static | core, extension | absence of optional rule inputs |
| `registry.core.device_detail` | semantic | core | extension-reserved device detail |

Each entry's descriptor anchors **MUST** identify every numbered-part clause that defines its
meaning. Part 11 outcomes **MUST** remain separate rule-language outcomes and **MUST** be attached
to the owning rule ID in the registry result.

The target-specific shared-key, paired-value, and by-position checks for a discriminator depend on
packet row values and **MUST** remain packet-validation semantics. Registry conformance **MUST**
establish that a declaration selects exactly one shape and makes its candidate target information
unambiguous; it **MUST NOT** claim that a particular row resolves.

### 3.6 Cross-declaration algorithms

Within each table, column names **MUST** be unique. Within each registry document, rule IDs
**MUST** be unique and each **MUST** begin with the ID of the resource that contains it.

A non-null primary key **MUST** contain unique member names, and each member **MUST** resolve once
to a required column. A null primary key **MUST** remain the declaration that duplicate rows are
admitted and **MUST NOT** serve as a reference target.

Each reference **MUST** contain unique source and target members of equal nonzero arity. Every
member **MUST** resolve. The target side **MUST** equal the target table's complete non-null primary
key in declared order. Each paired column **MUST** have compatible type and role and, when it is an
identifier, compatible identity. A data column paired with a discriminator as the declared shared
key is the sole role-compatibility exception.

A table owning an assigned identifier **MUST** declare exactly one corresponding assigned name,
formed by replacing the identifier's `_id` suffix with `_name`. A table
that merely carries or references that identifier **MUST NOT** acquire a name declaration from
that fact. The standard optional `metadata` column **MUST** occur only in the ownership bands Part
02 identifies. Every `determined_by` name **MUST** resolve to a column of the same table.

A discriminator **MUST** select exactly one declared resolution shape. Every named local column
and one-hop path **MUST** resolve with the presence, type, and role its selected shape requires.
Every `unit_from` and `clock_from` source **MUST** resolve locally or through the declared one-hop
reference; a clock source **MUST** resolve to `core.clocks`. Core **MUST NOT** declare a
device-detail table reserved to an extension.

Each rule **MUST** pass Part 11's static contract. The `registry.rule.required_inputs` outcome
**MUST** be derived from that checked rule's bound base-column references and **MUST** reject any
optional input column.

### 3.7 Session-scope proof

A table **MUST** be session-scoped exactly when it has a session-preserving reference path ending
at `core.sessions`; the zero-edge path makes `core.sessions` itself the base case. Every
session-scoped table **MUST** carry a required `int32` identifier named
`session_id` with assigned identity. A table without such a path **MUST NOT** carry that column.

A declared reference **MUST** be a session-preserving edge only when all of these conditions hold:

1. its source contains `session_id` exactly once and maps it at the same reference position to the
   target's `session_id`;
2. every source column in the reference is required, so a nullable composite member cannot evade
   the foreign-key anti-join;
3. the target is the complete non-null primary key required by §3.6; and
4. every pair passes the ordinary type, role, and identity compatibility checks.

The path **MUST** consist only of such edges and **MUST** terminate at
`core.sessions.session_id`. Graph reachability, a cycle, or a reference that carries some other
identifier **MUST NOT** prove session scope. Packet validation **MUST** enforce the ordinary
foreign-key anti-join at every edge; it need not execute a special recursive row query.

### 3.8 Naming and authoring-style boundary

Registry conformance **MUST** enforce lowercase resource and column syntax and these
declaration-backed relations:

- an identifier has an `_id` name, and an `_id` name declares an integer identifier;
- a coordinate has a `_tick` name, and a `_tick` name declares a coordinate;
- a structural index has an `_index` name, and an `_index` name declares a structural index or
  sequence position;
- an `_name` name declares a string; and
- an `_uri` name, or the bare name `uri`, declares a string.

The registry checker **MUST** determine discriminator behavior from the declaration and
**MUST NOT** infer it from a `_kind` suffix. A source-provenance label **MUST** retain its declared type;
the checker **MUST NOT** treat every `_label` suffix as an independent conformance rule.

Column order, adjacency, reserved-word preferences, plural-name preferences, prose-restatement
heuristics, and document-wide same-spelled-column vocabulary uniformity **MUST NOT** be registry
conformance requirements. Repository authoring checks **MAY** enforce such conventions without
changing the result defined in §3.3. A description **MUST NOT** contradict or override a machine
declaration; concise and non-duplicative wording remains specification style rather than a
machine comparison of English text.

### 3.9 External lexical domains

Part 02 **MUST** identify UCUM 2.2 as the normative authority for literal `unit` values and
**MUST** invoke its case-sensitive syntax. A checker **MUST** validate that syntax offline and
**MUST NOT** contact a network service. A checker without the exact required domain **MUST** report
the external-domain phase as unsupported rather than accept a printable approximation.

The specification **MUST NOT** make a particular parser library normative. Acceptance evidence
**MUST** record which exact UCUM data or parser implementation is distributed, its source edition,
and its license disposition.

An authority URI **MUST** be an absolute RFC 3986 URI. Validation **MUST NOT** dereference it.

### 3.10 Incompatible development-version transition

The revised registry meta-schema `$id` and every registry document `$schema` **MUST** be
`https://escapewheel.org/schemas/registry/0.4.0`. The core registry's `registry_version` **MUST** be
`0.4.0`. The shipped extension versions **MUST** be `0.4.0` for `aind_opto`, `0.3.0` for
`aind_unit_qc`, `0.5.0` for `dynamic_foraging`, and `0.4.0` for `vr_foraging`.

Every extension **MUST** carry the full `escapewheel-logical-v0.1` value in
`logical_standard_version` and **MUST NOT** carry `extends`. The 28 development corpus packets and
other generated fixtures **MUST** be regenerated against the new documents. An old document
**MUST NOT** be silently interpreted under the new meta-schema identifier.

This incompatible intermediate transition **MUST** be the exception to P10's provisional version
hold. It **MUST NOT** assign final release identities or permit later incompatible reuse of these
IDs; P10 retains that final assignment and verification decision.

## 4. What this does not change

- No substrate-independent scientific concept in Part 01 changes.
- No Parquet, Zarr, media, or packet-catalog physical shape changes.
- This revision does not identify an embedded registry by packet digest or decide when embedding
  is required; P6 owns registry binding.
- This revision does not decide how registry results compose with core, extension, or whole-packet
  verdicts; P7 owns that composition.
- This revision does not require a writer, validator, reader, adapter, or public constructor to
  invoke the result at a particular boundary; P4.2 owns those obligations.
- This revision does not replace registry replay with a direct declarative authoring source or
  assign final release membership and identifiers; P10 and P11 retain those decisions.

## 5. Consequence

The change deliberately breaks the unreleased registry-document root shape and development
identities. Core, all shipped extensions, generated fixtures, and the packet corpus must be
regenerated together. Table and column declarations should otherwise remain semantically stable,
except where this revision makes a currently implicit or contradictory invariant exact.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged because registry-document conformance represents existing concepts rather than changing scientific identity. | Part 01 byte comparison. |
| logical prose and registry | Part 02 receives the complete contract, revised local rules, phase model, session proof, local UCUM reference, and incorporated schema/descriptor/registries; core advances to 0.4.0. | Structural crosswalk, anchor and owner checks, normalized declaration comparison, positive and negative contract vectors. |
| physical profiles | Unchanged because no storage encoding or profile capability changes. | Parts 03 and 10 byte comparison apart from generated navigation if any. |
| packet catalog and JSON Schemas | Packet schemas are unchanged; generated packets update embedded or identified registry bytes and versions where present. | Catalog schema byte comparison and regenerated 28-packet corpus. |
| validation and import | Shared registry checking must implement the ordered result without crashing after shape failures; trust-boundary invocation remains P4.2. | Focused phase/outcome and invariant tests; no claim yet that every caller invokes them. |
| extensions | Four registries adopt the disjoint extension shape, full logical ID, new versions, and the same applicable invariants as core. | All extension positive vectors plus focused namespace, context, reference, and session-path negatives. |
| reader, writer, validator, adapters | Common registry-document result and types may be implemented; public invocation behavior remains unchanged until P4.2. Adapters do not acquire schema authority. | Package tests distinguish contract implementation from boundary invocation. |
| conformance fixtures and tests | Add raw JSON, schema-selection, shape, contract-selection, semantic, rule-static, external-domain, and precedence cases; regenerate development fixtures. | At least one positive and focused negative for every invariant and phase outcome. |
| revision process and tooling | No lifecycle meaning changes. A metadata-only anchor bootstrap precedes final appraisal; ledger and evidence later map every clause to its owner. | Stage, citation, repointing, structural, ledger, and evidence checks. |
| generated publications and developer documentation | Regenerate the combined specification, registry tables, counts, READMEs, and author guidance; keep authoring conventions distinct from conformance. | Generation and freshness checks plus documentation search for stale IDs and duplicate owners. |

## 6. Conformance and implementation evidence

The contract corpus must include a valid core document and a valid extension document with a
conforming core context. It must independently cover:

1. duplicate raw JSON members and the mapping-entry limitation;
2. missing, non-string, and unknown `$schema` selectors;
3. every local schema conditional, including `primary_key: null` as a positive case;
4. unknown semantic, logical, registry-contract, and rule-language IDs;
5. missing or unusable core context for an extension;
6. every descriptor invariant with one focused negative and sufficient positive cases;
7. invalid and unsupported Part 11 outcomes attached to rule IDs;
8. accepted and rejected case-sensitive UCUM expressions with no network access;
9. result precedence among independent invalid, unsupported, and incomplete phases; and
10. safe phase skipping after invalid shape.

Descriptor coverage must prove that every entry has a unique stable ID, valid phase, applicable
class, resolvable owning anchors, and a corresponding evidence case. A converse check must prove
that no semantic conformance check is hidden in implementation code without a descriptor entry.
Schema-owned constraints must be absent from the semantic inventory.

Registry migration evidence must compare all 43 core/analysis and 11 extension table declarations,
all 121 rules, and all 128 references before and after the root-shape transition. It must prove
that every reference targets a complete key, that all current rule IDs remain unique and owned,
and that the four indirect session paths satisfy every condition in §3.7. It must parse all 61
literal-unit declarations against the selected exact UCUM 2.2 data.

The same language-neutral checker must return the same result model for all five shipped registry
documents. Focused implementation tests must show that a missing role or another shape defect
returns findings without `KeyError`. P4.2 will later add public-construction, embedded-copy, and
trust-boundary evidence; those tests must not be misreported as complete by this revision.

Incorporation must run the stage, citation, repointing, heading, structural, ledger, and evidence
checks; every package suite affected by the result model; all registry-generation and publication
checks; the complete packet corpus; and the quick and full repository verifier. A known
environment preflight failure must be recorded explicitly rather than treated as a pass.

## 7. Open

P4.2 will decide mandatory invocation points and API behavior. P6 will bind registry identity to
packets. P7 will compose registry, resource, extension, and packet verdicts. P10 will select the
direct registry authoring source and final identifiers, and P11 will define immutable release
membership. Those decisions may consume this contract but cannot weaken or redefine it without a
later revision.
