# Current Specification Owners Carry Current Meaning, Not Revision History

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `4baad5df16c74d6cea445f05594d57d45c74c7a2` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Specification README status and §§5.1–5.2; revision-provenance references throughout Parts 00–10; `00_architecture.md` heading “Citing this specification” and its four subsections; Part 02 §§1, 3, and 9.1–9.4; Part 03 §9.3; Part 04 §3; `registry/logical_schemas.json`; `registry/registry.schema.json`; `registry/manifest.schema.json`; `registry/sources.schema.json`; `registry/rules.json`; extension registries; registry generation, checking, and rendering; generated specification publications; provisional release artifacts |
| **Depends on** | R120 §§3.1 and 3.3–3.7 (process authority, one-way current-owner traceability, structural change, anchors, citations, and evidence) |
| **Profile** | all |
| **Decision clauses** | §3.1, §3.2, §3.3, §3.4, §3.5, §3.6 |

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
specification” and its four subsections, together with Part 02 §9.4, rather than
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
repository editing and citation procedure. R120
now assigns the latter subjects to `revisions/CONTRIBUTING.md`. Part 00 §9 already says which parts
bind, and Part 02 §1 already incorporates the exact registry declarations, so retiring §10 does not
require a temporary normative replacement before the later authority revision.

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

The reverse-impact query over those five `00_architecture.md` headings and Part 02 §9.4 reports 18
citations at the
checkpoint: six in the promoted proposal preserved by Git, eight in immutable accepted history,
and four other live references. The live references are Part 07 §2.3's developer-comment guidance,
the “A revision is cited for what a part does not carry” subsection's reference to `since`,
`revisions/repoint.py`'s `since` exemption, and the dependent
authority draft. Each has an explicit disposition below. Historical accepted records remain
unchanged and are interpreted in their recorded contexts.

## 3. Decision

### 3.1 Current specification owners are independent of revision history

The authored specification README, numbered parts, and machine-readable artifacts incorporated by
them **MUST NOT** cite a proposal, draft, accepted revision, withdrawn revision, or the frozen proof
of concept as the authority or provenance for current meaning.

A current requirement or declaration **MUST** be understandable from its current owner and the
current owners that it cites. Current prose **MAY** retain rationale that helps an independent
implementer, but that rationale **MUST** state the present reason directly rather than narrating the
repository change that produced it.

Accepted revisions, the clause ledger, evidence manifests, and Git **MUST** remain the owners of
decision history and provenance. They **MUST NOT** require a current specification owner to cite
that history back.

### 3.2 Repository-maintenance procedure is not packet-specification content

The v0.2 numbered specification **MUST NOT** prescribe the repository's revision lifecycle,
structural-editing procedure, citation spelling, citation-checker behavior, or ledger maintenance.
Those subjects **MUST** remain owned by `revisions/CONTRIBUTING.md` under R120.

The `00_architecture.md` heading “Citing this specification” and its four subsections **MUST** be
retired. Their current-contract ownership observations are already
stated by Part 00 §9 and Part 02 §1. Part 07 §2.3's developer-facing comment and docstring guidance
**MUST NOT** keep a normative Part 00 process section alive; it **MUST** be removed from the packet
specification or replaced by current developer guidance outside the numbered parts.

### 3.3 Registry documents do not carry repository revision provenance

The registry meta-schema **MUST NOT** define `derived_from` as a property of a registry document.
It **MUST NOT** define `since` as a property of a table or column declaration. Because the affected
objects remain closed, a registry document containing either removed property does not conform to
the cleaned meta-schema.

The current core and extension registries **MUST NOT** contain registry-build `derived_from`, table
`since`, or column `since`. Part 02 §3's column-attribute inventory and Part 02 §9's registry model
**MUST NOT** describe or recommend either provenance field, and Part 02 §9.4 **MUST** be retired.

The packet catalog's resource-lineage `derived_from` **MUST** retain its current meaning and shape.
It is not a registry-build provenance field and is not removed by this clause.

### 3.4 The cleaned registry shape has a new identity

The cleaned registry meta-schema **MUST** carry this exact `$id`:

```text
https://escapewheel.org/schemas/registry/0.2.0
```

Every current core or extension registry document **MUST** carry that exact value in `$schema`.
The core registry **MUST** carry `registry_version` `0.2.0`.

The extension registries **MUST** retain their extension-specific registry versions because their
logical declarations do not change: `aind_opto` `0.2.0`, `aind_unit_qc` `0.1.0`,
`dynamic_foraging` `0.3.0`, and `vr_foraging` `0.2.0`.

The current repository and specification candidate **MUST NOT** retain a `0.1.0` copy of the
registry meta-schema as a current member. Current development packets and fixtures **MUST** be
regenerated with the cleaned registry. The specification makes no migration or current-conformance
promise for an unreleased development packet carrying the old registry-document shape.

### 3.5 Removing provenance does not change declaration or validation semantics

