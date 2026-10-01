# Escapewheel Project Sanity Check

**Review date:** 2026-09-17

**Reviewed commit:** `32f9e06884b483818c7156f80ea81f7e3a6ce002`

**Review mode:** Evaluation only; no specification or implementation files were changed

**Primary authority used for this review:** the generated v0.2 specification material in `escapewheel_poc_docs_v0.2/`

## Executive assessment

Escapewheel has a strong underlying design and is recognizably aimed at the right problem: a small, inspectable packet format built from commodity formats, with exact semantics supplied by registries rather than by a large object model. Integer time, explicit clocks, normalized tables, immutable resources, atomic manifest publication, extension registries, adapter boundaries, and tiered validation are all sound choices. The generated registry, conformance fixtures, and reference packages show substantially more rigor than a typical proof of concept.

The project is nevertheless not yet internally consistent enough to call the current v0.2 publication a stable contract. The most important problems are not missing implementation features. They are disagreements among authoritative specification sections, generated schemas, current registry data, and a few implementation paths that can publish packets the prose specification says are invalid. The largest examples are:

1. The repository does not state consistently enough that the generated v0.2 material is authoritative. Several prominent documents still imply that the frozen v0.1 POC plus accepted revisions is a co-equal binding source.
2. Unit identity has two incompatible definitions. The current registry uses `unit_id` alone, while semantic prose, reader behavior, examples, and tests still use a four-column composite identity.
3. The manifest prose and the manifest JSON Schema define materially different contracts. Many prose-required properties are optional in the schema, some conditional requirements are absent, and one resource-kind name disagrees.
4. The specification says a packet carries all profile-required resources, but the registry cannot express resource or table requiredness and the validator explicitly skips absent registered tables.
5. Extension failures do not make the implementation's overall validation verdict fail, even though Part 09 says packet validity is the conjunction of core and extension validity. The writer can therefore commit a packet with invalid extension content.
6. Recipe arbitration is supposed to be data driven and declared by the recipe, but the writer and the AIND plugin contain built-in preference policy that is not represented in the recipe model.

Across these examples, the deeper specification problem is imperfect separation of abstraction layers. Parts 00 through 05 define a sensible semantic-to-logical-to-physical progression, but their contents do not consistently obey it. Architecture contains table keys and benchmark results; semantics contains column types and writer algorithms; the physical packet profile contains amendment policy and the adapter API; and informative parts occasionally use normative keywords. This makes duplication likely and makes it unclear which statement a revision should update.

Those issues are release blockers because they prevent independent implementations from deriving the same packet and verdict from the published contract. They are fixable without abandoning the architecture.

My overall recommendation is to treat the current tree as a strong release candidate or design-development snapshot, perform one explicit reconciliation pass, then publish an immutable v0.2 bundle. After that point, new normative changes should target a new version rather than continuing to mutate the directory named v0.2.

## Scope and review basis

This review covered:

- the generated v0.2 specification parts, their combined document, generation scripts, and application ledger;
- the frozen POC and accepted/draft revision process as provenance for the generated specification;
- the core registry, meta-registry schema, extension registries, adapter declarations, and packet schemas;
- the reader, writer, validator, and AIND adapter implementation packages;
- root and package documentation, developer guidance, status files, conformance fixtures, and tests;
- the extent to which the design is genuinely data driven rather than relying on policy hidden in Python code.

The review deliberately gives the specification the greatest weight, the registry architecture the next greatest weight, and implementation completeness the least. A useful implementation disagreement is evidence of a specification or conformance problem; it is not a reason to reinterpret the authoritative specification silently.

### Authority model used in this report

The intended authority hierarchy should be stated explicitly and consistently as follows:

1. The generated v0.2 specification in `escapewheel_poc_docs_v0.2/` is the normative behavioral contract for v0.2.
2. The numbered parts are the maintainable source form. `Escapewheel_POC_v0.2_Implementation_Spec.md` is a generated convenience rendering of those parts, not a second contract.
3. `registry/logical_schemas.json` is the normative exact table declaration because Part 02 incorporates it for that purpose. It should be packaged and hashed with the v0.2 release so that this incorporation is unambiguous.
4. The frozen POC and revision documents explain provenance and design rationale. Once a revision has been incorporated into the generated v0.2 material, those historical files do not override the resulting v0.2 text.
5. Implementations, examples, tests, READMEs, and developer notes are non-normative. A mismatch between them and the authoritative artifacts is a defect to resolve, not an alternative precedence rule.

This hierarchy is not stated consistently today. The root `README.md` first says the frozen POC and accepted revisions bind, then later says the v0.2 generated specification binds. The root `CLAUDE.md` similarly points to v0.2 in some sections but describes the frozen v0.1 model and accepted revisions as binding elsewhere. The reader, validator, and writer `CLAUDE.md` files retain variants of the same ambiguity. By contrast, `escapewheel_poc_docs_v0.2/README.md` comes close to the intended rule by saying that revisions explain why and the current specification says what holds.

This should be fixed in every entry-point document with the same short authority statement. It would also help to place a machine-readable release index beside the specification, listing the authoritative part files, combined rendering, exact registry artifacts, JSON Schemas, versions, and hashes.

## What is working well

The problems below should not obscure the quality of the central design.

### Commodity-storage architecture

The division between Parquet tables, Zarr arrays, media files, small documents, and a compact manifest is appropriate. The manifest identifies resources rather than trying to become a database or object graph. Resource IDs are distinct from paths, which makes relocation and object-store layouts possible. The separation of logical schema from physical representation is a useful foundation for future back ends.

### Time and semantic model

Integer ticks plus explicit clock definitions avoid floating-point time ambiguity and make cross-resource synchronization inspectable. The normalized fact-table approach is much easier to query and validate than unconstrained nested records. The prohibition on arbitrary lab columns in core tables, combined with explicit extension registries, addresses a major source of schema accretion in NWB-like systems.

### Publication and integrity model

Immutable resource construction followed by atomic manifest publication is a good fit for local filesystems and object stores. Source references, checksums, validation state, derivation links, and processing runs provide the right vocabulary for reproducibility. The external-resource verification levels appropriately recognize that not every remote object can be fully rehashed on every access.

### Registry and validation structure

The registry describes tables, columns, roles, identities, references, vocabularies, and generated constraints in a compact form. The distinction between generated row-local checks, relational SQL checks, and physical-profile checks is sound. Core and extension registries use the same general representation, which is important for language-neutral tooling.

The repository registry checker succeeded on the current data. At review time it reported 43 core/analysis tables, 351 columns, and 111 references, plus four extension registries containing 11 tables, 161 columns, and 17 references. It also executed 122 SQL rules against 54 empty table shapes. That is strong infrastructure for a project at this stage.

### Package boundaries and testing

The reader, validator, writer, and adapter packages have understandable roles. The dependency direction is reasonable: validation builds on reading, and writing builds on validation. Optional heavy dependencies in the reader and shared command-line entry points are sensible packaging decisions.

