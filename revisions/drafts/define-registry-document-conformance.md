# A Registry Document Has One Complete Conformance Contract

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `8b22b501cec6d2b76a1f286d84d2c082055f62f6` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 sections 1–4, 7, 8.2–8.6, 9.1–9.4, 10.2, and a new section 13; Part 09 sections 5.1, 5.2, 5.5, 6.1, and 6.2; the specification README sections 2 and 4; `registry/registry.schema.json`; `registry/logical_schemas.json`; new registry-contract schema and descriptor artifacts |
| **Depends on** | R120 §§3.3–3.6; R121 §§3.1–3.2; R122 §§3.2–3.3 and 3.6; R124 §§3.1–3.3; R125 §§3.1–3.8 |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8; §3.9; §3.10 |

Section 3 is normative. Sections 1–2 and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision defines one complete, language-neutral conformance contract for core and extension
registry documents. It assigns local JSON shape to an incorporated registry meta-schema,
cross-declaration meaning to named prose invariants indexed by a small incorporated descriptor,
and exact core and analysis declarations to the incorporated core registry. It also defines
ordered validation phases and the four possible document results.

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
| [Part 02 §1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-core-logical-schema-scope), incorporation paragraph | revise in place | same anchor | incorporates the generic registry contract and core declarations, but no concrete extension registry | §3.1 |
| [Part 02 §2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-table-resource-requirements), “Table resource requirements” | revise in place | same anchor | makes the object member name the resource identifier and permits only the declared key forms | §§3.4, 3.6 |
| [Part 02 §3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-column-declaration), “Column declaration” | revise in place | same anchor | makes local role-dependent fields schema constraints and prevents descriptions from overriding declarations | §§3.4, 3.8 |
| [Part 02 §4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-logical-column-naming), “Naming” | replace in place | same anchor | retains declaration-backed naming as conformance and moves layout and prose heuristics to authoring guidance | §3.8 |
| [Part 02 §7](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-logical-references), “References” | revise in place | same anchor | requires complete target keys, compatible pairs, and resolvable nonempty sides | §3.6 |
| [Part 02 §7.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-session-scope), direct `session_id` reference | replace in place | same anchor | permits a proven chain of session-preserving references without weakening row integrity | §3.7 |
| [Part 02 §8.2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-identifier-semantics), “Identity” | revise in place | same anchor | states the assigned-name and carried/referenced-name invariant | §§3.5–3.6 |
| [Part 02 §8.3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-discriminator-semantics), “Discriminator” | split static declaration checks from row checks | same anchor and registry-conformance subsection | registry conformance proves that resolution is derivable; packet validation retains target-specific row obligations | §§3.5–3.6 |
| [Part 02 §8.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-unit-and-clock-context), “Unit and clock” | revise in place | same anchor and new normative-reference section | separates local source resolution from exact offline UCUM syntax | §§3.5, 3.9 |
| [Part 02 §8.5](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-functional-dependence), “Functional dependence” | revise in place | same anchor | makes determinant resolution and uniqueness exact | §§3.5–3.6 |
| [Part 02 §8.6](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-free-form-metadata), “Free-form metadata” | revise in place | same anchor | states exact standard metadata shape, description, and eligibility | §§3.5–3.6 |
| [Part 02 §9.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document), one registry shape | replace in place | same anchor | defines common root fields and disjoint core and extension classes | §§3.1–3.2 |
| [Part 02 §9.2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-self-description), current IDs and unknown-schema behavior | replace in place | same anchor | selects a local schema and contract without dereferencing and advances incompatible development versions | §§3.2–3.3, 3.10 |
| [Part 02 §9.3](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-vocabularies), “Vocabularies” | revise in place | same anchor | assigns local vocabulary combinations to shape and authority URI syntax to semantics | §§3.4–3.6 |
| no complete registry-conformance subsection | add | planned Part 02 section 9.4, `ew-registry-conformance` | owns artifacts, phases, results, and named semantic invariant algorithms | §§3.1–3.9 |
| [Part 02 §10.2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-tier-2-rules), “Tier 2: declared” | revise in place | same anchor | adds rule identity, ownership, required-input, and phase integration requirements | §§3.5–3.6 |
| no Part 02 normative-reference section | add | planned Part 02 section 13, `ew-logical-schema-normative-references` | identifies UCUM 2.2 case-sensitive syntax locally | §3.9 |
| [Part 09 §5.1](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-definition), “What an extension is” | revise in place | same anchor | makes extension class and required core context exact without naming a concrete extension | §§3.1–3.3 |
| [Part 09 §5.2](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-namespacing), “Namespacing” | revise in place | same anchor | states generic extension namespace ownership without a concrete namespace | §3.2 |
| [Part 09 §5.5](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-versioning), “Independent versioning” | revise in place | same anchor | makes `registry_version` the extension registry's own version, independent of the core registry's version | §§3.1–3.2 |
| [Part 09 §6.1](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-core-extension-reference-direction), “Core does not reference an extension” | revise in place | same anchor | completes core and extension reference-direction restrictions | §§3.1–3.2, 3.5 |
| [Part 09 §6.2](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-core-extension-discrimination), “Core may name an extension” | revise in place | same anchor | retains generic discriminator naming while removing the concrete extension example | §§3.1–3.2, 3.5 |
| specification README, authority summary and `registry_version` projection | revise as informative projections | same sections | points to the generic extension mechanism and labels the projected version as the core registry's | §§3.1–3.2, 3.10 |
| current meta-schema and core registry | replace incompatible development identities and roots | same artifacts under the incorporated Part 02 contract | makes shape, selectors, and exact core declarations agree | §§3.1–3.4, 3.10 |
| no machine-readable registry-contract index | add | `registry/registry_contract.schema.json` and `registry/registry_contracts/escapewheel-registry-contract-v0.1.json` | gives phases and prose invariants stable exact identities without duplicating algorithms | §§3.1, 3.5 |