Except for the fields removed by §3.3, the identities changed by §3.4, and revision-only prose in
descriptions or messages, the current core and extension registry declarations **MUST** remain
unchanged. Tables, columns, types, presence, roles, identities, keys, references, vocabularies,
units, clocks, rule identifiers, rule levels, rule SQL, and the set of offending rows **MUST** be
the same before and after incorporation.

Schema descriptions and declarative validation messages **MUST NOT** cite revision records. A
message may be rewritten to state its current explanation directly, but its rule identifier,
severity, query, execution conditions, and pass/fail effect **MUST NOT** change under this revision.

### 3.6 The specification README carries current status, not revision status

The specification README's status text **MUST** identify the current v0.2 proof-of-principle packet
specification without listing accepted or withdrawn revisions, open proposal or draft counts, the
derivation from v0.1, or the meaning of revision citations.

The current-version table and registry-version explanation **MUST** identify core registry
`0.2.0`, remove the temporary `0.1.0` hold, and state the regeneration boundary of §3.4 without
promising compatibility for the old development shape. The README **MUST NOT** introduce the term
*specification candidate* before the dependent authority revision defines that state.

## 4. What this does not change

- The packet catalog's resource-lineage `derived_from` remains unchanged.
- No table, column, key, reference, vocabulary, rule predicate, physical encoding, adapter source
  contract, or packet interpretation changes.
- Reader and validator algorithms remain unchanged. Writer output changes only where it embeds or
  records the cleaned registry and its new identity.
- Extension logical declarations and extension-specific registry versions remain unchanged.
- Accepted and withdrawn revision records, ledger dispositions, evidence manifests, and historical
  source contexts remain unchanged.
- Implementation comments and developer documents may retain useful historical rationale where
  they are not emitted into the current specification or a machine-readable contract artifact.
- This revision does not define specification-candidate authority, final release membership, a
  release-manifest schema, or publication tooling.

## 5. Consequence

The registry-document shape and identity change intentionally. Current development packets and
fixtures are regenerated; old development packets receive no migration or current-conformance
guarantee. Packet rows, arrays, media, catalog lineage, and logical interpretation do not change.

The registry generator replaces its one history-valued name-column selector with a derivation from
the sole non-exported assigned primary-key identifier. Other internal historical comments may
remain until the later direct-registry-source work; they do not enter current contract artifacts or
determine current declarations.

The stale root `RELEASE.json` is deleted. Root `release.py` moves to
`prototype/release-bundle/probe.py`, labels itself as a non-authoritative experiment, and loses its
ability to write `RELEASE.json`. The digest and inventory experiment remains available as design
evidence. The dependent authority revision classifies candidate and released states; the later
publication work decides manifest membership and publication tooling.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Remove 92 revision references from Part 01 while preserving each present concept meaning and obligation. | Semantic review records a self-contained current statement, current-owner link, or history-only deletion for every affected sentence. |
| logical prose and registry | Remove Part 02's provenance model, registry `derived_from`, table and column `since`, and historical description or message citations. Set the meta-schema and core registry identities from §3.4. | Cleaned meta-schema validates core and all four extensions; negative instances containing either removed property fail; normalized declaration comparison passes. |
| physical profiles | Remove or rewrite 87 revision references without changing a format, codec, layout, amendment rule, or adapter protocol. Part 03 §9.3 remains semantically unchanged. | Physical-profile review and existing probes pass; retained-registry and same-version collision tests pass against current version `0.2.0`. |
| packet catalog and JSON Schemas | Preserve resource lineage. Keep the Part 04 §3 field shape while current manifests record `0.2.0`. Remove revision citations from schema descriptions. | Catalog schema and lineage tests pass; current generated manifests and embedded registries agree on `0.2.0`. |
| validation and import | Remove 56 prose references and revision suffixes from declarative messages without changing procedures or verdicts. | Rule IDs, levels, SQL, execution modes, finding rows, and all corpus pass/fail outcomes compare equal. |
| extensions | Remove 14 `since` fields and six description citations; update `$schema`; preserve declarations and extension versions. | All four extension registries validate; exact normalized comparison and extension tests pass. |
| reader, writer, validator, adapters | Update writer output and reader-visible current version metadata. Preserve reader and validator algorithms and adapter source contracts. Update vendored registry schemas. | Package tests pass; version-specific assertions use `0.2.0`; generic version-transition tests retain arbitrary versions where appropriate. |
| conformance fixtures and tests | Regenerate fixtures and development packets. Add positive and negative meta-schema cases and a normalized registry equivalence test. | All 28 corpus packets behave as expected; valid packets are clean; the normalization test reports no undeclared difference. |
| revision process and tooling | Keep R120, the ledger, evidence, and accepted history unchanged. Remove checks requiring backward provenance and add a scoped negative check for revision references in current owners. | Stage, citation, ledger, evidence, impact, heading, and new history-free-owner checks pass. |
| generated publications and developer documentation | Regenerate `registry/tables.md`, registry facts, vendored schemas, and the combined specification; stop projecting revision status into the specification README; update version-specific guidance; delete and relocate the provisional release artifacts. | A second generation is clean; no current-owner source contains a forbidden revision reference; root `RELEASE.json` and root `release.py` are absent; the prototype probe cannot write a release snapshot. |

