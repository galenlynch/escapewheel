# Part 02 — Core Logical Schemas

Normative.

<a id="ew-core-logical-schema-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part defines how a logical resource is declared, what each kind of declaration contains, and
which core and analysis resources the incorporated registry comprises.

The logical standard defined by this part is identified by `escapewheel-logical-v0.1`.

The column-level definitions themselves are not written here. They are data (§9), carried in a registry document that a packet embeds and that generates the checks of Part 05. This part is the rules the registry obeys; the registry is the schema.

This part expressly incorporates the following artifacts:

| artifact | normative extent |
|---|---|
| `artifacts/registry.schema.json` | exact local JSON structure and conditional shape constraints |
| `artifacts/registry_contract.schema.json` | exact structure of a registry-contract descriptor |
| `artifacts/registry_contracts/escapewheel-registry-contract-v0.10.json` | exact contract selectors, phase order, invariant IDs, applicability, and owning anchors |
| `artifacts/logical_schemas.json` | exact current core and analysis resource declarations, including table columns, keys, references, vocabularies, and rules |

The generated core registry is what a packet embeds. `informative/tables.md` is a generated,
informative listing of the same declarations. This part owns the declaration model, conformance
algorithms, and meanings. A disagreement among the part and its incorporated artifacts makes the
specification candidate internally inconsistent.

<a id="ew-table-resource-requirements" data-spec-anchor="canonical"></a>
## 2. Logical resource declarations

Each member name of the root `resources` object is a declaration ID. A declaration ID MUST match
`^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`. The core registry is the exact declaration authority for
the `core` and `analysis` namespaces. An extension registry is the sole declaration authority for
the namespace equal to its `extension_id`.

A generated table-only implementation view MAY select table-kind declarations, but it MUST be
derived from `resources` and MUST NOT be serialized as a second authority.

<a id="ew-resource-common-fields" data-spec-anchor="canonical"></a>
### 2.1 Common fields

Every resource declaration contains exactly these common fields, plus the kind-specific field §2.3
permits:

- `content_class`, governed by §2.2;
- `kind`, one of `table`, `dense_array`, and `opaque`;
- `instances`, a closed object governed by §2.4;
- `requires`, an array of distinct declaration IDs, empty where there is no explicit dependency;
  and
- `lineage`, one of `forbidden`, `optional`, and `required`.

<a id="ew-resource-content-class" data-spec-anchor="canonical"></a>
### 2.2 Content class and canonicality

The `content_class` vocabulary and its consequences are:

| value | meaning | canonical | required by class |
|---|---|:---:|:---:|
| `core` | normalized facts of the core vocabulary | yes | no |
| `extension` | typed facts owned by a domain | yes | no |
| `analysis` | products reproducible from canonical resources | no | no |
| `compatibility_projection` | a projection into another representation | no | no |
| `documentation` | sidecars, which a packet lists and asserts no semantic or conformance fact through, and the tables that list them | no | no |

Canonicality is derived from this table and MUST NOT be independently declared. Promoting a
resource into the canonical set changes its declaration's content class through a specification
or extension-registry change; an implementation MUST NOT promote it with a Boolean.

A **sidecar** is an opaque resource of class `documentation`: one that a packet lists and through
which it asserts no semantic or conformance fact. The class also covers the tables that list
sidecars (§12.10). A sidecar MAY be read by a person or by a program. This specification defines no
behavior of a reader, a writer or a validator that interprets a sidecar's contents.

