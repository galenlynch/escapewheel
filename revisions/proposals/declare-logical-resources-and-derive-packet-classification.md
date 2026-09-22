# Declare logical resources and derive packet classification

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-22 |
| **Based on** | `d10550bf7cad17d4bfa4d63ce965e2518a70649c` |
| **Decision domain** | specification |
| **Affects** | logical resource declarations; packet content class, kind, requiredness, canonicality, and lineage; Parts 00, 02, 04, 06, and 09; the registry meta-schema and documents |

## 1. Problem

The logical registry declares tables but not the other resources a packet may contain. Arrays,
media, documents, and views consequently acquire their kind, packet content class, requiredness,
canonicality, and lineage policy from a mixture of packet fields, prose, namespace conventions,
and writer defaults. An extension can declare tables but has no equivalent data-driven way to
declare a non-table resource.

The packet then serializes `layer`, `kind`, and `canonical` as though they were independent facts.
Those fields can disagree with the resource identifier, the selected registry, and the logical
policy that gave the resource meaning. The current writer demonstrates the risk by marking every
table, staged array, referenced array, and referenced medium canonical, including analysis
resources. Its lineage and producing-run APIs accept only resources found in the table registry,
so the same catalog contract is not available to non-table resources.

The specification therefore lacks one declaration from which an implementation can determine:

- what logical resource declaration a manifest entry instantiates;
- the resource's logical kind and packet content class;
- whether an exact resource or a family of resource instances is required;
- whether the resource is canonical;
- what lineage and producing-run information it owes; and
- whether a core or extension registry owns the declaration.

This proposal addresses that missing logical model and its packet binding. A separate proposal
will describe portable-profile encodings and capabilities as data. Keeping the two decisions
separate preserves the rule that Part 02 is storage-agnostic and Part 03 owns technology-dependent
requirements.

## 2. Evidence

All observations below were reproduced at the recorded baseline.

### 2.1 The registry covers only tables

`registry/registry.schema.json` requires a root `tables` object and has no resource declaration
outside that object. The generated core registry contains 43 tables and no declaration for an
array, medium, document, or view. Four extension registries use the same table-only shape.

Part 02 §1 nevertheless says the part defines which resources the core content class comprises,
and Part 00 §3.1.2 lists tables, arrays, media, documents, views, and materializations as logical
resources. The prose claim is broader than the incorporated machine-readable declaration.

### 2.2 Packet entries repeat classifications without an owner

Part 04 §4.1 requires `layer`, `kind`, `physical_profile`, and `canonical` on every resource. The
incorporated authority model says that content class, namespace, resource kind, and physical
encoding are independent axes, but Part 04 does not define the `layer` vocabulary. The manifest
schema permits `core`, `analysis`, `extension`, and `docs`, which is not Part 00's content-class
vocabulary. It accepts `document_asset`, while Part 04 names `document`.

The manifest schema requires only `resource_id`, `layer`, `kind`, and `uri` for a generic resource;
it does not require `canonical`, `physical_profile`, or `validation_state`, despite Part 04's table.
This proposal does not attempt the complete manifest-schema reconciliation, but its decision must
settle which of these values are declarations and which remain packet-instance facts before that
reconciliation can be correct.

### 2.3 Requiredness is not expressible

No registry declaration says whether a table is required or optional. The validator skips a
registered table when its manifest entry is absent. The generated conformance corpus contains 29
packet manifests and 866 resource entries, but only 30 of the 43 generated tables occur in the
valid packet. Thirteen tables, including every analysis table and the array, media, calibration,
clock-phase-step, and preferred-run tables, do not occur there. Passing the corpus therefore does
not establish a general minimum resource set.

The corpus contains only table resources: 837 core table entries and 29 extension table entries.
It supplies no packet-level evidence for the non-table declaration model.

### 2.4 Dynamic assets already have an implicit declaration pattern

`core.array_assets`, `analysis.array_assets`, and `core.media_assets` hold rows that describe
logical asset instances. A manifest entry separately carries a packet resource ID and an
`array_asset_id` or `media_asset_id`. The writer permits the packet resource ID and the asset row's
name to differ, as in resource `core.waveform_means` linked to asset ID `wf`.

