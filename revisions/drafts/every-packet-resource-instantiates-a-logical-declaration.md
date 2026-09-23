# Every Packet Resource Instantiates a Logical Declaration

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `4e56020a336c6988a2252f747a6bfa2fb8781415` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§3.1.2, 3.2, 3.4, 4.1, and 5.1–5.2; Part 01 §§3.17–3.18; Part 02 §§1–4, 7, 9.1–9.4, and 11; Part 03 §§6.3, 6.5, and 11.3; Part 04 §§1–2, 4, 7, and 9; Part 05 §§1, 5.3, and 10; Part 06 §§1–2, 5, and 7–8; Part 09 §§5.1–5.2, 5.6, and 6.1; `registry/registry.schema.json`; `registry/logical_schemas.json`; `registry/registry_contracts/escapewheel-registry-contract-v0.1.json`; repository extension registries; `registry/manifest.schema.json`; `registry/resources.schema.json` |
| **Depends on** | [R122 §§3.2–3.3 and 3.6](../accepted/R122-define-specification-artifacts-and-normative-ownership.md#3-decision); [R126 §§3.1–3.8 and 3.10](../accepted/R126-a-registry-document-has-one-complete-conformance-contract.md#3-decision); [R127 §§3.2–3.7](../accepted/R127-registry-documents-are-checked-at-conformance-boundaries.md#3-decision) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8; §3.9 |

Section 3 is normative. Sections 1, 2, and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision makes every packet resource an instance of one checked logical declaration. It
generalizes the incorporated registry from a table map into a resource map, defines exact
singleton and family instance models, gives the registry ownership of resource content class and
kind, and makes resource presence and lineage policies data-driven for core and extensions.

It also removes packet fields that duplicate those declarations. A packet entry names its logical
declaration; a reader, writer, or validator obtains content class, kind, canonicality, presence,
and lineage policy from the checked registry context rather than from writer defaults or path
layout.

This revision is structural because the current rules are split among architectural content-class
prose, semantic asset definitions, table-only registry prose, packet-entry fields, and analysis
rules. Appending another classification would leave multiple owners. Incorporation therefore
retains semantic meaning in Part 01, consolidates logical declarations in Part 02, retains concrete
packet binding in Part 04, and leaves physical encoding with Part 03.

This revision does not define the machine-readable physical-profile descriptor, choose codec
capabilities, finish the packet manifest's registry-identity model, or compose final core,
extension, and packet validity. Those decisions remain separate because they concern physical
capability, release binding, and verdict composition rather than logical resource identity.

### 1.1 Structural crosswalk

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 00 §3.1.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-logical-standard), logical-kind examples that mix form and realization | revise in place | same anchor, with exact vocabulary in Part 02 | retains the storage-agnostic logical level while separating table/array/media/document form from view/materialization realization | §3.3 |
| [Part 00 §3.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-packet-content-classes), four content classes and independent canonicality prose | revise in place | same anchor | adds documentation, makes canonicality a consequence of content class, and leaves exact serialized values to Part 02 | §3.2 |
| [Part 00 §3.4](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-packet-catalog), catalog classification summary | revise in place | same anchor | says the catalog binds an instance to declarations rather than independently recording logical facts | §3.8 |
| [Part 00 §4.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-core-content-requirements), “core is what every packet has” | clarify in place | same anchor | makes the registry's presence policies, not every core declaration, define the minimum | §3.5 |
| [Part 00 §5.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-analysis-content-requirements), analysis lineage limited to core | replace in place | Part 06 §2 | permits an acyclic analysis chain rooted transitively in canonical core or extension instances and removes duplicate detailed policy from Part 00 | §§3.2, 3.7 |
| Part 00 §5.2, exact analysis-materialization criterion | replace with architectural summary and reference | Part 06 §§2 and 7 | removes a second analysis-policy owner while preserving materialization as a realization rather than a kind | §3.3 |
| Part 01 §3.17, array storage, URI-adjacent provenance, and producing-run statements | split | Part 01 retains the concept; Parts 02, 04, and 06 own declaration, binding, and provenance policy | removes physical and catalog mechanics from the semantic concept without changing what an array means | §§3.3, 3.6–3.8 |
| Part 01 §3.18, media URI and format requirement | split | Part 01 retains media meaning; Parts 02–04 own declaration, encoding, and location | removes physical facts from the semantic concept; stable logical identity remains | §§3.3, 3.6, 3.8 |
| [Part 02 §1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-core-logical-schema-scope), table-oriented scope and incorporated registry extent | revise in place | same anchor | covers every logical resource declaration and the generalized incorporated registry | §§3.1–3.3 |
| [Part 02 §2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-table-resource-requirements), table resource requirements | replace and subdivide | same anchor, retitled “Logical resource declarations” | defines common fields, instance models, presence, dependencies, kinds, and family binding before the table-specific contract | §§3.1–3.5 |
| [Part 02 §§3–4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-column-declaration), column contract and naming | retain under the table-kind contract and revise the `resource_id` exception | same anchors | preserves existing table meaning while permitting a carried string packet resource ID in a catalog table | §§3.3, 3.6 |
| [Part 02 §7](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-logical-references), foreign keys | clarify in place | same anchor | a populated reference also makes its target table resource necessary | §3.5 |
| [Part 02 §§9.1–9.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document), registry shape and conformance | revise in place | same anchors | replaces the table root with resource declarations and adds kind, presence, binding, and dependency invariants to the existing conformance phases | §§3.1–3.6, 3.9 |
| Part 02 §11, core resource index | regenerate | same section | indexes all logical declarations while retaining table-column projections | §§3.1–3.6 |
| Part 03 §§6.3 and 6.5, hardcoded `core.array_dimensions` lookup | revise in place | Part 02 owns the logical axes binding; Part 03 consumes it for stored rank, shape, and coordinates | a physical checker follows `array.axes_resource` instead of assuming the core table | §§3.3–3.4 |
| Part 03 §11.3, referenced-resource document and packet-owned array binding | revise in place | same section and `registry/resources.schema.json` | requires declaration binding for referenced resources and uses the catalog row's packet resource ID for a packet-owned asset | §§3.4, 3.6, 3.8–3.9 |
| Part 04 §§1–2, packet catalog scope and principles | revise in place | same sections | binds packet instances to checked logical declarations and physical encodings as separate axes | §§3.4, 3.8 |
| Part 04 §§4.1–4.2, common fields and kinds | replace in place | §4.1 binding fields; Part 02 owns kind vocabulary | adds `declaration_id` and removes declaration-selected classification, table-schema, and legacy asset-row binding fields | §§3.2–3.4, 3.8 |
| Part 04 §7, derived resources | revise in place | Part 04 retains instance lineage fields; Part 06 owns analysis obligations | applies declaration-selected lineage and producing-run policy to every kind | §3.7 |
| Part 04 §9, failed validation forbids presenting resources as canonical | replace in place | same section, with final verdict composition deferred | validation state does not alter declaration-derived canonicality; a failed packet cannot support a conformance claim | §§3.2, 3.8 |
| Part 05 §1, staged resources and canonical commitment | clarify in place | same section | a staged resource is not published before validation; no mutable canonical Boolean represents that state | §§3.2, 3.8 |
| [Part 05 §5.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-shim), cross-document shim | revise in place | same anchor | adds declaration resolution, presence, dependency, catalog binding, and catalog-row provenance checks | §§3.4–3.8 |
| [Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes), undefined-resource allowance | replace in place | same anchor | every catalogued resource must resolve a declaration; an unrecognized declaration is no longer an allowed opaque resource | §3.8 |
| Part 06 §§1–2, analysis scope and rules | revise in place | same sections | uses the analysis content class, canonical sources, and declaration policy rather than the `analysis` layer string | §§3.2, 3.7 |
| Part 06 §5, provenance of a materialization | revise in place | same section | makes resource-level producing-run binding independent of kind and reconciles catalogued asset rows | §§3.6–3.7 |
| Part 06 §§7–8, view/materialization and promotion | revise in place | same sections | separates logical kind from realization and makes promotion change content class | §§3.2–3.3 |
| [Part 09 §§5.1–5.2](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-definition), extension registry and namespace | revise in place | same anchors | gives extension registries the same resource declaration model without naming a concrete extension | §§3.1–3.5 |
| Part 09 §5.6, code-free extension handling | revise in place | same section | includes extension-owned non-table resources in the data-driven contract | §§3.1, 3.9 |
| [Part 09 §6.1](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-core-extension-reference-direction), reference direction | clarify in place | same anchor | applies the existing direction rule to declaration dependencies and family catalogs | §§3.4–3.5 |
| `registry/registry.schema.json` and `registry/logical_schemas.json` | replace incompatible shapes and identities | incorporated Part 02 artifacts | `resources` becomes the sole declaration root and table contracts become kind-specific payloads | §§3.1–3.6, 3.9 |
| current registry-contract descriptor | replace incompatible selector and invariant inventory | new `escapewheel-registry-contract-v0.2` descriptor incorporated by Part 02 | selects registry schema 0.5.0 and enumerates resource-classification, instance, catalog, and dependency invariants | §3.9 |
| repository extension registries | migrate independently | each extension registry remains its own authority | every table becomes a singleton resource and extensions may declare non-table resources with no plugin code | §§3.1–3.5, 3.9 |
| `registry/manifest.schema.json` | revise incompatible resource-entry shape and identity | published Part 04 schema projection | requires `declaration_id` and removes duplicated classification, schema-selection, and legacy asset-row binding fields; express incorporation and remaining manifest reconciliation are deferred | §§3.4, 3.8–3.9 |
| `registry/resources.schema.json` | revise incompatible delivery-entry shape and identity | Part 03 §11.3 | requires `declaration_id` with `resource_id` and `uri` on a referenced-resource delivery | §§3.4, 3.8–3.9 |

