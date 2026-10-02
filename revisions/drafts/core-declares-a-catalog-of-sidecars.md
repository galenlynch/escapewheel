# Core declares a catalog of sidecars

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `ba589b18678a7a35f3b5192b9b3f9f420734e0b5` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§2.2, 2.6, 4, 9.2, 11, 12 and 13; Part 03 §§3.1 and 7; Part 05 §4.3; Part 08 §§2 and 3; Part 09 §§2 and 3; the core registry |
| **Depends on** | R128 §3.2 (the content classes, whose `documentation` row this restates); R128 §3.6 (the three catalog tables and the `resource_id` naming exception, both of which this extends); R140 §3.3 (Part 02's normative references, which gain an entry); R150 §3.6 (an amending build's settlement of a delivered row, to which this adds a case); R152 §3.4 (the core registry version at the baseline) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A packet often has to list a file or a directory that Escapewheel does not interpret and that
nothing in the packet depends on: a protocol as a PDF, a README, a viewer's saved state, or an
anatomical scan that another holder keeps. Part 02 §2.2 calls such a thing a sidecar and gives it a
content class, `documentation`. Part 03 §§3.1 and 7 and Part 09 §2 place a sidecar in a directory
`docs/` under the packet root.

No registry declares a resource of that class, so no manifest can list a sidecar. A file in `docs/`
is a stray: no entry records its digest, no reader lists it, and a copy that follows the manifest
leaves it behind. Listing one today takes an extension registry that declares an opaque resource
and an adapter that delivers the payload.

This revision has the core registry declare three resources of class `documentation`: a catalog
table of sidecars, a table stating which rows of the packet each sidecar is about, and the opaque
resources the catalog lists. It restates what the class means, removes `docs/` and the two sentences
that place a value in a sidecar, lets an amending build add a sidecar to a packet that already lists
some, and advances the core registry's version. It changes no rule of delivery, storage or
validation, since those already serve an opaque catalog and a documentation resource.

The change is structural because the rules it restates sit in the middle of Part 02 §§2 and 4, Part
03 §§3 and 7, Part 05 §4.3 and Part 09 §§2 and 3, and an appended section would leave each of them
contradicting it.

`a-delivery-carries-the-compensations-its-adapter-applied.md` also amends Part 05 §4.3, in its
sentence on a compensation. §3.7 touches that section's settlement list alone, so the two apply in
either order. No other open draft touches a section this one amends.

### 1.1 Structural crosswalk

Every amended section carries a canonical anchor at the baseline, so no anchor bootstrap is needed.
No section moves, splits, merges or retires. The two new subsections take their anchors when they
are created.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §2.2, `documentation` means human-readable sidecars that assert no fact | revise in place | same section | a sidecar is an opaque resource the packet lists and asserts nothing through, whoever reads it; the class covers the tables that list sidecars | §3.1 |
| Part 02 §2.6, three catalog tables carry `resource_id` beside an assigned key | revise in place | same section | `core.sidecars` is a fourth, keyed on `resource_id` | §3.4 |
| Part 02 §4, the integer `_id` rule excepts the exact catalog field `resource_id` | revise in place | same section | the exception covers every column named `resource_id` | §3.4 |
| Part 02 §9.2, the core registry version | revise in place | same section | the version advances | §3.8 |
| Part 02 §11, the core resource index | extend with a subsection | a new subsection at the end of Part 02 §11, anchored `ew-core-sidecar-resource-index` | the index lists the three declarations | §§3.2, 3.3, 3.4 |
| Part 02 §12, rules for particular resources | extend with a subsection | a new subsection at the end of Part 02 §12, anchored `ew-sidecar-rules` | who chooses a sidecar's resource ID, what a scope row states, and what a consumer may conclude from one | §§3.2, 3.3 |
| Part 02 §13, four reference entries | extend in place | same section | a fifth entry, a living registry | §3.5 |
| Part 03 §3.1, the layout's `docs/` line | remove | Part 03 §11 already places a packet-owned opaque payload | the layout names no directory for an unlisted file | §3.6 |
| Part 03 §7, a lab-specific value in a sidecar and human-readable context in `docs/` | revise in place | same section | a value belongs in a column or an extension, and context in a listed sidecar | §3.6 |
| Part 05 §4.3, an amending build's settlement of a delivered row | extend in place | same section | a row of a documentation table the packet names is added where its key is new | §3.7 |
| Part 08 §§2 and 3, the example packet's core registry version | revise in place | same sections | the version advances | §3.8 |
| Part 09 §2, tier 4 in `docs/` sidecars | revise in place | same section | tier 4 is the sidecars `core.sidecars` lists | §3.6 |
| Part 09 §3, a field in an extension or a sidecar | revise in place | same section | a field is not placed in a sidecar | §3.6 |

