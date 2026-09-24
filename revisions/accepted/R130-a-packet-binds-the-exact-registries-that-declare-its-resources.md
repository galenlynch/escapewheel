# A Packet Binds the Exact Registries That Declare Its Resources

| | |
|---|---|
| **Status** | **Accepted** 2026-09-23 |
| **Based on** | `c459cf9f7b9c1737a8f42d2d7e0d9ea894aed6a9` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§4.1 and 5.1; Part 02 §§2.1, 2.2, 2.5, 2.7, 9.1, 9.2, and 9.4; Part 03 §§1, 3.1, 9.3, 11.3, and 12, with a new §3.3; Part 04 §§1–4 and 7–10, with a new §10 and the references renumbered to §11; Part 05 §§5.3, 10, 14.5, and 14.6; Part 06 §§2, 4, and 5; Part 08 §§2–3; Part 09 §5.3; the specification README §4; `registry/manifest.schema.json`; `registry/resources.schema.json`; `registry/registry.schema.json`; the registry-contract descriptor; `registry/logical_schemas.json`; the example extension registries |
| **Depends on** | [R122 §§3.2–3.3](../accepted/R122-define-specification-artifacts-and-normative-ownership.md#3-decision); [R126 §§3.2–3.3](../accepted/R126-a-registry-document-has-one-complete-conformance-contract.md#3-decision); [R127 §§3.2, 3.4, and 3.6](../accepted/R127-registry-documents-are-checked-at-conformance-boundaries.md#3-decision); [R128 §§3.4–3.5, 3.7, and 3.9](../accepted/R128-every-packet-resource-instantiates-a-logical-declaration.md#3-decision); [R129 §§3.6–3.7](../accepted/R129-a-portable-profile-declares-its-interfaces-and-reader-floor.md#3-decision) |
| **Profile** | all; §3.5 applies to `escapewheel-portable-v0.1` |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8; §3.9; §3.10; §3.11 |

Section 3 is normative. Sections 1, 2, and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision makes the packet manifest one contract with one structural owner. The manifest names
every registry document that declares its resources by registry ID, role, version, packet path,
and SHA-256 digest, and a conforming packet carries each of those documents. Part 04 incorporates
the manifest's JSON Schema as the exact owner of local structure and enumerates the named checks
that JSON Schema cannot express. The manifest entry keeps its lineage and loses its producing-run
field, so recording which software ran becomes optional, and a reader checks only what reading
needs.

Here the manifest is Part 04's packet manifest, `packet.json` in the portable profile. "Catalog"
keeps only its Part 02 §2.6 sense of a catalog table and its rows, and a release manifest is Part
00's separate record of a specification release.

At the baseline, four representations of the manifest disagree: Part 04's field tables, the
unincorporated `registry/manifest.schema.json`, the hand-copied `registry/resources.schema.json`,
and the reference implementations. The manifest records a bare core `registry_version` and relies
on the fixed path `schemas/logical_schemas.json`; the schema admits eight fields that no part
defines and leaves the root open; and the validator reads a caller-supplied registry in place of
the packet's own copy.

This revision is structural. Part 04 §8 is replaced, §4.3 is retired, a manifest-conformance
section is inserted before the normative references, and Parts 02, 03, 05, and 09 move packet
binding, embedding, and manifest checks to their subject owners. Appending a registry-binding
section would leave the old extension inventory, the version-only self-description, and the shim's
producing-run paragraph as competing owners.

This revision decides that a missing, unreadable, or mismatched bound registry is a manifest
binding failure. It does not decide how that failure composes into core, extension, and packet
verdicts, whether a declaration-phase finding blocks writer publication, how a reader offers
partial access to a packet with an unusable extension, the final release identifiers, or the
specification release manifest.

### 1.1 Structural crosswalk

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 00 §4.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-core-content-requirements), core minimum names producing-run rules | revise in place | same section | the minimum no longer includes a producing-run rule | §3.7 |
| [Part 00 §5.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-analysis-content-requirements), Part 06 owns producing-run requirements | revise in place | same section | Part 06 owns lineage, realization, promotion, and optional run provenance | §3.7 |
| [Part 02 §2.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-resource-common-fields), declaration field `producing_run` | remove the field | none | a declaration carries no producing-run policy | §3.7 |
| [Part 02 §2.2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-resource-content-class), analysis and compatibility-projection policies | revise in place | same section | those classes require lineage only | §3.7 |
| [Part 02 §2.5](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-resource-presence), presence conditions | revise in place | same section | a bound extension registry is active; a producing run no longer requires `core.processing_runs` | §§3.3, 3.7 |
| [Part 02 §2.7](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-resource-provenance-policy), lineage and producing-run policy | revise in place; retitle "Lineage policy" | same section | lineage is the only declaration-selected provenance | §3.7 |
| [Part 02 §9.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document), required registry members | expand in place | same section and incorporated meta-schema | every registry document carries `registry_id` | §3.4 |
| [Part 02 §9.2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-self-description), a packet records a registry version and should embed the registry | replace the packet obligation with a pointer; revise identifiers | Part 04 §8 for binding; planned Part 03 section 3.3 for storage; this section for registry identifiers | version-only binding and optional embedding become a full descriptor and mandatory embedding | §§3.3–3.5, 3.11 |
| [Part 02 §9.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-conformance), contract descriptor and invariant inventory | revise in place | same section and incorporated descriptor | descriptor v0.3 selects meta-schema 0.6.0 and adds one extension invariant | §§3.4, 3.11 |
| [Part 03 §1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-scope), incorporated artifacts | expand in place | same section | incorporates the delivery schema | §3.10 |
| [Part 03 §3.1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-packet-layout), recommended layout with `schemas/logical_schemas.json` and `extensions/<name>.json` | revise in place | same section | recommends `registries/<registry_id>/<version>.json.gz` | §3.5 |
| no current section stores a bound registry | add | planned Part 03 section 3.3, "Bound registries", `ew-portable-bound-registries` | each bound registry is one gzip member at its descriptor path, embedded rather than resolved, and a named file for immutability, amendment, and cleanup | §3.5 |
| [Part 03 §9.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-superseded-manifest-retention), superseded registry copies distinguished by `registry_version` | revise in place | same section | retention and ambiguity are judged by registry ID, version, and digest | §3.5 |
| [Part 03 §11.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-referenced-resource-delivery), a delivered entry "as Part 04 §5 declares one" | revise in place | same section, Part 04 §4.1, and the incorporated delivery schema | the delivered entry is the closed manifest entry without its build-supplied members | §3.10 |
| [Part 03 §12](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-normative-references), portable-profile references | extend in place | same section | adds RFC 1952 and RFC 1951 | §3.5 |
| [Part 04 §1](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-catalog-scope), scope | expand in place | same section | incorporates `registry/manifest.schema.json` | §3.1 |
| [Part 04 §2](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-catalog-principles), names rather than numbers | revise in place | same section | the manifest holds no producing-run name | §3.7 |
| [Part 04 §3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-identifiers), hand-authored top-level field table | replace with a generated projection | incorporated manifest schema | `registries` replaces `registry_version` and `extensions`; the root closes | §§3.1–3.3 |
| [Part 04 §4.1](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-resource-entry-fields), hand-authored entry table and retired-field list | replace with a generated projection | incorporated manifest schema; Part 03 §10 for when `sha256` is recorded | closure replaces the retired-field list; `processing_run_id` and `semantic_type` are removed; the table's duplicate `sha256` SHOULD is dropped | §§3.1–3.2, 3.7 |
| [Part 04 §4.2](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-logical-resource-kinds), resolved logical facts | revise in place | same section | the declaration supplies no producing-run policy | §3.7 |
| [Part 04 §4.3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-withdrawn-catalog-blocks), withdrawn blocks | retire; move the provenance-table sentence to §7 | schema closure and Part 04 §7 | a withdrawn member is rejected by closure rather than by a list | §3.2 |
| [Part 04 §7](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-resource-lineage), producing-run field and deferred run identity | remove; retitle "Resource lineage" | same section | lineage alone; an entry names no run | §3.7 |
| [Part 04 §8](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-registry-bindings), extension inventory | replace | same section, retitled "Registry bindings" | one descriptor map binds core and every extension | §3.3 |
| [Part 04 §9](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-validation-block), hand-authored validation-block table | replace with a generated projection | incorporated manifest schema | the block closes and loses `report_uri` | §§3.1–3.2 |
| no current manifest-conformance section | add | planned Part 04 section 10, "Manifest conformance", `ew-packet-manifest-conformance` | ordered phases and named checks | §§3.6–3.9 |
| [Part 04 §10](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-catalog-normative-references), normative references | renumber to §11 | same content | none | none |
| [Part 05 §5.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-shim), shim list of declaration checks and the producing-run paragraph | replace with a citation of planned Part 04 section 10 | planned Part 04 section 10 | the check inventory gains one owner; producing-run resolution is removed | §§3.6–3.7 |
| [Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes), analysis `processing_run_id` is MUST | remove the sentence | none | an analysis resource need not name a run; provenance remains optional | §3.7 |
| [Part 05 §14.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validator-registry-boundary), embedded or caller-supplied core registry | revise in place | same section | only bound registries direct packet checks; missing-registry binding is decided | §3.9 |
| [Part 05 §14.6](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-registry-result-reporting), subject labels | revise in place | same section | a registry ID labels each bound registry's result | §3.9 |
| [Part 06 §2](../../escapewheel_poc_docs_v0.2/06_analysis_layer.md#ew-analysis-rules), required producing-run policy and the parameter rule | revise in place | same section, citing Part 06 §5 | lineage stays required and a run becomes optional; §5 owns run parameters | §3.7 |
| [Part 06 §4](../../escapewheel_poc_docs_v0.2/06_analysis_layer.md#ew-analysis-spike-events), bucket width, omitted count, and collision reason in the producing run | revise in place | same section, citing Part 06 §5 | each is a parameter of a run the writer chose to record | §3.7 |
| [Part 06 §5](../../escapewheel_poc_docs_v0.2/06_analysis_layer.md#ew-analysis-materialization-provenance), a materialization records a run and names it from the entry | replace | same section | a writer may record a run; a recorded run carries the parameters the output cannot recover | §3.7 |
| [Part 08 §2](../../escapewheel_poc_docs_v0.2/08_example_packet.md#ew-example-packet-layout) and [§3](../../escapewheel_poc_docs_v0.2/08_example_packet.md#ew-example-packet-catalog), example layout and manifest | regenerate | informative example | shows the descriptor map and gzip members | §§3.3, 3.5 |
| [Part 09 §5.3](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-registration), extension registration | replace | same section, citing Part 04 §8 | registration is a descriptor with role `extension` | §§3.3, 3.9 |
| Specification README §4, `registry_version` row | regenerate | Part 04 §8 and Part 02 §9.2 | lists the core registry ID and version rather than a manifest field | §3.11 |
| `registry/manifest.schema.json` | revise and incorporate | Part 04 | closed manifest shape at `manifest/0.4.0` | §§3.1–3.3, 3.7, 3.11 |
| `registry/resources.schema.json` | revise and incorporate | Part 03 §§1 and 11.3, with Part 04 §4.1 | closed delivery shape at `resources/0.4.0` | §§3.10–3.11 |
| `registry/registry.schema.json`, contract descriptor, core and extension registries | advance | Part 02 | `registry_id`, meta-schema 0.6.0, descriptor v0.3, core 0.6.0 | §§3.4, 3.11 |

Eight affected headings lacked canonical anchors; §6.1 records the two bootstrap commits that added
them.

## 2. Background

### 2.1 A packet does not identify its registry bytes

Part 04 §3 requires a bare `registry_version`, and Part 02 §9.2 says a packet should embed the core
registry and compares only that version. The validator reads the core registry from the hard-coded
path `schemas/logical_schemas.json` and lets a caller-supplied mapping direct packet checks in its
place. Two documents with different declarations can carry the same version, so a manifest cannot
establish which bytes its `declaration_id` values select.

Part 04 §8 and Part 09 §5.3 require each extension's namespace, version, and registry path. The
manifest schema requires only the path. The reader silently drops a declared extension whose file
is absent or unparseable, and the validator checks only the extension bytes it can acquire.

A single descriptor map binds core and extensions with one comparison. An array of descriptors
would need a uniqueness check and a scan and would give order no meaning. Keeping the asymmetric
fields and adding digests would retain the implicit core path and leave two binding contracts.

### 2.2 Embedding costs less than referencing

The incorporated core registry is 182,460 bytes, and the four example extension registries total
72,498 bytes. At gzip level 9 they compress to 18,289 and 10,337 bytes, 11% of their size. Four
locally built development packets measure 52 MB, 479 MB, 578 MB, and 1.2 GB on disk; the
uncompressed registries are 0.05% of the 479 MB packet. Across 10,000 packets, compressed core
copies total 183 MB.

Referencing the core registry by digest would shed those bytes but would make a packet unreadable
to any consumer lacking that exact release. It would also need immutable registry releases, a
resolution rule, and a policy for every historical release, none of which exists, and extensions
would still be embedded because they have no publication home. Optional embedding doubles every
acquisition path and its negative tests and leaves a consumer unable to tell in advance whether a
packet is self-contained.

Zstandard compresses the core registry to 14,770 bytes but enters the Python standard library
only in 3.14, while the implementations support 3.12. Gzip is available in every mainstream
runtime. The descriptor digest covers the decompressed document, because gzip output varies with
header fields, compression level, and implementation.

### 2.3 The manifest schema and Part 04 describe different shapes

No numbered part incorporates `registry/manifest.schema.json`, so under
[Part 00 §2.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-authority-by-concern) Part 04's
tables alone own manifest shape. R128 recorded the schema as an unincorporated projection and
deferred its incorporation to this reconciliation. The two disagree:

- Part 04 §4.1 requires `validation_state`, and the schema does not.
- The schema requires 10 root members and leaves the root open.
- The schema admits the withdrawn `provenance` block and the undefined `creators`, `dataset_id`,
  `keywords`, `license`, `release_id`, `source_summary`, resource-level `semantic_type`, and
  validation-level `report_uri`. `release_id` invites confusion with the specification release.
- The schema gives `resource_id` no pattern, while the delivery schema gives it
  `^[a-z0-9_]+\.[a-z0-9_.-]+$` and Part 04 requires a dotted, namespaced value.
- `registry/resources.schema.json` copies three entry fields, their patterns, and the retired-field
  list, and cites Part 04 §5 for an entry that Part 04 §4.1 declares.

Prose tables cannot state patterns, closure, and conditional shape precisely enough to generate a
faithful schema, so a schema generated from Part 04 would need a second structured source.
Incorporating the schema repeats the split Parts 02 and 03 already use: the artifact owns exact
structure and the prose owns meaning.

### 2.4 Format keywords are not asserted

The schema declares `format: date-time` for `created_at`, `validated_at`, and `verified_at`. The
reader's `Manifest.load()` validates without a format checker. The registry checker passes
`jsonschema.FormatChecker()`, but in all three package environments that checker asserts only
`date`, `email`, `idn-email`, `idn-hostname`, `ipv4`, `ipv6`, `regex`, `time`, and `uuid`: its
`date-time` and `uri` checkers need optional packages that no lockfile carries. With
`rfc3339-validator` added, the checker rejected `2026-09-04 04:22:45`, `2026-13-04T04:22:45Z`, and
the offset-free `2026-09-04T04:22:45`, and accepted `2026-09-04T04:22:45Z`. All 58 timestamps in
the 29 fixture manifests, and every writer timestamp, use the accepted form.

### 2.5 A required producing run forces a software record on every analysis resource

The v0.1 manifest carried a producing run as `activity_id` beside `derived_from`. R9 §4 renamed it
`processing_run_id` and made the manifest the record of what a run produced, and R31 §3 required
every analysis resource to name a run. R128 §3.7 turned both into declaration policies and
required both for every analysis declaration, so every recorded analysis chain had to terminate in
canonical resources.

`core.processing_runs.processing_run_id` is an assigned integer, while the manifest field with the
same name holds a string. The validator accepts a value that equals either an assigned integer or a
non-null `processing_run_name`, a union that is not one identity; an exact join would need a
uniqueness rule on a nullable name column that R128 declined to add.

The four local development packets, with 45 to 56 entries each, show what the requirements
produced. Each records lineage and a run on one entry, `analysis.spike_events`: its `derived_from`
lists `core.spike_events`, `core.clock_anchors`, and `core.clocks`, and its run is the single
`materialization` row among the 22 in `core.processing_runs`, naming the writer, its version, and
the materialization's parameters. No core or extension entry carries either field, the import run
is a session-scoped row that no entry names, and none of the 29 fixture manifests carries either
field.

Lineage and a run answer different questions. Lineage names the resources an analysis resource
was derived from, which the writer already knows and which traces every analysis resource to
canonical facts. A run records which software ran, when, and with which parameters; requiring one
obliges every producer of an analysis resource to keep an execution record.

Tables already carry the provenance a consumer queries: eight core tables and
`analysis.array_assets` have a row-level `processing_run_id` foreign key. Part 06 makes every
analysis resource disposable, and Part 05 §10 already treats provenance as optional within packet
conformance.

### 2.6 Cross-entry checks have no owner

JSON Schema cannot establish resource-ID uniqueness, registry-byte identity, declaration
resolution, declaration-selected presence, dependency closure, catalog-row binding, or lineage
acyclicity. The validator implements most of these as
`packet.resource.*` checks that Part 05 §5.3 lists without IDs. The reader builds
`{resource_id: entry}` in its constructor, so a duplicate ID silently keeps the last entry during
ordinary access, and `json.load` likewise keeps the last of two duplicate object members.

### 2.7 Compatibility

Every fixture is generated, and there are no released consumers or remote. The four local
development packets embed core registry 0.1.0 and need a rebuild under the current 0.5.0 registry
regardless. None retains a superseded manifest, and Part 03 §9.2 forbids an amendment from
changing standard versions, so no packet will mix manifest shapes. The superseded manifest fails the
closed 0.4.0 schema rather than being read under it.

## 3. Decision

Each subsection below is one Decision clause. Part 04 owns the manifest contract, Part 02 owns
registry-document identity, Part 03 owns how the portable profile stores a bound registry, and
Part 05 owns the validator's registry boundary.

### 3.1 Part 04 incorporates the manifest schema

Part 04 MUST expressly incorporate `registry/manifest.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/manifest/0.4.0`. The schema owns the manifest's exact local JSON
structure: member names, JSON types, required members, object closure, patterns, enumerations,
formats, and conditional shape within one entry. Part 04 prose owns every field's meaning,
declaration-selected presence, and the checks of planned Part 04 section 10. A disagreement between
Part 04 and the incorporated schema makes the specification candidate internally inconsistent.

The field tables in Part 04 §§3, 4.1, 8, and 9 MUST be informative projections of the schema.
Each row states the member name, JSON type, whether the schema requires it, and its pattern,
enumeration, or format.

A checker evaluating manifest shape MUST assert the `date-time` format that JSON Schema Validation
Draft 2020-12 defines.

### 3.2 The manifest is closed and carries only owned fields

The manifest root, registry descriptor, resource entry, member entry, store digest, validation
block, and retention object MUST each be closed. A manifest MUST NOT carry a member the
incorporated schema does not declare.

The root requires `packet_id`, `packet_version`, `profile_id`, `semantic_standard_version`,
`logical_standard_version`, `registries`, `created_at`, `sessions`, `resources`, and `validation`,
and admits `description` and `retention`. A resource entry requires `resource_id`,
`declaration_id`, `uri`, and `validation_state`, and admits `external`, `source`, `sha256`,
`size_bytes`, `verified_at`, `members`, and `derived_from`. The validation
block requires `status`, `validated_at`, `validator_name`, and `validator_version` and admits
nothing else. Part 03 §9.5 continues to own the meaning of `retention`.

These members are removed without replacement: root `registry_version`, `extensions`,
`provenance`, `creators`, `dataset_id`, `keywords`, `license`, `release_id`, and `source_summary`;
resource-level `semantic_type` and `processing_run_id`; and validation-level `report_uri`. Closure
also rejects every field that R128 and R129 retired, so the schema MUST NOT keep a separate
retired-field list. Provenance continues to reside in `core.source_files`,
`core.processing_runs`, and `core.processing_run_inputs`.

The schema MUST declare these constraints on resource-entry members:

| member | type | constraint |
|---|---|---|
| `resource_id` | string | pattern `^[a-z][a-z0-9_]*\.[a-z0-9_.-]+$` |
| `declaration_id` | string | pattern `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` |
| `uri` | string | nonempty; an absolute URI requires `external: true` |
| `validation_state` | string | one of `passed`, `failed`, `not_run` |
| `source` | string | nonempty; present only where `external` is `true` |
| `derived_from` | array of string | nonempty, unique items, each matching the `resource_id` pattern |

The remaining entry members keep their baseline types and constraints. Part 03 §10 continues to
own when a writer records `sha256`, so the generated entry table carries no presence rule for it.

### 3.3 A packet binds every registry by identity, role, version, path, and digest

The root member `registries` MUST be an object with at least one member. Each member name is a
registry ID matching `^[a-z][a-z0-9_]*$`, and each value is a closed registry descriptor:

| member | type | presence | constraint |
|---|---|---|---|
| `role` | string | required | `core` or `extension` |
| `version` | string | required | pattern `^\d+\.\d+\.\d+$` |
| `path` | string | required | packet-relative path, below |
| `sha256` | string | required | pattern `^[0-9a-f]{64}$` |

A descriptor's `path` MUST be a relative reference to a location under the packet root: one or
more nonempty segments separated by `/`, with no scheme, no leading `/`, no `\`, and no segment
equal to `.` or `..`. Its `sha256` is the SHA-256 digest of the exact bytes of the registry
document, without decoding, re-serialization, or any other canonicalization.

A manifest MUST contain exactly one descriptor with role `core` and MUST NOT give two descriptors
the same `path`. The document at a descriptor's path MUST:

- carry `registry_id` equal to the descriptor's member name;
- be a core registry exactly when the descriptor's role is `core`;
- carry `registry_version` equal to the descriptor's `version`; and
- carry `logical_standard_version` equal to the manifest's, and, for the core registry,
  `semantic_standard_version` equal to the manifest's.

A packet MUST bind the core registry and every extension registry that declares one of its
resources. Binding an extension registry activates its required declarations under Part 02 §2.5.
Every `declaration_id` resolves only in the bound registries.

### 3.4 Every registry document names itself

Every registry document MUST carry `registry_id`, a string matching `^[a-z][a-z0-9_]*$`. A core
registry's `registry_id` MUST be `core`. An extension registry's `registry_id` MUST equal its
`extension_id`, and therefore MUST NOT be `core`, `analysis`, or `nwb`.

The registry meta-schema MUST require `registry_id` and constrain the core value. The registry
contract MUST check the extension equality as the semantic invariant
`registry.identity.registry_id`, applicable to the extension class and ordered immediately after
`registry.identity.name`.

Part 02 §9.2 MUST NOT state a packet obligation. It cites Part 04 §8 for binding and planned Part 03
section 3.3 for storage and retains the incorporated meta-schema, core-registry identifiers,
extension-version independence, and selection rules.

### 3.5 The portable profile embeds each bound registry as one gzip member

Under `escapewheel-portable-v0.1`, a writer MUST store each bound registry at its descriptor's
path as exactly one gzip member under RFC 1952 using the DEFLATE method of RFC 1951. The
decompressed bytes MUST be exactly the bytes the descriptor's `sha256` covers. A gzip header's
modification time, operating system, file name, and comment carry no meaning, and a reader MUST
ignore them.

A conforming packet MUST contain every bound registry. A writer MUST NOT bind a registry by remote
location or omit the stored copy, and a reader or validator MUST NOT resolve a bound registry from
anywhere else. A descriptor path names a file for the immutability, amendment, and cleanup rules
of Part 03 §§8.1, 9.1, and 9.5. Planned Part 03 section 3.3 owns the rules of this paragraph and
the one above.

Part 03 §3.1 MUST recommend `registries/<registry_id>/<version>.json.gz` in place of
`schemas/logical_schemas.json` and `extensions/<name>.json`. The manifest still records the actual
location.

Part 03 §9.3 MUST state retention by descriptor: where an amendment binds a different registry
document, the packet retains the superseded copy at the path the superseded manifest records. A
writer MUST refuse an amendment that would bind, anywhere in one packet's current and retained
manifests, two different digests under the same registry ID and version.

Part 03 §12 MUST list RFC 1952 for the gzip member format and RFC 1951 for DEFLATE, each at its
exact edition.

### 3.6 Manifest conformance has ordered phases and named checks

Planned Part 04 section 10 MUST define manifest conformance as these phases, evaluated in order:

1. `json`, which decodes the manifest as UTF-8 JSON under RFC 8259;
2. `shape`, which validates it against the incorporated schema;
3. `entries`, which runs checks that need only the manifest;
4. `registry_binding`, which acquires and compares every bound registry; and
5. `declaration`, which runs checks derived from the bound declarations.

A checker MUST NOT run a later phase over a manifest with a finding in `json`, `shape`, or
`entries`. A shape finding carries the check ID `packet.manifest.schema` and the schema-location
pointer. Every finding in the table below is at `error` and names the owning resource ID or
registry ID where one applies.

| check ID | phase | a finding exists when |
|---|---|---|
| `packet.manifest.invalid_json` | json | the bytes are not UTF-8 or not JSON |
| `packet.manifest.duplicate_member` | json | an object repeats a member name |
| `packet.manifest.schema` | shape | the manifest violates the incorporated schema |
| `packet.resource.id_unique` | entries | two entries share a `resource_id` |
| `packet.resource.member_unique` | entries | two members of one entry share a `key` |
| `packet.resource.member_size` | entries | an entry with `members` records `size_bytes` unequal to the sum of the members' sizes |
| `packet.resource.member_digest` | entries | an entry records `sha256` and `members`, every member records `sha256`, and the entry's value differs from the Part 04 §5.4 digest of that member list |
| `packet.registry.core_count` | entries | the number of core descriptors differs from one |
| `packet.registry.path_unique` | entries | two descriptors share a `path` |
| `packet.registry.missing` | registry_binding | nothing exists at a descriptor's path |
| `packet.registry.unreadable` | registry_binding | the stored copy does not decode as the packet's physical profile requires |
| `packet.registry.digest` | registry_binding | the decoded bytes' SHA-256 differs from `sha256` |
| `packet.registry.identity` | registry_binding | the document's `registry_id` differs from the descriptor's name |
| `packet.registry.role` | registry_binding | the document's class differs from the descriptor's role |
| `packet.registry.version` | registry_binding | the document's `registry_version` differs from `version` |
| `packet.registry.standard` | registry_binding | a standard identifier differs from the manifest's under §3.3 |
| `packet.resource.declaration_unknown` | declaration | `declaration_id` names no declaration in a bound registry |
| `packet.resource.singleton_identity` | declaration | a singleton entry's `resource_id` differs from its declaration ID |
| `packet.resource.family_namespace` | declaration | a family entry's `resource_id` lies outside its declaration's namespace |
| `packet.resource.required_missing` | declaration | an active required singleton has no entry |
| `packet.resource.dependency_missing` | declaration | a present declaration's transitive `requires` names an absent singleton |
| `packet.resource.array_axes_missing` | declaration | a dense-array entry's axes resource is absent |
| `packet.resource.reference_target_missing` | declaration | a populated table reference targets an absent singleton |
| `packet.resource.catalog_table_unreadable` | declaration | a catalog table's resource-ID column cannot be read |
| `packet.resource.catalog_row_binding` | declaration | a catalog row and a family entry do not bind one-to-one under Part 02 §2.6 |
| `packet.resource.derived_from_required` | declaration | the `lineage` policy is `required` and `derived_from` is absent |
| `packet.resource.derived_from_forbidden` | declaration | the `lineage` policy is `forbidden` and `derived_from` is present |
| `packet.resource.lineage_unresolved` | declaration | a `derived_from` member names no entry with a bound declaration |
| `packet.resource.lineage_class` | declaration | a lineage edge violates Part 02 §2.7's content-class relation |
| `packet.resource.lineage_cycle` | declaration | the lineage graph has a self-edge or cycle |

In the `registry_binding` phase, a checker MUST evaluate `missing`, `unreadable`, and `digest`
first. Only for decoded bytes that match the digest, it then obtains the Part 02 registry
result through the byte-oriented entry point, supplying the core context to every extension, and
evaluates the four comparison checks for each shape-valid document. The `declaration` phase runs
only from checked contexts that R127 permits to direct packet checks.

A binding finding for an extension registry withholds only that registry. The `declaration` phase
MUST run from every bound registry that passed binding, and a checker MUST NOT report a
declaration finding for an entry whose `declaration_id` namespace is the ID of an extension
registry that failed. A failed core registry withholds the whole `declaration` phase, because every
extension's checked context needs core. Part 09 §5.4 continues to attribute an extension's findings
and compose the verdicts.

Part 05 §5.3 MUST cite planned Part 04 section 10 for these checks rather than list them, and
retains kind-specific physical dispatch and `core.sessions.manifest_sessions_match`.

### 3.7 A packet records lineage but need not record a producing run

The resource-entry member `processing_run_id` MUST be removed without replacement, and the registry
meta-schema MUST remove the declaration field `producing_run`. Part 00 §§4.1 and 5.1, Part 02
§§2.1, 2.2, 2.5, and 2.7, Part 04 §§2, 4.1, 4.2, and 7, and Part 05 §5.3 MUST drop the
producing-run policy and the presence condition it created. Part 02 §2.7 is retitled "Lineage
policy", and Part 04 §7 "Resource lineage". Every `analysis` and `compatibility_projection`
declaration continues to require lineage, and every recorded analysis chain continues to
terminate in canonical resources.

Part 05 §10 MUST NOT require an analysis resource to name a run; provenance remains optional within
packet conformance. Part 06 §5 MUST permit, and not require, a writer to record a
`core.processing_runs` row for a materialization. Where a writer records one, the row's parameters
MUST carry every transform parameter the output cannot recover. Part 06 §2 MUST keep its lineage
requirement and cite §5 for parameters, and Part 06 §4 MUST state its bucket width, omitted-row
count, and collision reason as parameters of such a recorded run.

Row-level `processing_run_id` columns, `core.processing_run_inputs`, and `core.preferred_runs` are
unchanged.

### 3.8 A reader checks only what reading needs

A reader loading a manifest MUST decode it as UTF-8 JSON, MUST reject a repeated object member, and
MUST reject a repeated `resource_id` before it builds a lookup by resource ID or exposes an entry.
It MUST check the JSON type of each member it reads and fail naming a member that is absent where
the schema requires it or has the wrong type. A reader need not apply the incorporated schema or
assert its closure, patterns, or formats; the validator and the writer's publication gate own
those. A reader MAY expose the decoded JSON of a rejected manifest as raw data but MUST NOT resolve
declarations or resources through it.

A reader resolving a declaration MUST acquire the bound registry that declares it through its
descriptor, decode it as the packet's physical profile requires, and verify its digest. When the
registry is missing, unreadable, or fails the digest, the reader MUST fail the operation that needed
it and name the registry ID. It MUST NOT substitute other bytes or silently omit a bound registry.
Operations that need no such declaration proceed, and a reader need not run any other manifest check
or obtain a registry result for ordinary access.

### 3.9 Only bound registries direct packet checks

A validator MUST direct packet checks only from the checked contexts of bound registries that
passed the `registry_binding` phase. It MUST NOT substitute a caller-supplied, bundled, or remotely
resolved registry for a bound one. A validator MAY check a caller-supplied registry document on its
own under Part 02 but MUST NOT use it to direct packet checks or report its result as the
packet's.

Part 05 §14.5 MUST obtain a result for every bound registry whose decoded bytes match their
digest, and MUST treat `packet.registry.missing`, `packet.registry.unreadable`, and
`packet.registry.digest` as the packet-level outcome for a registry that cannot be acquired. Part
05 §14.6 MUST label each bound registry's result by its registry ID.

A writer MUST serialize each registry document, compute its digest over those exact bytes, store it
under §3.5, and record its descriptor before writing the final manifest. A writer MUST NOT publish a
manifest with a finding in the `json`, `shape`, `entries`, or `registry_binding` phase.

Part 09 §5.3 MUST state registration as a descriptor with role `extension` under Part 04 §8 and cite
planned Part 04 section 10 for its checks, which replace the existence check and keep core's checks
independent of an extension registry.

### 3.10 A delivered entry is a manifest entry without the build-supplied members

Part 03 §1 MUST incorporate `registry/resources.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/resources/0.4.0`. Its closed envelope admits an optional `$schema`
string and requires `resources`, an array of entries. Each entry is closed, requires
`resource_id`, `declaration_id`, and `uri`, and admits `external`, `source`, `sha256`,
`size_bytes`, `verified_at`, and `members`. The delivery schema defines each of those members, and
the entry's conditional shape, exactly as the manifest schema does; a difference makes the
specification candidate internally inconsistent. A build supplies `validation_state` and
`derived_from`, so a delivered entry MUST NOT carry either.

Part 03 §11.3 MUST cite Part 04 §4.1 for the entry and retain its delivery obligations.

### 3.11 Artifacts and incompatible identifiers advance together

These incorporated identifiers MUST advance:

| artifact | from | to |
|---|---|---|
| registry meta-schema `$id` | `https://escapewheel.org/schemas/registry/0.5.0` | `https://escapewheel.org/schemas/registry/0.6.0` |
| registry-contract descriptor ID | `escapewheel-registry-contract-v0.2` | `escapewheel-registry-contract-v0.3`, selecting meta-schema 0.6.0 |
| core registry `registry_version` | `0.5.0` | `0.6.0`, with `registry_id: core` |
| manifest schema `$id` | `https://escapewheel.org/schemas/manifest/0.3.0` | `https://escapewheel.org/schemas/manifest/0.4.0` |
| delivery schema `$id` | `https://escapewheel.org/schemas/resources/0.3.0` | `https://escapewheel.org/schemas/resources/0.4.0` |

An extension author migrating an extension registry MUST independently advance its
`registry_version`; the core specification MUST NOT assign it. A writer and an adapter MUST emit
only the new shapes, and a reader or validator need not accept the superseded ones. The
specification README MUST project the core registry ID and version in place of the
`registry_version` field.

## 4. What this does not change

Registry declarations remain the sole owners of resource presence, dependencies, kinds, instance
modes, tables, and rules; this revision gives their packet-side checks IDs without changing what
they require. `profile_id` remains the sole physical-profile selector, and no physical field
returns to the manifest. Part 04 §5's external-resource verification levels, the Part 05 §5.3
session-inventory check, and Part 09 §5.4's separate verdicts are unchanged.

## 5. Consequence

Every generated packet and delivery document is incompatible and must be regenerated. The four
local development packets are rebuilt on demand. Independent implementations gain one manifest
schema, one delivery projection, and one check inventory, and lose the fixed registry paths and
the manifest's producing-run field. The validator and writer gain an RFC 3339 format dependency;
the reader gains none.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | unchanged; binding and manifest mechanics alter no scientific meaning | specification diff |
| logical prose and registry | add `registry_id` to Part 02 §9.1, the meta-schema, the core registry, and every extension; add `registry.identity.registry_id`; replace Part 02 §9.2's packet obligation; remove the producing-run policy from Part 02 §§2.1, 2.2, 2.5, and 2.7, the meta-schema, and every core and extension declaration; make a materialization's run optional in Part 06 §§2, 4, and 5 and drop producing-run mentions from Part 00 §§4.1 and 5.1; advance meta-schema, descriptor, and core identifiers | registry checker, contract-descriptor tests, and negative extension with a mismatched `registry_id` |
| physical profiles | Part 03 stores each bound registry as one gzip member, recommends a new layout, restates retention by registry ID and version, incorporates the delivery schema, and cites RFC 1952 and RFC 1951 | writer and reader round trip of gzip members; retention test for two digests under one ID and version |
| packet manifest and JSON Schemas | incorporate the closed manifest schema; add `registries`; remove nine root, two entry, and one validation member; add planned section 10; have `registry/build.py` render the Part 04 tables and the delivery schema from the manifest schema | schema tests, and repository-verifier comparisons of the rendered tables and delivery schema against the manifest schema |
| validation and import | run the five phases; direct checks only from bound registries; assert `date-time`; retire the reference validator's `registry.schema`, `registry.version_mismatch`, `packet.resource.lineage_shape`, `packet.resource.processing_run_id_required`, `packet.resource.processing_run_id_forbidden`, and `provenance.*` findings, which the registry result, the named checks, and the schema replace | validator tests for every check ID |
| extensions | each example registry gains `registry_id` and advances its version; binding applies without naming any extension in a numbered part | extension registry checks and extension packet fixtures |
| reader, writer, validator, adapters | the reader rejects repeated members and resource IDs at load, checks the type of each member it reads, resolves registries through descriptors, and verifies digests; the writer serializes, hashes, and gzips registries before writing the manifest and names no run on an entry; the validator acquires registries only through descriptors; adapters deliver closed entries | package tests and cross-package builds |
| conformance fixtures and tests | regenerate every fixture; add the positive and negative cases in §6 | fixture suite and repository verifier |
| revision process and tooling | unchanged; the ordinary lifecycle, ledger, and evidence records apply | lifecycle scripts |
| generated publications and developer documentation | regenerate Part 04 tables, the Part 08 example, the specification README row, and the consolidated rendering; revise the root README packet layout, `registry/README.md`'s embedding path, the fixture guide's validation layers, the root contribution guide's generation diagram, and the validator guide's rule that a caller may pass a registry | clean regeneration, `facts.py`, and documentation review |

## 6. Conformance and implementation evidence

Incorporation must establish these positive cases:

- a core-only packet binds exactly one descriptor, with role `core`, and passes every check;
- a packet binding two extensions passes, and each extension's required singletons are active;
- a packet whose analysis resources record lineage but no run, and that carries no
  `core.processing_runs`, passes;
- a reader opens a manifest whose `created_at` is malformed and whose root carries an unknown
  member, while the validator reports `packet.manifest.schema` for both;
- two gzip members of one registry that differ only in header fields and compression level both
  satisfy the same descriptor;
- an amendment that binds a new core registry version retains the superseded copy at its recorded
  path;
- the generated Part 04 tables and delivery schema equal the checked-in copies; and
- opening a packet and listing resources do not acquire an extension registry.

It must establish these negative cases, each producing exactly its check ID:

- duplicate JSON members, including two `resource_id` members in one entry;
- each removed root, entry, and validation member, and an unknown member in each closed object;
- a malformed `created_at`, `validated_at`, and `verified_at`;
- a `resource_id` without a namespace, an empty or repeated `derived_from`, and `source` on an
  entry that is not external;
- two entries sharing a `resource_id`, rejected by the reader before any lookup;
- zero and two core descriptors, a repeated path, an absolute path, a path containing `..`, and a
  descriptor path with a scheme;
- a missing file, a non-gzip file, a two-member gzip file, and a digest mismatch;
- a registry ID, role, version, logical-standard, and semantic-standard mismatch;
- a caller-supplied registry that would pass a packet whose bound registry fails, which must still
  fail;
- an extension registry that fails binding, which yields its binding finding while core's
  declaration checks still run and no declaration finding names that extension's entries;
- repeated member keys, a size mismatch, and a member-digest mismatch;
- a declaration carrying `producing_run`, rejected by the registry result;
- a reader reading a member of the wrong JSON type, which fails naming that member; and
- a delivered entry carrying `validation_state` or `derived_from`.

The reader's manifest loader must be tested against duplicate IDs and members without constructing
a map first. The incorporation evidence must include regenerated fixtures, focused package tests,
the generated-projection comparisons, and the full repository verifier.

The accepted-clause ledger must mark R31 §§2, 3, and 5 superseded by this revision, because the
manifest no longer names a materialization's run, no analysis resource must name one, and no
manifest-to-table run check remains; its note on R31 §4 must record that the run requirement it
explains no longer exists. R9 §4 has no ledger record, and its placement of run outputs in the
manifest ends here. R128 §3.7 remains applied for the lineage policy, value shape, and edge
relation, including required analysis lineage and canonical-chain termination; its ledger note
must record that this revision removes the producing-run policy.

### 6.1 Completed anchor bootstrap

Commits `44855721f7ffe5987bf55c312905360489c62f39` and
`c459cf9f7b9c1737a8f42d2d7e0d9ea894aed6a9` added one canonical anchor immediately before each of
these affected existing headings:

| current heading | canonical anchor |
|---|---|
| Part 03 §3.1 | `ew-portable-packet-layout` |
| Part 03 §9.3 | `ew-superseded-manifest-retention` |
| Part 04 §4.3 | `ew-withdrawn-catalog-blocks` |
| Part 04 §8 | `ew-packet-registry-bindings` |
| Part 06 §4 | `ew-analysis-spike-events` |
| Part 08 §2 | `ew-example-packet-layout` |
| Part 08 §3 | `ew-example-packet-catalog` |
| Part 09 §5.3 | `ew-extension-registration` |

## 7. Open

The manifest carries no identifier of its own schema, so a checker applies the incorporated schema
and a superseded manifest fails it rather than selecting another. Whether the manifest gains a
`$schema` selector belongs with the final release identifiers.

The registry meta-schema and contract descriptor declare `format: uri`, which the same format
checker does not assert. Authority URIs are separately checked by `registry.authority.uri`, and
`$schema` is compared exactly, so this revision leaves that gap to the registry work that owns it.
