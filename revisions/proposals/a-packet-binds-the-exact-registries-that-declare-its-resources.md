# A packet binds the exact registries that declare its resources

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-23 |
| **Based on** | `cbfbccf384c7d0d754c2255157fb482da5358721` |
| **Decision domain** | specification |
| **Affects** | packet-catalog structure, registry identity and embedding, resource presence, catalog semantic checks, and referenced-resource schema generation |

## 1. Problem

The packet catalog is not yet one complete, data-driven contract. Its prose, JSON
Schema, registry declarations, and implementations disagree about three connected subjects.

First, a packet does not identify the exact registry documents that give its resources meaning.
The catalog records a bare core `registry_version` and assumes the fixed path
`schemas/logical_schemas.json`. Its `extensions` map uses a namespace as a key, requires only a
registry path in JSON Schema, and merely permits the version that Parts 04 and 09 require. Neither
binding records a content digest. Two different documents can therefore carry the same declared
version, and a catalog cannot establish which bytes its `declaration_id` values select.

Second, Part 04 and `registry/manifest.schema.json` describe different document shapes. Part 04
requires `validation_state` on every resource, but the schema does not. The schema admits
top-level and resource properties whose meanings Part 04 either withdrew or never defines. Several
nested objects remain open, while other objects are closed. The referenced-resource delivery
schema manually repeats a subset of the manifest resource entry even though it describes that
entry as the sole definition.

Third, constraints that cross entries or documents do not have one stated conformance boundary.
JSON Schema cannot establish resource-ID uniqueness, registry-byte identity, declaration
resolution, declaration-selected presence, dependency closure, catalog-row binding, lineage
acyclicity, or processing-run resolution. The validator implements many of these checks, but the
ordinary reader still builds a last-entry-wins resource map before detecting duplicate IDs, and
the manifest loader does not enable JSON Schema format checking. The current prose leaves the
packet-level `processing_run_id` as a string name while the table with that field name owns an
assigned integer identifier.

These are not independent cleanup tasks. Requiredness can be evaluated only after the catalog has
selected exact checked registries, and a registry binding is useful only if every resource entry
resolves through it under one catalog contract.

## 2. Evidence

The observations below were reproduced from the recorded baseline with a clean working tree.

- `uv run --project escapewheel-writer python verify.py --quick` passed all 31 stages, including
  regeneration, registry checks, the 29-packet corpus, citations, lifecycle checks, and candidate
  state preservation. The existing verifier therefore demonstrates internal reproducibility but
  does not detect the catalog disagreements below.
- [Part 04 §3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-identifiers)
  requires a bare `registry_version`. [Part 02 §9.2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-self-description)
  says a packet should embed the core registry and compares only that version. The validator reads
  the core registry from a hard-coded path and accepts a caller-supplied mapping when no embedded
  copy exists.
- Part 04 §8 and Part 09 §5.3 require an extension namespace, version, and registry path. The manifest
  schema requires only `registry`; the reader silently omits an absent or unparseable declared
  extension from its loaded map; and the validator checks only extension bytes it can acquire.
- The manifest schema requires 10 root properties but does not close the root. Its resource entry
  requires only `resource_id`, `declaration_id`, and `uri`, while
  [Part 04 §4.1](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-resource-entry-fields)
  also requires `validation_state`.
- The schema still admits the withdrawn top-level `provenance` block. It also admits `creators`,
  `dataset_id`, `keywords`, `license`, `release_id`, `source_summary`, and resource-level
  `semantic_type`, none of which has a current Part 04 field contract. `release_id` is particularly
  liable to be confused with the later specification-release identity, which is a different
  document.
- The ignored generated corpus contains 29 packet manifests and 866 resource entries. Its valid
  fixture carries the stale top-level `dataset_id` and `provenance` fields. The reference writer
  emits neither, but does emit the separately specified `retention` object. Regeneration, rather
  than compatibility handling, is available because there are no released consumers or remote.