## 2. Background

Observed in the tracked files at the baseline commit. Each count is taken from the incorporated
registry documents, the manifest schema, or a search of `spec/parts/`.

### 2.1 The parts name a place for a sidecar and declare none

The core registry holds 48 declarations, 43 of class `core` and 5 of class `analysis`. The four
extension registries in the repository hold 11, all of class `extension`. No declaration has the
class `documentation`. A search of `spec/parts/` for `docs/` and `sidecar` finds six statements: one
in Part 02 §2.2, one in Part 03 §3.1, two in Part 03 §7, and one each in Part 09 §§2 and 3.

Part 03 §9 defines a stray as a file under the packet root that no manifest ever named, and Part 05
§15.5 lets a packet carry one. Part 04 §4.3 records a digest for a manifest entry only.

Two of the six statements treat a sidecar as a place for values: Part 03 §7 places lab-specific
values in a `json_string` column or a sidecar, and Part 09 §3 says a lab-specific or free-form field
should be in an extension or a sidecar. A file holding values a consumer relies on does not fit a
class defined as asserting no fact.

### 2.2 The one opaque declaration in core describes frames on a clock

`core.media_asset_instances` is core's only opaque declaration, catalogued by `core.media_assets`.
Its catalog row requires a session and carries a presentation-timestamp rate and a clock. A document
has none of these, so a row for one would state nothing true about it.

A manifest entry cannot describe the payload either. Part 04 §4.1 gives an entry eleven members, and
none states a media type, a title or a description, so a catalog row is the only place an opaque
resource is described.

### 2.3 The existing rules already serve a documentation catalog, except in a second amendment

- **Delivery.** Part 12 §5 binds a payload to the catalog row of an opaque catalog family whose
  `resource_id` equals the payload's resource directory, and delivers a referenced resource as an
  entry of a resource document, which a build records as external. Neither rule names a family.
- **Storage.** Part 03 §11 stores a packet-owned opaque payload, one file or one directory, under
  its own name, and Part 03 §2 lets an opaque resource be packet-owned or external.
- **Dependence.** Part 02 §2.2 forbids a canonical declaration a reference, a `requires` entry or a
  catalog binding that targets a documentation declaration, and Part 02 §2.7 permits no class to
  take a documentation resource as a lineage source. Both are checked on the registry document and
  the manifest.
- **Registry.** The registry-document contract admits `documentation` in a core registry.
- **Amendment.** Part 05 §15.2 lets a writer performing an amendment add a resource other than a
  canonical table, and remove or replace a documentation resource. Part 05 §4.3, which an amending
  build follows, adds a row of a non-canonical table only where the packet's manifest does not name
  the table. Every other delivered row has to form a group the packet lacks, and Part 02 §2.8 has a
  non-canonical table declare no group list. An amending build can therefore list a packet's first
  sidecars and refuses every later one.

### 2.4 Core states a scope as a discriminator and a paired value

Part 02 §7.1 requires a session-scoped table to carry a required `session_id` and forbids the column
to any other table. A sidecar may be about the packet, a subject, several sessions or one resource,
so no session column fits.

`core.processing_runs` and `core.preferred_runs` each carry `scope_kind`, a discriminator holding
the dotted ID of a table, and `scope`, the key or name of a row of that table. Part 02 §8.3 governs
the pair:

- The two columns share one presence, and a row holding neither is undeterminable, which a consumer
  reports as a defect of the row. A null pair therefore cannot state that a sidecar is about the
  packet.
- The named table's primary key is one column. 17 of the core registry's 45 tables have such a key:
  16 of class `core` and `analysis.array_assets`. `core.coordinate_frames` is keyed on two columns.
