# Current Specification Owners Do Not Carry Revision History

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-19 |
| **Based on** | `b4695ca087376fd85e998743f81401164b2a15c5` |
| **Decision domain** | specification |
| **Affects** | Specification README, including §§5.1–5.2, and numbered parts; Part 00 §§10.1–10.4; Part 02 §§1, 3, and 9.1–9.4; Part 03 §9.3; Part 04 §3; the incorporated logical registry; registry meta-schema, packet and source schemas, declarative rule messages, extension registries, registry generation and rendering; development packets and version-specific tests; generated specification publications; provisional release tooling; coordination with the authority draft |

## 1. Problem

R120 established a one-way authority model for change history:

```text
accepted decision clause -> ledger disposition -> current owner
```

The accepted record preserves the decision and rationale; the current specification or
machine-readable artifact states what holds. A current owner does not need to cite its historical
revision back. Repository-change and citation-presentation procedure now belongs to
`revisions/CONTRIBUTING.md`, not normative Part 00.

The current authoritative artifacts have not yet been brought into that model. The specification
README and numbered parts contain hundreds of `R<N>` references. Part 00 §§10.1–10.4 mix current
authority, historical provenance, and repository-maintenance procedure. The incorporated logical
registry records its entire revision ancestry in `derived_from` and records a revision-valued
`since` on tables and columns. Meta-schema descriptions, packet-schema descriptions, validation
messages, and extension registry declarations also cite revision records.

Those references produce three problems:

1. A current rule is not self-contained when its only explanation of ownership or meaning points
   backward to a change record.
2. Repository procedure remains duplicated in the packet specification after R120 assigned it to
   the revision guide.
3. A packet can embed change provenance that describes this repository's editing history rather
   than the packet or logical standard it implements.

The third problem is not merely editorial. `derived_from` and `since` are permitted by the
registry meta-schema, generated into the incorporated registry, rendered for readers, checked by
repository tooling, and copied into packet registries. Removing them changes the accepted registry
document shape. The cleaned meta-schema therefore needs a distinct identity even though no
reference reader, writer, or validator uses either field to interpret packet data.

This proposal concerns revision history and misplaced maintenance material. It does not concern
the packet catalog's `resources[].derived_from`, which records data lineage between packet
resources and remains part of the packet contract.

## 2. Evidence

### 2.1 Baseline and overlap

The baseline is R120's incorporation commit. The quick verifier passes all 25 stages there, and
the stage checker reports no open proposal and one open draft. The authority draft is the only
overlapping lifecycle artifact. It is ordered after this work because it needs the cleaned source
population before it can construct its structural crosswalk and anchor bootstrap.

The current working tree also contains an uncommitted rebase and appraisal of that authority
draft. Those edits do not change the generated specification, registry, or measurements below.
They record this proposal as the draft's gating predecessor.

There is no configured remote, published Escapewheel release, or known external packet consumer.
That reduces migration cost but does not turn a registry-shape change into an editorial change.

### 2.2 Revision references in authored specification prose

This command counts specific revision tokens in the authoritative README and authored numbered
parts while excluding the generated combined rendering:

```bash
rg -o 'R[0-9]+' \
  escapewheel_poc_docs_v0.2/README.md \
  escapewheel_poc_docs_v0.2/[0-9][0-9]_*.md | wc -l
```

It reports 478 occurrences:

| source | occurrences |
|---|---:|
| specification README | 16 |
| Part 00 | 28 |
| Part 01 | 92 |
| Part 02 | 113 |
| Part 03 | 87 |
| Part 04 | 19 |
| Part 05 | 56 |
| Part 06 | 12 |
| Part 07 | 14 |
| Part 08 | 0 |
| Part 09 | 19 |
| Part 10 | 22 |

The README's generated status paragraph says that v0.2 is v0.1 with named revisions applied and
lists the accepted and withdrawn ranges. That is change history in the current entry point. In the
numbered parts, most references are trailing provenance citations, but some sentences describe
what a revision added, struck, withdrew, retained, or measured. A mechanical deletion of every
parenthesis would therefore damage some sentences or remove useful current rationale. The sweep
needs a semantic disposition: retain the present rule or rationale in self-contained prose, link
to a current owner, or remove historical narration that states no current rule.