- The incorporated core registry has 43 singleton table declarations: `core.sessions` is required
  and 42 are optional. Its dense-array and opaque declarations use catalog or family instances.
  The four example extension registries in `registry/extensions/` contain 11 optional singleton tables and no
  required singleton. The validator already evaluates required singleton presence, transitive
  singleton dependencies, populated-reference targets, dense-array axes, and catalog-family
  binding from these declarations.
- The validator already reports duplicate packet resource IDs as
  `packet.resource.id_unique`. The reader constructs `{resource_id: resource}` dictionaries in its
  constructor, so duplicate IDs are silently reduced to the last entry during ordinary access.
- The validator accepts a packet-entry string `processing_run_id` if it equals either an assigned
  integer `core.processing_runs.processing_run_id` or a non-null string
  `processing_run_name`. This union is not one logical identity. Current writer-generated values
  are names such as `import.<digest>`, so the implementation already follows the name branch.
- `registry/resources.schema.json` copies the three required entry fields, their patterns, and the
  retired-field exclusions from the manifest schema. No generator proves those definitions equal.
- `Manifest.load()` uses `Draft202012Validator` without a `FormatChecker`, so malformed
  `created_at`, `validated_at`, and `verified_at` strings can pass despite their `date-time`
  declarations. Registry-document checking already uses a format checker, demonstrating the
  available implementation path.
- No numbered part expressly incorporates `registry/manifest.schema.json`, so under
  [Part 00 §2.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-authority-by-concern) it
  owns nothing: Part 04's field tables are the sole owner of catalog shape, and the schema is an
  unchecked implementation copy of them. Part 03 §11 says the referenced-resource document's shape
  "is published as" `registry/resources.schema.json` without incorporating it either, and it
  describes each entry as the one "Part 04 §5 declares", although Part 04 §4.1 declares the entry
  fields. Part 02 and Part 03 already incorporate their exact JSON Schemas and descriptors while
  their prose owns meaning, which is the pattern the catalog lacks.
- Every one of the 29 generated fixture packets carries `core.processing_runs`, and every name its
  catalog entries reference matches exactly one row's non-null `processing_run_name`. Accepted
  revision R128 deferred this identity to the complete manifest reconciliation and forbade making
  the nullable name packet-unique merely to create a join.
- Four locally built development packets outside the repository (52 MB to 1.2 GB) embed core
  registry 0.1.0 and all four example extensions, while the incorporated core registry is 0.5.0.
  None retains a superseded manifest. The repository verifier and package tests do not read them;
  only measurement probes under `conformance/` do. They already predate the current contract.

The logical declaration work already resolved the shape of requiredness: singleton declarations
carry required or optional presence, catalog and family declarations have no minimum count, and
dependencies and populated rows can make otherwise optional singleton resources necessary. This
proposal does not reopen that model.

## 3. Desired outcome and constraints

A successful revision would leave one comprehensible packet-catalog contract with these
properties:

- the catalog selects every core and extension registry by stable identity, version, packet-local
  path, and digest of the exact embedded document bytes;
- the selected documents identify themselves, and one named semantic phase compares all four
  binding facts before registry-derived packet checks run;
- one authoritative catalog schema owns complete local JSON shape and format declarations, and
  Part 04 prose owns their meaning and every cross-field or cross-document rule;
- the registry declarations remain the sole owners of logical resource presence and dependencies;
- named catalog checks own uniqueness, cross-document resolution, and cross-field relationships
  that JSON Schema cannot express;
- the referenced-resource delivery schema projects its entry definition from the catalog entry
  rather than maintaining a second hand-edited definition;
- ordinary access does not become whole-packet validation and does not require a validation
  receipt; and
- packet validity composition, unavailable-extension verdicts, final release identifiers, and the
  immutable specification release remain available to their separate decisions.

The current project has no compatibility obligation to the superseded development manifest shape.
Generated packets and fixtures can be regenerated atomically with the owning schemas and
implementations. Local development packets are rebuilt on demand, as they already must be for the
current registry.

## 4. Options and tradeoffs

### 4.1 Registry binding

**Keep the current asymmetric fields.** Add `registry_sha256` beside the core
`registry_version`, require extension versions, and add a digest to each extension entry. This is
the smallest serialized diff, but retains an implicit core path, has no stable core-registry
identity, and leaves core and extension binding as two unrelated contracts.