- A discriminator resolving `required` draws the forward, key-form and paired-value checks at
  `error`. One resolving `optional` draws none of them, and an unresolvable value is reported as
  `info`. Both existing scope pairs resolve `optional`.

One pair states one row. A protocol is about each session that followed it, and a viewer's saved
state is about each probe it shows.

### 2.5 A catalog row is keyed on an assigned integer today

`core.array_assets`, `analysis.array_assets` and `core.media_assets` each carry an assigned integer
key, the `*_name` Part 02 §8.2 requires beside it, and `resource_id`. A sidecar has no source label
other than its resource ID, so the integer and the name would restate it. Part 02 §2.6 requires only
that the catalog column be a required string identifier with carried identity and free vocabulary,
and Part 02 §8.2 gives a carried identifier no name column. The registry meta-schema holds every
column named `resource_id` to that declaration, whatever its table, while Part 02 §4 words the
exception for the exact catalog field.

### 2.6 The declarations pass the registry checks

The three declarations of §3 were added to a copy of the registry source at the baseline, and the
registry was assembled and checked.

- The registry document is valid under every invariant of Part 02 §9.4, with 51 declarations and 47
  tables. The meta-schema and the registry-contract descriptor are unchanged.
- A carried string primary key is admitted on a catalog table and as a reference target, and
  `core.sidecar_scopes.resource_id` passes the reference invariants.
- A documentation table may declare a reference to another documentation table, and a Tier 2 rule.
  A canonical declaration that references or requires `core.sidecars`, a group list on either
  table, and a `lineage` other than `forbidden` are each refused.
- `core.sidecars` without `metadata` is refused by `registry.metadata.eligibility`, and
  `core.sidecar_scopes` is admitted with the column or without it.
- The reference validator generates the forward and key-form checks for `scope_kind` and one
  paired-value check for each named table the packet carries. `scope_kind` would be the first
  paired-value discriminator without `discriminates_via` to resolve `required`. Over a seven-row
  table the checks reported a scope naming an undeclared table, one naming
  `core.coordinate_frames`, and one naming a subject the packet lacks, and the reference check
  reported a scope for an unlisted sidecar. Rows scoping one sidecar to a subject and two sessions
  passed.
- The reference validator generates no paired-value check for a named core table the packet does
  not carry, so a scope naming a row of one draws no finding. Part 02 §8.3 has a validator generate
  that check for each kind a packet's rows name, so §5 lists the gap against the validator.
- The one check that failed is an authoring convention of the registry tooling, that an `_id` column
  is an integer, once for each of the two `resource_id` columns. The three existing catalog tables
  carry declared exceptions to it.

### 2.7 The provenance tables record a file a result was computed from

Part 04 §7 places provenance in `core.source_files`, `core.processing_runs` and
`core.processing_run_inputs`. A `core.source_files` row carries a required `uri` and a nullable
`sha256`, and locates a file the packet need not own. Part 05 §7 requires a row for each distinct
root among a recipe's sources, and no part limits the table to those rows.

### 2.8 Alternatives

- Retiring `docs/` and the class removes the contradiction of §2.1 at the least cost, and leaves a
  viewer state or a pointer to a scan unlisted, with no digest and no way to find it.
- Letting a manifest list a resource with no declaration contradicts Part 04 §4.2, and the entry
  would have no content class, lineage policy or instance rule for a validator to apply.
- Declaring the catalog with class `core` makes a sidecar canonical, so an amendment could add one
  and never replace or remove one, and a canonical table could come to depend on one.
- An opaque family with no catalog gives an instance no description or media type (§2.2), and Part
  12 §5 gives a family payload no binding rule.
- An assigned `sidecar_id` with a `sidecar_name` gives one payload three identifiers, and a scope
  row would reference a number the build assigns.
- One nullable scope pair on the catalog row leaves a sidecar about the packet undeterminable under
  Part 02 §8.3, and states one row where a sidecar is often about several (§2.4).
- A scope resolving `optional` lets a misspelled name pass as `info`, and a scope exists only so
  that a consumer can find the sidecars for a row.

## 3. Decision