This is evidence that non-table declarations cannot be modeled only as a fixed set of exact
resource IDs. The declaration language needs both singleton resources and resource families whose
instances bind to rows in a declared catalog table. Documents may also need an optional
many-instance family without a table row for each sidecar.

The present row-to-entry binding is not a stable logical identity. `array_asset_id` and
`media_asset_id` are packet-assigned integer identifiers in the logical registry, while the writer
puts their pre-assignment source labels in manifest fields of the same names. The table rows carry
`array_asset_name` and `media_asset_name` as the bridge to those source labels, but neither name is
declared unique and neither is the packet resource ID. A declaration cannot safely join a manifest
entry to its logical row through the current field.

The asset tables also carry `uri` and `format`. Those are packet location and physical-encoding
facts already recorded by the manifest, not storage-agnostic logical facts. No validator check
currently establishes that the duplicated row and manifest values agree. A generalized logical
registry should not preserve this cross-abstraction duplication.

The same leak appears in semantic prose. Part 01 §3.17 defines an array asset as stored outside the
table layer and discusses where its producing run appears in the manifest. Part 01 §3.18 requires
a media asset to have a URI and format. The semantic part should define what array and media assets
mean; logical instance identity and producing-run policy belong in Part 02 or Part 06, URI binding
belongs in Part 04, and encoding belongs in Part 03. Relocating those rules preserves their effect
while restoring the accepted abstraction direction.

### 2.5 Current implementation derives policy inconsistently

The writer:

- obtains a table's packet `layer` from its namespace, except that a loaded extension becomes
  `extension`;
- obtains an array or medium's `layer` directly from the first component of its resource ID;
- writes `canonical: true` for every table, staged array, referenced array, and referenced medium;
  and
- refuses `derives()` and `produced_by()` for a resource absent from the table registry.

The validator checks producing-run provenance only for entries whose serialized `layer` equals
`analysis`. The reader exposes the serialized `layer` and `kind` directly. A malformed or mistaken
classification therefore changes behavior instead of being rejected against one declaration.

### 2.6 Analysis rules disagree

Part 00 §5.1 limits analysis lineage to core resources, while Part 06 §2 permits lineage from any
canonical core or extension resource. Part 00 §5.2 frames materialization around layout, while
Part 06 also permits expensive or parameterized transformations. Parts 00 and 06 say analysis
resources are noncanonical unless promoted by specification change, but the writer marks an
analysis table canonical whenever it stages one.

Part 06 owns analysis-specific policy. Part 00 should retain only the architectural relationship,
and the registry should carry each declaration's exact machine-readable classification and
lineage policy.

### 2.7 Baseline and overlap checks

The quick monorepo verifier passed all 31 stages at the recorded baseline. `revisions/stages.py`
reported no other open proposal or draft. Accepted revisions R122, R126, and R127 are dependencies:
R122 separated content class, namespace, kind, and physical encoding; R126 defined registry
conformance; and R127 requires checked registries at conformance boundaries. This change must
extend those contracts rather than introduce a second validation path.

The citation-impact scan found live consumers of the affected Part 00, Part 02, Part 04, Part 06,
and Part 09 sections in the registry generator and checker, conformance sweep, reader, writer,
validator, tests, and specification entry point. Historical accepted revisions remain historical
and are not rewritten.

A source scan found 164 direct table-root accesses across 39 Python, Markdown, and JSON files: 11
writer files, seven validator files, seven reader files, seven conformance files, and seven other
generation, fixture, or prototype files. The migration is broad but mechanical. A single helper
that projects table contracts from generalized resource declarations can keep table algorithms
focused on tables without preserving a second authoritative `tables` object in the registry.

## 3. Desired outcome and constraints

A successful resolution should provide one data-driven declaration model for every logical
resource kind while preserving these constraints:

- Part 02 and an expressly incorporated registry own logical declarations; Part 03 and its future
  descriptor own physical encodings and portability capabilities; Part 04 owns only the binding of
  concrete packet instances to those declarations.