The affected existing headings in Part 00 §5.2; Part 01 §§3.17–3.18; Part 02 §11 and §§11.6,
11.8; Part 03 §§6.3, 6.5, and 11.3; Part 04 §2, §§4.1–4.2, §7, and §9; Part 05 §1; Part 06 §§1–2,
§5, and §§7–8; and Part 09 §5.6 do not yet have canonical anchors. They require a metadata-only
anchor bootstrap before final appraisal. Part 00 §3.1.2 and the other affected headings already
have canonical anchors. New Part 02 subsections receive canonical anchors when created. No
normative statement in the informational specification README changes owner; its registry and
catalog summaries are regenerated as informative projections.

## 2. Background

### 2.1 Current disagreement

At the baseline, the incorporated registry contains 43 table declarations under `tables` and no
declaration for arrays, media, or documents. Four repository extension registries use the same
table-only shape. The valid generated packet uses 30 of the 43 incorporated tables and no
non-table resource, so the existing corpus does not establish either a minimum table set or an
extension non-table path.

The packet schema instead requires each generic resource entry to carry `layer` and `kind`, permits
but does not generally require `canonical`, and uses vocabularies that differ from Part 00. The
writer derives a table's layer from a namespace, derives an array or medium's layer from its
resource ID, and marks every emitted resource canonical. The validator then uses the serialized
layer to decide whether producing-run provenance is required. A mistaken classification therefore
changes behavior instead of disagreeing with a checked declaration.