The eight clauses below restate the class, declare the catalog, its scopes and its instances, name
the authority for a media type, restate where metadata is placed, let an amending build add a
sidecar, and advance the registry's version.

### 3.1 A sidecar is an opaque resource the packet lists and asserts nothing through

The content class `documentation` covers sidecars and the tables that list them. A **sidecar** is an
opaque resource of that class: one that a packet lists and through which it asserts no semantic or
conformance fact. The class stays non-canonical, and no class requires it.

A sidecar MAY be read by a person or by a program. This specification defines no behavior of a
reader, a writer or a validator that interprets a sidecar's contents.

Listing a resource as a sidecar records no dependence on it: Part 02 §2.2 forbids a canonical
declaration a reference, a `requires` entry or a catalog binding that targets a documentation
declaration, and Part 02 §2.7 permits no lineage from one. A registry's author who needs a table to
reference a payload, or a rule or a reader to interpret one, therefore declares it as a canonical
resource, since a sidecar cannot be the target. A payload that a result in the packet was computed
from is recorded by the provenance tables (Part 04 §7), and the same payload MAY also be listed as
a sidecar.

### 3.2 `core.sidecars` lists a packet's sidecars

The core registry MUST declare `core.sidecars`: content class `documentation`, kind `table`, a
singleton of `optional` presence, `requires` empty, `lineage` `forbidden`, primary key
`resource_id`, no reference, no rule, and `amendment_groups` empty. Its columns, in order, are:

| column | type | presence | role | further fields | holds |
|---|---|---|---|---|---|
| `resource_id` | `string` | required | identifier | identity `carried`; vocabulary `free` | the sidecar's packet resource ID |
| `sidecar_type` | `string` | nullable | data | vocabulary `open`; no `authority`; no `reserved_values` | what kind of thing the sidecar is, as a lowercase snake-case name such as `readme`, `protocol`, `anatomical_image` or `neuroglancer_state` |
| `media_type` | `string` | nullable | data | vocabulary `open`; `authority` as §3.5 gives it | the sidecar's media type, as `type/subtype` without parameters |
| `description` | `string` | nullable | data | vocabulary `free` | what the sidecar is, in prose |
| `metadata` | `json_string` | optional | data | the description Part 02 §8.6 fixes | as Part 02 §8.6 states |

The table carries no `session_id` and assigns no identifier, so it has no `*_name` column. It
declares `metadata` because its key holds an identifier that no reference carries (Part 02 §8.6).

The author of a recipe chooses each sidecar's resource ID, and the adapter that delivers the row
hands the ID over as chosen. The ID matches the pattern Part 04 §4.1 gives a resource ID and is
unique among the packet's resource IDs, as Part 02 §2.6 requires of every catalog value. No part
derives it from the sidecar's name, type or contents.

A null `sidecar_type` states that the source named no type, and a null `media_type` that it named
none. `sidecar_type` names no authority, since no external nomenclature registers kinds of sidecar,
so every value conforms (Part 02 §9.3). The column is named `_type` because the registry's naming
conventions keep `_kind` for a discriminator.

### 3.3 `core.sidecar_scopes` states which rows a sidecar is about

The core registry MUST declare `core.sidecar_scopes`: content class `documentation`, kind `table`, a
singleton of `optional` presence, `requires` empty, `lineage` `forbidden`, primary key
(`resource_id`, `scope_kind`, `scope`), one reference from `resource_id` to
`core.sidecars.resource_id`, no rule, no `metadata` column, and `amendment_groups` empty. Its
columns, in order, are:

| column | type | presence | role | further fields | holds |
|---|---|---|---|---|---|
| `resource_id` | `string` | required | identifier | identity `carried`; vocabulary `free`; references `core.sidecars` | the sidecar |
| `scope_kind` | `string` | required | discriminator | `resolves` `required`; `discriminates` `scope` | the table holding the row the sidecar is about, as a dotted resource ID |
| `scope` | `string` | required | data | vocabulary `free` | that row's key where the key is carried, and its `*_name` where it is assigned |

A row states that one sidecar is about one row of one table. The named table has a primary key of
one column, as Part 02 §8.3 requires of a paired value's target, so a scope names neither a whole
table nor a row of a table keyed on several columns, such as a coordinate frame. Several rows state
several scopes for one sidecar. A sidecar with no row is about the packet as a whole or states no
scope, and the table does not tell the two apart.