The metadata-only bootstrap commit `8b22b501cec6d2b76a1f286d84d2c082055f62f6` added canonical
anchors to all 15 affected existing headings that lacked one. The process check confirms that the
commit changed only those anchors. The two new headings receive anchors during incorporation.

The refreshed reverse-impact query covers 20 affected existing sections and reports 378 citation
occurrences at 365 unique lines in 76 files. Of those, 70 occurrences at 64 lines in 16 accepted
records are historical and remain unchanged. The 308 current occurrences at 301 lines in 60 files
were read individually. Most continue to cite retained meanings. Incorporation must update the
stale direct-session checks and comments, printable-ASCII UCUM approximation, old schema and core
version projections, redirecting UCUM URI, concrete Part 09 examples, and implementation comments
whose owner or phase changes; generated tables and the combined rendering are regenerated rather
than edited.

## 2. Background

### 2.1 Current disagreement

At the baseline, the generated core registry has 43 core and analysis tables, and four extension
registries maintained in this repository add 11 tables. The five documents carry 121 Tier 2 rules
and 128 references. All rule IDs are unique and have the exact owning-resource-plus-local-ID form;
all references target a complete declared primary key. Those valid declarations nevertheless sit
behind three different partial contracts:

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
- The incorporated core registry carries the core and analysis declarations. A concrete extension
  registry carries its own declarations and claims the common contract independently; repository
  co-location does not incorporate it into the core specification.
- Informative positive and negative vectors establish implementation agreement.

This follows the hybrid already selected for the Tier 2 language. It avoids putting algorithms or
messages into JSON, but does not leave the invariant inventory hidden in one Python module.

### 2.4 Feasibility measurements