- Part 01 retains the domain meaning of array and media assets without owning their packet URI,
  encoding, registry declaration, or manifest provenance fields.
- A core or extension registry can declare tables and non-table resources without installing code.
- A manifest entry binds to exactly one checked declaration. Classification does not depend on
  writer defaults or path layout.
- A row describing a non-table asset binds to its manifest entry through an explicit packet
  resource ID. Source labels remain provenance bridges and packet-assigned integer IDs remain row
  identities; neither substitutes for the packet resource ID.
- Logical asset tables do not duplicate the manifest's URI or the physical profile's encoding.
- Singleton resources and families of zero or more instances are both expressible. A family can
  require one manifest resource for each row in a declared catalog table.
- Requiredness is decidable from checked registries and packet-visible facts. The model does not
  hide a new condition language in prose or implementation code.
- Explicit declaration dependencies and the registry's existing foreign keys can make another
  resource conditionally necessary without restating those relationships in a general expression
  language.
- Canonicality has one owner and cannot contradict content class.
- Lineage and producing-run rules apply uniformly to tables, arrays, media, and documents.
- Core and extension registries use the same applicable declaration invariants, while an
  extension owns only its namespace and does not become known to the core specification by name.
- Existing development packets may be regenerated; there is no external compatibility
  obligation. Migration cost still has to be measured and stated.

## 4. Options and tradeoffs

### 4.1 Keep table registries and serialized classifications

The current design could add validator checks around `layer`, `kind`, and `canonical` while
leaving non-table policy in prose. This has the smallest immediate implementation diff, but it
preserves the missing owner, keeps extension assets underspecified, and requires every writer to
reimplement the same classification rules. It does not meet the data-driven objective.

### 4.2 Add a companion resource registry

A new artifact could map resources to the existing table registry and describe non-table
families. This avoids changing the mature table declaration shape. It also creates two logical
registries with duplicated table identities and requires an explicit rule for their disagreement.
Generation could control that duplication, but the split would reflect implementation history
rather than a distinct abstraction boundary.

### 4.3 Generalize the logical registry

This proposal selects logical resources as the registry's primary declarations. A
resource declaration would carry its content class, logical kind, instance model, presence policy,
and lineage policy. A table resource would carry its existing columns, key, references, and rules
as its kind-specific contract. A non-table family could bind instances to rows of a declared
catalog table or admit optional unbound instances such as sidecars.

This is the most disruptive registry-shape change, but it produces one owner, lets the registry
meta-schema enforce kind-specific shape, and allows generation of table-only views for code that
needs them. With no released consumers, the present development phase is the least expensive time
to make that correction.

### 4.4 Classification fields in the packet

Three packet designs were considered:

1. retain `layer`, `kind`, and `canonical`, then require exact agreement with the declaration;
2. remove all three and resolve them through a declaration identifier; or
3. retain only values needed to dispatch before registry resolution and derive the rest.

This proposal selects the second design. Every packet already carries the checked core
registry and declares its checked extension registries, so duplicating logical facts in each entry
adds disagreement states without enabling independent interpretation. A required
`declaration_id` would make binding explicit for dynamic assets, where `resource_id` cannot itself
select a singleton declaration.

For catalog-bound families, the selected join is an explicit dotted `resource_id` column in the
logical catalog table. The table's assigned integer key continues to identify rows and references
within tabular data, while its `*_name` column continues to preserve a source or earlier packet's
label. The manifest's existing `resource_id` then binds to the row without pretending that a
source label is a packet-assigned ID. The physical `uri` and `format` columns would leave
`core.array_assets`, `analysis.array_assets`, and `core.media_assets`; the manifest and selected
physical profile remain their owners.

### 4.5 Requiredness models

One option is a general boolean expression language over packet facts. It is flexible but creates
another executable language before concrete conditions justify it. Another is a small fixed model:

- a singleton declaration is required or optional;
- a many-instance declaration is optional as a family;
- a catalog-bound family requires exactly one manifest instance for every row in its declared
  catalog table, with no unmatched instance;