Because `scope_kind` resolves `required`, the checks of Part 02 §8.3 report at `error` a scope that
names a table the packet does not declare, a table whose key is not one column, or a row the named
table does not hold. A sidecar about something the packet holds no row for, such as a surgery or a
scanning session, takes no scope row for it, and `description` MAY say so in prose. A scope MAY name
an extension's table, which Part 02 §8.3 lets core name and not reference.

A scope row states only that the sidecar is about the named row. A consumer MUST NOT conclude from a
scope row any other relation between the two, such as that a session followed a protocol, that a
coordinate was derived from an image, or that the named row depends on the sidecar. No checker
verifies this, since what a consumer concludes leaves no trace in a packet.

### 3.4 `core.sidecar_instances` are the resources `core.sidecars` lists

The core registry MUST declare `core.sidecar_instances`: content class `documentation`, kind
`opaque`, catalog instances naming `core.sidecars` and its column `resource_id`, `requires` empty,
and `lineage` `forbidden`.

Part 02 §2.6 names four catalog tables, `core.array_assets`, `analysis.array_assets`,
`core.media_assets` and `core.sidecars`, each carrying `resource_id`. In the first three an assigned
integer remains the primary key and its `*_name` the source-label bridge. In `core.sidecars`,
`resource_id` is the primary key and the table has neither. None of the four carries `uri` or
`format`, and `media_type` states no physical encoding that Part 03 defines.

A registry MUST declare every column named `resource_id` as a required `string` identifier with
carried identity and free vocabulary, whether the column is a catalog table's field or references
one. Part 02 §4's integer `_id` rule does not apply to a column of that name.

Part 02 §11 lists the three declarations in a subsection of their own.

### 3.5 A media type is spelled as its registry spells it

`core.sidecars.media_type` MUST declare one `authority` entry, named `IANA Media Types` with the
URI `https://www.iana.org/assignments/media-types/`. Part 02 §13 MUST carry this entry:

| reference | candidate edition | application |
|---|---|---|
| [IANA Media Types](https://www.iana.org/assignments/media-types/) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |

Part 02 §9.3 then governs the value as it governs any open column that names a nomenclature: a
writer that can identify the registered name writes it as registered, and a value the registry does
not register conforms. Part 02 is the one part that invokes the registry, so the entry belongs
there under Part 00 §9.

### 3.6 Context is placed in a listed sidecar and a value is not

Part 03 §3.1's recommended layout MUST NOT name a `docs/` directory. A packet-owned sidecar is a
payload, which that layout already places at `opaque/<resource_id>/<name>` (Part 03 §11), so a
README listed as `core.readme` lies at `opaque/core.readme/README.md`.

Part 03 §7 places metadata by kind:

| kind | location |
|---|---|
| packet-level facts | the manifest |
| queryable scientific facts | tables |
| semi-structured, lab-specific values | a `json_string` column, or an extension's table |
| context the packet asserts nothing through | a sidecar that `core.sidecars` lists |

Part 09 §2's tier 4 holds context the packet asserts nothing through, located in the sidecars that
`core.sidecars` lists. Under Part 09 §3, a field SHOULD be in an extension when it is institutional,
administrative, lab-specific, rarely queried, free-form, procedural but not required for analysis,
or biologically rich but not required to interpret the recording. That section no longer places a
field in a sidecar.

### 3.7 An amending build adds a sidecar to a packet that lists some

An amending build settling a delivered row against the packet (Part 05 §4.3) MUST add a row of a
table of class `documentation` that the packet's manifest names and that declares a primary key,
where no row the packet holds has the delivered row's primary key. A row equal to one the packet
holds is still dropped, together with any catalog instance it catalogues, and the build still
refuses a delivered row that shares a held row's primary key and differs from it.

The table the amendment writes holds the packet's rows and the added ones, and replaces the
documentation resource as Part 05 §15.2 permits. An amending build thereby adds sidecars and scope
rows to those a packet lists, and neither removes nor replaces one.

### 3.8 The core registry version advances

The core registry's `registry_version` MUST advance by one minor version from the version the
incorporated registry carries when this revision is incorporated. At the baseline that version is
`0.14.0`, which R152 §3.4 assigns. Other open work advances the same identifier, so this draft
takes the next free version at incorporation and fixes no order among them. The registry
meta-schema, the registry-contract descriptor and the rule language are unchanged.

## 4. What this does not change

A file under the packet root that no manifest names, including one in `docs/`, remains a stray that
Part 05 §15.5 protects.

No part of a build or a validator interprets a sidecar's contents, so an absolute URL inside one,
as a viewer's saved state carries, is not kept current when what it names moves, and nothing
reports it.

Part 05 §15.2 still lets a writer performing an amendment remove or replace a documentation
resource. §3.7 gives an amending build no way to do either.

Part 12 §5 still forbids a build to require a payload's media type of an adapter: `media_type` is
nullable, and an adapter states it in the catalog row where its source gives one.

An extension keeps the right to declare an opaque or documentation resource of its own.

## 5. Consequence

No existing packet changes in conformance: each binds the core registry it was built with, which
declares no sidecar. Every fixture and example packet is rebuilt to bind the new version, the
conformance corpus's 120 packets among them, and no row of any changes. A packet built afterwards
binds a core registry of 51 declarations.

An existing packet gains a sidecar through an amending build whose recipe names the new core
registry (Part 05 §15.1). Part 05 §3.5 admits that binding, since the semantic and logical standard
versions are unchanged, and Part 05 §15.3 has the packet retain the superseded registry copy. The
amended packet is validated whole against the new registry (Part 05 §15.4), which adds three
declarations to the version it advances from and changes no other. A packet bound to an earlier
version also has to satisfy what changed in between.

A sidecar is packet-owned or referenced. Its catalog row, its binding by `resource_id` and its scope
rows are the same either way, and the existing parts make these differences:

| | packet-owned | referenced |
|---|---|---|
| delivery (Part 12 §5) | a payload, one file or one directory, in the resource directory its resource ID names | an entry of a resource document, recorded `external: true` |
| location | `opaque/<resource_id>/<name>` under the recommended layout (Part 03 §11) | the entry's `uri` |
| `digest` and `size_bytes` | recorded from the staged bytes (Part 03 §10) | recorded only where the writer reached the resource (Part 04 §5.2) |
| what the packet promises | bytes no writer modifies once committed (Part 03 §8.1) | nothing (Part 03 §8.2) |

Part 05 §15.2 lets a writer replace or remove a documentation resource, so a packet promises a
sidecar for one version only. A scope naming a row of an analysis table resolves only while the
packet holds that row. A writer that removes or re-derives the table without the row replaces
`core.sidecar_scopes` as well, or validation reports the scope under Part 02 §8.3.

Where two sources of one recipe each deliver sidecars, each source entry names `core.sidecars` and
`core.sidecar_scopes` under `contributes` (Part 05 §3.3). Part 05 §3.4 refuses a recipe that leaves
two entries owning either table.

At incorporation the ledger entries of R128 §3.2, R128 §3.6, R140 §3.3 and R150 §3.6 each gain a
note naming the clause above that restates or extends part of them.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: a sidecar asserts no semantic fact, so Part 01 gains no concept. | Part 01 is byte-identical. |
| logical prose and registry | Part 02 §§2.2, 2.6, 4, 9.2 and 13 as §3 states, and a new subsection in each of Part 02 §§11 and 12. The registry source gains the three declarations and the new version. The meta-schema, the registry-contract descriptor and the rule language are unchanged. `spec/tools/conventions.py` gains a declared exception for `core.sidecars.resource_id` and one for `core.sidecar_scopes.resource_id`, without which the registry check fails (§2.6). | `spec/tools/check.py` passes over 51 declarations and 47 tables, and `spec/tools/framework.py`'s comparison of Part 02 §13 passes with the fifth entry. |
| physical profiles | Part 03 §§3.1 and 7 as §3.6 states. Part 03 §11 and the profile descriptor are unchanged. | The descriptor is byte-identical. |
| packet manifest and JSON Schemas | Unchanged: a sidecar's entry uses the existing eleven members. | The schemas are byte-identical. |
| validation and import | Part 05 §4.3 gains §3.7's case, and Part 09 §§2 and 3 read as §3.6 states. The catalog-binding checks, the amendment table and the delivery rules already cover a documentation catalog (§2.3), and Part 02 §8.3 already generates the checks of §3.3. | The corpus cases of §6 produce their expected findings with no check declared for them. |
| extensions | Unchanged: no extension registry is edited. A scope names an extension's table through the discriminator, with no declaration in the extension. | The extension registry checks pass. |
| reader, writer, validator, adapters | Each package's registry copy regenerates. The reader lists both tables and resolves a sidecar as it does any catalogued resource, which no test has exercised with a catalog keyed on `resource_id`. The writer gains an adapter that delivers the catalog rows, scope rows and payloads a recipe names. Its referenced-resource delivery, which binds the array and media catalogs by their assigned identifiers, extends to a catalog keyed on `resource_id`, and its amending build takes §3.7's case where it refuses the row today. The validator generates the paired-value check for a named table the packet does not carry, which it skips today (§2.6). | The package suites pass, with the tests of §6. |
| conformance fixtures and tests | The corpus regenerates under the new registry version and gains the packets of §6. The registry-conformance vectors gain the registry variants of §6. | `fixtures/corpus.py` runs them, and the registry-conformance suite runs the variants. |
| revision process and tooling | Four ledger notes. The heading record gains the two new subsections, and `spec/tools/framework_data.py` gains the reference entry and the expected registry version. No process rule changes. | `ledger.py`, `headings.py --check` and `verify.py` pass. |
| generated publications and developer documentation | The generated table listing, the combined rendering and the specification README's identifier table follow, and Part 08 §§2 and 3 carry the new version. The writer's guide documents the adapter, both ownerships and the `contributes` case. | The generators leave the candidate state unchanged. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 02 §2.2. §§3.2 and 3.3 are `applied` at the new subsections of Part 02
§§11 and 12, and §3.4 at Part 02 §§2.6, 4 and 11. §3.5 is `applied` at Part 02 §13, §3.6 at Part 03
§§3.1 and 7 and Part 09 §§2 and 3, §3.7 at Part 05 §4.3, and §3.8 at Part 02 §9.2 and Part 08 §§2
and 3. Each is placed by its canonical anchor. The registry carries the declarations of §§3.2 to
3.5.

Positive packets:

- one holding a packet-owned sidecar that is a file, a packet-owned sidecar that is a directory and
  a referenced sidecar, each bound to a `core.sidecars` row. The first has no scope row, the second
  one scope row naming a subject, and the third scope rows naming two sessions and a row of an
  extension's table. One row carries a null `sidecar_type` and `media_type`, one carries a
  `media_type` its registry registers, and one carries a `sidecar_type` and a `media_type` that no
  list holds; and
- one holding `core.sidecars` rows and no `core.sidecar_scopes` resource.

Negative packets, each failing under a check an existing rule defines:

- a `core.sidecars` row that no entry binds;
- an entry declaring `core.sidecar_instances` that no row binds;
- two `core.sidecars` rows of one `resource_id`;
- a scope row whose `resource_id` no `core.sidecars` row holds;
- a scope row naming a table that no registry the packet binds declares;
- a scope row naming a row of `core.probes` in a packet that carries no `core.probes`;
- a scope row naming `core.coordinate_frames`, whose key is two columns;
- a scope row naming a subject the packet does not hold;
- a scope row holding a null `scope`; and
- a sidecar's entry carrying `derived_from`.

Negative registry documents: a canonical table that references `core.sidecars` and a canonical
declaration that requires it, each refused by the canonical-target invariant of Part 02 §9.4;
`core.sidecars` without `metadata`; and `core.sidecars` with a group list.

Implementation tests:

- a build delivers a sidecar as a file, as a directory and as a referenced resource;
- a build takes sidecars from two sources that each contribute to `core.sidecars`;
- a build lists a copy of a recorded source file as a sidecar and keeps the source-file row;
- an amending build adds a sidecar and a scope row to a packet that binds the earlier core registry
  and lists none, and again to the packet that results;
- an amending build refuses a delivered `core.sidecars` row whose `resource_id` the packet holds
  with another `description`; and
- the reader lists both tables and resolves a sidecar by its resource ID.