The combined specification repeats these occurrences because it is generated from the README and
parts. It is excluded from the count and regenerated from cleaned inputs.

### 2.3 Revision references in machine-readable artifacts

The same token count over the current registry and related authored JSON reports 549 occurrences:

| artifact | occurrences | principal source |
|---|---:|---|
| `registry/logical_schemas.json` | 438 | 117 `derived_from.revisions` entries, 278 `since` values, and 43 descriptions or messages |
| `registry/registry.schema.json` | 34 | field descriptions and revision-shaped examples |
| `registry/manifest.schema.json` | 25 | descriptions citing the provenance of packet fields |
| `registry/sources.schema.json` | 3 | descriptions citing source-resolution decisions |
| `registry/rules.json` | 29 | two file-comment references and 27 references across 26 rule messages |
| four extension registry documents | 20 | 14 `since` values and six descriptions |

The generated `registry/tables.md`, vendored schema copies, and combined specification duplicate
these sources and are not additional owners.

The core registry's `derived_from.revisions` array names 117 accepted specification revisions.
Its `since` field appears on 23 tables and 255 columns. The extension registries add `since` to 14
columns. Part 02 §9.4 still reports 19 tables and 213 columns, showing that even a provenance count
copied into prose drifts as later declarations are added.

The registry meta-schema makes `derived_from` and `since` optional, but it sets
`additionalProperties: false` at the document, table, and column levels. Deleting those properties
from the meta-schema means an old registry that retains them no longer validates against the new
meta-schema. Regenerating the repository's current registries is straightforward; interpreting an
already embedded old registry under the changed meta-schema is the compatibility question.

### 2.4 No packet behavior consumes registry-build provenance

An exact search for dictionary access to `since` or registry-level `derived_from` in the reader,
writer, validator, and prototype finds no packet-behavior consumer. `registry/render.py` reads
`since` to print the human table, and `registry/check.py` checks revision-valued provenance against
the accepted history. `registry/build.py` produces both fields and has one additional construction
dependency: while applying the current Part 02 §8.2 name-column rule, it selects a generated column
with `c.get("since") == "R53 §2.3.1"`.

That construction dependency affects seven tables. In each one, the target is unambiguous from
current structure: it is the `<base>_name` column corresponding to the table's sole assigned
primary-key identifier that is not exported by a reference. The affected columns are
`analysis.array_assets.array_asset_name`, `core.array_assets.array_asset_name`,
`core.clocks.clock_name`, `core.devices.device_name`, `core.event_streams.event_stream_name`,
`core.media_assets.media_asset_name`, and `core.probes.probe_name`. The selected replacement derives
that exact name from the identifier declaration and does not inspect revision history.

The validator's shared registry-document checker explicitly excludes the revision ledger and
registry `derived_from` bookkeeping because they are facts about this repository's build rather
than a registry document an outside author needs. The writer's use of `derived_from` is different:
it writes resource lineage into the packet catalog and does not read the registry-build object.

No current evidence demonstrates that `since` supports compatibility selection, schema
negotiation, validation, migration, reader behavior, or writer behavior. Its observed uses are
historical display, repository consistency checks, and the one replaceable generator selector
described above.

### 2.5 Part 00 §10 mixes four subjects

Each current subsection needs a separate disposition:

| location | current subjects | preliminary disposition |
|---|---|---|
| Part 00 subsection 10.1 | current-owner authority, citation selection, registry and ledger dispositions | Preserve the one-owner meaning through R120 and the later authority revision; remove citation procedure and the claim that a revision can remain the current statement of record. |
| Part 00 subsection 10.2 | rationale citations, revision-valued `since`, the ledger, and revision-to-revision citations | Remove from the specification. Historical rationale belongs in accepted records; ledger and citation procedure belong under `revisions/`. |
| Part 00 subsection 10.3 | append-only editing and citation-checker behavior | Remove after R120; the revision guide is the current owner. |
| Part 00 subsection 10.4 | citation spelling, scope, checker behavior, and exceptions | Remove after R120; the revision guide is the current owner. |