**Use one registry-binding map.** Replace the bare core version and extension inventory with a
closed `registries` object keyed by stable registry ID. Each value contains `role` (`core` or
`extension`), `version`, packet-relative `path`, and `sha256`. Exactly one entry has the core role.
Every registry document gains the same stable `registry_id`; an extension's `registry_id` equals
its namespace-owning `extension_id`. The user chose this option because one descriptor and
one comparison algorithm cover every registry, while the role keeps core discoverable without a
reserved filename.

**Use an array of descriptors.** This resembles general artifact manifests, but identifier
uniqueness becomes another semantic check and lookup requires a scan. A JSON object already gives
unique keys and direct lookup, so an array adds no useful ordering semantics here.

Each descriptor's `sha256` covers the exact file bytes, avoiding a new canonical-JSON algorithm.
Final registry IDs, versions, and digest values can be assigned after the remaining contract
changes; this decision defines their shape and comparison semantics.

### 4.2 Embedding or referencing the core registry

The core registry is 182,460 bytes (18,253 gzipped); the four example extensions total 72,498 bytes
(10,359 gzipped). The two real packets built from it are 749 MB and 1.2 GB, so embedding the core
and every example extension adds about 0.03% to the smaller one. In a synthetic fixture of 285 KB
the same registry is most of the packet, but fixtures are not a storage workload. Across a
collection the cost is linear: 10,000 packets would carry about 1.8 GB of identical core copies.

**Embed every bound registry.** The packet remains self-describing and readable offline, for as
long as its files survive, without any registry distribution service. The reader already uses the
embedded copy for declaration resolution and session scope, and the one amended real packet
continued to work when the reference registry's version moved backwards during pre-release
iteration.

**Reference the core registry and embed extensions.** The core descriptor keeps `registry_id`,
`version`, and `sha256` but has no `path`; a reader or validator resolves those bytes from a
digest-keyed store of released core registries, such as copies vendored in the reader and
validator packages. This removes the duplicated core bytes but makes the packet unreadable to
any consumer lacking that exact release. It also depends on work that does not yet exist:
immutable registry releases, a resolution rule, and a vendoring or retrieval policy for
every historical release. Extensions have no publication home, so they would still be embedded,
reintroducing the core/extension asymmetry this decision otherwise removes.

**Require the digest and make embedding optional.** A packet may carry a copy or omit it. This
defers the choice to writers but doubles the reader and validator acquisition paths and their
negative tests, and a consumer cannot know in advance whether a packet is self-contained.

The user chose embedding every bound registry because the measured cost is
negligible against real packets and referencing needs a release and resolution infrastructure
that v0.2 does not otherwise require. Referencing remains a compatible later addition: a future
revision could make `path` optional for a core role whose digest names a released registry.

**Store embedded registries gzip-compressed.** The user conditioned embedding on compression. Compression reduces the embedded core from 182 KB
to 18 KB and the four example extensions from 72 KB to 10 KB, removing about 89% of the collection
cost. Gzip rather than Zstandard, because Zstandard (15 KB for the core) enters the Python
standard library only in 3.14 while the implementations support 3.12, and gzip is available in
every mainstream language runtime. The encoding is fixed rather than a writer option, so a reader
has one acquisition path. The descriptor's `sha256` covers the decompressed document bytes, not
the gzip stream: gzip output varies with header fields, compression level, and implementation,
and a digest of the document itself stays comparable with a registry's published bytes.

### 4.3 Manifest closure and dormant fields

**Preserve open objects and every admitted field.** This minimizes fixture changes but leaves
misspellings valid and gives dormant fields apparent authority without defining their semantics.

**Close the catalog and retain only fields with current owners.** Close the root, registry
bindings, validation summary, resource entries, member entries, store digests, retention object,
and all other locally defined objects. Retain the Part 04 fields and Part 03's `retention` object.
Remove the withdrawn `provenance` block and the currently unowned `creators`, `dataset_id`,
`keywords`, `license`, `release_id`, `source_summary`, and resource-level `semantic_type`. The user
chose this option. A future proposal can add a field with a precise meaning; arbitrary
typed scientific facts continue to belong in registry-declared resources rather than catalog
extensions.