The package test suites all passed during the audit:

- reader: 215 tests;
- validator: 117 tests;
- writer: 551 tests;
- AIND adapter: 66 tests.

That is 949 passing package tests. The issue is therefore not a generally unstable codebase. It is that several tests encode an older or contradictory contract, so green tests do not yet establish v0.2 conformance.

## Specification findings

Findings in this section have priority over implementation observations.

### S0 — Normative ownership and abstraction boundaries are not consistently enforced

**Severity: high; a root cause of several contradictions below**

Several apparent semantic disagreements are more precisely document-architecture defects: a detailed rule is repeated in an overview or neighboring concern after it already has a natural authoritative home. A later revision updates the owning section but leaves the duplicate behind. Readers then encounter two normative statements without a principled way to discard either one.

Unit identity is the clearest example. Part 00 is the architecture overview, yet §4.3 gives the exact four-column identity tuple and uses normative language. Part 01 repeats that tuple in the semantic definition of a unit. Part 02—the logical-schema part and the proper owner of primary keys, foreign keys, and reproducible ID allocation—defines the current, incompatible rule that `unit_id` identifies a unit by itself. R81 appears to have updated the logical-schema rule without removing the older restatements.

The same pattern contributes to other findings: publication order is summarized differently from its detailed Part 05 definition; analysis lineage/canonicality appears in the architecture overview as well as Part 06; physical checksum language overlaps the Part 04 resource contract; and exact registry counts are copied into prose rather than generated.

The parts should have explicit normative ownership:

| Concern | Owning location | What other parts should do |
|---|---|---|
| architectural goals, layer boundaries, and dependency direction | Part 00 | state principles and link to detailed contracts |
| domain meaning of session, unit, event, interval, and similar concepts | Part 01 | define meaning and relationships, not repeat storage keys |
| table identities, columns, references, presence, and ID-allocation rules | Part 02 and the exact registry | be the single machine-corresponding definition |
| physical encodings and portability capabilities | Part 03 | be referenced by resource declarations |
| manifest/resource fields, integrity, and cross-field state | Part 04 | be generated into JSON Schema and semantic checks |
| build, validation, and publication lifecycle | Part 05 | be summarized elsewhere only by reference |
| analysis-specific policy | Part 06 | not be restated normatively in Part 00 |
| extension eligibility and validity composition | Part 09 | be consumed by validator/writer contracts |

Part 00 should make the abstraction model explicit. It already begins to do so in §§2.1–2.3, but it calls semantic, logical, and physical “vocabulary levels” and then uses “layer” for core, extensions, analysis, and NWB in §3. Those are two different and orthogonal classifications. Leaving that distinction implicit makes phrases such as “the table layer,” “analysis layer,” and “storage layer” easy to confuse.

The specification should reserve two terms:

- **Abstraction level:** semantic, logical, or physical. This answers *what kind of contract is being stated?*
- **Content layer:** core, extension, analysis, or deferred NWB projection. This answers *what role does a resource play in a packet?*

A core table, an extension table, and an analysis table are all logical resources and all receive a physical representation. “Analysis” is therefore not below “logical,” and “core” is not above “physical”; the two axes cross. The catalog and build lifecycle are cross-cutting contracts rather than additional data-abstraction levels: the catalog binds concrete resource instances to the semantic/logical/physical versions they use, while the lifecycle constructs and validates those instances.

The intended abstraction direction is sound, but should be made operational in Part 00:

```text
Part 01: semantic concepts and meaning
    ↓ represented by
Part 02 + registry: logical resources, identities and constraints
    ↓ realized by
Part 03: portable storage encodings

Part 04: catalogs concrete resources and names their logical/physical contracts
Part 05: builds and validates instances using Parts 01–04
Part 06: owns analysis-layer policy
Part 09: extends the semantic/logical model without changing core
Parts 07, 08 and 10: explain, exemplify or justify; they add no obligations
```

Part 00 should then state the dependency rules explicitly:

1. Part 01 defines meaning without selecting tables, fields, scalar types, URIs, or storage technology.
2. Part 02 represents Part 01's concepts as logical resources and constraints without selecting a storage technology.
3. Part 03 maps Part 02's logical resources to bytes without changing their identity or meaning.
4. Part 04 names concrete resources and the versions/profiles governing them; it does not redefine those contracts.
5. Part 05 specifies how actors construct, validate, and publish conforming instances; it consumes upstream rules instead of restating them.
6. Content-layer rules say whether a logical resource is canonical core, canonical extension, derived analysis, or projection. They do not alter the abstraction-level boundaries.
7. Informative parts may supply implementation examples, executable examples, or evidence, but never the sole statement of an obligation.

A concise sentence suitable for Part 00 would be: “Escapewheel has three representation abstraction levels—semantic, logical, and physical—and an orthogonal set of packet content layers—core, extension, analysis, and projection. A resource occupies one content layer while being governed by all applicable abstraction levels.”

In particular, a lower layer may map a rule from the layer above, but must not redefine it. A workflow may say how a writer satisfies a logical invariant, but must not state a second version of the invariant. An informative part may explain why a rule exists, but must not contain the only `MUST` or `SHOULD` that expresses it.

#### Part-by-part placement audit