Part 07 §2.3 currently points to Part 00's first citation subsection for comment and docstring
citation behavior. That is
developer-facing guidance, not packet conformance. Its current rule should move to developer
documentation or cite the revision guide from a current human document; it should not preserve a
normative Part 00 process section merely to retain its target.

R120 already repointed current process tooling and roadmap references. Accepted R113 and R120
remain immutable historical records; their citations are interpreted in their historical source
contexts and are not rewritten.

### 2.6 Compatibility surfaces are separable

Removing a prose provenance citation while preserving the sentence's current meaning changes no
packet. Removing revision text from a validation message changes reported prose but not its rule
identifier, severity, query, or set of offending rows. Removing `derived_from` and `since` changes
registry bytes and the registry meta-schema, but not any table declaration, key, reference,
vocabulary, or validation predicate.

Current packets can be regenerated with a cleaned embedded registry. A packet carrying an old
registry still contains the same logical declarations, but that document includes properties the
new meta-schema rejects. Reusing the existing schema identifier would make one URI denote two
incompatible schemas. The selected resolution gives the cleaned meta-schema the new `$id`
`https://escapewheel.org/schemas/registry/0.2.0`, advances the core registry's
`registry_version` to `0.2.0`, and treats regeneration as the migration for development packets.
The extension registries update their `$schema` URI but retain their extension-specific registry
versions because their logical declarations do not change.

The repository retains no `0.1.0` copy of the registry meta-schema. Git preserves the old schema,
and a development packet can remain mechanically readable where its embedded registry suffices,
but neither the current specification bundle nor the reference implementation promises validation
or migration of that unreleased document shape.

The project currently holds the core `registry_version` at `0.1.0` despite breaking declaration
changes, has no released packets, and already treats migration as regeneration. The new identity
does not promise support for the old development shape; it prevents an identifier from being
silently redefined while making the intentional development-time break explicit.

### 2.7 Current citations into sections that may be retired

The reverse-impact query over Part 00's section 10 and subsections 10.1–10.4 and Part 02 §9.4
reports 18 citations at the proposal working state. Six are this proposal's own evidence, eight
are immutable accepted history, and four are other live references: the authority draft's
dependency discussion, Part 07 §2.3's comment guidance, Part 00's second citation subsection
referring to `since`, and `revisions/repoint.py`'s `since`-stamp exemption.

The historical citations remain unchanged. The proposal disappears when promoted and contributes
no live destination. The four other live references each need an explicit disposition before a
structural draft retires a source heading. This population was measured with:

```bash
uv run --project escapewheel-writer python revisions/impact.py \
  --section 00:10 --section 00:10.1 --section 00:10.2 \
  --section 00:10.3 --section 00:10.4 --section 02:9.4
```

## 3. Desired outcome and constraints

A successful resolution leaves the current specification and every incorporated
machine-readable artifact understandable without the frozen proof of concept or revision archive.
Accepted revisions, the clause ledger, evidence manifests, and Git retain decision provenance.
Current owners retain only current meaning.

The resolution should:

- remove references to historical documents from the specification README and numbered parts;
- remove registry-build `derived_from` provenance from the registry document model;
- remove revision-valued `since` without replacement because no compatibility, migration, or
  selection behavior consumes it;
- assign the cleaned registry meta-schema
  `https://escapewheel.org/schemas/registry/0.2.0`, advance the core registry to `0.2.0`, update
  every registry document's `$schema`, retain no current `0.1.0` meta-schema copy, and regenerate
  development packets;
- replace the registry generator's one history-valued construction selector with the exact
  assigned-primary-key structure that identifies the same seven name columns;
- remove revision citations from emitted schema descriptions, rule messages, and extension
  registry declarations without weakening their current semantic content;
- remove repository-maintenance and citation-presentation rules from Part 00 now that R120 owns
  them;
- retire Part 00 §10 only after confirming that Part 00 §9 and Part 02 §1 already preserve its
  current-contract ownership meaning, without an interim duplicate before P1;
- preserve the packet catalog's resource-lineage `derived_from` unchanged;
- preserve every table, column, key, reference, vocabulary, rule query, severity, and packet
  interpretation except for the intentionally removed provenance fields and the explicitly changed
  registry identities and message text;