**Add a generic annotations object.** This catches root misspellings while permitting arbitrary
metadata. It also creates an attractive place for untyped scientific or conformance facts and
would require rules defining what consumers may ignore. No demonstrated packet need justifies it.

### 4.4 Cross-document and cross-field checks

**Leave checks as implementation details.** This preserves code but does not tell independent
implementations which conditions decide catalog conformance or how findings correspond.

**Define a named catalog semantic phase.** Part 04 would enumerate stable check IDs and their
conditions for registry bindings, unique resource IDs, declaration resolution, instance binding,
presence and dependency closure, catalog rows, lineage, processing-run resolution, external/source
relationships, and member/digest consistency. JSON Schema remains the local-shape phase; checked
registry contexts precede declaration-derived checks. The user chose this option. It makes
the existing data-driven checks explicit without inventing a second SQL-like language for JSON
cross-document relationships.

The semantic checks would run for a conformance claim or writer publication. An ordinary reader
would still parse the catalog and resolve only what an operation needs. Duplicate resource IDs are
different: because silently selecting one entry changes ordinary lookup meaning, the catalog
loader would reject them before constructing its lookup map.

### 4.5 Processing-run binding

**Keep the string `processing_run_id` and its union lookup.** This retains bytes but lets the same
field sometimes denote an integer primary key and sometimes a name.

**Make it an integer foreign key.** This matches the table primary key but exposes a packet-local
assigned number in the catalog and requires the writer to serialize a different type.

**Rename it `processing_run_name` and resolve it only through that column.** This matches current
writer values, preserves name-based catalog identity, and makes the join explicit. A present value
would require `core.processing_runs` and exactly one row with the same non-null name. The user
chose this option. The declaration's `producing_run` policy governs the renamed field. Only a
referenced name must be unambiguous; unreferenced and null names remain unconstrained, so the
column does not become packet-unique and R128's constraint holds.

### 4.6 Catalog-schema authority

**Keep Part 04's field tables as the owner.** The schema remains an unincorporated implementation
file. Closure, patterns, formats, and object shape would have to be restated in prose, and nothing
would prevent the two from drifting again, which is the disagreement this proposal documents.

**Make the schema a generated projection of Part 04.** Prose tables would own every structural fact,
and a generator would emit the schema. Prose tables cannot express patterns, conditional shapes,
and closure precisely enough to generate a faithful schema without a second structured source.

**Have Part 04 expressly incorporate `registry/manifest.schema.json`.** The schema owns exact
local JSON structure: field names, types, required members, closure, patterns, and formats. Part 04
prose owns field meanings, declaration-selected presence, and the named semantic checks. Part 04's
field tables become an informative projection generated from and checked against the schema, as
Part 02's column tables are generated from the registry. This is the recommendation because it
repeats the ownership split Parts 02 and 03 already use and gives the catalog one editable
structural source.

Under either of the last two options, the referenced-resource document's entry is the catalog entry.

### 4.7 Shared resource-entry structure

**Use external JSON Schema references at runtime.** Both documents can refer to a standalone
entry schema, but every consumer must then package and resolve another schema resource.