All 61 current literal-unit declarations, comprising 16 distinct expressions, parse under a
case-sensitive UCUM 2.2 grammar. The core registry has nine UCUM authority entries; all use the
redirecting `https://ucum.org/ucum.html` spelling rather than the canonical
`https://ucum.org/ucum` identity. `ucumvert` 0.3.2 exposes an offline parser generated from vendored
UCUM 2.2 essence data dated 2024-06-17. Its code is MIT-licensed; its vendored data identifies the
separate [UCUM Copyright Notice and License](https://ucum.org/license), headed Version 1.1,
June 2024, whose notice must accompany redistribution.

All four current indirectly session-scoped extension tables have a session-preserving path:

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

The core specification **MUST NOT** incorporate a concrete extension registry, list one as a member
of the core specification candidate, or assign its version. Part 09 **MUST** define the class and
the rules by which any extension registry conforms, without naming a particular extension. A
supplied extension registry is the sole declaration source for resources in its namespace,
subject to the packet's registration and binding rules. Repository co-location, conformance
fixtures, and implementation support **MUST NOT** make that registry part of core or a member of
the core specification candidate.

The registry-contract schema **MUST** have identifier
`https://escapewheel.org/schemas/registry-contract/0.1.0`. The initial descriptor **MUST** have ID
`escapewheel-registry-contract-v0.1`. Its closed object **MUST** contain `$schema`, `id`,
`registry_schema`, `semantic_standard`, `logical_standard`, `rule_languages`, `phases`, and
`invariants`. Each closed invariant entry **MUST** contain exactly `id`, `phase`, `classes`, and
`anchors`, carrying its stable ID, phase, applicable document classes, and owning canonical
specification anchors respectively.

The descriptor schema **MUST** close the root and each invariant entry. `$schema` and
`registry_schema` **MUST** be absolute URI strings. `id`, `semantic_standard`,
`logical_standard`, and each `rule_languages` member **MUST** be strings matching
`^[a-z][a-z0-9]*(?:-[a-z0-9]+)*-v[0-9]+(?:\.[0-9]+)*$`.
`rule_languages`, `phases`, `invariants`, every invariant's `classes`, and every invariant's
`anchors` **MUST** be nonempty arrays with no duplicate member. `phases` **MUST** equal, in order,
`json`, `schema_selection`, `shape`, `contract_selection`, `semantic`, `rule_static`, and
`external_domain`. An invariant ID **MUST** consist of at least two dot-separated lowercase
snake-case components; its phase **MUST** occur in `phases`; each class **MUST** be `core` or
`extension`; and each anchor **MUST** be a canonical `ew-` anchor identifier. Invariant IDs
**MUST** be unique across the descriptor, and every anchor **MUST** resolve uniquely in the
numbered specification.

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
checker **MUST** select only local contracts and **MUST NOT** dereference an identifier. An
extension registry's `registry_version` **MUST** identify that extension registry and **MUST**
advance independently of the core registry's `registry_version`.

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

For a shape-valid core document, its class and declared registry-schema, semantic-standard,
logical-standard, and rule-language IDs **MUST** select exactly one locally held registry-contract
descriptor. For a shape-valid extension document, its class and declared registry-schema,
logical-standard, and rule-language IDs, together with the semantic-standard ID of its required
core context, **MUST** select exactly one descriptor. No selector component may be inferred or
ignored. An unknown or ambiguous tuple **MUST** make evaluation unsupported. A new semantic
contract **MUST NOT** reuse a tuple that selected a different contract, and a descriptor's `id`
**MUST NOT** be reinterpreted after publication.

When the core context is absent or unusable, the extension-visible class, registry-schema,
logical-standard, and rule-language components **MUST** still select an unambiguous local
descriptor before extension-local phases run. If none matches, evaluation **MUST** be unsupported;
more than one match **MUST** be ambiguous and unsupported. One match supplies the invariant
inventory, while the unavailable semantic-standard component makes only the core-dependent
evaluation incomplete.

An extension semantic evaluation **MUST** receive a core registry that selected the same contract,
is valid, and declares the logical-standard ID the extension declares. An absent, unsupported,
incomplete, invalid, or mismatched core context **MUST** make every core-dependent extension phase
incomplete and **MUST NOT**, by itself, make the extension invalid. Shape checks and every
extension-local invariant whose inputs remain available **MUST** still run. A resulting independent
invalid finding **MUST** dominate that incomplete state.

Applicable semantic invariants **MUST** run in descriptor order. Tier 2 rules **MUST** then receive
Part 11 static validation under the selected rule language. External lexical domains **MUST** run
last and offline.

The complete result **MUST** contain the selected descriptor ID whenever one descriptor was
selected, including the unique extension-visible selection used with absent core context; one
overall state; and one phase record for every phase in the seven-phase order above, whether or not
a descriptor was selected. Every descriptor **MUST** repeat that order exactly. The overall state
**MUST** be exactly one of `valid`, `invalid`, `unsupported`, or `incomplete`. A phase record
**MUST** identify its phase; have exactly one state from `passed`, `invalid`, `unsupported`,
`incomplete`, and `skipped`; and contain ordered outcome records for every check that did not pass
and every check skipped within a partially evaluated phase. An outcome record **MUST** identify
its state and stable schema, semantic-invariant, or rule-language outcome ID, the owning resource
or rule ID where one applies, and its instance location as an RFC 6901 JSON Pointer. A skipped
outcome or phase **MUST** contain a stable reason ID. A source mapping unable to preserve a byte
location **MUST** still preserve the JSON Pointer; the abstract result does not require a line or
byte offset.

Part 02 **MUST** assign the pre-contract outcome IDs `registry.json.invalid_utf8`,
`registry.json.invalid_syntax`, `registry.json.duplicate_member`,
`registry.schema.selector_missing`, `registry.schema.selector_type`,
`registry.schema.selector_unsupported`, `registry.contract.selector_unsupported`,
`registry.contract.selector_ambiguous`, and `registry.contract.core_context_unusable`. It **MUST**
assign skip-reason IDs `registry.phase.mapping_input`, `registry.phase.prerequisite_invalid`,
`registry.phase.prerequisite_unsupported`, and `registry.phase.prerequisite_incomplete`.
Schema-validation findings **MUST** use the selected meta-schema ID and schema-location pointer as
their stable outcome identity. Semantic and external-domain findings **MUST** use descriptor
invariant IDs, and rule-static findings **MUST** use Part 11 outcome IDs attached to the owning rule.

An outcome **MUST** be a finding exactly when its state is `invalid`; an unsupported, incomplete,
or skipped outcome **MUST NOT** be relabeled as a finding. An outcome before an instance can be
located **MUST** use the empty JSON Pointer for the document root. A duplicate-member outcome
**MUST** locate the containing object, not pretend that one of the duplicate values has a unique
pointer. Within one phase, outcome records **MUST** be ordered by instance pointer, then outcome ID,
then owning resource or rule ID, comparing each code point for code point.

A definitive violation **MUST** dominate an unsupported or incomplete independent phase;
otherwise unsupported **MUST** dominate incomplete, incomplete **MUST** dominate valid, and only
completed passing phases **MUST** produce valid. The same precedence **MUST** determine a partially
evaluated phase's state from its outcome records. A dependent phase skipped after an earlier
failure **MUST** be recorded with its reason. P4.2, not this revision, owns public API, CLI, report,
and exception serialization of this abstract result.

### 3.4 Meta-schema boundary

The registry meta-schema **MUST** use closed root, table, column, reference, authority, and rule
objects. It **MUST** own required members, scalar types, enumerations, identifier syntax, unique
members within a declared key or reference side, and constraints determined from one object and
its local children.

The meta-schema **MUST** express these local conditionals:

- an identifier requires `identity`, and every other role forbids it;
- a coordinate is `int64`;
- a discriminator is a required or nullable string, requires `resolves`, and forbids
  `vocabulary`;
- every other string requires `vocabulary`, and every non-string forbids vocabulary fields;
- `closed` and `enum` occur together, `reserved_values` occurs only with `open`, and an open
  vocabulary has a nonempty description;
- `unit` and `unit_from` are mutually exclusive, and `clock_from` occurs only on a coordinate;
- `json_string` is optional;
- a column named `metadata` has exactly type `json_string`, presence `optional`, and role `data`;
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
| `registry.metadata.eligibility` | semantic | core, extension | standard metadata shape, description, and eligibility |
| `registry.determined_by.resolves` | semantic | core, extension | local determinant resolution |
| `registry.discriminator.declaration` | semantic | core, extension | one complete discriminator shape and matched companion presence |
| `registry.discriminator.path` | semantic | core, extension | one-hop declared resolution path |
| `registry.context_source.resolves` | semantic | core, extension | unambiguous unit and explicit or implicit clock source resolution |
| `registry.unit.ucum_2_2_cs` | external_domain | core, extension | case-sensitive UCUM 2.2 syntax |
| `registry.authority.uri` | semantic | core, extension | authority eligibility, unique absolute URIs, and canonical UCUM identity |
| `registry.rule.id_unique` | semantic | core, extension | document-local rule identity |
| `registry.rule.id_owner` | semantic | core, extension | exact resource-owned rule ID form |
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

Each member name of the root `tables` object **MUST** be the resource ID of its table declaration.
That key, not an inferred filename or a field inside the table object, **MUST** determine the
resource namespace subject to §3.2.

Within each table, column names **MUST** be unique. Within each registry document, rule IDs
**MUST** be unique. A rule held by resource `namespace.table` **MUST** have the exact form
`namespace.table.local_rule_id`, where `local_rule_id` is one lowercase snake-case identifier
containing no dot; a shared prefix alone does not establish ownership.

A non-null primary key **MUST** contain unique member names, and each member **MUST** resolve once
to a required column. A null primary key **MUST** remain the declaration that duplicate rows are
admitted and **MUST NOT** serve as a reference target.

Each reference **MUST** contain unique source and target members of equal nonzero arity. Every
member **MUST** resolve. The target side **MUST** equal the target table's complete non-null primary
key in declared order. Each paired column **MUST** have compatible type and role and, when it is an
identifier, compatible identity. A data column paired with a discriminator as the declared shared
key is the sole role-compatibility exception.

A table owns an assigned identifier exactly when the identifier column is a member of that table's
primary key and is not a source member of any reference the table declares. For each owned assigned
identifier, the table **MUST** declare exactly one corresponding name formed by replacing the
identifier's `_id` suffix with `_name`; that name **MUST** be a string data column and **MUST NOT**
declare `identity`. A table that merely carries or references an assigned identifier **MUST NOT**
declare that corresponding same-base `_name` column.

A declared `metadata` column **MUST** have the exact type, presence, and role stated in §3.4 and
the standard description Part 02 defines. A table **MUST** declare it when the primary key contains
an identifier that is not a source member of a declared reference; it **MUST NOT** declare it when
the non-null primary key is nonempty, every key member is a reference source, and none is such an
owned identifier. Between those bounds the declaration remains permitted. Every `determined_by`
array **MUST** contain no duplicate name, and every member **MUST** resolve to a column of the same
table.

A discriminator **MUST** select exactly one resolution shape: paired value by declaring
`discriminates`, by position by declaring `positions_in`, or shared key by declaring neither. It
**MUST NOT** declare both fields. A field named by `discriminates` or `positions_in` **MUST** resolve
once in the same table to a string data column and **MUST** have the same `required` or `nullable`
presence as the discriminator; neither member of such a pair may be optional. Every
`discriminates_via` value `resource.column` **MUST** resolve to a column in `resource`, and that
resource **MUST** declare exactly one reference in which the named column is a source member and
the table carrying the discriminator is the target. This is a reverse one-hop declaration from
the discriminated rows to the discriminator, not a reference owned by the discriminator's table.
The selected shape's remaining target-specific obligations stay with packet validation as §3.5
requires.

Every `unit_from` and `clock_from` source **MUST** resolve once, either in the same table or through
exactly one declared one-hop reference. A `unit_from` target **MUST** be a string column whose
authority entries include the canonical UCUM identity `https://ucum.org/ucum`. For every coordinate,
the clock source is its explicit `clock_from` target when present and otherwise the same table's
`clock_id`; that source **MUST** be an identifier participating in a declared reference to
`core.clocks.clock_id`. A column carrying `authority` **MUST** be a string data column with an
`open` or `closed` vocabulary; its authority array **MUST** be nonempty and contain no repeated
URI. Every authority URI **MUST** satisfy §3.9.

In a core registry, no table other than `core.devices` **MUST** have a non-null primary key whose
first member is `device_id`. This structural test, rather than a table-name list, identifies the
extension-reserved device-detail shape.

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
conformance requirements. A description **MUST NOT** contradict or override a machine declaration;
concise and non-duplicative wording remains specification style rather than a machine comparison
of English text. The exact standard description required for `metadata` is a literal declaration,
not an instruction to infer semantics from arbitrary prose; no other description is compared for
semantic equivalence. A contradiction in other descriptive prose is an authoring defect that must
be corrected, but it neither overrides the declaration nor changes the registry result.

### 3.9 External lexical domains

Part 02 **MUST** cite [*The Unified Code for Units of Measure*](https://ucum.org/ucum), version 2.2,
revision date 2024-06-17, as an exact normative reference for its case-sensitive unit syntax and
terminal tables. A registry checker **MUST** validate every literal `unit` value against that
grammar offline and **MUST NOT** contact a network service. A checker without the exact required
domain **MUST** report the external-domain phase as unsupported rather than accept a printable
approximation. Registry-document conformance validates only literal declarations; P7 owns
validation of row values in columns selected by `unit_from`.

The specification **MUST NOT** make a particular parser library normative.

An authority URI **MUST** be an absolute RFC 3986 URI. An authority entry named `UCUM` **MUST** use
the canonical identity `https://ucum.org/ucum`, and an entry using that identity **MUST** be named
`UCUM`. Validation **MUST NOT** dereference an authority URI.

### 3.10 Incompatible development-version transition

The revised registry meta-schema `$id` and every registry document `$schema` **MUST** be
`https://escapewheel.org/schemas/registry/0.4.0`. The core registry's `registry_version` **MUST** be
`0.4.0`.

Every extension using the revised meta-schema **MUST** carry the full
`escapewheel-logical-v0.1` value in `logical_standard_version`, **MUST NOT** carry `extends`, and
when migrating a document from an earlier meta-schema **MUST** select a `registry_version`
different from that document's earlier version. A newly published extension selects its initial
version independently. The core specification **MUST NOT** select either version. An old document
**MUST NOT** be silently interpreted under the new meta-schema identifier.

These development identifiers **MUST NOT** be reused later for an incompatible contract. This
revision does not assign final release identities.

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
identities. The core registry, repository-maintained extension examples, generated fixtures, and
the packet corpus must be regenerated together for repository consistency. Migrating those
extension examples does not incorporate them into core or assign their versions normatively.
Table and column declarations should otherwise remain semantically stable, except where this
revision makes a currently implicit or contradictory invariant exact.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged because registry-document conformance represents existing concepts rather than changing scientific identity. | Part 01 byte comparison. |
| logical prose and registry | Part 02 receives the complete contract, revised local rules, phase model, session proof, local UCUM reference, and incorporated schema, descriptor, and core registry; core advances to 0.4.0 and its nine UCUM authority URIs use the canonical identity. | Structural crosswalk, anchor and owner checks, normalized declaration comparison, positive and negative contract vectors. |
| physical profiles | Unchanged because no storage encoding or profile capability changes. | Parts 03 and 10 byte comparison apart from generated navigation if any. |
| packet catalog and JSON Schemas | Packet schemas are unchanged; generated packets update embedded or identified registry bytes and versions where present. | Catalog schema byte comparison and regenerated 28-packet corpus. |
| validation and import | Shared registry checking must implement the ordered result without crashing after shape failures; trust-boundary invocation remains P4.2. | Focused phase/outcome and invariant tests; no claim yet that every caller invokes them. |
| extensions | Part 09 becomes generic and names no concrete extension. The four repository-maintained examples adopt the disjoint extension shape and full logical ID, choose new versions in their own histories, and remain non-incorporated conformance evidence. | Generic extension vectors, each repository example, and focused namespace, context, reference, and session-path negatives. |
| reader, writer, validator, adapters | Common registry-document result and types may be implemented; public invocation behavior remains unchanged until P4.2. Adapters do not acquire schema authority. | Package tests distinguish contract implementation from boundary invocation. |
| conformance fixtures and tests | Add raw JSON, schema-selection, shape, contract-selection, semantic, rule-static, external-domain, and precedence cases; regenerate development fixtures. Add `ucumvert >=0.3.2,<0.4` to the validator implementation and lock the exact resolved version for incorporation. Distribute the MIT license and the official UCUM notice applicable to the vendored data. | At least one positive and focused negative for every invariant and phase outcome; an offline capability probe records the parser version, bundled UCUM 2.2 revision, and both license dispositions. |
| revision process and tooling | No lifecycle meaning changes. A metadata-only anchor bootstrap precedes final appraisal; ledger and evidence later map every clause to its owner. Repository authoring checks may retain the conventions excluded from registry conformance, but their findings must not change §3.3's result. | Stage, citation, repointing, structural, ledger, and evidence checks. |
| generated publications and developer documentation | Regenerate the combined specification, registry tables, counts, READMEs, and author guidance; label projected registry versions as core-only, keep concrete extensions out of Part 09, and keep authoring conventions distinct from conformance. | Generation and freshness checks plus documentation search for stale IDs, concrete extension names in Part 09, and duplicate owners. |

## 6. Conformance and implementation evidence

The contract corpus must include a valid core document and a valid extension document with a
conforming core context. It must independently cover:

1. duplicate raw JSON members and the mapping-entry limitation;
2. missing, non-string, and unknown `$schema` selectors;
3. every local schema conditional, including `primary_key: null` as a positive case;
4. unknown and ambiguous class/schema/semantic/logical/rule-language selector tuples;
5. missing or unusable core context for an extension;
6. every descriptor invariant with one focused negative and sufficient positive cases;
7. invalid and unsupported Part 11 outcomes attached to rule IDs;
8. accepted and rejected case-sensitive UCUM expressions with no network access;
9. result precedence among independent invalid, unsupported, and incomplete phases;
10. extension-local invalid findings preserved when core-dependent checks are incomplete;
11. every phase record, outcome ID, owner ID, RFC 6901 instance location, and skip reason; and
12. safe phase skipping after invalid shape.

Descriptor coverage must prove that every entry has a unique stable ID, valid phase, applicable
class, resolvable owning anchors, and a corresponding evidence case. A converse check must prove
that no semantic conformance check is hidden in implementation code without a descriptor entry.
Schema-owned constraints must be absent from the semantic inventory.

Registry migration evidence must compare all 43 core/analysis and 11 repository-extension table
declarations, all 121 rules, and all 128 references before and after the root-shape transition. It
must prove that every reference targets a complete key, that all current rule IDs remain unique and
owned, and that the four indirect session paths satisfy every condition in §3.7. It must parse all
61 literal-unit declarations against the selected exact UCUM 2.2 data. That comparison is migration
and feasibility evidence; it does not incorporate any concrete extension registry.

The same language-neutral checker must return the same result model for the incorporated core
registry, a generic extension vector, and all four repository-maintained extension examples.
Focused implementation tests must show that a missing role or another shape defect returns
findings without `KeyError`. The implementation probe must establish that the locked `ucumvert`
release bundles UCUM 2.2 data dated 2024-06-17, runs offline, and is redistributed with both its
MIT license and the official UCUM notice applicable to that data. P4.2 will later add
public-construction, embedded-copy, and trust-boundary evidence; those tests must not be
misreported as complete by this revision.

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