- compare the old and new registries after normalizing away those approved differences, so exact
  declaration equivalence is measured rather than inferred;
- remove the stale provisional `RELEASE.json` without treating the cleanup as publication or
  deciding the membership of a future release bundle;
- move `release.py` to `prototype/release-bundle/probe.py`, label it non-authoritative, and remove
  its ability to write a root `RELEASE.json`, while retaining its inventory and digest experiment
  for later publication work;
- state the meta-schema, embedded-registry, packet-regeneration, and identifier consequences; and
- leave the authority draft a stable, history-free source population from which to build its
  crosswalk and anchor bootstrap.

This proposal does not remove accepted revisions, change the ledger or evidence semantics decided
by R120, rewrite historical records, define final specification editions, or decide release-bundle
membership. Deleting the stale provisional `RELEASE.json` says only that no release snapshot is
current. P1 classifies candidate and released authority; P11 remains responsible for any future
manifest, its members, and publication tooling. This proposal also does not require implementation
comments, tests, or developer documents to forget useful historical
rationale. A separate ordinary cleanup can repoint a current source comment that cites a revision
as authority; P0.2 covers those strings only where they are emitted into a current specification
or machine-readable contract artifact.

Because retiring Part 00 §§10.1–10.4 and Part 02 §9.4 changes the specification structure, the
eventual draft is expected to use the structural change form. Its final appraisal will need an
exact crosswalk and a metadata-only anchor bootstrap for affected existing headings, following
R120. Meaning-preserving removal of a trailing provenance citation does not by itself move or
renumber its containing section.

## 4. Options and tradeoffs

### 4.1 Keep all current provenance

This avoids registry-byte and meta-schema compatibility changes. It leaves the specification
dependent backward on change records, preserves process duplication after R120, and makes the
authority draft build on sources known to have overlapping owners. It does not meet the one-way
model.

### 4.2 Clean prose but retain machine-readable provenance

This makes the numbered prose self-contained while keeping `derived_from` and `since` in packet
registries. It reduces the visible problem but gives JSON a different authority model from prose
solely because it is structured. No implementation currently uses the fields for compatibility,
and their revision identifiers are repository-local rather than standard or edition identifiers.

### 4.3 Remove all backward provenance without replacement

This is the selected direction. The accepted archive, ledger, evidence manifests, and Git keep
history; the specification and incorporated declarations keep the current contract. The registry
renderer loses its revision column, and repository checks stop comparing declaration stamps with
accepted records. Current registries and packets are regenerated. The cleaned meta-schema receives
a new `$id`, and the core registry version advances, so the compatibility break is explicit rather
than hidden behind an existing identifier. The one generator decision that currently inspects a
`since` stamp is restated in terms of the assigned primary-key declaration that gives the selected
name column its current meaning.

### 4.4 Replace `since` with an edition-valued field

An edition or logical-standard identifier could support a real compatibility or migration
question in a way a revision number cannot. No such behavior is currently specified, and the
authority and publication work has not yet defined immutable edition identity. Adding the field
now would guess that later model and block this cleanup on P1, while P1 itself depends on this
cleanup. The project can add an edition-valued field later when a consumer and semantics exist.

### 4.5 Split `since` into another proposal

The prose and `derived_from` cleanup could proceed while `since` is appraised independently. This
is appropriate if a real consumer or compatibility behavior is found. Without one, the split
would preserve the largest backward link, leave Part 02 §9.4 in force, and fail to give P1 a clean
source population. The current evidence favors keeping the decisions together but giving `since`
its own Decision clause and compatibility analysis in the eventual draft.

### 4.6 Retain provenance outside normative registry content

Generation could emit a separate, explicitly non-normative provenance report for maintainers.
That is compatible with the one-way model if it is not embedded in packets or incorporated by a
part. The ledger and Git already answer which accepted decision changed a declaration, so another
generated report needs a demonstrated maintenance use before it is added.

## 5. Impact sketch