Three logical asset tables partly describe non-table instances. Their assigned integer IDs are row
identities, while their `*_name` fields preserve source labels. The writer nevertheless places a
source label in the manifest's `array_asset_id` or `media_asset_id`, so the packet has no stable
row-to-entry join. The same rows duplicate the manifest's `uri` and physical `format`, and no
validator establishes agreement.

### 2.2 Selected model

The selected model has one logical registry. A resource declaration owns content class, logical
kind, instance mode, presence, explicit dependencies, and resource-level provenance policy. A
table declaration embeds the current table contract as its kind-specific payload. A dense-array
declaration identifies the table that carries its logical axes. A packet entry names the
declaration it instantiates and carries only packet-instance and physical-binding facts.

The model deliberately has no general presence-expression language. Required and optional
singletons, optional unbound families, exact catalog-row families, explicit declaration
dependencies, and populated foreign keys cover the current inventory. A future condition requires
its own demonstrated use and revision.

The model also has no companion resource registry and no retained authoritative `tables`
projection. Implementations may generate a table-only view in memory, but the view must be derived
from `resources` and cannot disagree with it.

### 2.3 Compatibility

This is an incompatible development change to registry and packet shapes. There are no released
consumers or remote compatibility obligations. Existing generated packets and fixtures are
regenerated; the implementation need not accept the old `tables` root or old packet classification
fields. Exact source labels and assigned row IDs retain their meanings, but neither substitutes for
the new packet resource-ID join.

### 2.4 Feasibility probes

An in-memory migration of the incorporated registry wrapped all 43 current table contracts in the
selected resource declaration shape. Projecting declarations with kind `table` reproduced the old
`tables` mapping exactly, including every column, key, reference, and rule; JSON round-trip also
preserved the generalized mapping. The canonicalized resource object measured 115,554 bytes. This
establishes that a table helper can be a lossless projection rather than a second authority.

The existing core and analysis array catalog and dimensions tables also satisfy one generic axes
binding after the proposed catalog `resource_id` column is added. In each pair, the dimensions
table has exactly one foreign key from the leading columns of its primary key to the catalog's
whole primary key, followed by exactly one required structural-index column. An extension-shaped
copy satisfies the same predicate without a namespace-specific case. The proposed two-component
family declaration IDs satisfy the existing declaration-ID grammar; the earlier three-component
sketch did not.

The generated corpus contains 866 packet resource entries, all of which carry `schema_id`. Removing
that second table-schema selector is therefore an incompatible regeneration rather than cleanup of
an unused schema field. There are no released consumers or remote compatibility obligations.

## 3. Decision

### 3.1 A registry declares resources

Every core or extension registry document MUST contain a `resources` object and MUST NOT contain a
`tables` object. Each member name of `resources` is a declaration ID and MUST use the existing
dotted syntax `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`. Its value MUST be one closed resource
declaration.

Every resource declaration MUST contain exactly these common fields, plus the kind-specific field
permitted by §3.3:

- `content_class`, a string governed by §3.2;
- `kind`, one of `table`, `dense_array`, `media`, and `document`;
- `instances`, a closed object governed by §3.4;
- `requires`, an array of distinct declaration IDs, empty where the declaration has no explicit
  dependency;
- `lineage`, one of `forbidden`, `optional`, and `required`; and
- `producing_run`, one of `forbidden`, `optional`, and `required`.

