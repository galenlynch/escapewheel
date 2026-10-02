# Core declares a catalog of sidecars

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `9b8dcff1e054ae2d6a80f91eeb389f2b0dceb729` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§2.2, 2.6, 11 and 13; Part 03 §§3.1 and 7; Part 09 §§2 and 3; the core registry |
| **Depends on** | R128 §3.2 (the content classes, whose `documentation` row this restates); R128 §3.6 (the three catalog families, to which this adds a fourth); R140 §3.3 (Part 02's normative references, which gain an entry) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A packet often has to index a file that Escapewheel does not interpret and that nothing in the
packet depends on: a protocol as a PDF, a README, a viewer's saved state, or a scan of the subject
that another holder keeps. Part 02 §2.2 calls such a file a sidecar and gives it a content class,
`documentation`. Part 03 §§3.1 and 7 and Part 09 §2 place a sidecar in a directory `docs/` under
the packet root.

No registry declares a resource of that class, so no manifest can list a sidecar. A file in `docs/`
is a stray: no entry records its digest, no reader lists it, and a copy that follows the manifest
leaves it behind. Listing one today takes an extension registry that declares an opaque resource
and an adapter that delivers the payload.

This revision has the core registry declare a catalog table of sidecars and the opaque resources it
catalogues, both of class `documentation`. It restates what that class means, says what a sidecar's
row states, and removes `docs/` and the two sentences that place a value in a sidecar. It changes
no rule of delivery, storage, validation or amendment, since those already serve an opaque catalog
and a documentation resource.

The change is structural because the rules it restates sit in the middle of Part 02 §2, Part 03 §§3
and 7 and Part 09 §§2 and 3, and an appended section would leave each of them contradicting it.

### 1.1 Structural crosswalk

Part 03 §7 and Part 09 §§2 and 3 lacked canonical anchors. The baseline commit adds
`ew-metadata-placement`, `ew-metadata-tiers` and `ew-core-inclusion-rule` and changes nothing else.
The other amended sections already carried anchors. No section moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §2.2, `documentation` means human-readable sidecars that assert no fact | revise in place | same section | a sidecar is a file the packet indexes and asserts nothing through, whoever reads it; listing one records no dependence | §3.1 |
| Part 02 §2.6, three catalog tables carry `resource_id` | revise in place | same section | `core.sidecars` is a fourth | §3.3 |
| Part 02 §11, the core resource index | extend with a subsection | a new subsection at the end of Part 02 §11, anchored `ew-core-sidecar-resource-index` | the index lists the two declarations | §§3.2, 3.3 |
| Part 02 §13, four reference entries | extend in place | same section | a fifth entry, a living registry | §3.4 |
| Part 03 §3.1, the layout's `docs/` line | remove | Part 03 §11 already places a packet-owned opaque payload | the layout recommends no directory for an unlisted file | §3.5 |
| Part 03 §7, a lab-specific value in a sidecar and human-readable context in `docs/` | revise in place | same section | a value belongs in a column or an extension, and context in a listed sidecar | §3.5 |
| Part 09 §2, tier 4 in `docs/` sidecars | revise in place | same section | tier 4 is the sidecars `core.sidecars` lists | §3.5 |
| Part 09 §3, a field in an extension or a sidecar | revise in place | same section | a field is not placed in a sidecar | §3.5 |

## 2. Background

Observed in the tracked files at the baseline commit.

### 2.1 The parts name a place for a sidecar and declare none

The core registry holds 48 declarations, 43 of class `core` and 5 of class `analysis`. The
extension registries in the repository hold 11, all of class `extension`. No declaration has the
class `documentation`. A search of `spec/parts/` for `docs/` and `sidecar` finds six statements: one
in Part 02 §2.2, one in Part 03 §3.1, two in Part 03 §7, and one each in Part 09 §§2 and 3.

Part 03 §9 defines a stray as a file under the packet root that no manifest ever named, and Part 05
§15.5 lets a packet carry one. Part 04 §4.3 records a digest for a manifest entry only.

Two of the six treat a sidecar as a place for values: Part 03 §7 places lab-specific
values in a `json_string` column or a sidecar, and Part 09 §3 says a lab-specific or free-form field
should be in an extension or a sidecar. A file holding values a consumer relies on does not fit a
class defined as asserting no fact.

### 2.2 The one opaque declaration in core describes frames on a clock

`core.media_asset_instances` is core's only opaque declaration, catalogued by `core.media_assets`.
Its catalog row requires a session and carries a presentation-timestamp rate and a clock. A document
has none of these, so a row for one would state nothing true about it.

A manifest entry cannot describe the file either. Part 04 §4.1 gives an entry eleven members, and
none states a media type, a title or a description, so a catalog row is the only place an opaque
resource is described.

### 2.3 The existing rules already serve a documentation catalog

- **Delivery.** Part 12 §5 binds a payload to the catalog row of an opaque catalog family whose
  `resource_id` equals the payload's resource directory, and delivers a referenced resource as an
  entry of a resource document. Neither rule names a particular family.
- **Storage.** Part 03 §11 stores a packet-owned opaque payload under its own name, and Part 03 §2
  lets an opaque resource be packet-owned or external.
- **Dependence.** Part 02 §2.2 forbids a canonical declaration a reference, a `requires` entry or a
  catalog binding that targets a documentation declaration, and Part 02 §2.7 permits no class to
  take a documentation resource as a lineage source. Both are checked on the registry document and
  the manifest.
- **Amendment.** Part 05 §15.2 lets an amendment add a resource other than a canonical table, and
  remove or replace a documentation resource.
- **Registry.** The registry-document contract admits `documentation` in a core registry.

### 2.4 A table has a session or has none, and core already states a nullable scope

Part 02 §7.1 requires a session-scoped table to carry a required `session_id` and forbids the column
to any other table. A sidecar may be about the packet, a subject, a session or one resource, so no
session column fits.

`core.processing_runs` carries `scope_kind`, a discriminator holding the dotted ID of a table, and
`scope`, the key or name of a row of that table. Both are nullable, and the rule
`core.processing_runs.scope_pair_complete` requires them together or not at all.

### 2.5 The provenance tables record a file a result was computed from

Part 04 §7 places provenance in `core.source_files`, `core.processing_runs` and
`core.processing_run_inputs`. A `core.source_files` row carries a required `uri` and a nullable
`sha256`, and locates a file the packet need not own. Part 05 §7 requires a row for each distinct
root among a recipe's sources, and no part limits the table to those rows.

### 2.6 Alternatives

- **Retire `docs/` and the class.** This removes the contradiction of §2.1 at the least cost, and
  leaves a viewer state or a pointer to a scan unlisted, with no digest and no way to find it.
- **Let a manifest list a resource with no declaration.** This contradicts Part 05 §10, and the
  entry would have no content class, lineage policy or instance rule for a validator to apply.
- **Declare the catalog with class `core`.** A sidecar would be canonical, so an amendment could
  add one and never replace or remove one, and correcting a README would take a replacement packet.
- **Declare an opaque family with no catalog.** An instance would have no description or media
  type (§2.2), and Part 12 §5 gives a family payload no binding rule.

## 3. Decision

The five clauses below restate the class, declare the table and its instances, name the authority
for a media type, and restate where metadata is placed.

### 3.1 A sidecar is a file the packet indexes and asserts nothing through

The `documentation` row of Part 02 §2.2's content-class table reads:

| value | meaning | canonical | required by class |
|---|---|:---:|:---:|
| `documentation` | sidecars, which are files the packet indexes and asserts no semantic or conformance fact through, and the catalog that lists them | no | no |

A sidecar MAY be read by a person or by a program. Listing a file as a sidecar records no
dependence on it. A file that a result in the packet was computed from is recorded by the provenance
tables (Part 04 §7), and the same file MAY also be listed as a sidecar. A file whose meaning a table
of the packet states is not a sidecar: it takes a dense-array declaration or a declaration of an
extension.

### 3.2 `core.sidecars` lists a packet's sidecars

The core registry MUST declare `core.sidecars`: content class `documentation`, kind `table`, a
singleton of `optional` presence, `requires` empty, `lineage` `forbidden`, primary key
`sidecar_id`, no reference, and `amendment_groups` empty. Its columns, in order, are:

| column | type | presence | role | further fields | holds |
|---|---|---|---|---|---|
| `sidecar_id` | `int32` | required | identifier | identity `assigned` | the row's identity |
| `sidecar_name` | `string` | required | data | vocabulary `free` | the name `sidecar_id` stands for (Part 02 §8.2) |
| `resource_id` | `string` | required | identifier | identity `carried`; vocabulary `free` | the packet resource ID of the catalogued file |
| `media_type` | `string` | nullable | data | vocabulary `open`; `authority` as §3.4 gives it | the file's media type, as `type/subtype` |
| `description` | `string` | nullable | data | vocabulary `free` | what the file is, in prose |
| `scope_kind` | `string` | nullable | discriminator | `resolves` `optional`; `discriminates` `scope` | the table holding the row the sidecar is about, as a dotted resource ID |
| `scope` | `string` | nullable | data | vocabulary `free` | that row's key where the key is carried, and its `*_name` where it is assigned |
| `metadata` | `json_string` | optional | data | the description Part 02 §8.6 fixes | as Part 02 §8.6 states |

The table carries no `session_id`. A row whose `scope_kind` and `scope` are null describes a
sidecar about the packet. The table MUST declare the rule `core.sidecars.scope_pair_complete` at
level `error`, which reports each row holding one of `scope_kind` and `scope` without the other.

### 3.3 `core.sidecar_instances` are the files `core.sidecars` catalogues

The core registry MUST declare `core.sidecar_instances`: content class `documentation`, kind
`opaque`, catalog instances naming `core.sidecars` and its column `resource_id`, `requires` empty,
and `lineage` `forbidden`.

Part 02 §2.6 names `core.sidecars` beside `core.array_assets`, `analysis.array_assets` and
`core.media_assets` as a table carrying the required string identifier `resource_id`, with carried
identity and free vocabulary. `sidecar_id` remains row identity. The four tables carry neither `uri`
nor `format`; `media_type` states no physical encoding that Part 03 defines.

Part 02 §11 lists both declarations in a subsection of their own.

### 3.4 A media type is spelled as its registry spells it

`core.sidecars.media_type` MUST declare one `authority` entry, named `IANA Media Types` with the
URI `https://www.iana.org/assignments/media-types/`. Part 02 §13 MUST carry this entry:

| reference | candidate edition | application |
|---|---|---|
| [IANA Media Types](https://www.iana.org/assignments/media-types/) | living registry | the spelling of the names it registers, in open columns naming it (§9.3) |

Part 02 §9.3 then governs the value as it governs any open column that names a nomenclature. A
value the registry does not register conforms, and a null value states that no media type is known.

### 3.5 Context is placed in a listed sidecar and a value is not

Part 03 §3.1's recommended layout MUST NOT name a `docs/` directory. Part 03 §7's placement table
reads:

| kind | location |
|---|---|
| packet-level facts | the manifest |
| queryable scientific facts | tables |
| semi-structured, lab-specific values | a `json_string` column, or an extension's table |
| context the packet asserts nothing through | a sidecar that `core.sidecars` lists |

The location of tier 4 in Part 09 §2's table reads "sidecars that `core.sidecars` lists". Part 09
§3's third sentence reads: a field SHOULD be in an extension when it is institutional,
administrative, lab-specific, rarely queried, free-form, procedural but not required for analysis,
or biologically rich but not required to interpret the recording.

## 4. What this does not change

A file under the packet root that no manifest names, including one in `docs/`, remains a stray that
Part 05 §15.5 protects. An extension keeps the right to declare an opaque or documentation resource
of its own. Family mode keeps its definition in Part 02 §2.4, and Part 12 §5 still gives a family
payload no binding rule.

A referenced sidecar's entry records a digest only where the writer reached the file, as Part 04
§5.2 has it for any external resource.

## 5. Consequence

No existing packet changes in conformance: none carries either resource, and each binds the core
registry it was built with. A packet built afterwards binds a core registry of 50 declarations. An
amendment may add, replace or remove a sidecar, so a packet promises a sidecar's bytes for one
version only, and each version's manifest records the digest of a packet-owned one.

A sidecar is listed by the existing delivery rules, so an author needs an adapter that delivers the
catalog rows and the files, and no registry of their own.

At incorporation the ledger entries of R128 §3.2, R128 §3.6 and R140 §3.3 each gain a note naming
the clause above that restates part of them.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: a sidecar asserts no semantic fact, so Part 01 gains no concept. | Part 01 is byte-identical. |
| logical prose and registry | Part 02 §§2.2, 2.6, 11 and 13 as §3 states. The registry source gains the two declarations and the rule; the meta-schema and the registry-document contract are unchanged. | The registry checks pass over 50 declarations, and the authority comparison of Part 02 §13 passes with the new entry. |
| physical profiles | Part 03 §§3.1 and 7 as §3.5 states. Part 03 §11 and the profile descriptor are unchanged. | The descriptor is byte-identical. |
| packet manifest and JSON Schemas | Unchanged: a sidecar's entry uses the existing members. | The schemas are byte-identical. |
| validation and import | Unchanged in rule: the catalog-binding checks, the amendment table and the delivery rules already cover a documentation catalog (§2.3). Part 09 §§2 and 3 as §3.5 states. | The corpus cases of §6 produce their expected findings with no new check. |
| extensions | Unchanged: no extension registry is edited. | The extension registry checks pass. |
| reader, writer, validator, adapters | Each package's registry copy regenerates. The reader lists the table and resolves an instance as it does any catalogued resource. The writer gains an adapter that delivers the files a recipe names, each packet-owned or referenced. The validator applies its existing checks. | The package suites pass, with the tests of §6. |
| conformance fixtures and tests | The corpus gains the positive and negative packets of §6. | The corpus runs them. |
| revision process and tooling | Three ledger notes, and the heading record gains the new subsection of Part 02 §11. No process rule changes. | `ledger.py` and `headings.py --check` pass. |
| generated publications and developer documentation | The generated table listing and the combined rendering regenerate. The writer's guide documents the adapter. | The generators leave the candidate state unchanged. |

## 6. Conformance and implementation evidence

Positive packet: one holding a packet-owned sidecar and a referenced one, each bound to a
`core.sidecars` row, one with a null scope pair and one scoped to `core.subjects`.

Negative packets, each failing under an existing check or the new rule:

- a `core.sidecars` row that no entry binds;
- an entry declaring `core.sidecar_instances` that no row binds;
- a row holding `scope` and no `scope_kind`; and
- a sidecar's entry carrying `derived_from`.

Negative registry document: an extension table that declares a reference to `core.sidecars`, which
the canonical-target invariant of Part 02 §9.4 refuses.

Implementation tests: a build delivers a sidecar by each route; a build lists a copy of a recorded
source file as a sidecar and keeps the source-file row; and an amendment replaces one sidecar and
removes another, leaving the source-file row.