| Part | Intended abstraction | Boundary problems found | Recommended disposition |
|---|---|---|---|
| 00 — Architecture | vocabulary levels, packet/layer boundaries, actors, dependency direction | contains exact session-scope counts, unit-key rules, named columns and resources, reader projection behavior, a measured 2.93× join cost, analysis materialization rules, and packet-version behavior | retain principles and dependency rules; replace concrete schemas, algorithms, counts, and measurements with links to their owners |
| 01 — Semantic standard | substrate-independent meaning of scientific and provenance concepts | specifies `int32` identifiers, `*_name` columns, table/column prohibitions, nullability of a named column, URI/manifest placement, and importer algorithms | retain meanings and interpretation invariants; move representations to Part 02, catalog placement to Part 04, and writer/import behavior to Part 05 |
| 02 — Logical schemas | registry meta-model, table shapes, identities, references, logical constraints | largely appropriate, but also contains reader/writer algorithms, validator reporting behavior, and Parquet/Zarr performance rationale | keep declarative packet invariants here; move operational obligations to Part 05 and storage-dependent rationale/rules to Parts 03/10 |
| 03 — Portable physical profile | mapping of logical resources to portable stored bytes | also owns amendment semantics, retention and cleanup policy, source-adapter capability declarations, recipe inputs, delivery completeness, process lifecycle, and IPC protocols | keep Parquet/Zarr/layout/encoding rules; move packet lifecycle to Part 05 or a lifecycle part; move adapter semantics to a dedicated adapter-interface part, leaving only transport encodings that truly vary with the physical profile |
| 04 — Packet catalog | manifest shape, resource identity/state, integrity declarations and resolution | defines logical kinds as “Parquet table” and “Zarr array” despite Part 03 being the only technology-dependent normative part; also mixes declarations with reader/validator operation | define kinds as logical table/array/media/document resources; let `physical_profile` and Part 03 select Parquet/Zarr; keep catalog state here and put operational procedures in Part 05 where possible |
| 05 — Validation and import | recipe resolution, writer lifecycle, validation and publication | combines two different conformance subjects—packet validation and writer/process conformance—and states the distinction only late in the part; this contributed to the contradictory stage order | split internally or physically into packet validation/reporting and recipe/build/publication; identify the bound actor on every normative clause |
| 06 — Analysis layer | analysis eligibility, lineage and materialization policy | mixes normative and informative sections in one part; repeats Part 00; contains an exact table schema belonging to Part 02 and benchmarks belonging to Part 10 | make the analysis contract wholly normative and move examples/evidence out, or move its few normative rules to their owning parts and make all of Part 06 informative |
| 07 — Reference implementation | non-normative implementation description | uses uppercase `SHOULD`/`MUST NOT` for comments, performance behavior, and document placement despite saying nothing constrains an implementation; embeds mutable phase status | move developer policy and status to developer docs; reserve RFC keywords for quoted normative references |
| 08 — Example packet | executable illustration | its acceptance checklist and SQL can be mistaken for an additional contract and currently preserve obsolete unit columns | generate it from the released registry and run it in CI; state that disagreement is a defect in the example, never an override |
| 09 — Metadata and extensions | extension boundary, namespacing, registry and validity rules | repeats the architecture's core-inclusion boundary and includes some adapter/report-delivery behavior owned by the build interface | choose one owner for the core/extension placement test; keep extension contracts here and reference the adapter/build contract rather than restating it |
| 10 — Performance notes | non-normative measurements supporting rules elsewhere | §3 says a time-bucket row group `SHOULD` begin at each bucket boundary even though the scope says this part states no rules | move that `SHOULD` to Part 03 and leave only the evidence and consequence in Part 10 |

Two violations are especially structural. First, Part 00 explicitly says it defines no schema or file format, yet it gives exact keys and columns. Second, Part 00 says Part 03 is the only normative part whose rules may depend on storage technology, while Part 04 defines resource kinds in terms of Parquet and Zarr and Parts 01/02 include representation-specific requirements or rationale. These self-declared boundaries should become conformance checks on the specification itself.

The Part 03 adapter material deserves a careful split rather than a simple move. The fact that `files-v0.1`, Arrow IPC, and Flight encode delivery is transport-profile material. Ownership, `needs`/`accepts`/`produces`, delivery completeness, process startup, report semantics, and recipe arbitration are adapter/build-interface rules and do not inherently change merely because packet tables later use a different storage profile. Coupling both sets of rules to `escapewheel-portable-v0.1` makes a future packet profile redefine the ingestion API unnecessarily.

**Recommendation:** give each normative rule one canonical owner and stable clause ID. Overviews should summarize non-normatively and link to the owner instead of copying exact tuples, field lists, counts, or step order. Mark each clause or section as `normative`, `explanatory`, `example`, or `evidence`, rather than relying only on whole-part labels—especially while Part 06 remains mixed. As release checks, flag RFC keywords in informative material, technology names in substrate-independent parts, concrete registry field lists outside Part 02, actor obligations outside their owning workflow, and repeated normative sentences across parts. This is not a reason to eliminate useful explanation; it is a reason to distinguish explanatory restatement from the one binding definition.

### S1 — Unit identity is contradictory and currently breaks valid reader operations

**Severity: release blocker**

Parts 00 and 01 define a unit by a composite identity involving session, sorting run, curation set, and unit ID. Part 02 and the current registry instead make `unit_id` the identity of `core.units`, and dependent spike rows carry only `session_id`, `unit_id`, and time. The example SQL in Part 08 still joins on the removed composite columns. As described in S0, the exact key should never have been independently normative in Part 00; its survival there made a superseded design look current.

The implementation contains both models. The current registry follows the single-column design, but `Packet.spike_times()` and its documentation retain sorting-run and curation-set filtering. When those optional arguments are supplied against the current `core.spike_events` schema, the reader attempts to filter columns that do not exist. Reader tests avoid the disagreement by constructing a hand-maintained legacy registry and legacy-shaped tables.

This is not a cosmetic naming issue. It changes primary keys, foreign keys, query APIs, extension joins, and migration behavior. An independent implementation cannot choose correctly from the published v0.2 text.

**Recommendation:** make one decision in Part 02 and the exact registry, then propagate it mechanically through example SQL, reader APIs, fixtures, extension registries, and tests. Part 00 should say only that logical identities are registry-defined and stable within a packet, with a link to Part 02. Part 01 should define what a unit means and which semantic contexts it belongs to, without specifying the physical/logical key tuple. If `unit_id` is packet-global, Part 02 should specify how writers allocate it and how original sorter identities are preserved. If identity remains composite, restore the necessary columns and references to every dependent table. Add a generated executable example for the selected rule.

### S2 — Manifest prose and JSON Schema define different packet contracts

**Severity: release blocker**

Part 04 describes common resource properties and kind-specific requirements, including schema IDs, physical profiles, canonical state, validation state, derivation, processing-run provenance, and complete extension declarations. `registry/manifest.schema.json` requires only a small subset for a generic resource: `resource_id`, `layer`, `kind`, and `uri`. It lacks most of the documented conditional requirements and generally permits extra properties. Extension entries require only a registry reference in the schema, while the prose requires namespace, version, and path information.

There is also a direct vocabulary disagreement: the prose uses `document`, while the schema accepts `document_asset`. A minimal resource lacking several prose-required properties passes the schema; `document` fails and `document_asset` passes.

`registry/resources.schema.json` is a second, looser resource description that requires only ID and URI. It does not reuse the manifest resource definitions and can drift independently. The reader's JSON Schema invocation does not enable format checking, so strings declared with formats such as `date-time` are not necessarily validated as dates.

**Recommendation:** derive one resource schema from one declarative resource matrix. Decide which fields are required for every resource and which are conditional on `kind`, `layer`, locality, validation state, or canonicality. Generate or share the definitions used by the manifest and adapter-resource schemas. Add format checking, unique resource-ID validation, and negative conformance fixtures for every conditional rule.

### S3 — Required resource presence is asserted but cannot be expressed

**Severity: release blocker**

The v0.2 overview and Part 00 say a packet carries every profile-required resource and that every packet contains the core. Part 02 says the registry defines which resources comprise the core. The registry, however, describes tables without a required/optional/conditional presence property. The validator explicitly skips a registered table when it is absent.

Some presence is enforced only indirectly. For example, manifest/session reconciliation assumes `core.sessions`, but there is no general rule from which another implementation could determine the minimum conforming packet.

**Recommendation:** put presence in the data model. At minimum, each registered resource should declare `required`, `optional`, or a machine-readable condition. If table registration remains separate from resource registration, introduce a profile-resource registry that maps logical resources to kinds, schemas, requiredness, canonical policy, and physical constraints. Generate presence validation from it.

### S4 — Validation and publication order is self-contradictory