The incorporated core registry MUST remain the exact declaration authority for the `core` and
`analysis` declaration namespaces. An extension registry MUST be the sole authority for the one
declaration namespace equal to its `extension_id`. No registry document owns any other declaration
namespace. The root and resource declarations MUST remain closed under the incorporated registry
meta-schema. A generated table-only implementation view MAY select declarations whose `kind` is
`table`, but it MUST NOT be serialized as a second registry authority.

### 3.2 Content class determines canonicality

The machine-readable `content_class` vocabulary MUST be `core`, `extension`, `analysis`,
`compatibility_projection`, and `documentation`. Part 00 MUST define their meanings as follows:

| value | meaning | canonical | unconditionally required by class |
|---|---|---:|---:|
| `core` | domain-general normalized facts | yes | no |
| `extension` | canonical typed facts owned by a domain | yes | no |
| `analysis` | products reproducible from canonical resources | no | no |
| `compatibility_projection` | a projection into another representation | no | no |
| `documentation` | human-readable sidecars that assert no semantic or conformance fact | no | no |

Canonicality MUST be derived from this table and MUST NOT be independently declared in a registry
or packet entry. Promoting a resource into the canonical set MUST change its declaration's content
class through a specification or extension-registry change; an implementation MUST NOT promote it
by setting a Boolean.

A documentation resource MAY describe any packet resource without creating a logical dependency or
supplying conformance evidence for the described resource. A machine-interpreted validation
report, registry, manifest, source-resolution document, or other control artifact MUST NOT acquire
documentation semantics merely because its serialization is also a document.

The core registry MUST NOT declare the `extension` content class. An extension registry MAY declare
`extension`, `analysis`, `compatibility_projection`, or `documentation` resources in its own
namespace, but MUST NOT declare `core`. Namespace and content class otherwise remain independent.

The incorporated registry MUST migrate its current declarations with these exact common fields:

| declaration set | content class | instances | lineage | producing run | requires |
|---|---|---|---|---|---|
| `core.sessions` | `core` | required singleton | `optional` | `optional` | empty |
| every other current `core.*` table | `core` | optional singleton | `optional` | `optional` | empty |
| every current `analysis.*` table | `analysis` | optional singleton | `required` | `required` | empty |
| `core.array_asset_instances` | `core` | catalog over `core.array_assets.resource_id` | `optional` | `optional` | empty |
| `analysis.array_asset_instances` | `analysis` | catalog over `analysis.array_assets.resource_id` | `required` | `required` | empty |
| `core.media_asset_instances` | `core` | catalog over `core.media_assets.resource_id` | `optional` | `optional` | empty |

An extension registry migrating an existing table MUST declare it as an optional singleton with
content class `extension`, optional lineage, optional producing run, and an empty `requires` array
unless the extension's own reviewed contract selects stricter values.

### 3.3 Kind describes logical form

The four logical kinds have these meanings:

| kind | logical form | kind-specific declaration |
|---|---|---|
| `table` | rows and declared columns | required `table` object containing the existing columns, primary key, references, and rules contract |
| `dense_array` | an n-dimensional dense array with declared logical axes | required closed `array` object containing `axes_resource` |
| `media` | an image or time-ordered audiovisual resource | none |
| `document` | a document or sidecar | none |

A table declaration MUST contain `table`, MUST NOT contain `array`, and MUST use singleton
instances. A dense-array declaration MUST contain `array`, MUST NOT contain `table`, and MUST use
catalog instances. A media or document declaration MUST contain neither kind-specific object and
MAY use any instance mode permitted by §3.4.

A dense-array declaration's `axes_resource` MUST name a visible singleton table declaration. Its
axes table MUST have exactly one **binding reference** to the declaration's catalog table: the
reference MUST target the whole catalog primary key, its local columns MUST be the leading columns
of the axes table's primary key, and that primary key MUST consist of the binding-reference columns
followed by exactly one required structural-index column. Other references from the axes table to
the catalog table do not become binding references merely by targeting it. Presence of a dense
array instance MUST make its axes-table singleton present. Part 03 MUST obtain the logical axes
through this binding when it compares them with stored rank, shape, and coordinates; it MUST NOT
select `core.array_dimensions` or another axes table by namespace or fixed resource ID.

Stored materialization and view are realizations, not logical kinds. An implementation MUST NOT use
`view`, `materialized_table`, `dense_array_asset`, `media_asset`, or `document_asset` as a registry
kind. A later physical-profile declaration MAY constrain whether a kind is stored, referenced, or
presented as a view without changing its logical kind.

Part 01 MUST define an array asset as the semantic concept of a dense array with declared axes and
a media asset as an image or video with its timing facts represented logically. Part 01 MUST NOT
make URI, container format, registry binding, physical encoding, or resource-level producing-run
placement part of either concept.

### 3.4 Instance modes bind declarations to packet resources

An `instances` object MUST match exactly one of these closed forms:

| mode | required fields | packet binding |
|---|---|---|
| singleton | `mode: "singleton"`; `presence` equal to `required` or `optional` | the declaration ID is also the only permitted packet `resource_id` |
| catalog | `mode: "catalog"`; `catalog_resource`; `resource_id_column` | zero or more packet resources bind one-to-one to rows of the named singleton table |
| family | `mode: "family"` | zero or more packet resources bind only by declaration ID |

Every packet resource entry MUST contain `resource_id` and `declaration_id`. Its
`declaration_id` MUST resolve through the packet's checked core or extension registry context. A
singleton entry's `resource_id` MUST equal its declaration ID. A catalog entry MUST satisfy §3.6.
A family entry MAY use any packet-unique dotted resource ID in a namespace the declaration's
registry owns under §3.1.

A catalog declaration's `catalog_resource` MUST resolve to a singleton table declaration visible
to that registry. Its `resource_id_column` MUST name a required string column with role
`identifier`, identity `carried`, and free vocabulary. An extension catalog MAY name a core table
or a table in the same extension under Part 09's reference-direction rule; a core catalog MUST NOT
name an extension table.

Within one visible core-and-extension declaration context, at most one catalog declaration MAY
name the same `catalog_resource` and `resource_id_column` pair. This makes the row sufficient to
select its family when an adapter delivers packet-owned bytes without a separate resource
document. Registry conformance MUST reject an ambiguous pair.

A catalog declaration's kind-specific requirements remain additional to this common binding. In
particular, a dense-array catalog MUST also satisfy the axes-resource contract in §3.3.

### 3.5 Presence is a declaration property

The incorporated core declaration `core.sessions` MUST be a required singleton. Every other table
currently incorporated in the core registry MUST be an optional singleton. An extension author
MUST select `required` or `optional` for each extension singleton. Declaring an extension in a
packet activates the required singleton declarations in that extension; installing or co-locating
an extension registry does not.

A packet MUST contain an instance when any of these conditions applies:

- the instance is a required singleton in an active registry;
- a present resource's declaration names the instance's singleton declaration in `requires`;
- a populated table foreign key targets the instance's singleton table declaration; or
- a row in a catalog table requires that exact catalog-family instance under §3.6; or
- a present `processing_run_id` requires the `core.processing_runs` singleton.

An absent optional singleton creates no empty table by itself. A present singleton table MAY have
zero rows unless a separate logical rule requires rows. A family is optional as a family and has no
minimum instance count; its catalog rows, if any, determine the exact required catalog instances.
`analysis`, `compatibility_projection`, and `documentation` declarations MUST be optional.

Each `requires` member MUST resolve under the same core-and-extension visibility rules as a
reference. A packet containing an instance MUST contain every singleton dependency in the
transitive closure of its declaration's `requires`. Registry conformance MUST reject an unresolved
dependency and MUST reject a dependency on a family because it does not identify one packet
instance. Cycles are permitted only when every member is a singleton; presence of any member then
requires the entire cycle.

### 3.6 Catalog rows carry packet resource identity

`core.array_assets`, `analysis.array_assets`, and `core.media_assets` MUST each gain this column:

| field | type | presence | role | identity | vocabulary |
|---|---|---|---|---|---|
| `resource_id` | string | required | identifier | carried | free |

For this exact field, Part 02's general integer `_id` naming convention MUST NOT apply. Its values
are packet resource identifiers read before assigned row identifiers; `array_asset_id` and
`media_asset_id` remain assigned integer primary keys, and `array_asset_name` and
`media_asset_name` remain source-label bridges. The three tables MUST remove `uri` and `format`.
Location remains a packet-entry fact and physical encoding remains a Part 03 fact.

The incorporated core registry MUST declare the three catalog families named in §3.2. For each row
in one of those catalog tables, a conforming packet MUST contain exactly one resource entry whose
`resource_id` equals the row's `resource_id` and whose `declaration_id` names the corresponding
family. Every entry naming one of those families MUST match exactly one row. The values in each
catalog resource-ID column MUST be unique and MUST also satisfy packet-wide resource-ID
uniqueness.

An extension MAY declare the same pattern using its own singleton catalog table and catalog
family. An implementation MUST derive the check from the declaration; it MUST NOT special-case the
three incorporated family IDs or require extension code.

### 3.7 Lineage and producing runs apply to every kind

The declaration fields `lineage` and `producing_run` govern the presence of the packet entry's
`derived_from` and `processing_run_id` fields respectively. For either policy, `forbidden` means
the field MUST be absent, `optional` means it MAY be present, and `required` means it MUST be
present. A present `derived_from` MUST be a nonempty array of distinct existing packet resource
IDs. This revision does not change the value representation or resolution target of a present
`processing_run_id`. In particular, it MUST NOT make the nullable source-bridge
`core.processing_runs.processing_run_name` packet-unique merely to create a manifest join. The
complete manifest and cross-field reconciliation MUST settle that identity and any agreement
between a catalog row and its resource entry.

