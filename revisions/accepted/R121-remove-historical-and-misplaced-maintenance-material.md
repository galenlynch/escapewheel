# Current Specification Owners Carry Current Meaning, Not Revision History

| | |
|---|---|
| **Status** | **Accepted** 2026-09-19 |
| **Based on** | `41aad8a15b7c8c3415f6c52b3c12e64114658718` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Specification README status and §§5.1–5.2; revision-provenance references throughout Parts 00–10; `00_architecture.md` heading “Citing this specification” and its four subsections; Part 02 §§1, 3, and 9.1–9.4; Part 03 §9.3; Part 04 §3; Part 07 §2.3; `registry/logical_schemas.json`; `registry/registry.schema.json`; `registry/manifest.schema.json`; `registry/sources.schema.json`; `registry/rules.json`; extension registries; registry generation, checking, and rendering; `CONTRIBUTING.md`; `revisions/CONTRIBUTING.md`; `revisions/drafts/README.md`; `registry/README.md`; `escapewheel-validator/src/escapewheel_validator/registry_document.py`; generated specification and registry publications; provisional release artifacts |
| **Depends on** | R120 §§3.1 and 3.3–3.8 (process authority, one-way current-owner traceability, structural change, anchors, citations, evidence, and provisional-release process boundary) |
| **Profile** | all |
| **Decision clauses** | §3.1, §3.2 |

Section 3 is normative. Sections 1–2 and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

The generated v0.2 specification and the machine-readable declarations it incorporates are the
current owners of packet meaning. They nevertheless carry the repository history that produced
that meaning: 478 revision tokens in the authored specification README and numbered parts, and 549
more in the measured registry, schema, rule, and extension sources. The incorporated registry also
embeds its accepted-revision ancestry and attaches a revision-valued `since` field to tables and
columns.

R120 established one-way traceability from an accepted decision through the ledger to a standalone
current owner. This revision brings the current specification artifacts into that model. It removes
backward revision provenance and repository-maintenance procedure from current owners, removes the
registry's revision-history fields, gives the changed registry document shape a new identity, and
preserves current contract meaning independently of the revision archive.

The revision is structural because it retires the `00_architecture.md` heading “Citing this
specification” and its four subsections, together with
[Part 02 §9.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-declaration-provenance), rather than
appending contradictory replacement text. Meaning-preserving removal of a trailing provenance
citation does not by itself move or renumber the containing section.

The packet catalog's `resources[].derived_from` is outside this change. It records lineage between
packet resources rather than the editing history of this repository.

## 2. Background

This section is informative.

### 2.1 Current prose points backward

The authored specification sources contain 478 occurrences matching `R[0-9]+`: 16 in the README,
28 in Part 00, 92 in Part 01, 113 in Part 02, 87 in Part 03, 19 in Part 04, 56 in Part 05, 12 in
Part 06, 14 in Part 07, none in Part 08, 19 in Part 09, and 22 in Part 10. The generated combined
rendering repeats those sources and is not an additional owner.

Most occurrences are trailing provenance citations. Others narrate what a revision added, struck,
withdrew, retained, or measured. Removing punctuation mechanically would therefore be unsafe. Each
sentence has to retain its self-contained current rule or useful rationale, link to another current
owner, or disappear when it states only historical sequence.

The `00_architecture.md` heading “Citing this specification” mixes current-owner observations with
repository editing and citation procedure. R120 now assigns the latter subjects to
`revisions/CONTRIBUTING.md`.
[Part 00 §9](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-numbered-part-ownership)
already says which parts bind, and
[Part 02 §1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-core-logical-schema-scope)
already incorporates the exact registry declarations, so retiring the five citation headings does
not require a temporary normative replacement before the later authority revision.

### 2.2 Machine-readable declarations carry repository history

The measured machine-readable sources contain 549 revision tokens: 438 in
`registry/logical_schemas.json`, 34 in the registry meta-schema, 25 in the packet schema, three in
the source-resolution schema, 29 in declarative rules, and 20 in extension registries. The core
registry includes 117 accepted revision identifiers in `derived_from.revisions`, `since` on 23
tables and 255 columns, and revision references in descriptions and messages. Extension registries
add `since` to 14 columns.