## 6. Conformance and implementation evidence

The incorporation must preserve a copy of the pre-change generated registry for comparison. A
normalizer removes only:

- root registry-build `derived_from`;
- table and column `since`;
- `$schema` and the core `registry_version` values changed by §3.4; and
- revision-only text removed from descriptions and rule messages.

After normalization, every remaining core and extension declaration and every rule predicate must
compare exactly. Description and message rewrites receive a separate human review so the normalizer
cannot conceal a semantic deletion behind the text exception.

Positive meta-schema cases cover the cleaned core registry and all four cleaned extension
registries. Negative cases add root `derived_from`, table `since`, and column `since` separately and
establish that each closed object rejects the property.

The history-free-owner check scans the authored specification README, Parts 00–10,
`registry/logical_schemas.json`, the registry, manifest, and source schemas, `registry/rules.json`,
and the extension registries for revision-record references. It excludes accepted and withdrawn
records, process documents, evidence, the frozen proof of concept, and non-emitted implementation
comments. Generated projections are regenerated from clean sources and checked for stability.

Every hard-coded `0.1.0` is classified. A value denoting the current core registry changes to
`0.2.0`; a value used only to exercise generic version parsing, retention, pruning, collision, or
transition behavior remains a test value. The reader, writer, validator, prototype, and conformance
tests record that classification through their resulting diffs and assertions.

The seven-column generator probe establishes that the structural selector resolves exactly one
target per affected table and produces the same name column selected before incorporation. A
missing or ambiguous target is a generation failure rather than a silent choice.

The reverse-impact query is rerun after the required anchor bootstrap and before acceptance. Each
live citation into a retired heading is repointed or removed according to the crosswalk below; the
immutable accepted-history citations remain unchanged.

| old location | disposition | current destination or consequence | semantic effect | Decision clause |
|---|---|---|---|---|
| `00_architecture.md` — “Citing this specification” | retire heading | Part 00 §9 for current part ownership; process guide for repository citation procedure | Split subjects between existing current owner and process owner; no packet rule changes. | §3.2 |
| `00_architecture.md` — “A requirement is cited from the part that states it” | retire | Part 00 §9 and Part 02 §1; `revisions/CONTRIBUTING.md#ew-citation-context` for citation procedure | Remove the obsolete claim that a revision can remain the current statement of record. | §§3.1–3.2 |
| `00_architecture.md` — “A revision is cited for what a part does not carry” | retire | Accepted history for rationale; §3.3 for removal of `since`; revision guide for historical citation practice | Remove backward provenance and process exceptions from packet-conformance prose. | §§3.1–3.3 |
| `00_architecture.md` — “A part is numbered by appending” | retire | `revisions/CONTRIBUTING.md#ew-structural-reorganization` | No packet rule; R120 already owns structural editing. | §3.2 |
| `00_architecture.md` — “A part is cited as Part 02” | retire | `revisions/CONTRIBUTING.md#ew-citation-context` | No packet rule; R120 already owns citation presentation and checking. | §3.2 |
| Part 02 §9.4 | retire | No replacement field; accepted history and Git retain provenance. | Registry documents no longer carry repository revision provenance. | §3.3 |
| README revision-status block and surrounding provenance explanation | replace | Short history-free v0.2 status statement; process status remains outside the specification README. | Removes history and changing lifecycle counts without changing packet conformance. | §3.6 |
| README §§5.1–5.2 current registry value and temporary hold | replace in place | Core registry `0.2.0` and the regeneration boundary in §3.4 | Changes registry identity and development-packet compatibility boundary only. | §§3.4, 3.6 |

The complete repository verifier, package tests, fixture corpus, registry generation, schema
validation, stage and citation checks, ledger, evidence checker, heading checker, and combined
specification check close incorporation.

## 7. Pre-acceptance work

This section is informative and adds no Decision clause.

Before final acceptance appraisal, the structurally affected existing headings in the crosswalk
must receive canonical anchors in a separately committed metadata-only bootstrap under R120. The
draft then rebases on that commit, replaces numbered source and destination references with exact
anchors where required, reruns the 478, 549, and reverse-impact measurements, and confirms the
crosswalk against the resulting source population.

The semantic sweep of prose and machine-readable message text must be complete before acceptance;
the token counts measure its population but do not prove that every rewritten sentence preserved
meaning. The normalized registry comparison, description/message review, hard-coded-version
classification, and release-prototype relocation must also have concrete incorporation plans and
tests in the final appraised draft.

These are execution and evidence requirements for the settled Decision, not open design questions.