| surface | expected effect |
|---|---|
| semantic prose | Affected editorially: remove 92 revision references from Part 01 while preserving every current concept meaning and obligation. No semantic concept changes. |
| logical prose, registry meta-schema, registry declarations, and declarative rules | Affected materially: remove Part 02's revision-provenance model, registry `derived_from`, table and column `since`, revision citations in descriptions and messages, and the associated build, check, and render logic. Preserve all declaration and predicate semantics. |
| physical profiles | Affected editorially: rewrite or remove 87 revision references in Part 03 without changing a format, codec, layout, or adapter protocol. Part 03 §9.3's retained-registry and same-version collision behavior remains unchanged and is reverified against the new current version. |
| packet catalog and other incorporated JSON Schemas | Packet catalog lineage remains unchanged. Part 04 §3 retains the same `registry_version` field, but current packet manifests carry `0.2.0`. Schema descriptions lose historical citations. The registry meta-schema gets `$id` `https://escapewheel.org/schemas/registry/0.2.0`; registry documents update `$schema`; no current `0.1.0` meta-schema copy is retained. |
| validation and import | Part 05 loses 56 historical references without changing procedure or verdicts. Tier 2 message strings lose revision citations; rule IDs, levels, SQL, and findings remain unchanged. |
| extension registries | Affected: remove 14 `since` fields and six description citations from three of four packaged extensions, regenerate or validate all four under the cleaned meta-schema, and preserve their tables, columns, references, and rules. |
| reader, writer, validator, adapters, and code generation | Reader and validator algorithms and adapter source contracts are unchanged. Writer output, embedded-registry identity, manifest `registry_version`, reader-visible metadata, registry generation and rendering, structural checks, vendored schemas, and exact message assertions change. Replace the generator's history-valued name-column selector with the equivalent assigned-primary-key derivation. Current implementation citations outside emitted contract artifacts are out of scope. |
| existing packets and migration or regeneration | Existing packet rows, arrays, media, and catalog meaning are unchanged. The core registry advances to `0.2.0`, and packets used as current conformance examples are regenerated with it. Old development packets are not migrated or promised current conformance. Extension registry versions remain unchanged because their declarations do not change. |
| conformance fixtures and implementation tests | Regenerate fixtures that embed the registry. Classify every hard-coded `0.1.0`: update values that denote the current core registry while retaining values used only to exercise generic version transitions. Update reader, writer, validator, prototype, and conformance assertions accordingly. Compare the pre-change and post-change registries after normalizing away `derived_from`, `since`, the approved identities, and revision-only message or description text; all other declarations and rule predicates must be byte-equivalent. Add a negative repository check for revision references in current specification and incorporated artifacts. Update message snapshots if any assert the removed suffixes. Packet pass/fail expectations remain unchanged. |
| revision lifecycle, ledger, evidence, and process tooling | R120's one-way ledger and immutable history remain unchanged. The structural draft needs a crosswalk and anchor bootstrap. Repository checks that require `derived_from` or revision-shaped `since` are removed or replaced with checks that current artifacts contain no forbidden historical reference. |
| generated publications and developer documentation | Regenerate `registry/tables.md`, the registry README facts, vendored schema copies, and the combined specification. Stop emitting revision status into the specification README. Update its §§5.1–5.2 and version-specific implementation guidance for core registry `0.2.0`. Update current authority and contribution documentation where it describes `derived_from` or `since`. Delete the stale provisional `RELEASE.json`; move the non-writing digest experiment to `prototype/release-bundle/probe.py`; leave authority classification to P1 and release-manifest design to P11. |

## 6. Resolved design questions

### 6.1 Registry identity and development compatibility

The cleaned registry meta-schema receives `$id`
`https://escapewheel.org/schemas/registry/0.2.0`, and the core registry's `registry_version`
advances to `0.2.0`. Every registry document updates `$schema`. Extension registries retain their
own current registry versions because this change removes repository provenance without changing
their logical declarations. Current development packets and fixtures are regenerated; the project
promises no migration or current conformance for unreleased packets carrying the old shape. The
repository retains no current `0.1.0` meta-schema copy.

### 6.2 No replacement for revision-valued `since`

No repository behavior uses `since` for compatibility, migration, or packet selection, and the
project has no known external consumer. One generator branch uses the field as a construction-time
selector. P0.2 replaces that use by deriving the exact `<base>_name` target from the table's sole
non-exported assigned primary-key identifier, then removes `since` without replacement. If a future
behavior needs standard-edition identity, that field and its semantics require a separate proposal
after edition identity exists.