No reader, writer, or validator uses registry-build `derived_from` or revision-valued `since` for
packet interpretation, compatibility, migration, or selection. The renderer displays `since`, and
the repository checker compares both fields with accepted history. The generator has one further
construction dependency: it uses the value `R53 §2.3.1` to select seven generated name columns
while applying the current assigned-identifier rule.

Those seven targets are structurally unambiguous. Each is the `<base>_name` column belonging to the
table's sole assigned primary-key identifier that is not exported by a reference:

- `analysis.array_assets.array_asset_name`;
- `core.array_assets.array_asset_name`;
- `core.clocks.clock_name`;
- `core.devices.device_name`;
- `core.event_streams.event_stream_name`;
- `core.media_assets.media_asset_name`; and
- `core.probes.probe_name`.

The generator can derive each target from the current declaration instead of asking which revision
introduced it.

### 2.3 The registry shape changes

The registry meta-schema permits `derived_from` at the document level and `since` on tables and
columns. Its objects are closed, so removing those properties makes a registry containing them
invalid under the cleaned meta-schema. Reusing the existing `$id` would make one identifier denote
two incompatible schemas.

There is no configured remote, published Escapewheel release, known external packet consumer, or
compatibility behavior that needs the old fields. Development packets are already regenerated
against the current registry. The clean boundary is therefore a new meta-schema identity and core
registry version, regeneration of current packets, and no retained current copy or compatibility
promise for the unreleased old shape.

### 2.4 Structural impact is bounded