**Severity: high**

The summary pipeline in Part 05 places commit before provenance finalization and materialization. Later normative text requires the completed packet, including materialized products, to be validated before promotion. The writer follows the latter and safer model: it stages content, finalizes provenance/materialization, validates, and then publishes.

**Recommendation:** rewrite the overview sequence to match the detailed contract and implementation: ingest into staging, finalize derivation and processing provenance, materialize required products, validate the entire staged packet, then atomically publish the manifest. Define failure cleanup separately from publication.

### S5 — The adapter no-write rule conflicts with the array contract

**Severity: high**

Part 05 says an adapter returns records and must not write files. Part 03 requires a packet-owned array adapter to write Zarr data to the writer-provided array location. Both ideas can coexist, but the exception is not stated.

**Recommendation:** say that adapters may not choose or publish packet paths and may not mutate committed packet state. They may stream or write payload bytes only through a writer-owned capability/location supplied for that resource. Make the ownership and cleanup responsibility explicit.

### S6 — Analysis-layer lineage and canonicality disagree across parts

**Severity: high**

Part 00 describes analysis lineage as pointing to core resources, while Part 06 permits derivation from canonical core or extension resources. Part 00 also uses wording suggesting that analysis concerns layout rather than arithmetic, while Part 06 allows expensive computation and parameterized transformations. More importantly, Part 00 says analysis content becomes canonical only through an explicit revision, and revision R30 specifically says `analysis.spike_events` is not canonical.

**Recommendation:** use Part 06's broader lineage rule consistently. Replace the arithmetic/layout slogan with a precise distinction: analysis resources are reproducible derived representations and products; their cost is irrelevant to their layer. Define canonicality as registry/profile policy, not as a value inferred from successful writing.

### S7 — File checksum wording excludes prefix resources in one part

**Severity: medium**

Part 03 describes a whole-file checksum and says one file corresponds to one resource. Part 04 correctly defines tree digests for prefix resources such as Zarr stores. The former reads as a universal rule even though it is only valid for single-object resources.

**Recommendation:** make the checksum rule explicitly depend on resource shape: byte digest for one object, deterministic tree digest for a prefix resource, and an explicit verification mode for external resources.

### S8 — The specification's own table of contents is stale

**Severity: medium**

The v0.2 `README.md` says the specification has eleven parts but lists only Parts 00 through 09, omitting Part 10. Part 00 includes Part 10 but says there are “ten files.” These are small errors, but they undermine confidence in a document that depends on exact cross-references.

**Recommendation:** generate the part count and contents table from the same input used by `combine.py`, and check them in CI.

### S9 — Normative numeric summaries have drifted from the registry

**Severity: medium**

Several prose passages hard-code table or column counts from earlier snapshots. Examples include Part 00's session-scope counts, Part 02's table/column descriptions, and Part 03's “30 of 330 columns” statement. The current registry has 43 core/analysis tables and 351 columns. A current structural check found 41 of those 43 tables session scoped, with the two exceptions not reaching sessions through a path that lacks `session_id`.

**Recommendation:** avoid normative hard-coded counts unless generated. Where a count is merely explanatory, label it as non-normative and generate it into the combined document or release facts file.

### S10 — The mandatory codec floor is not represented precisely enough

**Severity: medium**

Part 03 makes uncompressed, gzip, and Zstandard Zarr v3 codecs the mandatory portable floor and allows Blosc and sharding as optional capabilities. The validator's codec-floor set includes Blosc and sharding, so its `codec.outside_the_floor` terminology does not match the specification. Codec names are also represented too coarsely to enforce parameters that affect interoperability, such as the Blosc compressor and shuffle configuration.

**Recommendation:** distinguish `mandatory_portable`, `recognized_optional`, and `unsupported`. Use structured codec declarations where parameters matter. A validator should be able to say whether a packet is universally portable within the profile or requires an advertised optional capability.

### S11 — Resource-ID uniqueness and cross-field invariants are underspecified

**Severity: high**

The manifest schema does not enforce unique `resource_id` values. JSON Schema cannot express that uniqueness directly for an array of objects without changing representation or adding a semantic check. The reader builds an ID map with ordinary dictionary assignment, so duplicate IDs silently resolve to the last entry. The validator also lacks systematic checks relating `canonical`, `derived_from`, `processing_run_id`, layer, and validation state, including the rule that a failed committed resource cannot be canonical.

**Recommendation:** make unique resource IDs a named semantic invariant, reject duplicates before constructing lookup maps, and specify all cross-field state transitions in one validation table. Generate semantic checks and negative fixtures from that table.

### S12 — The profile's scope should be stated more sharply

**Severity: clarification, not a defect**

The current design is a convincing electrophysiology-oriented successor profile and storage contract. It is not yet a demonstrated replacement for the full breadth of NWB types and workflows. That is a reasonable POC boundary, especially with Iceberg and other scale features deferred, but introductory language can sound broader.

**Recommendation:** distinguish the general Escapewheel packet architecture from the current ecephys/core profile, and state what a future profile must supply. This makes the ambition credible without making the current registry carry every NWB domain at once.

## Data-driven architecture findings

The project is substantially data driven, but not yet end to end. The key improvement is to move remaining policy decisions into versioned declarations from which validators, writers, documentation, and tests can be generated.

### D1 — The meta-registry schema validates syntax, not the full registry contract

**Severity: high**

`registry/registry.schema.json` checks the JSON shape. Important invariants—reference integrity, identity rules, role compatibility, namespace/redefinition rules, and related structural constraints—live in Python in `registry/check.py` and the validator's registry-document checks. This two-tier approach can be valid, but it is not published as a complete, versioned registry-validation contract.

More importantly, packet validation checks an embedded registry against JSON Schema and a version but does not run the complete structural validator used on the repository registry. A third party can therefore embed a registry that is schema-valid but semantically invalid.

**Recommendation:** formally define registry validation as (1) JSON Schema shape plus (2) named semantic invariants. Publish the semantic rule IDs, run them on every embedded core and extension registry, and provide language-neutral positive and negative registry fixtures. If practical, express more invariants in the meta-registry; do not force constraints into JSON Schema where a small declarative semantic-rule layer is clearer.

### D2 — Extension registries are not validated like the core registry

**Severity: release blocker**

The packet validator loads extension registries and uses their table mappings and generated checks, but it does not consistently validate them against the meta-schema, adapter/declaration expectations, the full structural invariants, or all physical type and presence rules. The reader may suppress a missing or unparsable extension registry so that core data remains readable; that is a useful reader behavior, but a validator must still report the declared extension as invalid.

**Recommendation:** enumerate extension declarations from the manifest independently of successfully loaded registries. Produce a per-extension result for missing, unparsable, meta-schema-invalid, structurally invalid, and data-invalid states. Apply the same logical, physical, and relational validation pipeline used for core tables.

### D3 — The registry models tables well but does not model the whole packet profile

**Severity: high**