Every `analysis` and `compatibility_projection` declaration MUST set both policies to `required`.
Every `documentation` declaration MUST set `lineage` to `forbidden`; describing another resource
does not create derivation. A `core` or `extension` declaration MAY select any policy consistent
with its logical meaning.

A present lineage edge MUST obey this content-class relation:

| derived resource class | permitted source classes |
|---|---|
| `core` | `core` |
| `extension` | `core`, `extension` visible to the same extension registry |
| `analysis` | `core`, `extension`, `analysis` |
| `compatibility_projection` | `core`, `extension`, `analysis` |
| `documentation` | none |

The lineage graph MUST NOT contain a self-edge or cycle. Because every analysis resource has
nonempty lineage, every finite analysis chain MUST terminate in canonical core or extension
resources. Analysis can therefore record the intermediate resource it actually consumed while
remaining transitively reproducible from canonical facts. A compatibility projection may project
an analysis product. Registry visibility and Part 09's ownership direction still apply when the
source declaration belongs to an extension.

A writer MUST apply these policies without regard to resource kind. A validator MUST resolve them
from the checked declaration and MUST NOT select provenance checks from a serialized layer or
namespace. A reader MUST expose the resolved policy and content class without requiring a
validation receipt for ordinary access.

A singleton analysis catalog table and each analysis instance it catalogs are distinct packet
resources. The singleton entry's lineage and producing run describe materialization of the table;
each catalogued instance carries its own declaration-selected provenance. A table may therefore
aggregate rows for instances produced by different runs without weakening either resource's
policy. This revision retains the existing row-level provenance columns and meanings; it neither
adds a media row-level run column nor defines row-to-entry run agreement.

### 3.8 The packet does not repeat logical classification

A packet resource entry MUST contain `declaration_id` as a string in the declaration-ID syntax and
MUST NOT contain `layer`, `kind`, `canonical`, `schema_id`, `catalog_table_ref`, `array_asset_id`,
or `media_asset_id`. Part 04 MUST define `declaration_id` as the logical declaration binding and
MUST direct a consumer to the checked registry context for content class, kind, instance mode,
canonicality, table contract, presence, and provenance policy. The catalog row's `resource_id` is
the only packet-to-row binding for a catalog instance; assigned row IDs and source-label bridges
retain only their Part 02 meanings.

The packet entry MUST continue to own instance facts, including `resource_id`, `uri`, integrity and
external-resource fields, physical-encoding selection, validation state, lineage values, and
producing-run value where applicable. This revision does not rename or finish reconciling those
fields beyond the logical-classification changes stated here.

A referenced-resource document delivered under Part 03 §11.3 MUST contain `resource_id`,
`declaration_id`, and `uri` for every entry. A writer MUST preserve that declaration binding when
it creates the packet entry and MUST reject a document whose binding does not resolve or does not
admit the resource ID. For a packet-owned catalogued array delivered as bytes, the writer MUST use
the catalog row's `resource_id` and the unique family selected by its catalog pair; it MUST NOT use
the source label or assigned integer row ID as packet resource identity.

Because JSON Schema cannot inspect a checked registry context, the manifest schema MUST check the
local shape of `declaration_id` but MUST NOT reproduce declaration-selected kind conditions. The
Part 05 shim MUST resolve the declaration before applying kind-specific packet and physical checks.

A packet resource's validation state MUST NOT change its declaration-derived content class or
canonicality. A failed or incomplete validation result cannot support a conformance claim; it does
not turn a canonical core or extension resource into analysis content. A writer MUST keep staged
resources out of a committed catalog until the applicable publication gate passes rather than
representing staging by changing canonicality.

A reader, writer, or validator MUST NOT infer a declaration from URI, directory placement,
namespace alone, or logical kind. It MUST reject a packet conformance claim when a declaration is
unknown, the instance mode does not admit the resource ID, a required instance is absent, a
forbidden classification field is present, or a presence, catalog-binding, lineage, or
producing-run rule fails.

This unknown-declaration rule supersedes Part 05's current permission to carry a resource the
specification does not define. An extension registry is the data-driven route for such a resource;
an opaque, undeclared resource is not a conforming packet resource.

### 3.9 Artifacts, conformance, and incompatible identities advance together

The incorporated registry meta-schema MUST advance from
`https://escapewheel.org/schemas/registry/0.4.0` to
`https://escapewheel.org/schemas/registry/0.5.0`. The incorporated core registry MUST advance from
`0.4.0` to `0.5.0`. An extension author migrating an extension registry to the incompatible
resource shape MUST independently advance that extension's `registry_version`; the core
specification MUST NOT assign the extension's version.

The incorporated registry-contract descriptor MUST advance from
`escapewheel-registry-contract-v0.1` to `escapewheel-registry-contract-v0.2`, select registry schema
0.5.0, retain the existing applicable invariant IDs, and add these semantic-phase invariants:

- `registry.resource.classification`, for document-class/content-class eligibility;
- `registry.resource.instance`, for kind and instance-model eligibility;
- `registry.resource.catalog`, for catalog visibility, column eligibility, and unambiguous catalog
  pairs;
- `registry.resource.array_axes`, for dense-array catalog mode and the axes-table binding; and
- `registry.resource.dependency`, for dependency resolution and singleton eligibility.

The existing table, column, reference, rule, and external-domain invariants MUST operate on the
`table` payload of table-kind resource declarations. Their stable IDs MUST NOT change merely
because their JSON Pointer gains the enclosing `resources` and `table` components.

The manifest schema MUST advance from
`https://escapewheel.org/schemas/manifest/0.1.0` to
`https://escapewheel.org/schemas/manifest/0.2.0`. The referenced-resource delivery schema MUST
advance from `https://escapewheel.org/schemas/resources/0.1.0` to
`https://escapewheel.org/schemas/resources/0.2.0`. Generated development packets and deliveries
MUST use the new registry, manifest, and resource-document shapes; implementations are not
required to accept the superseded shapes.

The existing registry-document phases and checked-context boundaries remain in force. Registry
shape and semantic phases MUST additionally reject:

- a missing or additional common declaration field;
- a kind-specific field on the wrong kind;
- an invalid content-class, kind, instance-mode, presence, or provenance-policy value;
- a declaration ID outside the registry's namespace ownership;
- an unresolved or ineligible catalog resource, resource-ID column, or dependency;
- a dense-array declaration without one eligible axes-table binding;
- a core declaration of extension content or an extension declaration of core content; and
- an incompatible registry identity.

Packet validation MUST run declaration resolution before using kind-specific physical checks.
Ordinary reader access remains outside the registry conformance boundary established by R127: a
reader need not validate a registry or possess a receipt merely to resolve a declaration for an
operation.

## 4. What this does not change

- Part 03 continues to own Parquet, Zarr, media-container, codec, and other physical requirements.
  A later descriptor will make those capabilities machine-readable.
- Packet registry identifiers, embedded-copy comparison, and complete manifest reconciliation
  remain separate decisions; this revision changes only fields forced by logical declaration
  binding.
- The exact identity carried by packet-entry `processing_run_id`, its resolution to a run row, and
  any agreement with row-level provenance remain for the complete manifest and cross-field
  reconciliation. This revision changes only declaration-selected field presence.
- Final composition of core, extension, resource, and packet verdicts remains separate. This
  revision supplies decidable declaration and resource findings for that composition.
- `resource_id` is packet identity; assigned integer IDs remain row identity, and `*_name` fields
  remain bridges to a source or earlier packet.
- Session/reference-clock consistency is an independent tracked defect and is not resolved by
  resource presence.
- Adapters still translate source formats into declared resources. They do not acquire authority to
  extend the registry or choose undeclared packet semantics. Static non-table capability and
  delivery arbitration remain with the adapter-contract reconciliation; this revision changes only
  the declaration binding on a resource that is delivered.

## 5. Consequence

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Part 01 retains array and media meaning but loses URI, encoding, declaration, and catalog-provenance mechanics. | Crosswalk review and semantic-definition tests or text checks showing no physical owner remains in §§3.17–3.18. |
| logical prose and registry | Part 02 defines resource declarations, kinds, instances, presence, dependencies, catalog binding, dense-array axes binding, and provenance policies; the registry root becomes `resources`; all current tables become singleton declarations. | Meta-schema positive and negative vectors; exact normalized declaration comparison; generated table projection from resources; registry conformance mutations for every new invariant. |
| physical profiles | Part 03 remains the physical-encoding owner, follows the declaration-selected axes table for dense arrays, and adds declaration binding to its resource-delivery boundary; no capability descriptor is added by this revision. | Owner/citation check showing no format or codec field entered the logical registry; core, analysis, and extension axes cases; resource-document vectors require `declaration_id`. |
| packet catalog and JSON Schemas | Part 04 adds `declaration_id` and removes `layer`, `kind`, `canonical`, `schema_id`, `catalog_table_ref`, `array_asset_id`, and `media_asset_id`; its still-unincorporated manifest-schema projection and the delivery schema advance with the same binding, while complete schema reconciliation remains deferred. | Schema vectors and manifest semantic cases for singleton, catalog, family, unknown declaration, forbidden duplicate fields, delivered references, and missing required instances. |
| validation and import | Part 05's shim resolves declarations before kind dispatch; presence, catalog binding, dependency closure, canonicality, lineage, and producing runs are declaration-driven, and unknown declarations fail conformance. | Stable finding IDs with positive and negative core and extension packets; phase-order tests prevent unsafe access after a non-valid registry. |
| extensions | Each repository extension migrates to resources and independently advances; extension-owned catalog and axes declarations use the same logical checks as core declarations. | All four extension registries pass shared logical checks; fixture-only extension array and document declarations pass without a registry-specific logical checker; invalid namespace, dependency, catalog, and axes cases fail. |
| reader, writer, validator, adapters | Shared helpers project tables and resolve declarations; writer staging covers declared kinds; reader APIs expose resolved facts; validator removes serialized-layer dispatch; adapters keep their existing source role. Static adapter capability and full extension physical parity remain deferred. | Focused package tests plus writer-to-reader-to-validator integration for core, extension, analysis, array, media, and documentation resources, without treating adapter capability or the future physical descriptor as evidence for this revision. |
| conformance fixtures and tests | Packets and fixtures are regenerated in the incompatible shape; add absent singleton, bad dependency, catalog mismatch, duplicate row binding, wrong provenance policy, and analysis-canonicality cases. | Quick and full verifier pass; corpus expected outcomes name every new finding; old-shape rejection is explicit. |
| revision process and tooling | Lifecycle rules are unchanged; structural incorporation needs the listed anchor bootstrap and current citation repointing. | Anchor-only bootstrap check, structural crosswalk, ledger dispositions, evidence manifest, stages, citations, and repoint checks. |
| generated publications and developer documentation | Resource index, table projections, README facts, combined specification, registry-author guidance, and extension-author examples regenerate from `resources`. | Candidate-state preservation checks and examples for all three instance modes and all four kinds. |