At the anchor-bootstrap baseline, the numeric reverse-impact query over the seven bootstrapped
source headings reports 18 citations: eight in immutable accepted history and ten live. Six live
citations are in this draft, one is in the dependent authority draft, two are in the numbered
specification, and one is the `since` exemption in `revisions/repoint.py`. The specification sites
are [Part 07 §2.3](../../escapewheel_poc_docs_v0.2/07_reference_implementation.md#ew-code-comment-guidance)
and the reference to declaration provenance under the “A revision is cited for what a part does
not carry” heading. Each live site has an explicit disposition below. Historical accepted records
remain unchanged and are interpreted in their recorded contexts.

## 3. Decision

### 3.1 The cleaned registry-document shape excludes revision provenance

A registry document conforming to the Escapewheel registry meta-schema defined by §3.2 **MUST NOT**
contain registry-build `derived_from` at its root or `since` on a table or column declaration. The
meta-schema's root, table, and column objects **MUST** remain closed, so each removed property makes
the containing registry document invalid.

This rule does not apply to the packet catalog's resource-lineage `derived_from`. That field names
relationships among packet resources and retains its current meaning and shape.

### 3.2 The cleaned registry-document shape has a new identity

The Escapewheel registry meta-schema governing the shape in §3.1 **MUST** carry this exact `$id`:

```text
https://escapewheel.org/schemas/registry/0.2.0
```

Every core or extension registry document published with the v0.2 specification **MUST** carry that
exact value in `$schema`. The core registry published with the v0.2 specification **MUST** carry
`registry_version` `0.2.0`.

## 4. What this does not change

- The packet catalog's resource-lineage `derived_from` remains unchanged.
- No logical resource or table set, column name, type, presence, role, identity, unit, vocabulary,
  key, reference, rule predicate, physical encoding, adapter source contract, or packet
  interpretation changes. Only registry-document history fields and revision-bearing explanatory
  text are removed.
- Reader and validator algorithms remain unchanged. Writer output changes only where it embeds or
  records the cleaned registry and its new identity.
- Extension logical declarations and extension-specific registry versions remain unchanged.
- Accepted and withdrawn revision records, ledger dispositions, and historical source contexts
  remain unchanged. R120's current evidence manifest changes only to repoint the moved
  implementation path; its recorded clause, owner, and evidence meaning do not change.
- Implementation comments and developer documents may retain useful historical rationale where
  they are not emitted into the current specification or a machine-readable contract artifact.
- This revision does not classify the authority of a working specification, define final release
  membership, introduce a release-manifest schema, or select publication tooling.

## 5. Consequence

The registry-document shape and identity change intentionally. Current development packets and
fixtures are regenerated; old development packets receive no migration or current-conformance
guarantee. Packet rows, arrays, media, catalog lineage, and logical interpretation do not change.

Incorporation removes revision-record references from the authored specification README, numbered
parts, and incorporated machine-readable sources. Each resulting statement either states its
current rule completely, cites another current owner for the rule it uses, states useful rationale
directly, or is removed because it said only how the repository reached its present state. Accepted
and withdrawn records, the clause ledger, evidence manifests, and Git continue to carry decision
history without requiring a current specification artifact to cite them back.

The `00_architecture.md` heading “Citing this specification” and its four subsections are retired.
[Part 00 §9](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-numbered-part-ownership)
and [Part 02 §1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-core-logical-schema-scope)
already carry the current ownership observations that survive.
[Part 07 §2.3](../../escapewheel_poc_docs_v0.2/07_reference_implementation.md#ew-code-comment-guidance)
is retired without replacement: its comment-writing advice is not packet-specification content,
and the contribution guides already own current citation guidance.

The specification README's status becomes a short statement about the v0.2 proof-of-principle
packet specification, without revision ranges, open-stage counts, derivation history, or revision-
citation instructions. Its version summary reports core registry `0.2.0`, while Part 02 owns the
registry-document rule and compatibility boundary. Incorporation removes the temporary `0.1.0`
hold and makes no migration or conformance promise for an unreleased development packet carrying
the old registry-document shape.

The extension registries retain their extension-specific registry versions because their logical
declarations do not change: `aind_opto` `0.2.0`, `aind_unit_qc` `0.1.0`, `dynamic_foraging`
`0.3.0`, and `vr_foraging` `0.2.0`. The current schema source, vendored registry meta-schemas, core
registry, extension registries, fixtures, and generated packets use the §3.2 meta-schema identity;
no tracked current schema source or vendored copy at those paths retains the old identity.

The registry generator replaces its one history-valued name-column selector inside the existing
R95 merge step. A candidate table is one that still contains a literal `name` column at that step.
For each candidate, the generator selects assigned identifiers that participate in the primary key
and are not exported by a reference, requires exactly one, removes a terminal `_id` from its name,
and requires exactly one `<base>_name` column. It transfers the literal `name` column's presence to
that target and removes the literal column, as the existing transformation does. Zero or multiple
identifiers or targets stop generation. This selects exactly the seven columns listed in §2.2;
the finished registry alone has other structurally similar name columns, so omitting the candidate-
table precondition would not be equivalent.

Other internal historical comments may remain until the later direct-registry-source work; they do
not enter current contract artifacts or determine current declarations.

`registry/render.py` stops emitting table-introduction notes, the `Since` column, the
revision-bearing key fallback and advisory labels, and the registry revision-ancestry line. It
continues to render every current declaration field and rule. Incorporation regenerates
`registry/tables.md` from that cleaned renderer. It deletes the tracked `registry/tables.html`,
which has no current generator, is not a release member or normative owner, and already presents a
stale registry. A future HTML publication requires a separately reviewed reproducible generation
path rather than retention of this orphaned snapshot.

The stale root `RELEASE.json` is deleted. Root `release.py` moves to
`prototype/release-bundle/probe.py`, labels itself as a non-authoritative experiment, and loses its
ability to write `RELEASE.json`. The digest and inventory experiment remains available as design
evidence without defining a publication tool. The dependent authority revision classifies working
and released states; the later publication work decides manifest membership and publication
tooling. The current process guide is updated to name the non-writing probe rather than a
provisional release generator. R120's accepted record remains unchanged; its current evidence
manifest repoints the implementation path and records that the snapshot it once described was
retired by this later change.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Remove 92 revision references from Part 01 while preserving each present concept meaning and obligation. | Semantic review records a self-contained current statement, current-owner link, or history-only deletion for every affected sentence. |
| logical prose and registry | Remove Part 02's provenance model, registry `derived_from`, table and column `since`, and historical description or message citations. State the §3.1 shape and §3.2 identities in Part 02. | Cleaned meta-schema validates core and all four extensions; negative instances containing either removed property fail; normalized declaration comparison passes. |
| physical profiles | Remove or rewrite 87 revision references without changing a format, codec, layout, amendment rule, or adapter protocol. Part 03 §9.3 remains semantically unchanged. | Physical-profile review and existing probes pass; retained-registry and same-version collision tests pass against current version `0.2.0`. |
| packet catalog and JSON Schemas | Preserve resource lineage. Keep the Part 04 §3 field shape while current manifests record `0.2.0`. Remove revision citations from schema descriptions. | Catalog schema and lineage tests pass; current generated manifests and embedded registries agree on `0.2.0`. |
| validation and import | Remove 56 prose references and revision suffixes from declarative messages without changing procedures or verdicts. | Rule IDs, levels, SQL, execution modes, finding rows, and all corpus pass/fail outcomes compare equal. |
| extensions | Remove 14 `since` fields and six description citations; update `$schema`; preserve declarations and extension versions. | All four extension registries validate; exact normalized comparison and extension tests pass. |
| reader, writer, validator, adapters | Update writer output and reader-visible current version metadata. Preserve reader and validator algorithms and adapter source contracts. Update vendored registry schemas and the validator registry-document docstring that describes `derived_from` as current build bookkeeping. | Package tests pass; the focused writer assertion checks both the embedded registry and manifest at `0.2.0`; generic version-transition tests retain arbitrary versions where appropriate; implementation documentation describes the cleaned document. |
| conformance fixtures and tests | Regenerate fixtures and development packets. Add positive and negative meta-schema cases and a normalized registry equivalence test. Remove the now-forbidden synthetic table `since` from `conformance/interval-kinds/probe.py` while retaining that probe's independent registry versions. | All 28 corpus packets behave as expected; valid packets are clean; the normalization test reports no undeclared difference; every registry document constructed by a current probe obeys the cleaned shape. |
| revision process and tooling | Keep R120's accepted record and ledger dispositions unchanged. Repoint its evidence manifest from the moved release prototype, remove checks requiring backward provenance, and add a scoped negative check for revision references in current owners. Update `CONTRIBUTING.md`, `revisions/CONTRIBUTING.md`, and `revisions/drafts/README.md`, whose current explanations depend on `since`, registry `derived_from`, compiled-spec backlinks, or the root release prototype. | Stage, citation, ledger, evidence, impact, heading, and new history-free-owner checks pass. R120's evidence resolves at the moved probe, and current process guidance describes the one-way model without relying on removed fields. |
| generated publications and developer documentation | Remove revision-bearing output templates from `registry/render.py`; regenerate `registry/tables.md`, `registry/README.md` facts, vendored schemas, and the combined specification; delete orphaned `registry/tables.html`; stop projecting revision status into the specification README; align the specification style guide with history-free current parts; update version-specific guidance; delete and relocate the provisional release artifacts. | A second generation is clean; the combined specification and generated registry listing contain no forbidden revision reference; `registry/tables.html`, root `RELEASE.json`, and root `release.py` are absent; current guidance does not direct specification prose to add revision history; the prototype probe cannot write a release snapshot. |

## 6. Conformance and implementation evidence

The two Decision clauses have these planned current-owner dispositions. The accepted revision will
record the structural and editorial cleanup as history; it will not remain the owner of either
registry rule.

| Decision clause | planned ledger disposition | current owner and projections |
|---|---|---|
| §3.1 | `applied` | [Part 02 §9.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document) states the permitted registry-document contents. Part 02 §3 omits the removed column attribute; the meta-schema, core and extension registries, renderer, and validator are checked projections or implementations. |
| §3.2 | `applied` | [Part 02 §9.2](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-self-description) states the meta-schema identity and core registry version. The specification README, registry documents, vendored schemas, manifests, fixtures, and examples are checked projections or instances. |

### 6.1 Semantic sweep

The pre-acceptance prose sweep read all 394 authored lines containing the 478 measured revision
tokens. A citation-only line retains a complete statement after its trailing provenance citation
is removed; a direct-review line uses a revision as grammatical or explanatory content and needs a
written replacement or history-only deletion.

| authored source | revision tokens | affected lines | citation-only | direct review |
|---|---:|---:|---:|---:|
| specification README | 16 | 7 | 5 | 2 |
| Part 00 | 28 | 25 | 24 | 1 |
| Part 01 | 92 | 71 | 67 | 4 |
| Part 02 | 113 | 93 | 75 | 18 |
| Part 03 | 87 | 75 | 69 | 6 |
| Part 04 | 19 | 18 | 17 | 1 |
| Part 05 | 56 | 46 | 43 | 3 |
| Part 06 | 12 | 10 | 8 | 2 |
| Part 07 | 14 | 11 | 9 | 2 |
| Part 08 | 0 | 0 | 0 | 0 |
| Part 09 | 19 | 16 | 15 | 1 |
| Part 10 | 22 | 22 | 4 | 18 |
| **total** | **478** | **394** | **336** | **58** |

The 58 direct-review lines have been read individually. Their incorporation dispositions are:
state the current rule without narrating its introduction; link to the current owning part; retain
a benchmark number, date, or rationale without its revision label; or delete a statement that says
only what a revision did. The seven retired headings use the structural crosswalk instead. No
reviewed line requires a third Decision clause or changes packet meaning.

The 549 machine-readable tokens have this complete source classification. The generated registry
row is reviewed through its authored `registry/build.py` descriptions and `registry/rules.json`
messages, then checked again after generation.

| current artifact | classified population | incorporation disposition |
|---|---|---|
| generated core registry | 117 root-ancestry tokens; 278 table/column `since`; 16 description tokens; 27 tokens in 26 rule messages | Remove the first two populations; rewrite the 16 emitted descriptions at their build sources and the 26 messages at their rule source. |
| registry meta-schema | 30 tokens in 21 retained descriptions; four tokens in the two `since` descriptions | Rewrite the retained descriptions; delete the root `derived_from` and both `since` property definitions. |
| manifest schema | 25 tokens in 19 descriptions | State each present field meaning directly. |
| source-resolution schema | three tokens in two descriptions | State the sidecar and `$schema` meanings directly. |
| authored rules | two tokens in the file comment; 27 tokens in 26 messages | Rewrite the comment and messages without changing IDs, levels, SQL, or execution modes. |
| extension registries | 14 `since` values; six tokens in four descriptions | Remove `since`; rewrite four descriptions; retain extension declarations and versions. |

Non-emitted historical comments in `registry/build.py` are outside the current contract-artifact
scan and may remain. A targeted generated-path inventory identifies the 16 emitted descriptions,
so their authored source strings cannot be mistaken for the many implementation comments.

### 6.2 Contract-preservation comparison

Incorporation compares the bootstrap commit's generated core registry, four extension registries,
and authored rules with the cleaned result. The comparison normalizer removes only:

- root registry-build `derived_from`;
- table and column `since`;
- `$schema` and the core `registry_version` values changed by §3.2; and
- revision-only text removed from descriptions and rule messages.

After normalization, every remaining core and extension declaration and every rule predicate must
compare exactly. Description and message rewrites receive a separate human review so the normalizer
cannot conceal a semantic deletion behind the text exception.

`conformance/history-cleanup/probe.py` performs that comparison against commit
`41aad8a15b7c8c3415f6c52b3c12e64114658718`. It checks the normalized core and each extension
separately and compares each rule's ID, level, SQL, execution mode, and table placement. The
registry verifier runs the comparison while the core registry version is `0.2.0`; a later registry
version may replace this version-specific ratchet through its own reviewed revision.

Positive meta-schema cases cover the cleaned core registry and all four cleaned extension
registries. Negative cases add root `derived_from`, table `since`, and column `since` separately and
establish that each closed object rejects the property.

The history-free-owner check scans the authored specification README, Parts 00–10,
`registry/logical_schemas.json`, the registry, manifest, and source schemas, `registry/rules.json`,
and the extension registries for revision-record references. After generation it also scans the
combined specification and `registry/tables.md`, and it establishes that `registry/tables.html` is
absent. It excludes accepted and withdrawn records, process documents, evidence, the frozen proof
of concept, and non-emitted implementation comments. Generated projections are regenerated from
clean sources and checked for stability.

### 6.3 Version classification

Every `0.1.0` occurrence outside accepted or withdrawn history and this draft has been classified
by what the value versions.

| classification | paths or surfaces | disposition |
|---|---|---|
| current meta-schema or core registry | `registry/registry.schema.json`; `registry/build.py`; generated registry and table renderings; every shipped registry's `$schema`; the validator's vendored registry schema; specification README and Part 08 core-registry values | Change the meta-schema identity and current core registry to `0.2.0`; regenerate projections. Part 08's packet, validator, and extension versions do not change. |
| provisional release snapshot | root `RELEASE.json` | Delete rather than relabel it as a release. |
| independent version domains | manifest, source, resource, and adapter schema IDs and examples; package and lock-file versions; packet, validator, and software versions; Part 10's part version | Retain `0.1.0`; none denotes the core registry or its meta-schema. |
| extension and synthetic registry versions | shipped extension `registry_version` values; extension scaffold and package tests; interval-kind probe; reader and validator synthetic packet fixtures; registry-codegen prototype's own `registry_version` | Retain each declaration's own version. The extension documents and registry-codegen prototype update `$schema` to identify the cleaned meta-schema. The interval-kind probe removes its synthetic table's now-forbidden `since` without changing either shape it measures. |
| version-behavior tests | writer amendment, retention, pruning, collision, and transition tests | Retain arbitrary `0.1.0` specimens because the number is test data, not a current-reference assertion. |
| current human guidance | specification version summary, `TODO.md` live blocker, `STATUS.md` current phase rows, and validator contribution guidance | Report the new current version, close the hold, and phrase embedded-registry behavior generically. Preserve clearly historical measurements and the dated project review. |

The package fixtures that happen to use `0.1.0` exercise an arbitrary embedded registry. The
reference-writer fixture instead reads `registry/logical_schemas.json`; its packet and manifest
therefore demonstrate the new current version without replacing generic version test values.

The seven-column generator probe captures the table state immediately before the R95 merge,
establishes that exactly seven tables carry a literal `name`, and verifies that the algorithm in §5
resolves exactly one assigned non-exported primary-key identifier and one derived target in each.
It compares those targets with the seven listed in §2.2. Removing the candidate-table precondition,
or encountering a missing or ambiguous identifier or target, makes the probe fail.

`registry/build.py` exposes the selector as a side-effect-free helper. `registry/check.py` exercises
the seven current targets plus missing-identifier, multiple-identifier, missing-target, and
multiple-target cases. It also runs the positive and negative meta-schema cases above.
`escapewheel-writer/tests/test_writer.py::test_the_registry_travels_with_the_packet` is extended to
assert that the input registry, embedded registry, and `packet.json` each carry exact
`registry_version` `0.2.0` and that the two written values equal the input value. Generic amendment
and collision tests retain their arbitrary versions.

The release-prototype move retains the importable digest and inventory functions but removes
`OUT`, the `--write` option, and every file-writing call. The existing
`revisions/test_process.py::test_release_generator_selects_moved_ledger` loads the moved probe and
continues to establish R120's ledger selection. A new
`revisions/test_process.py::test_release_probe_is_non_writing` invokes its CLI with writes mocked,
establishes that no write occurs, and establishes that `--write` is rejected. R120's evidence
manifest names the moved probe; the
[process incorporation boundary](../CONTRIBUTING.md#ew-process-incorporation-boundary) names the
non-writing experiment and no tracked release snapshot.

The reverse-impact query is rerun after the required anchor bootstrap and before acceptance. Each
live citation into a retired heading is repointed or removed according to the crosswalk below; the
immutable accepted-history citations remain unchanged.

| old location | disposition | current destination or consequence | semantic effect | Decision clause |
|---|---|---|---|---|
| [`00_architecture.md` — “Citing this specification”](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-specification-citations) | retire heading | [Part 00 §9](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-numbered-part-ownership) for current part ownership; process guide for repository citation procedure | Split subjects between existing current owner and process owner; no packet rule changes. | — |
| [`00_architecture.md` — “A requirement is cited from the part that states it”](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-current-requirement-citations) | retire | [Part 00 §9](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-numbered-part-ownership) and [Part 02 §1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-core-logical-schema-scope); [revision citation procedure](../CONTRIBUTING.md#ew-citation-context) | Remove the obsolete claim that a revision can remain the current statement of record. | — |
| [`00_architecture.md` — “A revision is cited for what a part does not carry”](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-revision-rationale-citations) | retire | Accepted history for rationale; [Part 02 §9.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document) for the cleaned registry shape; revision guide for historical citation practice | Remove backward provenance and process exceptions from packet-conformance prose. | §3.1 |
| [`00_architecture.md` — “A part is numbered by appending”](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-append-only-numbering) | retire | [structural-reorganization procedure](../CONTRIBUTING.md#ew-structural-reorganization) | No packet rule; R120 already owns structural editing. | — |
| [`00_architecture.md` — “A part is cited as Part 02”](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-part-citation-form) | retire | [revision citation procedure](../CONTRIBUTING.md#ew-citation-context) | No packet rule; R120 already owns citation presentation and checking. | — |
| [Part 02 §9.4](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-declaration-provenance) | retire | [Part 02 §9.1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-registry-document) states the cleaned registry shape; accepted history and Git retain provenance. | Registry documents no longer carry repository revision provenance. | §3.1 |
| [Part 07 §2.3](../../escapewheel_poc_docs_v0.2/07_reference_implementation.md#ew-code-comment-guidance) | retire | No replacement; contribution guides retain current citation guidance. | Remove developer-facing comment advice from the informative packet specification. | — |
| README revision-status block and surrounding provenance explanation | replace | Short history-free v0.2 status statement; process status remains outside the specification README. | Removes history and changing lifecycle counts without changing packet conformance. | — |
| README §§5.1–5.2 current registry value and temporary hold | move the normative rule to Part 02 §9.2 and retain an informative summary | Core registry `0.2.0` and the regeneration boundary in §5 | Changes registry identity and development-packet compatibility boundary only. | §3.2 |

The complete repository verifier, package tests, fixture corpus, registry generation, schema
validation, stage and citation checks, ledger, evidence checker, heading checker, and combined
specification check close incorporation.

The clause evidence manifest uses these exact executable records after incorporation:

| clause | executable evidence |
|---|---|
| §3.1 | `registry: structural checks` identifiers `history cleanup preserves declarations and rules`, `removed registry history fields are rejected`, `name-column selector resolves the seven targets`, `name-column selector rejects missing or ambiguous inputs`, `registry validates against its meta-schema`, and `every extension validates against the same meta-schema`; citation-stage identifier `current contract artifacts contain no revision references` |
| §3.2 | `registry: structural checks` identifiers `registry meta-schema identity is 0.2.0`, `core registry version is 0.2.0`, `every shipped registry names the current meta-schema`, and `every vendored schema matches its source`; `escapewheel-writer/tests/test_writer.py::test_the_registry_travels_with_the_packet` |

The evidence manifest also names the exact owner anchors and affected generator, schema,
validator, writer, documentation, probe, and projection paths listed in the impact inventory,
including `registry/render.py`, `conformance/interval-kinds/probe.py`, `CONTRIBUTING.md`,
`revisions/CONTRIBUTING.md`, `revisions/drafts/README.md`, `registry/README.md`, and
`escapewheel-validator/src/escapewheel_validator/registry_document.py`. The full package suites and
28-packet corpus remain incorporation-closure checks; they are not substitutes for the focused
evidence above.

## 7. Pre-acceptance work

This section is informative and adds no Decision clause.

Commit `41aad8a15b7c8c3415f6c52b3c12e64114658718` is the separately committed metadata-only anchor
bootstrap required by R120. It adds canonical anchors to every existing source and destination in
the crosswalk without changing a heading, number, body sentence, normativity marker, meaning, or
alias. This draft uses that commit as its baseline and links the affected locations by anchor. The
prose and machine-readable populations still contain 478 and 549 revision tokens respectively;
§2.4 records the refreshed 18-citation reverse-impact population.

The final numeric query over the seven retiring headings still reports those 18 citations. The
anchor query reports 17 sites: seven generated heading-index entries and ten links in this draft.
The ten draft links identify the reviewed source locations and become historical crosswalk context
after acceptance; every other live numeric citer has the disposition stated in §2.4.

Sections 6.1–6.3 record the completed pre-acceptance semantic and version classifications and name
the concrete incorporation checks. The actual rewrites, normalized comparison result, generated
diffs, package runs, and evidence manifest belong to the atomic acceptance-and-incorporation
change. They are execution requirements for the settled Decision, not open design questions.