Listing a resource as a sidecar records no dependence on it: the rule below forbids a canonical
declaration a reference, a `requires` entry or a catalog binding that targets a documentation
declaration, and §2.7 permits no lineage from one. A registry's author who needs a table to
reference a payload, or a rule or a reader to interpret one, therefore declares it as a canonical
resource. A machine-interpreted control artifact does not acquire documentation semantics merely
because its serialization is a document. A payload that a result in the packet was computed from is
recorded by the provenance tables ([Part 04 §7](04_packet_catalog.md#ew-resource-lineage)), and the
same payload MAY also be listed as a sidecar.

The core registry MUST NOT declare `extension`. An extension registry MAY declare `extension`,
`analysis`, `compatibility_projection`, or `documentation` in its own namespace and MUST NOT
declare `core`. Every `analysis` and `compatibility_projection` declaration requires lineage.
Every `documentation` declaration forbids lineage. These three
classes are optional under §2.5.

A registry document MUST NOT declare a `core` or `extension` resource that has a table reference,
a `requires` entry or a catalog binding targeting an `analysis`, `compatibility_projection` or
`documentation` declaration. A non-canonical resource holds no fact a canonical one may depend on,
and a writer may delete any analysis resource
([Part 06 §2](06_analysis_layer.md#ew-analysis-rules)), which would leave a canonical
resource depending on one without its target. §2.7 states the same relation for lineage. A
discriminator names a resource without depending on it
([Part 09 §6.2](09_metadata_and_extensions.md#ew-core-extension-discrimination)), so this rule
does not reach one. Which registry a declaration may target is
[Part 09 §6.1](09_metadata_and_extensions.md#ew-core-extension-reference-direction)'s rule.

<a id="ew-resource-kind" data-spec-anchor="canonical"></a>
### 2.3 Kind

The logical kind states which generic payload structure, if any, Escapewheel interprets:

| kind | generic payload contract | kind-specific declaration |
|---|---|---|
| `table` | rows and declared columns | required `table` object |
| `dense_array` | an n-dimensional dense array with declared logical axes | required closed `array` object containing `axes_resource` |
| `opaque` | a payload with no generic Escapewheel logical model | none |

A table declaration MUST contain `table`, MUST NOT contain `array`, and MUST use singleton
instances. Its `table` object contains an ordered column list (§3), a primary key or `null`,
references (§7), Tier 2 rules (§10.2), and amendment groups (§2.8).

A dense-array declaration MUST contain `array`, MUST NOT contain `table`, and MUST use catalog
instances. Its `axes_resource` MUST name a visible singleton table declaration. The axes table MUST
have exactly one binding reference to the array declaration's catalog table: the reference targets
the complete catalog primary key, its local columns lead the axes table's primary key, and that
primary key adds exactly one required structural-index column. Presence of a dense-array instance
makes its axes-table singleton necessary. Part 03 follows this declaration and MUST NOT hardcode an
axes resource.

An opaque declaration contains neither kind-specific object and may use any instance mode. Opaque
qualifies only the generic payload model. Escapewheel still identifies, locates, integrity-checks,
and records provenance for the resource; related declarations and tables may describe its
scientific meaning. Generic code is not thereby required to parse, decode, or render its payload.

Stored materialization and view are realizations, not kinds. `view`, `materialized_table`,
`dense_array_asset`, `media_asset`, and `document_asset` MUST NOT be registry kinds.

<a id="ew-resource-instance-model" data-spec-anchor="canonical"></a>
### 2.4 Instance modes

An `instances` object matches exactly one closed form:

| mode | required fields | packet binding |
|---|---|---|
| singleton | `mode: "singleton"`; `presence` is `required` or `optional` | the declaration ID is the only permitted packet `resource_id` |
| catalog | `mode: "catalog"`; `catalog_resource`; `resource_id_column` | zero or more resources bind one-to-one to rows of the named singleton table |
| family | `mode: "family"` | zero or more resources bind only by declaration ID |

A family resource ID is packet-unique and dotted within a namespace the declaration's registry
owns. A catalog resource and column satisfy §2.6.

<a id="ew-resource-presence" data-spec-anchor="canonical"></a>
### 2.5 Presence and dependencies

`core.sessions` is a required singleton. Every other currently incorporated table is an optional
singleton. An extension selects required or optional for each singleton; binding that extension
registry in a packet under [Part 04 §8](04_packet_catalog.md#ew-packet-registry-bindings)
activates its required declarations. Merely installing a registry does not. A singleton
declaration whose content class is `analysis`, `compatibility_projection` or `documentation` MUST
declare `presence` `optional`.

A packet contains an instance when any of these conditions applies:

- it is a required singleton in an active registry;
- a present declaration names its singleton declaration in `requires`;
- a populated table reference targets its singleton table declaration; or
- a catalog row requires that exact family instance under §2.6.

An absent optional singleton creates no empty table. A present table may contain zero rows unless
another rule requires rows. Catalog and family declarations have no minimum instance count.

Each `requires` member resolves under the same visibility and direction rules as a reference and
names a singleton. A present instance requires the transitive closure of those dependencies.
Dependency cycles are permitted only where every member is a singleton; presence of one then
requires the entire cycle.

<a id="ew-resource-catalog-binding" data-spec-anchor="canonical"></a>
### 2.6 Catalog binding

A catalog declaration's `catalog_resource` MUST name a visible singleton table declaration, and its
`resource_id_column` names one column of that table. That column MUST be a required string
identifier with carried identity and free vocabulary. An extension catalog may
name a core table or one in the same extension; a core catalog MUST NOT name an extension table.
Within one visible core-and-extension context, no two catalog declarations may name the same
table-and-column pair.

For every catalog row, a conforming packet contains exactly one entry whose `resource_id` equals
the row's catalog resource-ID value and whose `declaration_id` names that catalog family. Every
entry in the family matches exactly one row. Catalog resource-ID values and packet resource IDs are
unique.

Four catalog tables carry `resource_id`: `core.array_assets`, `analysis.array_assets`,
`core.media_assets` and `core.sidecars`. In the first three an assigned integer, `array_asset_id`
or `media_asset_id`, remains the primary key and row identity, and its `*_name` the source-label
bridge. In `core.sidecars`, `resource_id` is the primary key and the table has neither. None of the
four carries `uri` or `format`: location belongs to Part 04 and physical encoding to Part 03, and
`core.sidecars.media_type` states no physical encoding that Part 03 defines.

A registry MUST declare every column named `resource_id` as a required `string` identifier with
carried identity and free vocabulary, whether the column is a catalog table's field or references
one. Neither §4's integer `_id` rule nor the integer type §5.3 gives an identifier applies to a
column of that name.

<a id="ew-resource-provenance-policy" data-spec-anchor="canonical"></a>
### 2.7 Lineage policy

The `lineage` field governs the packet entry's `derived_from`. `forbidden` requires absence,
`optional` permits presence, and `required` requires presence. A present lineage is a nonempty array of
distinct existing packet resource IDs.

Lineage edges obey this relation:

| derived class | permitted source classes |
|---|---|
| `core` | `core` |
| `extension` | visible `core` and same-extension `extension` |
| `analysis` | `core`, `extension`, `analysis` |
| `compatibility_projection` | `core`, `extension`, `analysis` |
| `documentation` | none |

The lineage graph contains no self-edge or cycle. Because every analysis resource has nonempty
lineage, every finite analysis chain terminates in canonical core or extension resources. A writer
and validator apply this policy without regard to kind. [Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance) has a reader expose the
resolved facts.

<a id="ew-amendment-groups" data-spec-anchor="canonical"></a>
### 2.8 Amendment groups

Every `table` object carries `amendment_groups`, an array of **group lists**, beside its columns,
primary key, references and rules. A group list is a nonempty array of distinct column names of the
table. Under one group list, the rows whose listed columns hold equal values, a null equal to a
null, form one **group**. A group list **carries** each declared reference whose source columns are
all members of the list, where the referenced table has a column named by each other member: the
referenced row is then the one the group describes. A version **holds** a group where it holds a row
of the group, or where the list carries at least one declared reference to a table that does not
declare `[]` and each such reference resolves, on the group's values, to a row that version holds. A
canonical table a version's manifest does not name holds no rows in that version. A table an
amendment may not add rows to declares `[]`.
[Part 05 §15.2](05_validation_and_import.md#ew-amendment-scope) lets an amendment add rows to a
table only in groups its superseded version does not hold.

A packet holding a stream therefore holds the stream's group of `core.events` before the stream has
an event, since that table's list carries `stream_id`'s reference to `core.event_streams`. A packet
holding a frame holds a basis's group of `core.electrode_coordinates` only where it holds
coordinates in that basis, since the table's first list carries no reference to
`core.coordinate_frames`, which has no `coordinate_basis` column. The lists of `core.intervals`, the
second of `core.unit_quality_labels`, the first of `core.electrode_coordinates` and the second of
`core.unit_coordinates` carry no reference, since an interval kind, a label source and a coordinate
basis name no row, so a group under those is held only by its rows.

A group list MUST name only columns whose presence is `required` or `nullable`. Two group lists of
one table MUST NOT name the same set of columns. A table whose content class is not canonical MUST
declare `[]`, since an amendment may replace such a resource whole.

<a id="ew-column-declaration" data-spec-anchor="canonical"></a>
## 3. Column declaration

Every column MUST declare a name, a type, a presence, and a role. The role and type determine which
other fields the column requires or permits.

| attribute | required | clause |
|---|---|---|
| `name` | yes | §4 |
| `type` | yes | §5 |
| `presence` | yes | §6 |
| `role` | yes | §8.1 |
| `identity` | for identifiers | §8.2 |
| `finite` | for `float32` and `float64` columns | §5.4 |
| `enum` | for closed vocabularies | §9.3 |
| `resolves`, `discriminates`, `discriminates_via` | as applicable for discriminators | §8.3 |
| `unit`, `unit_from`, `clock_from` | where applicable | §8.4 |
| `authority` | where named nomenclatures cover the column | §9.3 |
| `description` | for an open vocabulary | §9.3 |

A description MUST NOT contradict or override a machine declaration. Concise, non-duplicative
wording remains authoring style rather than a registry-conformance comparison of English text.
The one description compared literally is the standard `metadata` description in §8.6.

<a id="ew-logical-column-naming" data-spec-anchor="canonical"></a>
## 4. Naming

Resource names and column names MUST be lowercase snake case. Registry conformance enforces these
relations in both directions where stated:

- an identifier has an `_id` name, and an `_id` name declares an integer identifier, except that
  a column named `resource_id` is a string identifier with carried identity (§2.6);
- a coordinate has a `_tick` name, and a `_tick` name declares a coordinate;
- a structural index has an `_index` name, and an `_index` name declares a structural index or
  sequence position;
- an `_name` name declares a string; and
- an `_uri` name, or the bare name `uri`, declares a string.

A checker determines discriminator behavior from its declaration and MUST NOT infer it
from a `_kind` suffix. Column order, adjacency, reserved-word preferences, plural-name preferences,
and the vocabulary of same-spelled columns are authoring conventions rather than registry
conformance requirements.

A source-provenance label — `local_electrode_label`, `local_channel_label`, `local_unit_label`, `local_interval_label` — is a `string` carrying whatever base the producing software used, and a consumer MUST NOT use it as an offset into any packet resource.

## 5. Type system

### 5.1 Permitted types

A column's type MUST be one of:

```text
string  int32  int64  float32  float64  bool  timestamp  date  json_string
```

<a id="ew-no-nested-types" data-spec-anchor="canonical"></a>
### 5.2 No nested types

A column's type MUST NOT be `list`, `struct`, or `map`. A registry document MUST declare a repeated value, a fact holding zero or more values for one row, as a child table, and MUST NOT declare it as a delimited string or as JSON. No checker verifies this beyond the type prohibition above. A semi-structured value becomes a `json_string` in an optional column.

This keeps a conforming reader able to satisfy every required column without a JSON parser, and keeps every value within reach of a rule: Part 11 binds no collection type and admits no routine that reads inside one, so a rule can check a repeated value, a reference included, only where each value is its own row.

A value that varies per row and is queried belongs in a typed column of a specialising resource; a value constant across the table belongs once, on the table that owns the whole. §8.6 states what a `metadata` column may hold, and §12.6 what `core.processing_runs.parameters` may hold. Part 05 §3.2 and Part 05 §4.3 state what a build records in an import run's `parameters`, and Part 06 §5 what a writer records in a materialization run's. Part 01 §3.11 permits an event a structured payload. No part states what `core.events.payload` or `core.sorting_runs.parameters` holds. The core registry declares which of its columns are `json_string`, as the declaration authority for the `core` and `analysis` namespaces (§2).

<a id="ew-fixed-representations" data-spec-anchor="canonical"></a>
### 5.3 Fixed representations

A writer MUST NOT use wraparound, truncating or saturating semantics for a value whose role is `identifier`, `coordinate`, `structural_index` or `sequence_position`, nor for arithmetic over interval bounds. Where a conversion's result would fall outside the declared type, it MUST fail before the value is written, naming the column and the value. A validator is not required to re-derive this: a wrapped value is a valid value of its type and the evidence is gone by the time rules run.

Tick columns MUST be `int64`. Wall-clock columns MUST be `timestamp` with microsecond precision in
UTC. Identifier columns MUST be `int32`, except where the number of distinct values may exceed
`int32`, where the column MUST be `int64`, and except a column named `resource_id` (§2.6).
No core table is near the integer bound; an extension declaring an integer identifier over more
than 2^31 rows declares `int64` for it.

<a id="ew-finite-values" data-spec-anchor="canonical"></a>
### 5.4 Finite values

A value of a `float32` or `float64` column is **non-finite** when it is NaN, positive infinity, or
negative infinity. Every other non-null value of those types is finite, and null is neither.

Every column whose type is `float32` or `float64` MUST declare `finite`, a boolean, and a column of
any other type MUST NOT declare it. There is no default, so an absent declaration is a defect
rather than a claim.

- `finite: true` declares that the column holds no non-finite value. A packet MUST NOT hold a
  non-finite value in such a column.
- `finite: false` admits non-finite values. A Tier 2 rule reading such a column sees them in the
  order [Part 11 §5](11_tier_2_rule_language.md#ew-tier-2-deterministic-semantics) defines.

A column declares `finite: false` only where a non-finite value carries a meaning no finite value
can, such as an interval with no end, and the column's `description` MUST state what each
non-finite value it admits means. No checker verifies this, since a description is prose. A
computation whose result is non-finite where the column gives that result no meaning has computed
nothing, and its value is null under [§6.3](#ew-absence); a non-finite value in a column is
therefore always one its description gives a meaning.

<a id="ew-column-presence" data-spec-anchor="canonical"></a>
## 6. Presence

A column is `required`, `nullable` or `optional`:

| state | the column | its values |
|---|---|---|
| `required` | MUST be present | MUST be non-null in every row |
| `nullable` | MUST be present | MAY be null |
| `optional` | MAY be absent | MAY be null where present |

A conforming reader must be able to satisfy every required column without a JSON parser, so a
column holding `json_string` is always optional.

A present nullable column is preferred to an absent one, because a stable column set simplifies query code. A schema MUST NOT declare a column that duplicates what the data already declares: `core.array_assets` carries no dtype or shape, because the array declares them.

Duplication is permitted only where it buys otherwise-unavailable access. Axis names are carried in `core.array_dimensions` because a Zarr binding in another language cannot see them.

<a id="ew-undeclared-columns" data-spec-anchor="canonical"></a>
### 6.1 Undeclared columns

A table MUST NOT hold a column that its declaration does not declare. Its declaration is the one its
resource entry's `declaration_id` names in a registry the packet's manifest binds
([Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance)). A column is undeclared
whatever its values, every value null included, and whatever wrote it.
[Part 05 §5.3](05_validation_and_import.md#ew-validation-shim) has a validator report one, and
[Part 05 §3.5](05_validation_and_import.md#ew-recipe-check) has an amending build refuse or drop one
a held table carries.

<a id="ew-null-naming-columns" data-spec-anchor="canonical"></a>
### 6.2 Nulls in naming columns

A null in a column whose role is `identifier` or `discriminator` states only that the row names
nothing in that column. It states neither that nothing exists to name nor that something exists
that the row does not name, and a consumer MUST NOT conclude either from the null. A consumer that
reports what such a column names MUST report, for a null, that the packet names nothing there. A
consumer that does not report what the column names owes only the first of these. No checker
verifies either.

This reading holds for such a column whatever registry declares it, except where a numbered part
gives a null in that column another reading.
[Part 03 §6.3](03_portable_physical_profile.md#ew-array-axis-coordinates) gives the only other
readings: a null `label_id` on `core.array_labels` or `analysis.array_labels` states padding, and a
null `coordinate_resource`, `coordinate_array_asset_id` or `clock_id` on `core.array_dimensions` or
`analysis.array_dimensions` says the axis does not take that coordinate form. A consequence a
numbered part attaches to a row that names nothing, such as an undeterminable discriminator row
([§8.3](#ew-discriminator-semantics)), an undeterminable run scope (Part 01 §2.6) or an unrecorded media device
([Part 01 §3.18](01_semantic_standard.md#ew-media-asset-concept)), is not another reading and
stands.

<a id="ew-one-null" data-spec-anchor="alias"></a>
<a id="ew-absence" data-spec-anchor="canonical"></a>
### 6.3 Absence

A column value is present or null; there is no second marker. A value that is inapplicable, one
that was never recorded, one a source recorded as unknown and one that could not be computed, such
as a ratio of zero to zero or the mean of no values, are each null. A writer MUST NOT adopt a
sentinel value meaning absent. Where the reason for an absence matters, a registry records the fact
that distinguishes it in a column of its own rather than encoding the reason in the value: a run's
`scope` distinguishes an undeterminable scope from an unambiguous one, and `normalized_label` is
null where a source's label has no honest projection.

A table whose file omits an `optional` column holds null in that column in every row. A reader
need not expose the omitted column, and one that does MUST expose it as null in every row.
[Part 11 §3](11_tier_2_rule_language.md#ew-tier-2-relation-environment) still exposes no omitted
column to a rule, which [§10.2](#ew-tier-2-rules) keeps from naming one.

Where a writer cannot tell whether a source's non-finite value is a value or an absence, it MUST
write null. One null merges every reason a value is absent, so the conversion states nothing the
source did not. No checker verifies this, since a packet does not hold what the source meant.

Every element of a dense array is a value, an element of a chunk the array does not store
included, and this specification defines no marker of an absent element. A NaN or a `fill_value`
in an array is therefore a value, whose meaning the array's data type states where it states one.
A data type that needs to say a stretch or a channel holds no observation states it as rows, such
as an interval of a kind it specialises or a status of the channel.

<a id="ew-logical-references" data-spec-anchor="canonical"></a>
## 7. References

A table declares each foreign key as a reference naming the target resource, this table's columns, and the target's columns. A reference MAY be composite, nullable, or self-referencing, and MAY declare `specialises`, naming the discriminator whose rows its table specialises (§8.3).

Where a reference has a populated source value, the packet MUST contain the target singleton table
resource. This presence consequence is in addition to row-level foreign-key resolution.

A reference's source and target lists MUST be nonempty, contain no duplicate member, and have equal
arity. Every source and target member MUST resolve. The target list MUST equal the target table's
complete, non-null primary key in declared order.

Each paired column MUST have the same type and role and, where it is an identifier, the same
identity. A data column paired with a discriminator as the declared shared key is the sole role
exception. A join is on values: columns of different types resolve to each other not at all, and
relating an assigned identifier to a carried one resolves to nothing.

Where §5.3 requires `int64` of an identifier whose distinct values may exceed `int32`, every column referencing it is `int64` too — the escape is taken on both sides or on neither, since a narrow column referencing a wide one truncates silently.

<a id="ew-session-scope" data-spec-anchor="canonical"></a>
### 7.1 Session scope

A table is **session-scoped** exactly where it has a session-preserving reference path ending at
`core.sessions`; the zero-edge path makes `core.sessions` the base case. A session-scoped table
MUST carry a required `int32` identifier named `session_id` with assigned identity. A table without
such a path MUST NOT carry that column.

A reference is a session-preserving edge only where:

1. its source contains `session_id` exactly once and maps it at the same position to the target's
   `session_id`;
2. every source member is required;
3. the target is the complete non-null primary key required by §7; and
4. every pair satisfies §7's type, role, and identity compatibility rules.

The path MUST consist only of session-preserving edges and MUST terminate at
`core.sessions.session_id`. Graph reachability, a cycle, or a reference carrying a different
identifier does not prove session scope. Packet validation enforces the ordinary foreign-key
anti-join at every edge and need not execute a recursive row query.

A writer fills the column from the parent row it already read, or from the session it was constructed with, and MUST NOT infer it from a name: a file path and a packet directory both spell a session, and neither is a statement this specification constrains.

## 8. Column semantics

### 8.1 Role

Every column MUST declare exactly one role, from a closed vocabulary with no default:

| role | meaning |
|---|---|
| `data` | a value to be read |
| `identifier` | a stable identity, per §8.2 |
| `coordinate` | a position on an axis, such as a tick |
| `structural_index` | a zero-based offset into a stored sequence |
| `sequence_position` | an ordinal within an ordered set |
| `discriminator` | a value naming the resource another column resolves against |

The role is what makes index-base conversion derivable from a packet rather than hard-coded in each one-based client. A `structural_index` converts at the client boundary; a `coordinate` does not.

### 8.1.1 Index base

A **structural index** addresses a position in a stored resource and MUST be a **0-based offset**. A client converting to a 1-based language MUST convert at the boundary; the format picks one base and clients adapt, because an offset whose base changes per reader is not an offset.

A **source label** is copied verbatim from acquisition or sorting software. Its base is whatever that software used, and a consumer MUST NOT use it as an offset into any packet resource.

A **coordinate** is neither: copied verbatim like a source label, but used arithmetically, which a source label MUST NOT be. Its zero is where its clock's origin says it is.

Because a reference relates columns of the same role (§7), converting every structural index at a boundary is join-preserving by construction.

<a id="ew-identifier-semantics" data-spec-anchor="canonical"></a>
### 8.2 Identity

An `identifier` column MUST declare `carried` or `assigned`. A table owns an assigned identifier
exactly where the identifier is in its primary key and is not a source member of a reference the
table declares. For every owned assigned identifier, the table MUST declare exactly one
corresponding name formed by replacing `_id` with `_name`. The name MUST be a string data column
whose presence is `required`, and MUST NOT declare `identity`.

A table that merely carries or references an assigned identifier MUST NOT declare that same-base
`*_name` column. A carried identifier likewise gets no corresponding name column: its value is
already the source's own identity.

An assigned identifier's `*_name` MUST be unique within its packet. A name column pairing with no assigned identifier names a kind of thing, such as `core.sorting_runs.sorter_name`, and is expected to repeat. The registry-document contract checks, as `registry.identity.name`, the pairing and the name's presence together. A checker reports that invariant for an owned assigned identifier whose name is absent, declared twice, not a `string` `data` column, declaring `identity`, or of a presence other than `required`, and for a table that carries or references an assigned identifier and declares the same-base name.

A generated check (§10.1) reports two rows of one table that carry one name. No check reports two things a writer merged under one name: a writer numbering an assigned identifier per distinct name emits one row per name, so two things wrongly sharing a name are already one row by the time the packet exists, and that row is indistinguishable from the correct case where four streams naming one serial become one device. The obligation not to merge falls on whatever composes the name.

<a id="ew-discriminator-semantics" data-spec-anchor="canonical"></a>
### 8.3 Discriminator

A `discriminator` column MUST be a `string` holding a dotted resource identifier — a namespace and
a table name, each lowercase snake_case — naming a table in the packet's registry or in one of its
extensions. Its value states the kind of the rows it specialises, its **specialised rows**, which
lie in its **specialised table**.

**A discriminator may lie one reference away.** A discriminator MAY be declared on its specialised
table, or on a table the specialised rows reach through one declared reference. In the second case
it MUST declare `discriminates_via`, naming the specialised table's referencing column as a dotted
`resource.column`, and the specialised table MUST declare exactly one reference in which that column
is a source member and the discriminator's table is the target.

A column copying a discriminator's value into a shared key is `data` and MUST NOT declare the
`discriminator` role, since it resolves nothing a consumer of its row does not already know. A
reference relating it to the discriminator it copies is the one role mismatch a reference may
carry.

**A discriminator declares whether it must resolve.** A discriminator MUST declare `resolves`, which
has no default:

| `resolves` | an unresolvable value is |
|---|---|
| `required` | a defect: the row is uninterpretable |
| `optional` | a fact: the packet does not hold that resource |

**A discriminator resolves through a shared key or a paired value.** Resolution reads a row's kind,
takes that resource's key from the registry, and joins; Part 05 §13.4 has a reader offer it. The
join takes one of two shapes, and a discriminator MUST NOT declare `positions_in`:

- in a **shared key**, the specialised row and a row of the named resource share a key; and
- in a **paired value**, a column of the specialised table holds the key of a row of the named
  resource.

**A shared key relates a detail row to its specialised row.** A reference declaring `specialises`,
a dotted `resource.column` naming a discriminator, is a **specialising reference**. Its table is a
**detail table** of that discriminator, a row of it is a **detail row**, and the row a detail row's
reference resolves to is its specialised row. Resolution joins a specialised row to the named
resource through that resource's specialising reference. A specialising reference MUST meet four
conditions:

- `specialises` resolves, under the visibility and direction rules of a reference target, to a
  discriminator column that declares no `discriminates`;
- the reference targets that discriminator's specialised table;
- the detail table's primary key begins with the reference's `columns`, in their order; and
- no other reference of the detail table declares `specialises`.

Every resource a shared-key discriminator names MUST be one of its detail tables. Where the
discriminator resolves `required`, the reverse check below reports a row naming any other resource;
where it resolves `optional`, no checker verifies this.

A packet MUST NOT hold a detail row whose specialised row's discriminator value is null or names a
resource other than the detail table. That value lies on the specialised row, or with
`discriminates_via` on the discriminator's row that the specialised row references.

A detail table carries the discriminator's value only where the discriminator is a member of the
shared key. `core.intervals.interval_kind` is not, so a table specialising an interval references
`core.intervals.interval_id` alone and carries no `interval_kind`.

A row's kind-specific facts live in a detail table. `core.devices` names such a table through
`device_kind`, and core MUST NOT declare a detail table of it, since Part 01 §3.17 makes this
standard name no instruments: a camera's target or a thermistor's range belongs to an extension. A
fact no detail table models stays in `metadata`, and a rule or a query that has to read it is what
justifies promoting it.

**A paired value holds the named row's key.** A paired-value discriminator MUST declare
`discriminates`, naming the column of the specialised table that holds the key, its **paired
value**. A paired value holds one key, so the named resource's primary key MUST be one column, and
the paired value MUST take one of two forms:

- a `string` `data` column, whose value matches the named key where that key is `carried` and its
  `*_name` where the key is `assigned`; or
- an `identifier` column whose type and identity equal the named key's, holding that key's value.
  A writer MUST fill it with the identifier it assigned the named row, as it fills any reference
  to that resource ([Part 05 §4.3](05_validation_and_import.md#ew-import-normalization)).

Without `discriminates_via`, the paired value and the discriminator share a table and one presence,
`required` or `nullable`, and a row MUST hold both values or neither. A row holding neither is
**undeterminable**, and a consumer MUST report it apart from a row whose value resolves to nothing:
the fix for one is to record the missing half, and for the other to correct what it names.

With `discriminates_via`, the paired value is `required` or `nullable`, and its row takes its kind
from the discriminator's row, so a null paired value is not undeterminable: the specialised row
names no row of that kind. A packet MUST NOT hold a specialised row whose discriminator value is
null, since that row would pair a value with no kind.

**Discriminators generate checks.** A validator MUST generate each check below for what its row
names, at **error**, and MUST generate a per-kind check once for each kind a packet's rows name:

| check | generated for | returns |
|---|---|---|
| specialisation | each specialising reference, whatever its discriminator declares for `resolves` | each detail row whose reference resolves and whose specialised row's discriminator value is null or is not the detail table's resource ID |
| forward | each discriminator resolving `required` | each row whose value names no resource the manifest declares |
| reverse | each shared-key discriminator resolving `required`, per kind | each row of the discriminator's table whose key has no counterpart in the named resource |
| key form | each paired-value discriminator resolving `required` | each named resource whose primary key is not one column of the paired value's form, built from the registry's key declarations as literals |
| paired value | each paired-value discriminator resolving `required`, per kind | each row whose paired value is not null and matches no row of the named resource |
| kind | each paired-value discriminator resolving `required` and declaring `discriminates_via` | each specialised row whose discriminator value is null |

A detail row whose reference resolves to nothing is left to that reference's anti-join. A reverse
check's counterpart is the row of the named resource whose specialising reference naming this
discriminator resolves to the discriminator's row, so a named resource declaring no such reference
holds none and the check returns every row naming it. Where a discriminator resolves `optional`,
none of the last five checks is generated, and an unresolvable value is reported as `info`.

Every generated check MUST be built over **every resource the packet declares, extensions
included**. A check built over core alone lets an extension kind match no branch and pass in
silence, which is the one case the mechanism exists to cover.

Core MAY name an extension's resource through a discriminator and MUST NOT reference one. Naming
creates no dependency, so core stays checkable alone, an absent target is a reportable fact, and no
integrity constraint couples the versions.

<a id="ew-unit-and-clock-context" data-spec-anchor="canonical"></a>
### 8.4 Unit and clock

A `data` column carrying a physical quantity SHOULD declare its `unit`, or `unit_from` naming a column that carries it. A `coordinate` column MUST declare `clock_from` where the clock its ticks are on is not the one that row's `clock_id` names, and MUST declare it where the table has no `clock_id` at all. Measured across the registry, 6 of 20 coordinates declare one and the other 14 resolve to their own row's clock; none has neither.

`unit_from` and `clock_from` each name a column of the same table or a one-hop
`resource.column`. The latter form MUST resolve through exactly one reference the table declares.
A consumer resolves the source rather than guessing.

A **unit code** is an expression in the case-sensitive syntax of UCUM version 2.2, revision date
2024-06-17, as §13 identifies it. A **unit column** is a string column whose `authority` entries
include `https://ucum.org/ucum`. A column's literal `unit` MUST be a unit code, and a packet MUST
hold a unit code in every non-null value of a unit column. An annotation in curly braces, such as
`{adc}`, is a unit code and denotes a dimensionless quantity, which is the unit of a quantity
normalised by something the packet measured.

`unit` and `unit_from` are mutually exclusive. A `unit_from` target MUST be a unit column. For a
coordinate, the clock source is its explicit `clock_from` target where present and otherwise the
same table's `clock_id`. That source MUST be an identifier participating in a reference to
`core.clocks.clock_id`. `clock_from` MUST NOT occur on another role.

A consumer MAY label a quantity with its declared unit, and MUST NOT silently compare or combine two columns whose declared units differ. One vocabulary is what makes that rule run: `volts` and `V` differ while naming one unit, so without it the rule refuses a legitimate comparison exactly as readily as it catches a wrong one.

<a id="ew-functional-dependence" data-spec-anchor="canonical"></a>
### 8.5 Functional dependence

A column MAY declare `determined_by`, naming the columns whose values fix its own: two rows agreeing
on every column named agree on this one, and an empty list declares a constant. Every member MUST
resolve to a column of the same table, and no member may occur twice. The declaration is
structural, decidable from the registry with no packet in hand.

It is a statement about values and holds under any profile. What a profile does with it is the profile's: Part 03 §5.3 uses it to decide whether a table's stored order settles its primary key, and requires the scan establishing that order to verify the declaration against rows, because a wrong one waives a check rather than failing one.

<a id="ew-free-form-metadata" data-spec-anchor="canonical"></a>
### 8.6 Free-form metadata

A column named `metadata` MUST be an optional `json_string` data column with this exact
description: “What the source stated about this row that the standard does not model, carried in
the source's own vocabulary and read by no rule.”

A table's registry entry MUST declare `metadata` where its primary key includes an `identifier` column that is not part of a declared reference, MUST NOT declare one where every key column is part of a declared reference, and MAY declare one otherwise. An identifier of the table's own is what makes a row a thing rather than a statement about other things; a key made entirely of other tables' identifiers makes it a relationship, and nothing can be said about a relationship that is not a fact about one of its ends. Both bounds are decidable from the registry with no packet in hand, and the registry-document contract checks them as `registry.metadata.eligibility` against core and against every extension.

Where the key neither requires the column nor forbids it, declaring one is a judgement, and Part 05 §5.3's report of an unfilled `metadata` column is the evidence against which it is revisited.

A writer MAY fill `metadata` on every row of a table that declares it. Parquet reads the columns a query projects and no others, so a consumer who does not project the column does not read it.

A writer MUST NOT emit a `metadata` key holding a fact that a column of the logical schema holds, unless the duplication buys access that is otherwise unavailable, and MUST NOT emit one that contradicts such a column under any circumstance. The same otherwise-unavailable-access exception applies throughout the schema, so the bag is exactly as strict as the schema around it; a contradiction takes no exception, since it buys nothing by definition. A fact required to interpret the data belongs in a column, never in a key.

No rule checks either half and none is added. The content is schemaless by design, so a constraint on it is unenforceable in principle rather than merely in practice, and an adapter names a key in the source's vocabulary where core names a column in its own. The obligation binds the writer, which is the only party that knows what it put in the bag.

A writer MUST NOT put a mark, a value an event carries beyond its tick (Part 01 §3.12), in `core.events.metadata`. No checker verifies this.

A writer SHOULD put prose in a prose column where the table has one, and not in `metadata`. A human-readable string has no structure to preserve, so a JSON envelope costs a serialisation, puts the value where no rule reads it and no filter uses it, and buys none of the otherwise-unavailable access the exception above requires.

### 8.7 Coded values

A writer that can decode a source's code MUST store the decoded value, declaring the vocabulary it decodes onto as §9.3 requires of any other. A code is a token standing for something the emitting system names elsewhere, and a packet holding one without the key leaves no rule, query or reader able to tell one value from another.

A writer that cannot decode one stores the code itself, verbatim, in a `string` column declaring an open vocabulary, whose description names where the key lives. An undecoded code is a label carrying no contract, and an open vocabulary is how this standard declares one (Part 01 §3.17); an integer column declares nothing of the sort, since §9.3 permits a vocabulary on no other type and a code stored as an integer is indistinguishable from a count.

A source's own token is a string, kept as the source emitted it, and a consumer MUST NOT use it as an offset. This applies to a scorer's label and to a source-provenance label alike.

No rule checks either half, and none is added. Nothing structural tells a code from a count, so the obligation binds the writer, which is the party that knows whether it had a key.

## 9. The registry

<a id="ew-registry-document" data-spec-anchor="canonical"></a>
### 9.1 The schema is one document

Resource declarations, table structure, and validation rules are carried in one JSON document. Every registry document
MUST carry `$schema`, `registry_id`, `registry_version`, `logical_standard_version`,
`rule_language`, and `resources`, and MUST NOT carry `tables`.

`registry_id` names the document to a packet that binds it and matches `^[a-z][a-z0-9_]*$`. A core
registry's `registry_id` MUST be `core`. An extension registry's `registry_id` MUST equal its
`extension_id`, and therefore MUST NOT be `core`, `analysis`, or `nwb`.

A core registry MUST carry `semantic_standard_version` and MUST NOT carry `extension_id` or
`extends`. An extension registry MUST carry `extension_id` and MUST NOT carry
`semantic_standard_version` or `extends`. The presence of `extension_id` determines the document
class; caller context MUST NOT redefine it.

The selected rule language applies atomically to every Tier 2 rule. A rule MUST NOT repeat or
override it, and one document MUST NOT mix languages. Root, resource, instance, array, table,
column, reference, authority, and rule objects are closed. Registry-build `derived_from` and `since` fields are therefore
invalid; this does not affect the packet manifest's resource-lineage `derived_from`.

<a id="ew-registry-self-description" data-spec-anchor="canonical"></a>
### 9.2 Self-description

A packet binds each registry that declares its resources under
[Part 04 §8](04_packet_catalog.md#ew-packet-registry-bindings), and
[Part 03 §3.3](03_portable_physical_profile.md#ew-portable-bound-registries) owns how the portable
profile stores a bound registry.

The incorporated registry meta-schema has `$id`
`https://escapewheel.org/schemas/registry/0.12.0`. Every registry document conforming to that
schema MUST carry that value in `$schema`. A registry document SHOULD carry `$schema` as its first
member, so that the head of the file shows which meta-schema governs it; member order carries no
other meaning, and no checker verifies it. The incorporated core registry has `registry_id: core`,
`registry_version: 0.20.0`, `semantic_standard_version: escapewheel-semantic-v0.1`,
`logical_standard_version: escapewheel-logical-v0.1`, and
`rule_language: escapewheel-rule-sql-v0.2`.

An extension's `registry_version` identifies that extension registry and advances independently of
the core registry's version. An extension conforming to the incorporated meta-schema MUST carry
the full `escapewheel-logical-v0.1` logical-standard identifier and MUST NOT carry `extends`.
The core specification does not assign an extension's version. An extension registry migrated to
meta-schema 0.9.0 MUST carry a `registry_version` different from the one it carried under 0.8.0,
one migrated to `escapewheel-rule-sql-v0.2` a `registry_version` different from the one it carried
under `escapewheel-rule-sql-v0.1`, one migrated to meta-schema 0.10.0 a `registry_version`
different from the one it carried under 0.9.0, one migrated to meta-schema 0.11.0 a
`registry_version` different from the one it carried under 0.10.0, and one migrated to meta-schema
0.12.0 a `registry_version` different from the one it carried under 0.11.0. No checker verifies
any of these, since a checker reads only the document before it and not the version that document
replaced.

A checker selects schemas and contracts only from local artifacts and MUST NOT dereference an
identifier. An old registry document MUST NOT be silently interpreted under the new meta-schema
identifier. These development identifiers MUST NOT later be reused for an incompatible contract.

<a id="ew-registry-vocabularies" data-spec-anchor="canonical"></a>
### 9.3 Vocabularies

Every `string` column declares a `vocabulary`, whatever its role, except a discriminator, whose value space §8.3 fixes; a column of any other type declares none. There is no default, so an absent declaration is a defect rather than a claim of openness.

| value | what it says |
|---|---|
| `closed` | the column also declares `enum`, and a validator MUST reject a value outside it |
| `open` | the values name kinds of thing, comparable between packets; a validator MUST NOT reject an unrecognized one, except as stated below for a unit column, and the column MAY declare `reserved_values` |
| `free` | not a vocabulary — a name, a description, a URI, a digest, a version string, a person; nothing may be reserved and no report is due |

Four columns are closed:

| column | values |
|---|---|
| `core.processing_runs.status` | `succeeded`, `failed`, `partial` |
| `core.units.quality_label` | `sua`, `mua`, `noise` |
| `core.unit_quality_labels.normalized_label` | `sua`, `mua`, `noise` |
| `core.subjects.sex` | `male`, `female`, `hermaphrodite`, `other` |

A scorer's own `label` is open, because aggregating over scorers is incompatible with one closed set. A writer MUST record `core.unit_quality_labels.label` as the source emitted it and MUST NOT replace it with the value it projects onto, which belongs in `normalized_label`. Where a source's label has no honest projection onto `sua`, `mua` or `noise`, a writer MUST leave `normalized_label` null and MUST NOT force a value. No checker verifies either obligation: a packet does not hold what the source emitted, and no rule can tell a forced projection from an honest one.

`core.processing_runs.status` says whether the run completed: `succeeded`, it completed and its outputs are usable; `failed`, it did not complete; `partial`, it completed for some inputs only, so its committed outputs are incomplete.

A value MAY be reserved only where it is read **whole**: where a consumer comparing two packets learns something from the value alone, without knowing what either packet was doing. Where an external nomenclature defines the values instead, the registry names it rather than copying a set the standard does not itself define. A validator SHOULD report a value outside a reserved set at `info`, and MUST NOT fail on one. A writer MUST NOT write a value outside a column's reserved set for data that a reserved value describes. No validator checks this obligation: whether a value is a synonym of a reserved one cannot be decided from the packet, so it binds the writer, which alone knows what its data is.

An `open` column MUST carry a nonempty description stating the form its values take. A string data
column with an open or closed vocabulary MAY declare `authority`, a nonempty array whose entries
each carry a human-readable `name` and an absolute `uri` as RFC 3986
([Part 00 §9](00_architecture.md#ew-normative-references)) defines one. No URI may occur twice in one
array. An authority URI is identity rather than a fetch instruction: a validator MUST NOT
dereference one when checking a registry or a packet, and MUST NOT reject a value for being absent
from its column's authority. Neither this rule nor the `open` row above covers a unit column's value
that is not a unit code, which §8.4 makes nonconforming, because UCUM defines its codes by a grammar
rather than a list. An entry named `UCUM` MUST
use `https://ucum.org/ucum`, and an entry using that URI MUST be named `UCUM`.

Where a writer can identify the name that a nomenclature in an open column's `authority` registers
for the thing a value names, it MUST write that name as the nomenclature spells it. Otherwise, as
for a strain not yet registered or a source value matching no registered name, a writer MUST write
the value as the source states it. A validator verifies neither obligation, since it neither
dereferences an authority nor rejects a value for being absent from one. A unit column's value is
the exception: §8.4 requires it to be a unit code whatever the source states, and a validator
checks it by UCUM's grammar under [Part 05 §5.3](05_validation_and_import.md#ew-validation-shim).
[§13](#ew-logical-schema-normative-references) identifies each nomenclature the core registry names
in this way, and the edition that applies.

A closed column's `enum` is its whole value set and spells every value it admits. On a closed
column, `authority` records where the `enum`'s spelling came from and invokes no nomenclature.

`informative/tables.md` MUST render these declarations of a column from the fields holding them: its vocabulary, the closed set itself where the vocabulary is `closed`, its reserved values, its authorities by name, and a discriminator's `resolves`. That document is what a person reads to learn what a column is.

<a id="ew-registry-conformance" data-spec-anchor="canonical"></a>
### 9.4 Registry-document conformance

The incorporated registry-contract descriptor enumerates one complete, language-neutral
conformance contract. Its closed root contains `$schema`, `id`, `registry_schema`,
`semantic_standard`, `logical_standard`, `rule_languages`, `phases`, and `invariants`. Each closed
invariant entry contains exactly `id`, `phase`, `classes`, and `anchors`. The descriptor contains
identities and applicability only; it MUST NOT contain algorithms, executable expressions,
messages, exception lists, or implementation selectors. The prose in this part and Part 09 owns
the algorithms and meanings.

The incorporated descriptor has ID `escapewheel-registry-contract-v0.10`, selects the 0.12.0
meta-schema, and lists `escapewheel-rule-sql-v0.2` alone in `rule_languages`. That meta-schema MUST
declare `finite` as a boolean member of a column, require it where `type` is `float32` or
`float64`, and forbid it otherwise; the `shape` phase therefore decides §5.4's declaration rule, and
the descriptor adds no invariant for it. It MUST also require `amendment_groups` in the `table`
object, after `rules`, as a duplicate-free array of nonempty, duplicate-free arrays of names, and
admit `specialises` in the `reference` object as an optional member after `resource_columns`, a
string matching `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`. A checker MUST evaluate its
phases in this order:

1. `json`;
2. `schema_selection`;
3. `shape`;
4. `contract_selection`;
5. `semantic`;
6. `rule_static`; and
7. `external_domain`.

A byte-oriented entry point MUST decode UTF-8 JSON and reject every duplicate object member. A
mapping-oriented entry point begins after `json` and MUST NOT claim that the source bytes had
unique members.

After JSON decoding, a checker MUST inspect only root `$schema` to select a local meta-schema. A
missing or non-string selector makes the document invalid; an unknown selector makes evaluation
unsupported. The selected meta-schema validates the complete shape, and later phases MUST NOT
index into a shape-invalid document.

For a shape-valid core document, its class and declared registry-schema, semantic-standard,
logical-standard, and rule-language identifiers MUST select exactly one local descriptor. For an
extension, the tuple substitutes the required core context's semantic-standard identifier. No
component may be inferred or ignored. An unknown or ambiguous tuple makes evaluation unsupported.
A descriptor ID and a tuple that selected a contract MUST NOT be reinterpreted after publication.

Without usable core context, an extension's visible class, registry-schema, logical-standard, and
rule-language components MUST still select one unambiguous local descriptor before local checks
run. No match or more than one match is unsupported. One match supplies the invariant inventory;
only core-dependent evaluation is incomplete. An extension's core context is usable only where it
selected the same contract, is valid, and declares the extension's logical-standard identifier.
An absent, unsupported, incomplete, invalid, or mismatched core context makes core-dependent
extension phases incomplete, not invalid. Shape and available extension-local invariants still
run, and an independent invalid result dominates incompleteness.

Applicable semantic invariants run in descriptor order. Tier 2 rules then receive Part 11 static
validation. External lexical-domain validation runs last and offline. A checker that lacks the UCUM
edition §13 identifies MUST report the `external_domain` phase as `unsupported`, and MUST NOT judge
a literal `unit` by an approximation of that syntax.

The complete result contains the selected descriptor ID where selection succeeded, exactly one
overall state from `valid`, `invalid`, `unsupported`, and `incomplete`, and one record for every
phase in order. Every phase record has a state from `passed`, `invalid`, `unsupported`,
`incomplete`, and `skipped`, and ordered outcome records for each check that did not pass and each
check skipped within a partially evaluated phase.

An outcome record contains its state and stable schema, invariant, or rule-language outcome ID;
the owning resource or rule ID where applicable; and an RFC 6901 instance pointer. A skipped
outcome or phase also contains a stable reason ID. A mapping without byte locations still
preserves the pointer.

Pre-contract failures use these IDs:

- `registry.json.invalid_utf8`;
- `registry.json.invalid_syntax`;
- `registry.json.duplicate_member`;
- `registry.schema.selector_missing`;
- `registry.schema.selector_type`;
- `registry.schema.selector_unsupported`;
- `registry.contract.selector_unsupported`;
- `registry.contract.selector_ambiguous`; and
- `registry.contract.core_context_unusable`.

Skipped work uses these reason IDs:

- `registry.phase.mapping_input`;
- `registry.phase.prerequisite_invalid`;
- `registry.phase.prerequisite_unsupported`; and
- `registry.phase.prerequisite_incomplete`.

Schema findings use the selected meta-schema ID and schema-location pointer. Semantic and
external-domain findings use descriptor invariant IDs. Rule-static findings use Part 11 outcome
IDs and identify the owning rule. An outcome is a finding exactly when its state is `invalid`;
unsupported, incomplete, and skipped outcomes are not findings. A pre-instance outcome uses the
empty pointer. A duplicate-member outcome points to its containing object.

Within a phase, outcomes are ordered by instance pointer, outcome ID, then owner, comparing code
point for code point. A definitive violation dominates an independent unsupported or incomplete
phase; otherwise precedence is `invalid`, `unsupported`, `incomplete`, then `valid`. Only completed
passing phases produce `valid`. A checker MUST determine a partially evaluated phase's state from
its outcome records by the same precedence. A dependent skipped phase records its reason.

The descriptor assigns these invariants in this exact order:

| invariant ID | phase | classes |
|---|---|---|
| `registry.namespace.owned` | semantic | core, extension |
| `registry.namespace.reference_direction` | semantic | core, extension |
| `registry.column.name_unique` | semantic | core, extension |
| `registry.primary_key.resolves` | semantic | core, extension |
| `registry.reference.resolves` | semantic | core, extension |
| `registry.reference.target_key` | semantic | core, extension |
| `registry.reference.compatible` | semantic | core, extension |
| `registry.session_scope.path` | semantic | core, extension |
| `registry.identity.name` | semantic | core, extension |
| `registry.identity.registry_id` | semantic | extension |
| `registry.metadata.eligibility` | semantic | core, extension |
| `registry.determined_by.resolves` | semantic | core, extension |
| `registry.discriminator.declaration` | semantic | core, extension |
| `registry.discriminator.path` | semantic | core, extension |
| `registry.context_source.resolves` | semantic | core, extension |
| `registry.unit.ucum_2_2_cs` | external_domain | core, extension |
| `registry.authority.uri` | semantic | core, extension |
| `registry.rule.id_unique` | semantic | core, extension |
| `registry.rule.id_owner` | semantic | core, extension |
| `registry.rule.required_inputs` | rule_static | core, extension |
| `registry.core.device_detail` | semantic | core |
| `registry.resource.classification` | semantic | core, extension |
| `registry.resource.instance` | semantic | core, extension |
| `registry.resource.catalog` | semantic | core, extension |
| `registry.resource.array_axes` | semantic | core, extension |
| `registry.resource.dependency` | semantic | core, extension |
| `registry.resource.canonical_targets` | semantic | core, extension |
| `registry.amendment_groups.resolves` | semantic | core, extension |
| `registry.discriminator.specialisation` | semantic | core, extension |

Every descriptor anchor MUST identify every numbered-part clause defining the invariant. Invariant
IDs are unique. The descriptor schema closes its objects; requires nonempty, duplicate-free arrays;
and checks the identifier, class, phase, and canonical-anchor syntax stated by its incorporated
artifact. Every anchor MUST resolve uniquely in the numbered specification.

Column names and rule IDs are unique within a table and registry document respectively. A rule in
`namespace.table` has the exact form `namespace.table.local_rule_id`, where `local_rule_id` is one
lowercase snake-case identifier containing no dot. A non-null primary key has unique members, and
each member resolves once to a required column. A null key admits duplicate rows and cannot be a
reference target.

Every `determined_by` member resolves locally. A discriminator selects the paired-value shape by
declaring `discriminates` and the shared-key shape by not declaring it. The column `discriminates`
names resolves on the table `discriminates_via` names where the discriminator declares it, and on
the discriminator's own table otherwise; it is one `string` `data` column or one `identifier`
column; and it has the discriminator's non-optional presence on the discriminator's own table and
`required` or `nullable` presence on another. Target-specific row resolution remains packet
validation, not registry conformance.

In a core registry, no table other than `core.devices` may have a non-null primary key whose first
member is `device_id`. This structural condition reserves device-detail tables for extensions.
Each rule MUST pass Part 11's static contract, including rejection of every optional bound input.

The resource invariants enforce §§2.1–2.7: document-class/content-class eligibility; kind and
instance eligibility; unambiguous visible catalog bindings; the dense-array axes binding; visible
singleton dependencies; and canonical resources' canonical targets, whose outcome points at the
offending reference, `requires` entry or catalog binding and is core-dependent where the target
lies in the core context. `registry.amendment_groups.resolves` enforces §2.8: it reports a
group-list member naming no column of its table or a column whose presence is `optional`, two group
lists of one table naming the same set, and a nonempty `amendment_groups` on a non-canonical table.
Its outcome points at the offending member, at the later of two group lists naming one set, and at
`amendment_groups` itself on a non-canonical table. `registry.discriminator.specialisation`
enforces §8.3's specialising references: it reports a `specialises` value naming no visible column,
naming a column that is not a discriminator, or naming a discriminator that declares
`discriminates`; a specialising reference whose target is not the table its discriminator
specialises; a detail table whose primary key does not begin with its specialising reference's
`columns` in their order; and a table declaring `specialises` on more than one reference. Its
outcome points at the offending `specialises` member, at the later one of a table declaring two,
and is core-dependent where the discriminator lies in the core context. The existing table, column, reference, rule, and external-domain
invariants operate on the `table` payload of table-kind declarations. Their stable IDs do not
change merely because their instance pointers gain enclosing `resources` and `table` components.

This section defines an abstract result. Public APIs, command-line output, reports, exception
serialization, and the boundaries that require invocation are defined separately.

<a id="ew-registry-result-serialization" data-spec-anchor="canonical"></a>

### 9.5 Registry-result serialization

A portable registry result MUST validate against the incorporated closed Draft 2020-12 schema
`artifacts/registry_result.schema.json`, whose identifier is
`https://escapewheel.org/schemas/registry-result/0.1.0`. It contains the selected descriptor ID, or
null when contract selection did not succeed; the complete document state; and exactly the seven
phase records in the order defined in §9.4.

Each phase record contains its phase, state, and outcomes. A `skipped` phase also contains a stable
reason; another phase MUST NOT contain a phase reason. A `passed` or `skipped` phase has no
outcomes. An `invalid`, `unsupported`, or `incomplete` phase has at least one outcome.

Each outcome contains its state, stable ID, and instance JSON Pointer. It may contain its owner,
reason, schema-location JSON Pointer, and informative diagnostic detail. A skipped outcome contains
a stable reason. The `instance` and `schema_location` fields conform to RFC 6901. An implementation
MUST NOT let diagnostic `detail` determine conformance, equality, or ordering; no checker verifies
this.

The incorporated schema owns this representation's structure. Section 9.4 owns phase algorithms,
state precedence, applicability and ordering of outcomes, reason and outcome semantics, and when
the descriptor ID is null.

## 10. Validation rules

<a id="ew-tier-1-rules" data-spec-anchor="canonical"></a>
### 10.1 Tier 1: generated from structure

A validator MUST generate, from the declaration alone: required-column non-null checks, foreign-key anti-joins, and closed-vocabulary membership. A nullable foreign key is guarded with a null test.

A validator MUST also generate, from the declaration alone, for every column declaring
`finite: true`, a check that reports each row holding a non-finite value (§5.4) in that column, at
level `error`, under the check ID `<declaration_id>.<column>.finite`, such as
`core.clocks.tick_rate_hz.finite`. Where the column is `optional` and a table omits it, the check
reports nothing. The finding belongs to the registry holding the declaration under
[Part 05 §9.5](05_validation_and_import.md#ew-verdict-composition), and
[Part 05 §5.4](05_validation_and_import.md#ew-validation-extensions) applies the check to the columns
an extension declares.

A validator MUST also generate, from the declaration alone, for the name of every owned assigned
identifier (§8.2), a check that reports each row whose name another row of the same table holds, at
level `error`, under the check ID `<declaration_id>.<column>.unique`, such as
`core.units.unit_name.unique`. The check groups a table's rows on the name alone, whatever other
columns the table's primary key holds, and counts no null name. Two names are equal where their
sequences of Unicode scalar values are equal, compared as
[Part 11 §5](11_tier_2_rule_language.md#ew-tier-2-deterministic-semantics) compares characters,
without case folding or normalization. Where the name is `optional` and a table omits it, the check
reports nothing. A validator generates the check wherever a valid registry context directs packet
checks, whichever registry-contract descriptor that registry was checked under. The finding belongs
to the registry holding the declaration under
[Part 05 §9.5](05_validation_and_import.md#ew-verdict-composition), and
[Part 05 §5.4](05_validation_and_import.md#ew-validation-extensions) applies the check to the names
an extension declares.

A validator MUST establish that a table's primary key is unique, by query or by any means a physical profile defines as establishing it. That a key is unique holds under any profile and is this part's; how a validator may establish it depends on how rows are stored, and is the profile's.

<a id="ew-tier-2-rules" data-spec-anchor="canonical"></a>
### 10.2 Tier 2: declared

A rule the structure cannot imply declares `id`, `level`, `message`, and `sql`, or uses a named
template that the registry build expands to those fields. Its registry-level `rule_language`
selects the interpretation of `sql`; [Part 11](11_tier_2_rule_language.md) defines the current
language, relation mapping, and finding relation. A rule is logically attached to the resource
whose `rules` array contains it, but it may name other resources the selected language permits.

Rule IDs MUST be unique within a registry document. A rule held by `namespace.table` MUST have the
exact ID `namespace.table.local_rule_id`, where `local_rule_id` is one lowercase snake-case
identifier containing no dot.

A rule's SQL MUST NOT reference a column whose presence is `optional`. A rule is executed against the file, and `optional` permits the column to be absent from it (§6), so a rule naming one does not miss a check — the query fails to parse, and the run meant to find defects reports an error of its own. A constraint that wants an optional column either makes it `nullable`, which declares it always present and sometimes empty, or moves to the shim of §10.3.

The language contract determines the result relation. A completed empty result passes; a completed
non-empty result produces the declared finding. Invalid, unsupported, and incomplete evaluation
are not findings and cannot establish a pass (Part 11 §8).

A rule declares a level of `error`, `warning`, or `info`. A rule MAY be `advisory`. A validator MUST
NOT run an advisory rule unless its invocation asks for advisory rules, and an advisory rule MUST
NOT be `error`, so that enabling it cannot change whether a packet previously passed. Stated as the guarantee it is: **running with advisory rules enabled MUST NOT
change whether a packet passed**. A validator MUST expose the choice, and a report MUST state whether
advisory rules were run: two reports over one packet may legitimately differ, and one that does
not say which mode produced it cannot be compared with the other.

<a id="ew-tier-2-exclusions" data-spec-anchor="canonical"></a>
### 10.3 What is not a rule

A Tier 2 rule MUST NOT express physical order, file presence, Parquet types, Zarr rank and codecs, or checksums. These are checked by the shim of Part 05 §5.3.

<a id="ew-core-resource-index" data-spec-anchor="canonical"></a>
## 11. Core resource index

The incorporated registry comprises the following declarations. Table column definitions and the
common declaration fields are in the registry.

### 11.1 Session and subject

| resource | contents |
|---|---|
| `core.sessions` | one row per session; declares the reference clock and time origin |
| `core.subjects` | one row per subject |
| `core.session_experimenters` | experimenters, one row each |

### 11.2 Instruments

| resource | contents |
|---|---|
| `core.devices` | instruments used, each with the hardware revision and firmware version it ran |
| `core.probes` | devices carrying electrodes |
| `core.electrodes` | recording contacts |
| `core.electrode_coordinates` | a contact's position per frame and basis |
| `core.electrode_coordinate_values` | one row per axis of that position |
| `core.calibrations` | what was measured about an instrument so its numbers can be read |
| `core.calibration_devices` | the devices each calibration covers |
| `core.calibration_points` | the paired series of a calibration that is a curve |

### 11.3 Time

| resource | contents |
|---|---|
| `core.clocks` | declared counters, their rates, origins, and parents |
| `core.clock_anchors` | anchor pairs mapping a clock onto its parent |
| `core.clock_observation_intervals` | when each clock was observing |
| `core.clock_phase_steps` | the steps in a clock's alignment to its parent |

### 11.4 Structure

| resource | contents |
|---|---|
| `core.intervals` | bounded spans, discriminated by kind |
| `core.events` | timestamped observations, one per tick per stream |
| `core.event_streams` | what produced a set of events, and on what clock |
| `core.event_stream_observation_intervals` | a stream's refinement of its clock's window |

### 11.5 Sorting

| resource | contents |
|---|---|
| `core.sorting_runs` | what sorted what, on which clock |
| `core.sorting_run_channels` | the channels a run used, in the order it counted them |
| `core.curation_versions` | named states of a sorting's unit set |
| `core.units` | one row per unit per sorting and curation |
| `core.spike_events` | one row per spike |
| `core.unit_quality_labels` | one row per unit per scorer |
| `core.unit_electrodes` | the contacts a unit sits on |
| `core.unit_coordinates` | a unit's position per frame and basis |
| `core.unit_coordinate_values` | one row per axis of that position |
| `core.unit_observation_intervals` | a unit's refinement of its clock's window |

<a id="ew-core-array-media-resource-index" data-spec-anchor="canonical"></a>
### 11.6 Arrays and media

| resource | contents |
|---|---|
| `core.array_assets` | catalog rows describing core dense-array instances |
| `core.array_asset_instances` | dense-array resources catalogued by `core.array_assets.resource_id`, with axes in `core.array_dimensions` |
| `core.array_dimensions` | one row per logical axis, bound to its array catalog row |
| `core.array_labels` | the row each position of a labelled axis stands for |
| `core.array_channels` | per-channel scaling and acquisition shift |
| `core.media_assets` | catalog rows describing image and video instances |
| `core.media_asset_instances` | opaque resources catalogued by `core.media_assets.resource_id` |
| `core.media_frames` | frame timing |

### 11.7 Provenance

| resource | contents |
|---|---|
| `core.source_files` | inputs the packet was built from |
| `core.processing_runs` | activities that produced resources |
| `core.processing_run_inputs` | which files fed which run |
| `core.preferred_runs` | which of several coexisting results to use |

<a id="ew-analysis-resource-index" data-spec-anchor="canonical"></a>
### 11.8 Analysis

| resource | contents |
|---|---|
| `analysis.spike_events` | core spikes on the reference clock, bucketed by time |
| `analysis.array_assets` | catalog rows describing derived dense-array instances |
| `analysis.array_asset_instances` | analysis dense-array resources catalogued by `analysis.array_assets.resource_id` |
| `analysis.array_dimensions` | their logical axes |
| `analysis.array_labels` | the row each position of their labelled axes stands for |

### 11.9 Space

Frames stand to a coordinate as §11.3's clocks stand to a tick: the declared reference the value is stated against.

| resource | contents |
|---|---|
| `core.coordinate_frames` | the spaces coordinates are positions in, and which published atlas each one is |
| `core.coordinate_frame_axes` | one row per axis of a frame, with its name, direction, and unit |

<a id="ew-core-sidecar-resource-index" data-spec-anchor="canonical"></a>
### 11.10 Sidecars

| resource | contents |
|---|---|
| `core.sidecars` | the packet's sidecars, each with its type, media type and description |
| `core.sidecar_scopes` | the rows each sidecar is about |
| `core.sidecar_instances` | opaque resources catalogued by `core.sidecars.resource_id` |

<a id="ew-particular-resource-rules" data-spec-anchor="canonical"></a>
## 12. Rules for particular resources

Sections 2 through 10 bind every declaration and table payload. What follows binds particular
tables, where identifying a
row, resolving a value, or reading an absence takes more than the generic rules give.

<a id="ew-unit-identity-architecture" data-spec-anchor="alias"></a>
<a id="ew-unit-identity" data-spec-anchor="canonical"></a>
### 12.1 Unit identity

`unit_id` identifies a unit on its own. The packet assigns it; `core.units` records the run and the
curation as ordinary columns, and `local_unit_label` records what the sorter called it.

A writer MUST number a packet's units densely from 0. It MUST number each curation's units, those
sharing `sorting_run_id` and `curation_id`, consecutively in ascending order of `local_unit_label`,
and MUST number the units one build adds curation by curation, in ascending order of
`sorting_run_id`, then `curation_id`. It MUST compare two labels by their length in Unicode scalars,
shorter first, and two labels of equal length by Unicode scalar value
([Part 11 §5](11_tier_2_rule_language.md#ew-tier-2-deterministic-semantics)). A null label follows
every other label. Units of one curation that tie on their label, two null labels included, MAY be
numbered in either order. `core.units.numbered_in_order` checks that identifiers are dense from 0
and that each curation's units are numbered consecutively in label order; the order of curations
binds the writer alone, and no rule checks it.

A packet carrying `core.units` MUST carry `core.sorting_runs` and `core.curation_versions`.

A table keyed on a unit carries `unit_id` and not the run or the curation. A consumer relating a
unit to anything outside the packet that holds a name, such as another packet, a recipe or a later
build, uses `unit_name`.
A consumer MUST NOT identify a unit by its `unit_id` outside the packet that assigned it, where the
number means nothing. No checker verifies this.

`core.units` also declares what its spikes are counted on and measured in: `clock_id`, required,
and `amplitude_unit`, nullable and open. Both are facts of the sorting run, and a
spike cannot reach the run — §8.4 admits one hop and spike → unit → run is two — so they live on
the table a spike references directly. `core.spike_events.t_tick` therefore declares
`clock_from: core.units.clock_id` and `amplitude` declares `unit_from: core.units.amplitude_unit`,
and neither `core.spike_events` nor `core.unit_observation_intervals` carries a
`clock_id` of its own. The run still determines both values, since a unit names its run
in a reference it MUST carry.

### 12.2 Channel indices in a sorting run

A sorting drops bad channels before it runs, so a channel index a source emits counts the channels
it kept and not the probe's contacts. `core.sorting_run_channels` records that list in the run's
own order.

A writer that can read it SHOULD emit the table, MUST NOT derive it from `core.unit_electrodes` or
from a bad-channel list, and SHOULD emit nothing where it cannot read it.

A consumer holding such an index MUST resolve it through that table and MUST NOT read it as a
position in `core.electrodes`; where the run declares no channels the index is unresolvable, and
the consumer MUST report that rather than resolve it against the contact list.

Where a run declares its channels, every `core.unit_electrodes` row for one of its units MUST name
an electrode among them.

### 12.3 Calibration

A calibration is a standing property of an instrument rather than an activity of this packet, so
`core.calibrations` records the session it was **in force** for and, separately, when it was
measured; a consumer MUST NOT read the two as one fact. A calibration in force for
several sessions is recorded once per session, as for any row whose results reach more than one
session.

The devices a calibration covers are a child table, since one calibration of the rig's manipulators
is cited by six probes; a calibration covering a device the packet does not hold gets no
row there, which is a fact rather than a defect, and a writer that records the calibration SHOULD
record the devices it names.

A paired series is carried as `core.calibration_points`, whose two value columns take their units
of measure from the calibration, since the unit varies per calibration and so cannot be a literal
on either column. Content that is an array rather than a curve names the array asset
holding it.

Where a row has no points, no array asset and no detail kind, it records that the calibration was in force
and that the packet holds nothing further, which a consumer MUST read as **unrecorded** rather than
as absent. A source stating that no calibration was performed gets no row at all.

`core.calibrations` declares `metadata` and the two child tables MUST NOT, because its key holds an
identifier of its own where theirs are keyed by other tables' identifiers.

### 12.4 A clock's rate

A clock MUST NOT declare both `tick_rate_hz` and a rational rate; `core.clocks.tick_rate_declared` already requires at least one, so exactly one is present. The float is for a source that measured its rate rather than stating an exact one, and forcing a rational on it would make a writer invent a denominator — a rounding decision this specification does not make on a source's behalf.

### 12.5 A clock's observation window

A packet MUST declare at least one row of `core.clock_observation_intervals` for every clock any of its rows is timestamped on. More than one is permitted, for an acquisition paused and resumed. A clock that exists only as a parent declares none: the chain is required to be well founded, so such a clock is declared, and nothing is observed on it for an inherited interval to reach.

`core.clocks.observation_declared` checks the part of that a query can see — a clock that has anchors, or that a session names as its `reference_clock_id`, and declares no interval. A clock aligned by `transform_slope` alone carries data and has no anchors, so the obligation reaches it and the rule does not; the obligation binds the writer, which knows what it timestamped.

<a id="ew-clock-alignment-record" data-spec-anchor="canonical"></a>
### 12.6 A clock's alignment record

Three facts about how a packet's clocks were aligned are columns, because a consumer needs them to place a tick and Part 02 §8.6's line puts such a fact in a column and never in a key.

`core.sessions.alignment_bound` holds how far past its anchors the writer mapped, in median anchor intervals. A writer establishing a bound wider than the default of one median anchor interval MUST record it; a consumer reading a null MUST map at that default, which is a fact and not a defect. It is on the session because the bound is a property of the times the packet states, as `t_zero_tick` is, so one session declares one bound and no rule is needed to say which run wins. A value below one is refused.

The **terminal-anchor test** predicts a clock's first and its last anchor from a fit over that anchor's neighbours and compares the residual with the distribution of the same residual over the clock's interior anchors. A writer SHOULD run it on each clock whose anchors it writes, because anchor quality is a property of a rig and a session and no fixed tolerance stands in for it; a clock with too few anchors to give that distribution cannot be tested. `core.clocks.withheld_first_anchor` and `withheld_last_anchor` record the test on that clock, and a writer running it MUST record both. Three states distinguish the outcomes: null is a clock the test did not run on, false is a terminal it kept, true is one it withheld — so a silent zero and an untested clock differ structurally rather than by a rule nothing can observe. A clock with no anchors MUST NOT declare either.

`core.clock_phase_steps` holds one row per step in a clock's alignment to its parent, a clock having possibly several (§5.2). A writer detecting a step MUST record it, and a step is reported and never corrected: the map is exact at every anchor, so it carries the step faithfully, and subtracting it would need to know whether the step also moved the devices timestamped on that parent, which the packet does not record. A clock whose `parent_clock_id` is null MUST NOT have rows here.

`core.processing_runs.parameters` keeps the evidence behind each decision and none of the three facts themselves. A writer SHOULD record there the tolerance it judged its alignment against and, where it measured its error (Part 01 §3.9), the distance and the measurement. A writer recording the measurement MUST record its median, p95 and maximum together, so a consumer can judge the packet by a stricter rule than the writer applied. No checker verifies the record, since `parameters` names no key for it. A consumer needs the bound to place a tick and not the residual that justified it.

<a id="ew-frame-axes" data-spec-anchor="canonical"></a>
### 12.7 A frame's axes

A frame declares one row of `core.coordinate_frame_axes` per axis it has, and two axes of one frame MUST NOT carry the same `axis_name`, which `core.coordinate_frame_axes.axis_names_distinct` checks. An axis name is the source's own word for the field the values came from, so two axes sharing one means a writer put two quantities under one name and the packet cannot say which value is on which axis.

A coordinate's values reference the axis rows of their own frame on `(session_id, coordinate_frame, axis_index)`, so a value on an axis the frame never declared is an orphan Tier 1 reports, and a frame's axis count cannot disagree with the shape of its coordinates.

A coordinate MAY carry values on fewer axes than its frame declares, where its source states none on the rest, and a consumer MUST NOT read an absent axis row as a zero: it is a position the source did not state on that axis.

`axis_value` declares `unit_from` of `core.coordinate_frame_axes.unit`, resolved one hop through that reference (§8.4): the unit is the axis's, so a frame stated in millimetres needs no second set of columns and no column name carries a unit.

<a id="ew-coordinate-atlas-annotation" data-spec-anchor="canonical"></a>
### 12.8 A coordinate's atlas annotation

A registry document MUST NOT declare a column holding an atlas structure's full name or its
ancestry path: both derive from the structure's identifier, and an ancestry path is a list, which
§5.2 forbids in a delimited string. No checker verifies this. Part 01 §3.8 defines the annotation.

<a id="ew-interval-identity" data-spec-anchor="canonical"></a>
### 12.9 Interval identity

`interval_id` identifies an interval on its own. A writer assigns it, and records the number or
name its source gave the interval in `local_interval_label`, null where the source gave none. A
consumer relating an interval to anything outside the packet that holds a name uses
`interval_name`. `core.intervals.label_unique_within_kind` draws each label two intervals of one
session and kind share.

A writer MUST number a packet's intervals densely from 0. It MUST number each session's intervals
of one kind consecutively, in ascending order of `clock_id`, `start_tick` and `stop_tick`, and MUST
number the intervals one build adds session by session and kind by kind, in ascending order of
`session_id`, then `interval_kind` compared by Unicode scalar value. Intervals of one session, kind
and clock with equal bounds MAY be numbered in any order. `core.intervals` is stored in its key's
order (Part 03 §5.3), so each kind of one session is one contiguous run, and within it each clock's
intervals are in tick order. `core.intervals.numbered_in_order` checks that identifiers are dense
from 0 and that each session's intervals of one kind are numbered consecutively in order; the order
of sessions and kinds binds the writer alone, and no rule checks it.

<a id="ew-sidecar-rules" data-spec-anchor="canonical"></a>
### 12.10 Sidecars

`core.sidecars` lists a packet's sidecars (§2.2), one row each, keyed on the sidecar's packet
resource ID. The table carries no `session_id` and assigns no identifier, so it has no `*_name`
column. It declares `metadata` because its primary key holds an identifier that is part of no
reference the table declares (§8.6).

The author of a recipe ([Part 05 §3.1](05_validation_and_import.md#ew-recipe-purpose)) chooses each
sidecar's resource ID, and the adapter that delivers the row hands the ID over as chosen. The ID
matches the pattern [Part 04 §4.1](04_packet_catalog.md#ew-packet-resource-entry-fields) gives a
resource ID and is unique among the packet's resource IDs, as §2.6 requires of every catalog value.
No part derives it from the sidecar's name, type or contents.

A null `sidecar_type` states that the source named no type, and a null `media_type` that it named
none. `sidecar_type` names no authority, since no external nomenclature registers kinds of sidecar,
so every value conforms (§9.3). The column is named `_type` because the registry's naming
conventions keep `_kind` for a discriminator. `media_type` holds a media type as `type/subtype`
without parameters and names IANA Media Types as its authority (§13).

A row of `core.sidecar_scopes` states that one sidecar is about one row of one table: `scope_kind`
names the table, and `scope`, its paired value (§8.3), names the row. The named table has a primary
key of one column, as §8.3 requires of a paired value's target, so a scope names neither a whole
table nor a row of a table keyed on several columns, such as a coordinate frame. Several rows state
several scopes for one sidecar. A sidecar with no row is about the packet as a whole or states no
scope, and the table does not tell the two apart.

Because `scope_kind` resolves `required`, the checks of §8.3 report at `error` a scope that names a
table the packet does not declare, a table whose key is not one column, or a row the named table
does not hold. A sidecar about something the packet holds no row for, such as a surgery or a
scanning session, takes no scope row for it, and `description` MAY say so in prose. A scope MAY
name an extension's table, which §8.3 lets core name and not reference.

A scope row states only that the sidecar is about the named row. A consumer MUST NOT conclude from
a scope row any other relation between the two, such as that a session followed a protocol, that a
coordinate was derived from an image, or that the named row depends on the sidecar. No checker
verifies this, since what a consumer concludes leaves no trace in a packet.

<a id="ew-logical-schema-normative-references" data-spec-anchor="canonical"></a>
## 13. Normative references

The application column states the extent to which this part invokes each external authority:

| reference | candidate edition | application |
|---|---|---|
| [The Unified Code for Units of Measure](https://ucum.org/ucum) | version 2.2, revision date 2024-06-17 | unit codes (§8.4) and the spelling of values in open columns naming it (§9.3) |
| [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |
| [Mouse Genome Informatics (MGI)](https://www.informatics.jax.org/) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |
| [Rat Genome Database (RGD)](https://rgd.mcw.edu/) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |
| [IANA Media Types](https://www.iana.org/assignments/media-types/) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |

This section MUST carry an entry whose link is the `uri` of each `authority` entry declared on an
open column of the incorporated core registry, in its `core` or `analysis` namespace. A core
registry naming such an authority without a matching entry makes the candidate internally
inconsistent under [Part 00 §2.3](00_architecture.md#ew-candidate-consistency). The comparison is
exact on the URI string and dereferences nothing, so the core registry and this section alone
decide it. An authority on a closed column, such as HL7 FHIR's administrative-gender value set on
`core.subjects.sex`, records provenance under §9.3 and has no entry here. An extension registry's
authorities are outside this condition.

Validation of unit codes and authority URIs is offline, and §9.3 forbids dereferencing an identifier. A
registry check parses literal `unit` declarations, and
[Part 05 §5.3](05_validation_and_import.md#ew-validation-shim) parses the values of a packet's unit
columns.