- a declaration can name another declaration that its presence requires; and
- a populated foreign key requires its target resource through the reference Part 02 already
  declares.

This proposal selects the fixed model for v0.2. It is machine-checkable, language-neutral, and
covers the existing distinction between exact tables and row-described assets. A later change may
extend it if an appraised resource inventory demonstrates a condition that it cannot express; the
current revision does not reserve or embed a general expression language.

An additional choice is whether every table in the core registry is a required singleton, emitted
as an empty typed table where the packet has no rows, or whether selected core tables remain
optional. Requiring all core tables gives “the core” a literal, discoverable minimum, but it also
collapses two useful states: a modality the packet does not carry and a carried observation that
has zero rows. Current prose explicitly permits packet provenance to be absent, says a writer may
emit nothing where sorting-run channels cannot be read, and distinguishes no calibration row from
a calibration row with no further detail. This proposal therefore selects a reviewed
per-declaration minimum. `core.sessions` is an unconditionally required singleton. Every other
singleton declaration explicitly states whether it is required or optional, and every family is
optional unless a catalog row requires an instance. A declaration's presence also becomes
necessary when a present declaration names it as a required dependency or when a populated foreign
key targets it. Analysis declarations are optional. Extension authors make the same
required-or-optional choice for extension singletons rather than inheriting requiredness merely
from the extension content class. The exact declaration matrix must be appraised rather than
inferred from the current fixture.

### 4.6 Canonicality models

Canonicality is a consequence of packet content class: core and extension resources are
canonical; analysis, compatibility-projection, and documentation resources are not. It is not an
independent declaration or packet field. If a derived product is promoted, its declaration changes
content class rather than setting a contradictory boolean.

### 4.7 Logical kind and materialization

The current vocabulary mixes logical form (`table`, `dense_array_asset`, `media_asset`,
`document_asset`) with realization (`materialized_table`, `view`). The new registry uses only the
logical-form kinds `table`, `dense_array`, `media`, and `document`. Stored materialization versus
view is represented separately where it applies, so realization does not become another resource
kind.

### 4.8 Documentation content

The existing `docs` layer has no corresponding packet content class in Part 00. Treating a
document solely as a resource kind does not answer whether its contents are canonical, derived, or
conformance-bearing. Excluding sidecars from the resource declaration model would preserve a
special case in the catalog and prevent extensions from declaring their documentation uniformly.

This proposal adds a `documentation` packet content class: optional and noncanonical,
subject to catalog, integrity, and physical-profile checks, but not a source of semantic facts or
packet validity claims. A documentation resource may describe resources from any content class
without creating a logical reference or shared verdict. This makes the current `docs` value an
architectural class rather than an unexplained path convention. Validation reports and other
machine-interpreted control artifacts remain governed by their owning contracts rather than being
reclassified as documentation merely because they use JSON.

### 4.9 Illustrative declaration shape

The following is an informative feasibility sketch, not proposed normative JSON. It shows that the
selected choices fit one closed registry without making a runtime resource ID double as a family
identifier:

```json
{
  "resources": {
    "core.sessions": {
      "content_class": "core",
      "kind": "table",
      "instances": {"mode": "singleton", "presence": "required"},
      "table": {"columns": [], "primary_key": ["session_id"], "references": [], "rules": []}
    },
    "core.array_assets.instances": {
      "content_class": "core",
      "kind": "dense_array",
      "instances": {
        "mode": "catalogued",
        "catalog_resource": "core.array_assets",
        "resource_id_column": "resource_id"
      },
      "lineage": "optional"
    }
  }
}
```

Here `core.sessions` is both a declaration ID and the one permitted runtime resource ID. The
second declaration identifies a family; a manifest entry such as `core.waveform_means` names
`core.array_assets.instances` as its declaration and matches one `core.array_assets.resource_id`
value. The final schema may choose different field names, but it needs equivalent information and
closed kind-specific branches.

## 5. Impact sketch