Arrays, videos, documents, and other assets appear as generic manifest resources or rows in catalog tables. Their requiredness, canonicality, allowed physical encodings, validation expectations, and lineage policies are consequently spread through prose and writer code. This is the main reason the manifest schema and implementation have accumulated hand-coded conditions.

**Recommendation:** add a resource/profile registry, either as a new top-level section of the meta-registry or as a companion artifact. A resource declaration should be able to state:

- logical resource name and namespace;
- resource kind and layer;
- required/optional/conditional presence;
- logical schema or media semantics;
- allowed physical profiles and capability requirements;
- canonicality policy;
- lineage and processing-run requirements;
- integrity/checksum shape;
- whether multiple instances are allowed and how they are keyed.

The manifest schema, validation plan, writer defaults, conformance matrix, and documentation should then be generated from these declarations.

### D4 — Arbitration policy is hidden in implementation code

**Severity: release blocker**

Part 05 and revision R115 say ownership conflicts are resolved by preferences declared in the session recipe, and that the build system must not contain its own preferences. The current recipe data model and parser have no preference field. The writer has built-in `PREFERRED` and `SHARED` policy, and the AIND adapter package adds plugin preference rules. Writer tests explicitly preserve this behavior.

The automatic shared-contributor list is another implicit policy that can override the apparent meaning of each source's `owns` and `contributes` declarations.

**Recommendation:** implement the R115 model. Add explicit recipe preference and shared-contribution declarations, validate them, record the resolved arbitration in build provenance, and delete built-in lab/task preference tables. The engine should supply a deterministic algorithm, not domain policy.

### D5 — Session recipes have no published schema

**Severity: high**

Adapters have a JSON Schema, but the session recipe—the document that composes sources, adapters, ownership, and intended outputs—is checked by ad hoc TOML parsing and Python conditions. This weakens the most important data-driven boundary.

**Recommendation:** publish a versioned `recipe.schema.json` or an equivalent format-neutral schema. Require explicit empty values for important sets such as states, consumes, contributes, and preferences where omission would be ambiguous. Generate typed models and documentation from it.

### D6 — Adapter declarations are underspecified relative to the prose

**Severity: medium**

The adapter schema requires only kind, protocol, produces, and needs. The prose also treats states, accepted inputs, and consumed roles as part of the declaration, although some are described as optional. The reference generator includes these fields, but a third-party declaration can omit them, leaving behavior to convention.

**Recommendation:** decide which omissions mean an empty set and which mean unknown/default. Encode that distinction in the schema and require explicit values for fields used in planning or conflict detection.

### D7 — v0.2 is rebuilt from the old baseline plus a long imperative compiler

**Severity: medium now; high for future maintenance**

The generated result is built from the frozen v0.1 document and a large sequence of revision-specific transformations in `build.py`. This is valuable provenance, but it is a difficult permanent authoring model: a current rule can be distributed across the baseline, multiple superseding revisions, and imperative transformation code.

**Recommendation:** preserve the existing compiler as historical reproduction machinery, but after v0.2 is reconciled, freeze a canonical v0.2 source snapshot and start future revisions from it. Future deltas should transform v0.2 into v0.3 rather than replaying the entire project history for routine editing.

### D8 — Registry extensions currently center on tables, leaving extension assets unclear

**Severity: medium**

The extension mechanism is clear for tables. It is much less clear how an extension declares a new array, media, or document resource with extension ownership. The writer's array staging derives `layer` from namespace, while the manifest schema admits only the fixed layer vocabulary and separately represents extension identity. This suggests extension-owned non-table assets are not yet coherently modeled.

**Recommendation:** include non-table resources in the profile/extension registry and specify how `layer`, namespace, and extension ID interact. Add one conformance packet containing an extension-defined array or media asset.

### D9 — Cross-language intent needs one actual cross-language proof

**Severity: medium**

The adapter protocol and static declarations are designed to permit out-of-process and non-Python implementations, which is excellent. The conformance evidence is still almost entirely the Python reference path.

**Recommendation:** implement a deliberately small adapter in another language or as a minimal protocol-only executable. Use it in CI to prove that discovery, framing, error reporting, resource handoff, and deterministic output do not rely on Python-specific assumptions.

## Revision-process audit

The revision process is unusually disciplined for a project at this stage. Accepted revisions are structured, application is scripted, the ledger checks disposition, and citation/impact tools exist. The current generated document is reproducible, the source artifacts were clean, and the audit found no unresolved citations reported by the citation checker.

The application ledger reported 612 tracked clauses: 305 applied, 176 retained as rationale, 107 affecting registry work, 24 superseded, and none undisposed. It also reported 77 uncorroborated clauses. Those numbers show good bookkeeping, but bookkeeping is not yet the same as semantic reconciliation.

### R1 — Revision status does not distinguish design acceptance from release completion

**Severity: high**

An accepted revision can be incorporated into generated prose while its required registry, schema, implementation, test, and documentation changes remain incomplete. R115 is a concrete example: it clearly requires recipe-declared preference policy, while the implementation still uses built-in preferences and the recipe model lacks the field.

**Recommendation:** use an explicit lifecycle such as `Draft`, `Accepted`, `Incorporated`, `Implemented`, `Conformance verified`, and `Released`—or record those dimensions separately. “Accepted” should mean the design decision is approved, not that every downstream artifact already conforms.

### R2 — The ledger proves disposition, not semantic agreement

**Severity: high**

The ledger can show that a clause was applied, superseded, routed to rationale, or assigned to registry work. It cannot prove that older contradictory prose was removed everywhere or that examples and implementations agree. The unit-identity conflict survived despite complete disposition accounting.

**Recommendation:** attach executable assertions or structured semantic facts to high-impact revisions. Examples include the primary key of `core.units`, the list of required packet resources, or the definition of overall validity. CI should compare these facts across spec generation, registry output, examples, and package tests.

### R3 — Clause extraction misses some normative language

**Severity: medium**

The ledger extractor focuses on Section 2 and occurrences of `MUST` or `SHOULD` elsewhere. Normative `MAY`, `SHALL`, prohibitions phrased without those words, and requirements in other explicitly normative sections can escape clause accounting.

**Recommendation:** recognize the full RFC keyword family and explicit normative blocks. Better still, give normative clauses stable IDs in revision source rather than deriving identity solely from prose scanning.

### R4 — Revision impact checking finds references, not behavioral consequences

**Severity: medium**

The impact tool is helpful for discovering textual citers. It cannot determine that a primary-key change requires a reader signature change, or that a validity-definition change affects writer commit behavior.

**Recommendation:** add an impact checklist by artifact class—spec, registry, schemas, reader, validator, writer, adapters, examples, conformance, and documentation—and require a disposition for each class on contract-changing revisions. Link the affected tests or explicitly mark an area not applicable.

### R5 — The v0.2 publication is mutable in place

**Severity: high for release management**

The generated v0.2 parts are edited by applying every newly accepted revision. That is convenient during development, but once users build against v0.2 the name must identify immutable bytes or at least an immutable tagged release. Otherwise two packets can both claim v0.2 while depending on different rules.