### 6.3 Retirement of Part 00 subsection 10.1

No temporary normative replacement is needed. Part 00 §9 states which parts bind, Part 02 §1
incorporates the exact registry declarations, and `revisions/CONTRIBUTING.md` owns repository-change
and citation procedure under R120. The statement that a revision can remain the current statement
of record conflicts with that model. Part 00 §§10.1–10.4 can therefore be retired in full; P1 can
later make artifact roles more explicit without preserving an interim duplicate.

### 6.4 Specification README status

The specification README retains a short, history-free statement that it is the current v0.2
proof-of-principle packet specification. It loses accepted and withdrawn revision ranges, open
proposal and draft counts, the derivation from v0.1, and the explanation of revision citations.
The term *candidate* is not introduced before P1 defines it. Current-work counts remain in process
or repository-status documents rather than the specification entry point.

### 6.5 Provisional release snapshot

P0.2 deletes the tracked `RELEASE.json` and does not regenerate it. The file is already a stale
prototype, and producing a new snapshot would imply a publication state that has not been defined.
The useful inventory and digest experiment moves from root `release.py` to
`prototype/release-bundle/probe.py`, describes itself as non-authoritative, and loses its option to
write `RELEASE.json`. This disposition does not decide whether a later release has a manifest or
what it contains. P1 classifies candidate and released authority; P11 owns final release-manifest
and publication-tooling design.

### 6.6 Implementation and developer-document citations

Implementations and developer documentation are non-normative. If either expresses behavior that
no current specification owner states, that is a missing specification requirement rather than a
reason to retain a historical citation. Acceptance evidence checks that the clause ledger still
resolves every accepted decision, reviews every historical citation emitted into a specification
or contract artifact, and disposes the known Part 07 §2.3 pointer. It does not require an
indiscriminate purge of useful historical comments. Any genuinely missing current rule is added to
its specification owner or separated as a substantive proposal.

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
- [x] The proposal has explicit approval to advance to a revision draft.

## 8. Promotion appraisal — 2026-09-19

**Disposition: revise before promotion.** The problem, owner, scope boundary, preferred design, and
compatibility policy are settled. Fresh measurements reproduce 478 revision tokens in authored
specification prose, 549 in the measured machine-readable sources, and 18 reverse citations into
the six headings proposed for retirement. The quick verifier passes all 25 stages, the lifecycle
checker reports one structurally complete proposal and one draft, the citation checker reports
zero unresolved citations, and all 13 process tests pass.

Three bounded revisions remain before the direction can be carried into exact draft clauses and an
incorporation plan:

1. **Account for the generator's operational `since` dependency.** Section 2.4 currently says the
   observed repository uses are display and consistency checks. `registry/build.py` also uses
   `c.get("since") == "R53 §2.3.1"` to select the generated assigned-identifier name column while
   applying the current Part 02 §8.2 rule. This does not justify retaining `since` in registry
   documents, but the proposal must record the dependency and select a replacement that derives the
   target from current structure rather than revision history. The incorporation evidence must show
   that removing the selector and emitted provenance preserves all declarations other than the
   fields intentionally removed.
2. **Complete the `0.2.0` consequence inventory.** Advancing the core registry changes writer
   output, embedded-registry identity, manifest `registry_version`, reader-visible metadata,
   fixtures, vendored schemas, and hard-coded implementation tests. The impact row saying packet
   behavior is unchanged is therefore too broad. The proposal must name the current version table
   and hold language in the specification README, Part 02 §§9.1–9.2, the Part 04 registry-version
   field, Part 03 §9.3's retained-registry behavior, and the applicable implementation and
   contributor documentation. It must also say whether the repository retains an old `0.1.0`
   meta-schema copy; the selected no-compatibility policy suggests that it does not.
3. **Finish the provisional-release disposition.** Deleting `RELEASE.json` is coherent, but the
   roadmap's P11 text still instructs later work to reconcile the tracked file, and `release.py`
   still describes and can recreate its output as a release. The proposal must state how that
   script is labelled as non-authoritative prototype tooling until P1/P11 revises or replaces it,
   and the roadmap must describe the deleted snapshot as history rather than a future tracked
   input. The authority draft's baseline observation can remain until its required post-P0.2
   rebase.