| surface | impact |
|---|---|
| semantic prose | structurally affected; Part 01 retains domain meaning while misplaced URI, encoding, declaration, and manifest-provenance rules move to their subject owners without semantic change |
| logical prose | affected; Part 02 gains the general declaration and binding model, kind meanings, instance modes, presence, and lineage fields |
| registry meta-schema | affected; generalized resource declarations and kind-specific contracts replace or subsume the table-only root |
| core registry | affected; every current table receives a resource declaration and non-table families are added |
| logical asset tables | affected; gain an explicit packet `resource_id` binding and lose duplicated physical `uri` and `format` columns |
| declarative rules | affected only where registry invariants validate declaration ownership, uniqueness, bindings, or policies; scientific Tier 2 table rules are unchanged |
| physical profiles | existing Part 03 encoding ownership is clarified, but its machine-readable capability descriptor remains a separate proposal |
| packet catalog | affected; Part 04 binds each entry to one declaration and removes or constrains redundant classification fields |
| manifest and resource-delivery schemas | affected in the later manifest reconciliation; this decision determines their declaration-binding and classification fields |
| validation and import | affected; registry validation covers resource declarations, and packet validation resolves classification, presence, catalog bindings, lineage, and producing runs from them |
| extension registries | affected; the same declaration model admits extension tables and extension-owned non-table families without core naming a particular extension |
| reader | affected; resource filtering and dispatch resolve declaration facts rather than trusting duplicated packet fields |
| writer | affected; staging accepts any declared resource kind, derives classification, emits required empty tables where selected, and applies lineage APIs to all resources |
| validator | affected; generated plans cover all declarations and reject absent, unmatched, multiply bound, or policy-inconsistent resource instances |
| adapters | contract is affected only at the resource-delivery boundary; source-format knowledge and delivery protocols remain unchanged |
| existing packets | incompatible development shape; fixtures and generated packets are regenerated rather than migrated in place |
| conformance fixtures | affected; add missing required-resource, unknown declaration, wrong binding, catalog-row mismatch, extension array, non-table lineage, and analysis-canonicality cases |
| implementation tests | affected in reader, writer, validator, extension tooling, registry generation, and cross-package integration |
| revision lifecycle and tooling | unchanged; ordinary specification-domain lifecycle applies |
| generated publications | affected through normal registry tables, fact regions, headings, and combined-spec generation |
| developer documentation | affected after incorporation; registry author and extension author guides need examples of each instance mode |

## 6. Resolved direction

The proposal advances the following decisions together:

1. Generalize the existing logical registry so resource declarations are primary. Do not add a
   companion resource registry or preserve `tables` as a second authority.
2. Require every manifest resource, including a singleton table, to name its `declaration_id`.
   Remove the duplicated `layer`, `kind`, and `canonical` fields rather than treating them as
   checked packet projections.
3. Declare presence per resource. `core.sessions` is the unconditional required singleton; other
   resources become necessary through their own required declaration, an explicit declaration
   dependency, a populated foreign key, or an exact catalog-row binding. Analysis declarations and
   resource families are otherwise optional. Extension singletons state their own presence.
4. Derive canonicality solely from content class. Core and extension resources are canonical;
   analysis, compatibility-projection, and documentation resources are noncanonical.
5. Limit logical kind to `table`, `dense_array`, `media`, and `document`; represent stored
   materialization versus view separately.
6. Use required or optional singletons, optional families, exact catalog-row binding, explicit
   dependencies, and existing foreign-key semantics as the complete v0.2 presence model. Do not
   add a general condition language without a demonstrated requirement.
7. Give each catalogued non-table row a required, unique packet `resource_id` that binds exactly
   one manifest resource. Retain assigned integer IDs and source-name fields for their existing
   distinct roles, and remove physical `uri` and `format` from logical asset tables.
8. Add an optional, noncanonical `documentation` content class for human-readable sidecars. Keep
   it distinct from the `document` logical kind and from machine-interpreted control artifacts.

Portable-profile encoding and capability declarations are deliberately excluded. They require a
separate physical-layer proposal and descriptor owned by Part 03. This proposal establishes only
the logical declaration fields and the packet binding that the later physical model will consume.

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
- [ ] The proposal has explicit approval to advance to a revision draft.