**Recommendation:** define the current state as a candidate until reconciliation is complete. Publish an immutable v0.2 release bundle with hashes. Further breaking normative changes should target v0.3; errata should be narrowly classified and versioned.

### R6 — Large revisions are hard to review and verify atomically

**Severity: medium**

The project accepted 119 revisions over a short development period, and some revisions—R115 in particular—span many contracts and hundreds of lines. This reflects productive discovery, but large revisions make partial application easy and semantic review difficult.

**Recommendation:** split future revisions by independently verifiable contract change. Use one umbrella design note if needed, with smaller normative revisions for the recipe schema, arbitration algorithm, provenance, registry changes, and implementation effects.

### R7 — Successful citation checks are noisier than necessary

**Severity: low**

The citation checker reports zero unresolved citations but emits many loose-match diagnostics, including citations against frozen v0.1 numbering. The tool is useful; its signal is simply harder to read than it should be.

**Recommendation:** separate failures, warnings, and historical-reference notices. Prefer stable clause IDs over section-number matching where possible.

### R8 — The prior review should be clearly historical

**Severity: documentation hygiene**

`Escapewheel_v0.2_Spec_Review_and_Recommended_Changes.md` remains at the repository root. Several of its recommendations have since been addressed, while others have changed context. A new reader can reasonably mistake it for the current project verdict.

**Recommendation:** after this evaluation is accepted, label earlier review documents with their review date and status, and link to the current review. Do not silently delete them; they are useful design history.

## Implementation audit

The implementations are generally well structured and well tested, but several high-impact paths encode a different contract from the generated v0.2 material.

### I1 — Overall validation status ignores extension failures

**Severity: release blocker**

Part 09 says core validity is separately reportable but overall packet validity is the conjunction of core validity and all declared extension validity. In `escapewheel-validator`, `Report.passed` is based on core findings only. `Report.errors` includes extension errors, while serialized `status` uses the core-only result and does not preserve enough per-extension status information. A report can therefore serialize as passed while also reporting extension errors.

The writer uses this `passed` value when committing both new packets and amendments, so it can publish a packet with an invalid declared extension. Tests currently assert the core-only behavior, confirming this is intentional implementation policy rather than an incidental edge case.

**Recommendation:** expose three concepts explicitly: `core_passed`, a result for each extension, and `packet_passed`. Make serialized top-level status mean packet status. Preserve `finding.extension` and per-extension summaries in JSON. The writer must require `packet_passed` for publication unless an explicitly specified partial-validation mode produces a noncanonical, noncommitted artifact.

### I2 — Embedded registries do not receive full structural validation

**Severity: high**

Repository registry checks pass, but packet validation does not apply the same semantic structural checks to arbitrary embedded core and extension registries. This creates a trust gap: conformance depends on the repository copy being good rather than on the packet proving its embedded authority is coherent.

**Recommendation:** factor one registry-validation library and use it in repository checks, packet validation, extension loading, and writer startup. Report stable rule IDs.

### I3 — Reader unit APIs and fixtures preserve the obsolete identity model

**Severity: release blocker, coupled to S1**

`Packet.spike_times()` still accepts sorting and curation identity components and sends them as filters to `core.spike_events`. Current registry data does not define those columns. Reader fixture registries and data reintroduce the old columns, so tests validate the obsolete contract rather than the shipped registry.

**Recommendation:** after resolving S1, generate reader test tables from the released registry and add a writer-to-reader-to-validator integration test. Keep a legacy fixture only if it is explicitly labeled as a migration-compatibility case.

### I4 — The writer marks analysis and other staged resources canonical too broadly

**Severity: high**

The table-writing path marks resources canonical regardless of whether their namespace is core or analysis. Array and external-resource paths also default broadly to canonical. This conflicts with the specification and R30, which say analysis products are not canonical without an explicit profile decision.

**Recommendation:** derive canonicality from the resource/profile registry. Until that exists, use a conservative rule: analysis and extension-derived outputs are noncanonical unless the authoritative registry explicitly opts them in.

### I5 — Non-table derived resources cannot express lineage consistently

**Severity: high**

The writer's `derives` and `produced_by` handling resolves resources through table specifications. That prevents derived arrays or media from using the same first-class lineage and processing-run model even though the manifest contract is resource general.

**Recommendation:** make derivation operate on resource declarations/IDs, not table specs. Validate acyclicity, existence, layer policy, and processing-run requirements uniformly for tables, arrays, media, and documents.

### I6 — Duplicate resources, format checks, and manifest state rules are not enforced

**Severity: high**

The reader silently overwrites duplicate resource IDs in its lookup dictionary. Schema date/time formats are not enabled during validation. The validator does not comprehensively enforce `canonical`, `derived_from`, validation-state, and processing-run relationships.

**Recommendation:** add an early manifest semantic-validation phase before constructing `Packet`; make duplicate IDs fatal; enable format checking; and centralize state invariants so reader, validator, and writer use the same checks.

### I7 — Extension physical schemas are incompletely checked

**Severity: high**

Generated extension SQL can detect some problems when expected columns are present, but extension tables do not consistently receive the core pipeline's systematic column-presence, type, nullability, role, and physical-profile checks. A missing extension registry may also disappear from the loaded-registry loop rather than becoming a declared-extension failure.

**Recommendation:** build a validation plan from every successfully validated registry and a failure entry from every unsuccessfully loaded declaration. Execute the same structural, physical, generated, and relational phases for core and extensions.

### I8 — Zarr capability reporting conflates mandatory and optional codecs

**Severity: medium, coupled to S10**

The validator recognizes optional codecs as if they were inside the universally supported floor. This can give users the wrong interoperability signal.

**Recommendation:** report both validity and portability class. A packet using a recognized optional codec can be valid while requiring an advertised capability.

### I9 — Cross-package tests do not protect the released contract

**Severity: high**

Individual package coverage is good, but independently maintained fixtures have allowed an old unit model and core-only extension verdict to become test expectations. The current exact registry is not the single source for all relevant test data.

**Recommendation:** add a release-gate matrix that:

1. builds a packet with the writer from a recipe and current registries;
2. reads it using only public reader APIs;
3. validates it with the validator;
4. checks the manifest against the published schema with format checking;
5. exercises one valid and one invalid extension;
6. compares selected example queries with the specification;
7. repeats with a non-table derived resource and an external resource.

Package-specific unit tests should remain, but generated contract fixtures should be shared.

### I10 — Type annotations and docs still reflect earlier logical types

**Severity: low to medium**

Some reader APIs annotate identifiers such as `unit_id` or `session_id` as strings even where the current registry declares integer types, and nearby documentation still describes the composite unit identity. These do not always fail at runtime, but they mislead downstream users and static tooling.

**Recommendation:** generate or verify public API type expectations against logical registry types where the API exposes a direct registry field.

### I11 — Direct writer construction can bypass declaration validation

**Severity: medium**