**Generate the delivery entry from the catalog definition.** The catalog schema remains the sole
structural owner of a resource entry. `registry/build.py` copies that exact definition into the
standalone referenced-resource schema and fails if a hand-edited projection differs. Part 03 keeps
the delivery obligations and cites Part 04 for the entry shape. This option is selected because both
deployed schemas remain self-contained while only one definition is edited.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Registry binding and packet catalog mechanics do not alter scientific meanings. |
| logical prose, registry meta-schema, registry declarations, and declarative rules | Every registry document gains a stable `registry_id`, equal to `extension_id` for an extension. Part 02 §9.2's version-only self-description and optional embedding become the descriptor comparison and a mandatory embedded copy. The registry-contract descriptor gains a semantic invariant that an extension registry's `registry_id` equals its `extension_id`, which JSON Schema cannot compare. Resource presence, dependencies, kinds, tables, and rules remain unchanged. Current registry identities advance mechanically because the root shape changes. |
| physical profiles | Affected in layout only. Part 03 §3.1's fixed `schemas/logical_schemas.json` and `extensions/<name>.json` entries become gzip members at catalog-recorded paths, and §9.3's superseded-registry retention distinguishes copies by registry ID and version. `profile_id` remains the sole physical-profile selector, and no resource encoding fields return to the catalog. Part 03 §11's delivery entry cites Part 04 §4.1 instead of §5. |
| packet catalog and incorporated JSON Schemas | Affected directly: Part 04 incorporation of the catalog schema and generated field tables, registry bindings, object closure, required fields, stale-field removal, format enforcement, semantic-check inventory, and generated delivery-entry projection. |
| validation and import | The writer emits and hashes all embedded registries before the final catalog; validation compares binding identity, role, version, path, and exact bytes before declaration-derived checks. Existing declaration-presence checks become named catalog checks rather than local policy. |
| extension registries | The same binding and identity contract applies without naming any particular extension in a numbered part. Example registries and extension fixtures migrate and advance independently. |
| reader | Catalog loading rejects duplicate resource IDs before map construction and enables JSON Schema format checking. Registry loading follows declared paths rather than constants. Ordinary access remains lazy and does not run whole-packet conformance. |
| writer | Registry files are serialized first, their exact bytes are hashed, and the final catalog records the descriptors. Stale catalog fields and the old extension inventory disappear. |
| validator | Core and extension acquisition becomes descriptor-driven. Binding failures receive stable catalog check IDs; only valid checked contexts direct declaration-derived checks. Final core/extension/packet verdict composition remains separate. |
| adapters and code generation | Adapters retain declaration IDs and resource entries. The referenced-resource schema is generated from the manifest resource definition; no adapter chooses registry identity. |
| existing packets and migration | All fixtures are regenerated, and local development packets are rebuilt on demand. The implementation need not accept the superseded manifest shape. No existing packet retains a superseded manifest, and an amendment cannot span the change because it may not alter the standard versions, so no packet mixes catalog shapes. |
| conformance fixtures and tests | Add positive core-only and extension packets plus negatives for every binding comparison, path rule, format, duplicate ID, required singleton, dependency, catalog binding, lineage edge, processing-run name, external/source relation, stale field, and projection mismatch. |
| revision lifecycle, ledger, evidence, and process tooling | Unchanged except for the ordinary revision and evidence records. |
| generated publications and developer documentation | Part 04, relevant Part 02/03/05/08/09 passages, examples, schemas, vendored copies, public reader/writer types, and manifest examples regenerate together. |

## 6. Open questions

The user approved these resolutions of the earlier questions on 2026-09-23:

1. One closed `registries` map, keyed by registry ID, replaces `registry_version` and
   `extensions`; each descriptor carries `role`, `version`, packet-relative `path`, and `sha256`,
   and exactly one descriptor has the core role.
2. Every registry document carries a stable `registry_id`; an extension registry's value equals its
   `extension_id`. Final identifier strings are assigned with the other release identifiers.
3. A conforming packet embeds every bound registry as a gzip member whose descriptor `sha256`
   covers the decompressed document bytes. Remote registry resolution and an absent embedded
   registry are non-conforming; raw catalog access to a damaged packet remains possible.
4. The catalog is closed at every locally defined object, and `provenance`, `creators`,
   `dataset_id`, `keywords`, `license`, `release_id`, `source_summary`, and resource-level
   `semantic_type` are removed.
5. The packet entry's `processing_run_id` becomes `processing_run_name` and resolves to exactly one
   `core.processing_runs` row with that non-null name.
6. Catalog loading rejects duplicate resource IDs before building its lookup map; the remaining
   named catalog checks run for explicit validation and writer publication.

One question remains:

7. Should Part 04 expressly incorporate `registry/manifest.schema.json` as the exact owner of
   local catalog structure, with Part 04's field tables regenerated from it as an informative
   projection and `registry/resources.schema.json` generated from its resource entry?

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