Existing packets, registries, and implementation fixtures are not shape-compatible. They are
development artifacts and will be regenerated rather than silently upgraded in place. Public
reader and writer models that expose `layer`, serialized `kind`, serialized `canonical`, or
`schema_id` will either remove those properties or, for logical classification only, return
declaration-resolved values documented as derived. `schema_id` has no derived packet-entry
replacement because the declaration selects the table contract.

The four repository extension examples are independent artifacts rather than incorporated core
members. Their incompatible migration is expected to advance `aind_opto` from 0.4.0 to 0.5.0,
`aind_unit_qc` from 0.3.0 to 0.4.0, `dynamic_foraging` from 0.5.0 to 0.6.0, and `vr_foraging` from
0.4.0 to 0.5.0. Those values are repository migration evidence, not versions assigned by the core
specification or named in Part 09.

## 6. Conformance and implementation evidence

The incorporation evidence needs at least these positive cases:

- the core registry with `core.sessions` required and the other 42 current tables optional;
- a packet containing only the required singleton plus targets made necessary by its populated
  references;
- an optional singleton present as an empty typed table and absent entirely in another packet;
- one core array and one medium bound one-to-one to catalog rows;
- core and analysis arrays whose physical checks resolve their distinct declaration-selected axes
  tables;
- one extension-owned array with its own catalog and axes table, accepted by the shared logical
  declaration path without extension-specific checker code;
- one optional documentation family with two differently named instances;
- analysis table and array resources with canonical core or extension lineage and one producing
  run;
- a two-stage acyclic analysis chain whose terminal sources are canonical resources; and
- derived in-memory table projections that are byte-for-byte equivalent to the table contracts
  nested in resource declarations.

The negative corpus needs to distinguish at least these cases with stable findings:

- old `tables` registry root, old manifest classifications, and missing `declaration_id`;
- unknown declaration, singleton resource-ID mismatch, and resource ID outside an owned namespace;
- missing required singleton, missing explicit dependency, and missing populated-foreign-key
  target;
- unresolved or family-valued dependency and an ineligible catalog resource-ID column;
- two visible catalog declarations naming one catalog resource-and-column pair;
- missing, duplicate, or unmatched catalog row binding;
- duplicate packet resource IDs or duplicate catalog `resource_id` values;
- core declaration of extension content and extension declaration of core content;
- any forbidden packet field: `layer`, `kind`, `canonical`, `schema_id`, `catalog_table_ref`,
  `array_asset_id`, or `media_asset_id`;
- a dense-array declaration with no catalog binding, no axes resource, or an ineligible axes-table
  primary-key/reference structure;
- missing required lineage or producing run, forbidden lineage, an ineligible lineage source, a
  lineage self-edge, and a lineage cycle;
- a referenced-resource document lacking `declaration_id` or carrying an inadmissible binding; and
- non-valid registries rejected at R127's production and conformance boundaries before a resource
  plan is generated.

Implementation must replace direct root `tables` accesses with one shared declaration API or a
generated table projection. The incorporation review must inventory all such accesses in the
reader, writer, validator, registry checker and generator, conformance tools, fixtures, prototypes,
and documentation generators. Passing tests that still construct the superseded registry or
manifest shape are not acceptable evidence.

## 7. Open

The machine-readable physical-profile descriptor, exact encoding selector that packet entries will
use, codec capability floor, packet registry digest binding, complete manifest reconciliation,
exact processing-run identity and row-to-entry agreement, static adapter capability, delivery
arbitration, and final validity composition are deliberately deferred. Either outcome of those
later decisions leaves this draft's logical declaration, instance, presence, and classification
rules unchanged.