The normal generated path supplies well-formed extension and adapter data, but direct `PacketWriter` construction performs only limited namespace and redefinition checks. Malformed declarations may fail later and less clearly.

**Recommendation:** validate every supplied registry and declaration at the public boundary, regardless of whether it came from repository-generated code or a third party.

## Documentation and project-organization findings

### Current-status documents have drifted

The root `README.md` reports 24 packets in one place while current generated facts report 28. It describes Phase 5 as in progress and Phase 6 as not started even though later project material describes a more advanced state. It also says each package is maintained in its own repository, while this is a monorepo.

`STATUS.md` still labels the contract POC v0.1 and says the root is not tracked as a repository. `DEVELOPING.md` refers to a 26-packet corpus. `registry/README.md` describes building from the frozen Part 02 plus only revisions R3–R11, even though the history now extends through R119, and some command examples use bare `python3` rather than the project's documented `uv` workflow.

These documents are prominent enough to affect architecture comprehension, not merely polish.

**Recommendation:** generate volatile facts—test counts, packet counts, current phase, versions, and artifact inventory—from one status source. Keep historical logs explicitly dated and separate. Entry-point documentation should explain the current architecture and link to history rather than embedding a long mutable history itself.

### Developer guidance repeats normative content

The various `CLAUDE.md` files repeat authority rules, versions, table facts, and revision descriptions. Repetition makes agent guidance convenient but has already produced contradictions.

**Recommendation:** keep a short authority statement and workflow rules in each package, then link to generated facts for schema counts, versions, and contract details. Do not restate normative requirements in tool guidance unless they are generated from the same source.

### The specification could be easier to navigate

The v0.2 specification is roughly 35,000 words. Part 03 combines physical storage requirements with the adapter IPC boundary, and Part 02 carries both registry concepts and a large schema description. This is more than a navigation problem: as S0 details, some content is in the wrong abstraction layer and becomes a second normative source. The material is coherent enough to keep as parts, but the responsibilities of those parts need enforcement.

**Recommendation:** add three compact generated views without weakening the normative text:

- a conformance matrix mapping every resource kind to its required manifest fields, physical profile, integrity rule, and validation stages;
- a lifecycle diagram for recipe resolution, staging, provenance, validation, and publication;
- a terminology/identity table for every primary entity and identifier.

Consider moving the adapter/build interface into its own normative part in the next version, with packet-profile-specific transport encodings referenced from Part 03. The Part 08 example SQL should execute in CI against a generated example packet.

### The existing root review has become stale

The earlier v0.2 review is useful history, but its presence beside current docs without a status banner creates another apparent authority source. Date and label all reviews, and point readers toward the newest accepted review or issue tracker.

## Where to start

Do not start by repairing reader or writer behavior independently. Start with one small governance revision whose only purpose is to make the specification capable of owning subsequent changes consistently.

### Step 1 — Establish authority and normative ownership in Part 00

The first revision should be titled along the lines of **“Specification authority, abstraction levels, and normative ownership.”** It should make no scientific or storage-design changes. It should:

1. name the generated v0.2 parts as the authoritative behavioral specification;
2. state how the exact registry and published JSON Schemas participate in that authority;
3. distinguish semantic/logical/physical abstraction levels from core/extension/analysis/projection content layers;
4. assign each part one subject and define the allowed dependency direction among parts;
5. require every normative rule to have one owning location;
6. say that summaries and examples are non-normative restatements and cannot override their owner;
7. classify a disagreement among authoritative artifacts as a release defect rather than supplying an informal precedence escape hatch;
8. distinguish revision acceptance, incorporation, implementation, conformance verification, and release.

This should be applied through the existing revision/generation process rather than by treating the generated parts as unrelated hand-edited documents. Once generated, the same authority paragraph should be copied or linked consistently from the root and package entry-point documentation.

### Step 2 — Perform a semantics-preserving placement pass

Before deciding disputed behavior, inventory every normative clause and classify it by owner. For each duplicate, choose one of four dispositions: `own`, `reference`, `explain non-normatively`, or `remove as superseded`. This pass should move or demote statements without changing their intended meaning.

Start with the most obvious boundary violations:

- remove exact keys, columns, registry counts, measured costs, and workflow behavior from Part 00;
- remove scalar storage types, column names/presence, manifest placement, and importer algorithms from Part 01;
- separate packet-storage rules in Part 03 from packet lifecycle and adapter/build-interface rules;
- remove independent RFC-keyword obligations from informative Parts 07, 08, and 10;
- make Part 06 either wholly normative for analysis policy or wholly informative after moving its normative rules.

Because current revisions cite section numbers, introduce stable clause IDs or leave explicit forwarding stubs before moving large blocks. Otherwise improving organization will break the provenance mechanism used to justify it.

This pass will expose genuine semantic decisions cleanly. For example, the composite unit-key statements in Parts 00 and 01 should first be classified as misplaced duplicates; Part 02 and the registry then become the sole place where the actual identity decision must be resolved.

### Step 3 — Resolve the blocking semantic contracts in dependency order

After ownership is clear, resolve the substantive blockers in this order:

1. **Unit identity.** It affects keys, references, extensions, example queries, reader APIs, fixtures, and migrations. Decide it once in Part 02 and the registry.
2. **Profile/resource declarations and requiredness.** Add the data model that says which tables, arrays, media, or documents must or may be present and what canonicality/lineage rules apply.
3. **Manifest contract.** Generate the resource conditions in Part 04 and JSON Schema from that model, supplemented by named semantic checks where JSON Schema is insufficient.
4. **Validity composition.** Define core, per-extension, and overall packet verdicts against the now-unambiguous manifest/registry declarations.
5. **Recipe arbitration.** Put preferences and shared-contribution policy in the recipe rather than writer or lab code.
6. **Remaining reconciliations.** Fix publication order, adapter write capability, analysis lineage, prefix checksums, and codec capability terminology.

This order avoids designing the manifest around hand-maintained resource rules or fixing writer commit behavior before “valid packet” has one definition.

### Step 4 — Regenerate contracts before changing packages

For each substantive decision, change the authoritative spec source and data model first, then regenerate and review:

- numbered and combined v0.2 documents;
- exact core and extension registries;
- manifest, registry, adapter, resource, and recipe schemas;
- generated validators and documentation;
- positive and negative conformance fixtures.

No implementation should need to infer the decision from prose once those outputs exist.

### Step 5 — Bring implementations into conformance from the center outward

Update the shared contract/validation path first, followed by the components that depend on its verdict:

1. registry and schema validation;
2. validator reports and overall verdict;
3. writer publication gates and recipe resolution;
4. reader APIs and resource lookup behavior;
5. lab/task adapters;
6. package documentation and examples.

Finish each group with a writer → reader → validator integration packet built from the current registries. Do not rely on hand-maintained package fixtures as the release gate.

### First concrete milestone

The first useful checkpoint is therefore not “fix `spike_times()`.” It is:

> Part 00 explicitly defines both axes and the ownership of every part; every existing normative clause has an assigned owner; and the old unit-identity statements are identified as either the selected Part 02 rule or non-owning/superseded duplicates.

That milestone is small enough to review, changes no packet bytes by itself, and makes every later change substantially safer.

## Recommended release plan

### P0 — Resolve before declaring stable v0.2

1. Publish the authority hierarchy and define an immutable v0.2 release bundle, including exact registry/schema artifacts and hashes.
2. Assign every normative rule one owning part, remove or demote duplicate statements, and correct the abstraction-layer violations summarized in S0.
3. Resolve unit identity everywhere: specification, registry, extensions, examples, APIs, fixtures, and tests.
4. Reconcile Part 04 with the manifest and resource schemas; add semantic uniqueness, format, and cross-field validation.
5. Add data-driven required/optional resource semantics.
6. Define `core_passed`, per-extension validity, and overall `packet_passed`; prevent the writer from committing any invalid declared extension.
7. Move ownership/preference/shared-contribution policy into the session recipe as required by R115.
8. Run full meta-schema and structural validation on embedded core and extension registries.

### P1 — Complete the data-driven contract

9. Add a resource/profile registry for arrays, media, documents, requiredness, canonicality, lineage, and physical capabilities.
10. Publish a session-recipe schema and tighten adapter declarations.
11. Reconcile pipeline order, adapter write capability, analysis lineage/canonicality, and prefix-checksum language.
12. Support derived non-table resources with the same lineage/provenance model as tables.
13. Add current-registry writer-to-reader-to-validator integration tests, including valid and invalid extensions.

### P2 — Harden interoperability and maintenance

14. Represent codec capabilities and parameters precisely.
15. Generate document counts, tables of contents, status facts, and conformance matrices.
16. Extend revision state and impact tracking beyond textual incorporation.
17. Start future revisions from a frozen v0.2 baseline and target a new version for normative changes.
18. Add a real non-Python or protocol-only adapter conformance test.
19. Clean up stale root/package documentation and label historical reviews.

## Suggested v0.2 release criteria

The following is a practical definition of “ready” for this project:

- every authoritative artifact is listed and hashed in a release index;
- every normative clause has one identifiable owning layer, and informative sections introduce no independent obligations;
- no generated spec part contradicts another on identities, presence, validity, or publication order;
- exact registry data passes both shape and semantic structural checks;
- manifest prose, JSON Schema, and semantic validation accept and reject the same conformance cases;
- every registered resource has a computable presence rule;
- a declared extension failure makes overall packet validity fail and prevents publication;
- recipe resolution contains no lab/task preference policy outside declarations;
- one packet built from the current recipe/registry path passes reader and validator integration tests;
- negative fixtures cover duplicate IDs, missing required resources, invalid extension registries, wrong physical schemas, bad lineage, and failed-canonical combinations;
- the example packet and Part 08 queries execute successfully;
- current entry-point documentation names generated v0.2 as the sole normative behavioral source.

## Detailed lower-priority observations

These observations did not drive the headline verdict but should not be lost:

- The combined v0.2 document correctly identifies itself as a convenience artifact generated from parts. That distinction should be repeated in the authority statement.
- `logical_schemas.json` records that it was derived from the frozen specification. This is useful provenance, but “derived from” should not make readers think the old document overrides current generated v0.2.
- The reader's ability to expose core data when an extension cannot be interpreted is valuable. It should be preserved while making validation strict about declared extensions.
- Open top-level and resource objects in the manifest schema may be intended for forward compatibility. If so, the extension mechanism for unknown fields should be documented; otherwise use `unevaluatedProperties: false` or an explicit annotations object to catch typos.
- External-resource verification is sensibly separated from local integrity, but canonicality should not be inferred merely because an external reference was successfully recorded.
- Analysis materialization order in the writer already follows the safer interpretation of Part 05; the specification overview should adopt it.
- The generated registry checker exercising SQL rules against empty typed tables is a useful smoke test, but it cannot validate join semantics or cardinality. Add small positive and negative data fixtures for high-risk SQL rules.
- The conformance corpus includes an extension, but current expected behavior preserves the core-only overall verdict. Update it after resolving I1 and add missing/unparseable/structurally invalid extension cases.
- A registry schema version, logical registry version, profile version, and semantic-standard version currently remain at v0.1/0.1.0 in places despite breaking v0.2 development changes. The v0.2 README describes this as a deliberate hold, and `TODO.md` already flags it as a production-trial blocker. Before release, bump every identifier whose governed content is incompatible. A physical profile may retain its old version only if its actual contract is unchanged.
- Reusing an old `$id` or registry version for incompatible meta-schema or logical-registry contents defeats embedded-registry authority and cache correctness. Version identifiers should describe the bytes/contract they identify, not the maturity of the whole project.
- The spec's normalized table philosophy is clear, but the boundary between a core table, an extension table, and an analysis representation would benefit from a short decision tree.
- The registry can generate many Tier 1 checks and contains Tier 2 SQL, but manually authored validators remain necessary for file layout, checksums, Zarr metadata, media probing, and manifest state. The architecture should present these as declared validator capabilities, not imply every invariant will be generated from table metadata.
- `resources.schema.json` may be intended only as adapter-to-writer input rather than committed-manifest shape. Rename or document it accordingly, and still share common field definitions so the two stages cannot disagree accidentally.
- The packet reader should fail before lookup-map construction on duplicate IDs rather than allowing last-entry-wins behavior.
- The extension namespace should be present on serialized findings so machine consumers can group errors without parsing messages or paths.
- Root status material mixes durable architecture, active work tracking, and historical narrative. Those have different lifecycles and should be separate documents or generated views.
- A claim of full NWB succession should remain aspirational until additional domain profiles demonstrate that the registry/resource model generalizes beyond the current electrophysiology focus. The current work is already useful without overstating that breadth.

## Final verdict

Escapewheel is not off track. Its foundational choices are coherent and, in several respects, better suited to durable commodity storage than a monolithic object-format successor would be. The project has reached the stage where adding more implementation surface is less valuable than making the published contract singular, data-driven, and executable.

The immediate goal should be a reconciliation release, not a redesign: establish one authority statement; resolve the few contradictory identities and lifecycle rules; make manifest and resource requirements declarative; remove hidden arbitration policy; apply registry validation uniformly; and make packet validity include every declared extension. Once those items are complete, the current architecture is a credible base for an immutable v0.2 and for later storage/profile expansion.

## Verification record

During the evaluation that produced this report:

- all four package test suites passed, totaling 949 tests;
- the generated v0.2 combined-document check passed;
- the registry structural/code-generation check passed;
- the citation checker reported zero unresolved citations;
- the revision ledger reported no undisposed clauses;
- no specification, registry, source, test, or documentation artifact was changed.

The repository-wide verification wrapper was not run because it regenerates tracked artifacts and the evaluation phase explicitly prohibited changes. Individual read-only or package-level checks were used instead. At the time of review, the only unrelated working-tree item observed was the pre-existing untracked `.vscode/` directory.