The remaining lifecycle gates are mechanical and authorial. This proposal is still untracked, so
`git ls-files --error-unmatch` fails; the exact revised proposal and appraisal must be committed
before promotion. A later promotion request must explicitly authorize advancing that committed
state to a draft.

## 9. Response to the promotion appraisal — 2026-09-19

All three substantive blockers in §8 have been resolved in the proposal:

1. Section 2.4 inventories the generator's one operational `since` selector, names all seven
   affected columns, and replaces it with a derivation from the sole non-exported assigned
   primary-key identifier. Sections 3, 4.3, 5, and 6.2 carry that decision and require declaration
   equivalence evidence.
2. The affected-artifact header, compatibility analysis, constraints, impact table, and §6.1 now
   cover the new meta-schema identity, core registry version, absence of a retained `0.1.0`
   meta-schema, packet manifests, implementation surfaces, version-specific tests and documents,
   regenerated development packets, and unchanged extension versions.
3. Sections 3, 5, and 6.5 delete the stale root snapshot, preserve the non-authoritative digest
   experiment as a non-writing prototype, distinguish P1 authority classification from P11
   publication design, and require the roadmap to stop treating the snapshot as a future tracked
   input.

The proposal is ready for a fresh promotion appraisal. Its two final lifecycle criteria remain
unchecked: the exact post-appraisal state has not been committed, and no request has authorized
promotion of that committed state.

## 10. Promotion re-appraisal — 2026-09-19

**Disposition: substantively ready for promotion; checkpoint and authorization remain.** The R120
incorporation commit remains the relevant baseline. The generated v0.2 sources and machine-readable
artifacts have not changed, there is still no configured remote or known external consumer, and the
authority draft remains the only overlapping lifecycle artifact, ordered after P0.2.

Fresh measurements reproduce 478 revision tokens in authored specification prose, 549 in the
measured machine-readable sources, and 18 reverse citations into the six headings proposed for
retirement. The 18 divide exactly as §2.7 records: six in this proposal, eight in immutable accepted
history, and four other live references with stated dispositions.

The three prior blockers now pass:

1. The generator dependency is reproduced, bounded to one selector and seven columns, and replaced
   by an implementable structural derivation. Normalized pre-change/post-change registry comparison
   will detect any unintended declaration or predicate change.
2. The `0.2.0` identity decision now reaches every owner and implementation surface that observes
   the current registry version. It distinguishes changed packet bytes and reader-visible metadata
   from unchanged reader, validator, amendment, catalog-field, and adapter semantics. Regeneration,
   non-retention of the old meta-schema, and the lack of a compatibility promise are explicit.
3. The provisional release artifacts have one bounded disposition: delete the stale root snapshot,
   retain the useful code only as a non-writing and non-authoritative prototype, let P1 classify
   authority states, and leave manifest membership and publication tooling to P11. The roadmap now
   describes that sequence consistently; the authority draft will update its baseline observation
   during its required post-P0.2 rebase.

The proposal is coherent as one structural specification change. It does not need to split the
prose cleanup, registry-provenance removal, version change, or provisional-release cleanup because
each is a direct consequence of making current owners independent of revision history. The draft
can express the decisions as separate normative clauses and give the retired headings an exact
crosswalk after the required anchor bootstrap.

No substantive promotion blocker remains. At the time of this re-appraisal, the exact proposal and
appraisal were not yet tracked in `HEAD`, and the request authorized appraisal rather than stage
transition. Both procedural gates are closed in §11 before promotion.

## 11. Promotion authorization and checkpoint — 2026-09-19

The user explicitly authorized completing the procedural gates and promoting this proposal. The
checkpoint commit containing this section preserves the exact proposal, response, re-appraisal,
coordination updates, generated open-stage counts, and dependent authority-draft state before any
stage transition. After that commit, both required mechanical checks resolve this path from `HEAD`
with no byte difference. The following promotion commit may therefore carry this design into a
revision draft and delete the proposal-stage file without losing the reviewed state.
