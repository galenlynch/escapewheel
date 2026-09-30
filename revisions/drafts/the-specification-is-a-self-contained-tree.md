# The specification is a self-contained tree

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `a110521e9b61e9f62e12d66506528ad6fa1539fd` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§2.1, 2.3 and 2.4; Part 02 §§1, 4, 9.3 and 9.5; Part 03 §§1 and 6.5; Part 04 §§1 and 5.5; Part 05 §§1 and 3.1; Part 08 §§2 and 3; Part 10 §§1 and 5; Part 11 §1; Part 12 §§1 and 7; the description of `resources.schema.json`; the specification README |
| **Depends on** | R122 §3.1 (the candidate's composition, which this locates); R122 §3.3 (internal consistency, whose checks this places); R111 §3.3 (a requirement binds a defined actor, which the checker makes true of fifteen uses) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 00 §2.1 makes the specification candidate the numbered parts together with every artifact a
numbered part expressly incorporates. Nothing places those members together, and nothing keeps the
candidate from depending on the software that implements it. The parts sit in
`escapewheel_poc_docs_v0.2/` beside the tools that check and render them, and the fourteen
incorporated artifacts sit in `registry/` among 81 files of other kinds. Producing and checking the
candidate runs the reference implementation: the reference writer writes Part 08's example regions,
and code in the reference reader and validator decides four of the consistency conditions
Part 00 §2.3 governs. The candidate therefore cannot be regenerated, checked or handed to another
implementer apart from the packages it governs, and a release has no directory to be frozen from.

The specification also binds an actor it does not define. Parts 02, 03 and 04 order the phases of a
checker, and Part 00 §2.4 names four actors, none of them a checker, while requiring every
requirement to bind one of them or state a property of an artifact.

This revision makes the specification one directory, the specification's tree. The tree holds
every member and names files only within itself, and its own tools produce its generated content
and decide its consistency. Part 00 §2.4 gains the checker, of which a validator is one kind. No
packet, artifact identifier or registry byte changes.

The change is structural because it revises Part 00 §§2.1, 2.3 and 2.4 in place, rewrites the path
in every incorporation statement, and turns Part 08's generated regions into committed text.
Appended sections would leave each part naming `registry/` paths that a separated tree cannot
resolve, and Part 00 §2.4 counting four actors beside a section defining a fifth.

### 1.1 Structural crosswalk

Every affected section already carries a canonical anchor, so no bootstrap commit precedes this
draft and `Based on` is the commit of the proposal it was promoted from. Every part's file moves
into the tree with its number, order, headings and anchors unchanged. No section moves, splits,
merges or retires. The rows are the sections whose text changes.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 00 §2.1, the candidate's members | extend in place | same section | the members lie in the specification's tree, incorporated artifacts in its `artifacts/`; a part names files only within the tree; a release draws its members from it | §3.1; §3.2 |
| Part 00 §2.3, internal consistency | extend in place | same section | generated content is derived within the tree by its tools; the tree decides each checked projection and explicit consistency condition | §3.3; §3.4 |
| Part 00 §2.4, the actors | extend in place | same section | a fifth actor, the checker, of which a validator is one kind; the roster's counts follow | §3.5 |
| Part 02 §1, the incorporated artifacts and the rendered listing | revise in place | same section | paths from the tree's root | none (form required by §3.2) |
| Part 02 §4, the registry checker | revise in place | same section | the actor is a checker | §3.5 |
| Part 02 §9.3, the rendered listing | revise in place | same section | path from the tree's root | none (form required by §3.2) |
| Part 02 §9.5, the result schema | revise in place | same section | path from the tree's root | none (form required by §3.2) |
| Part 03 §1, the schema and descriptor | revise in place | same section | paths from the tree's root | none (form required by §3.2) |
| Part 03 §6.5, the physical checker | revise in place | same section | the actor is a validator | §3.5 |
| Part 04 §§1 and 5.5, the manifest and sources schemas | revise in place | same sections | paths from the tree's root | none (form required by §3.2) |
| Part 05 §1, the actors it binds | revise in place | same section | names the four of five actors it binds | none |
| Part 05 §3.1, the recipe schema | revise in place | same section | path from the tree's root | none (form required by §3.2) |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | replace in place | same sections | committed text, which the reference writer is checked to reproduce | none (form required by §3.3) |
| Part 10 §§1 and 5, the conformance probes | revise in place | same sections | the probes are named without a path | none (form required by §3.2) |
| Part 11 §1, the rule-language schema and descriptor | revise in place | same section | paths from the tree's root | none (form required by §3.2) |
| Part 12 §§1 and 7, the resources and adapter schemas | revise in place | same sections | paths from the tree's root | none (form required by §3.2) |
| specification README, the actor summary | revise in place | Part 00 §2.4, as now | counts five actors | none |

## 2. Background

The counts were taken from the tracked files at the baseline commit. Paths were found by searching
the parts, the specification README and style guide for backticked spans and link targets, and by
extracting every string from each tracked JSON file under `registry/`.

### 2.1 The members sit among files of other kinds

Nine sections in seven parts incorporate the fourteen artifacts, each by a path under `registry/`:
Part 02 §§1 and 9.5, Part 03 §1, Part 04 §§1 and 5.5, Part 05 §3.1, Part 11 §1 and Part 12 §§1
and 7. `registry/` holds 95 tracked files. Besides the fourteen, it holds the 49 TOML files the core
registry is assembled from, 20 files of four extension registries the specification does not
incorporate, 4 example documents, 5 scripts, and `README.md`, `tables.md` and `.gitignore`. A reader
handed `registry/` cannot tell which files carry normative force.

Part 02 §§1 and 9.3 cite `registry/tables.md`, the generated informative listing. Part 10 §1 cites
`conformance/`, and Part 10 §5 cites `conformance/zarr-probe/` as the source of its Zarr
measurements; both lie outside any tree the specification could be given. `resources.schema.json`
is the only incorporated artifact whose text names a repository path: its root description names
`registry/build.py`. Every link between parts is relative to the specification directory.

### 2.2 Producing and checking the candidate runs the reference implementation

Four of the five writers of generated content need only the standard library: `registry/assemble.py`
and `registry/render.py` for `logical_schemas.json` and `tables.md`, `registry/build.py` for
`resources.schema.json` and the generated regions of Parts 03 and 04, `columns.py` for Part 06 §4's
column table, and `combine.py` for the combined rendering. The fifth, `integration/example.py`,
writes Part 08 §§2–3 by building a packet with the reference writer. `registry/build.py` also writes
thirteen vendored copies into the source trees of the reader, validator and writer, so the
specification's build knows each consumer by path. `headings.py` imports the revision tooling's
`impact.py` to list the citers of a changed heading.

`registry/check.py` makes 41 named checks, and 34 need only the standard library or `jsonschema`.
The other seven reach outside the specification:

- the complete result of Part 02 §9.4, over the core registry and each of the four extensions,
  imports the reference validator;
- the physical profile's check imports the reference reader;
- the check of Part 03 §5.4's consistency condition imports the reference reader;
- the Tier 2 static and execution check imports the validator's rule checker and DuckDB;
- the table-set check runs a script under `conformance/spec-sweep/` that parses the frozen v0.1
  Part 02;
- the history-cleanup check runs a script under `conformance/history-cleanup/` against Git
  history; and
- one check validates a document under `prototype/registry-codegen/`.

Four of the seven decide consistency conditions under Part 00 §2.3: the complete result of
Part 02 §9.4 over the core registry, Part 03 §1's generic cross-member checker, Part 03 §5.4's
condition, and Part 11's static contract over the core registry's rules. The reader's profile
checker and Part 03 §5.4's condition are about 90 lines needing only `jsonschema`. The validator's
registry-document checker is 1,859 lines needing `jsonschema`, `sqlglot` and `ucumvert`, and the
rule checker it calls is 394 lines needing `sqlglot`. Their tests are 1,152 lines.

### 2.3 The registry checkers check no packet

Part 02 §9.4 defines registry-document conformance as a contract of its own, whose result
Part 02 §9.5 serialises, and a validator applies it to the registries a packet binds.
`registry_document.py` imports only `rule_language.py` and those three libraries. The validator's
manifest, generation and validation modules import it, and it imports none of them. It does import
its rule checker by the validator's package name and locates its artifacts beside its own file,
where Part 03 §1's checker takes its artifacts as arguments.

The Tier 2 check also executes each rule in DuckDB against empty tables built from the registry.
Part 11 defines an engine-neutral language, so that execution shows that one engine accepts the
rules and decides no condition of Part 00 §2.3.

### 2.4 Six parts bind a checker that Part 00 §2.4 does not define

"Checker" appears 26 times in six parts, in two senses.

- Eleven times, in Parts 01, 02, 03, 05 and 06, it labels an unchecked requirement: "No checker
  verifies this" follows a writer obligation that no validator decides either, so the label reads a
  checker as including a validator.
- Fifteen times, in Parts 02, 03 and 04, it binds or describes an actor. Part 02 §9.4 orders a
  checker's phases over a registry document, and Part 02 §9.2 forbids it to dereference an
  identifier. Part 03 §1 requires the generic cross-member checker to refuse a misplaced
  `overriding_orders`. Part 04 §10 orders a checker's phases over a manifest, and Part 03 §4 and
  Part 04 §4.3 name findings it reports in them. Part 02 §4 calls it a registry checker, and
  Part 03 §6.5 calls a physical checker what checks a packet's arrays, which a validator does.

Part 00 §2.4 defines a validator as deciding whether a packet conforms, and a registry document or
descriptor checked alone is no packet. The manifest phases run inside packet validation, and the
registry-document phases run there, over each registry a packet binds, and over a registry
document alone.

### 2.5 The old paths are cited widely, but frozen records need not follow them

172 tracked files name `registry/` or `escapewheel_poc_docs_v0.2` at the start of a path, excluding
the frozen v0.1 documents and lock files. 107 are accepted revisions or their evidence manifests.
The other 65 are current files: revision tooling and its data (13, this draft among them), the
writer (9), the registry directory (8), the specification directory (8), the validator (5),
`conformance/` (5), the reader, `escapewheel-aind` and `prototype/` (2 each), `integration/` (1),
and the root documents and scripts (10). More scripts compute the paths than name them, among them
`verify.py`, `facts.py`, `check_citations.py`, `ledger.py`, `impact.py`, `repoint.py`, and the
package test suites through `parents[2] / "registry"`. `revisions/registry-targets.toml` locates
109 accepted clauses in 292 registry paths, and `ledger.py` refuses a target outside `registry/`.

The accepted records need no edit. The revision guide's citation-context rule makes a committed
accepted revision an immutable record that need not resolve against the current working
specification, `check_citations.py` checks no accepted record's links, and `evidence.py` resolves
only the manifest of a revision not yet committed. Two conformance probes, `registry-contract` and
`history-cleanup`, read one path both at a past commit and in the working tree. The field test's
recipes name the core registry and all four extensions by absolute path into `registry/`. No
packet records a repository path: a packet embeds the registries it binds (Part 04 §8), and every
`$id` is a URL.

### 2.6 Other formats and the alternatives

These were read from each project's repository or documentation on 2026-09-30.

- NWB keeps its schema, format documentation and extension schema in
  `NeurodataWithoutBorders/nwb-schema`, which PyNWB pins as a Git submodule. The schema
  repository's continuous integration checks the schema with an implementation: its
  `validate_schema.yml` installs HDMF from Git and runs `validate_hdmf_spec`.
- Parquet keeps its prose and `parquet.thrift` in `apache/parquet-format`, tagged separately from
  parquet-java. parquet-java took the Thrift file from the released format artifact until September
  2026, then vendored a copy with a sidecar recording the source commit, because a released
  dependency blocked builds against unreleased format changes (apache/parquet-java pull request
  3709). Arrow C++ vendors its own copy and synchronises it by hand.
- OpenAPI and JSON Schema each keep the specification in its own repository and publish schemas at
  versioned URLs. JSON Schema keeps its conformance suite in a third repository.
- GeoParquet keeps its specification, JSON Schema, examples and test data in
  `opengeospatial/geoparquet`. Its `scripts/` directory declares and locks its own Python
  environment, in which it tests the JSON Schema and generates and tests the example file.
- Iceberg keeps its specification inside the Java implementation's repository, unversioned. A 2024
  Apache thread wanted the Variant encoding's specification moved out of Spark so that engines would
  not depend on another engine's modules, and it later moved into `parquet-format`.

Where an implementation vendors a copy that nothing generates or checks, the copy drifts, as Arrow
C++'s Thrift file and `openapi-spec-validator`'s schemas have.

The specification could stay where it is, move to its own repository now, or become one directory
in this repository. Staying leaves nothing to freeze a release from. A repository of its own makes
every change to the contract and its implementation a coordinated change to two repositories while
the contract still changes with most revisions. One directory keeps a change in one commit, and
`git subtree split` can later make it a repository with its history.

A part could name an artifact by its `$id` rather than by a path, but the core registry has no
`$id`, and an identifier names a version rather than a file a reader can open. A published
specification package is blocked while the specification is unreleased, since a released package
depends only on released packages, and could not be built against before release, which is why
parquet-java stopped consuming one.

The validator's two checks could stay outside the tree, run from `conformance/` against the
reference validator, as NWB checks its schema with HDMF. A separated tree could then not check its
own release, because its consistency check would import a package that copies from the tree.

Part 00 §2.4 could keep four actors, but the fifteen uses would still bind an actor nobody is
defined as. A checker could be defined as a validator acting on one document, but a validator
decides a packet, and the tree's tools, which check the candidate's own registry and descriptor,
would then act as validators.

## 3. Decision

The subsections state what the specification's tree holds, how a part names a file, how the tree
produces its generated content and decides its consistency, and the checker.

### 3.1 The specification's tree holds every member

The **specification's tree** is the directory holding the specification README. The numbered parts
MUST lie within it, and every artifact a numbered part incorporates MUST lie in its `artifacts/`
directory, which MUST hold no other file.

A specification release draws its members from the tree. Which of the tree's other files a release
includes, and the format of its publication record, remain unselected, as Part 00 §2.1 leaves them.

### 3.2 A part names only files within the tree

Where a numbered part or an incorporated artifact names a file by path, other than in a link from
one part to another, the path MUST be relative to the tree's root and MUST name a file within the
tree. A numbered part MAY name evidence outside the tree, such as a conformance probe, by what it
is, and MUST NOT give its path.

### 3.3 The tree produces its generated content alone

Each generated file within the tree, and each generated region of a file within it, MUST be derived
only from files within the tree by a tool within the tree. A tool within the tree MUST import only
its language's standard library, files within the tree, and the libraries the tree declares, at the
versions the tree locks.

### 3.4 The tree decides its own consistency

The specification's tree MUST contain a tool deciding each mechanically checked projection within
the tree and each explicit consistency condition that Part 00 §2.3 admits between the candidate's
owners. The conditions include:

- the core registry's conformance under Part 02 §9.4;
- the physical-profile descriptor's conformance under Part 03 §1;
- the static conformance of the core registry's rules under Part 11; and
- Part 03 §5.4's conditions between the descriptor and the core registry.

### 3.5 A checker decides whether a document conforms

A **checker** decides whether a document conforms to the contract governing it, and reports its
findings. The documents are a registry document under Part 02 §9.4, a physical-profile descriptor
under Part 03 §1, and a manifest under Part 04 §10. A validator is the checker of a packet: it
checks each such document a packet carries as a checker does, and decides the rest of the packet,
so a requirement on a checker binds a validator checking one of those documents. Part 00 §2.4's
actors are therefore five: a writer, a reader, a checker, a validator and a consumer.

Part 02 §4's registry checker is a checker. What Part 03 §6.5 calls a physical checker resolves a
packet's axes table from its dense-array declaration, and is a validator.

## 4. What this does not change

The tree's tools are not members. A tool deciding a condition of §3.4 owns nothing: the prose and
the incorporated artifacts own the condition (Part 00 §2.2), and a tool disagreeing with them is a
defect in the tool. An extension registry is not incorporated (Part 09), so where one sits carries
no normative force.

## 5. Consequence

Every existing packet conforms unchanged, and none is rebuilt. No packet records a repository path,
no artifact's `$id` or shape changes, and no registry's identity or bytes change.
`resources.schema.json`'s description stops naming the script that derives it, which changes its
bytes but not its `$id` or shape. A second implementer handed the tree receives the whole contract
and can establish that it is consistent, and the only software it holds is the tools that produce
and check it.

Incorporation carries out one large mechanical move before the field test. The tree is `spec/`,
holding the README and style guide, `parts/`, `artifacts/`, `source/core/` for the core registry's
TOML, `informative/` for the rendered listing, the combined rendering and the example documents,
`conformance/` for the corpus and its expected findings, and `tools/` with the environment they run
in. The rest of the repository depends on `spec/`, and `spec/` depends on none of it:

- the reader, validator, writer and `escapewheel-aind` go under `packages/`; each package's build
  copies the artifacts and checkers it uses from `spec/`, and each package checks that its copies
  agree;
- the validator's registry-document and rule checkers, with their tests, move into `spec/tools/`,
  stop importing by the validator's package name and stop locating their artifacts beside their own
  file, so that a copy can match its source byte for byte; the reader's descriptor checker and
  Part 03 §5.4's condition move likewise;
- `spec/tools/` declares and locks `jsonschema`, `sqlglot`, `ucumvert` and PyArrow, and each package
  copying a checker admits the locked version of each library it imports;
- `aind_opto` and `aind_unit_qc` join `escapewheel-aind`, `dynamic_foraging` and `vr_foraging` go
  under `extensions/`, and each extension's registry is checked where it sits by the tree's
  registry-document checker;
- Part 08's example regions become committed text, and `integration/` checks that the reference
  writer reproduces them;
- executing the Tier 2 rules in DuckDB, and each check reading Git history, a prototype or the
  frozen v0.1 documents, move to `conformance/`, whose runner opens the tree's corpus with the
  reader and validates it with the validator;
- the frozen v0.1 documents, the root audit documents, `inventory/` and `prototype/` go under
  `history/`; and
- `revisions/` stays the change process outside the tree; the heading tool reports changed
  headings and the revision tooling finds their citers.

The 65 current files naming the old paths, and the scripts computing them, are repointed.
`registry-targets.toml`'s 292 paths are repointed, and `ledger.py`'s containment check follows
them. The two conformance probes of §2.5 take a separate path for the past commit. The field-test
recipes change their registry and extension paths. The links in accepted records stop resolving in
the current tree, which the citation-context rule already permits. R111 §3.3's ledger note, which
lists the roster, gains the checker.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 names no file, and its three unchecked labels keep their meaning. | None required. |
| logical prose and registry | Part 02 §§1 and 9.5 cite their artifacts under `artifacts/`, and §§1 and 9.3 cite the rendered listing under `informative/`. Part 02 §4's registry checker becomes a checker. No declaration, identity or byte of the core registry changes. | The tree's path and consistency checks; `evidence/R<N>.json` names the anchors. |
| physical profiles | Part 03 §1 cites its schema and descriptor under `artifacts/`, and Part 03 §6.5's physical checker becomes a validator. Neither artifact changes. The tree's tools write Part 03's generated regions. | The tree's regeneration and consistency checks. |
| packet manifest and JSON Schemas | Part 04 §§1 and 5.5, Part 05 §3.1 and Part 12 §§1 and 7 cite their schemas under `artifacts/`. `resources.schema.json`'s description names no script. No schema's `$id` or member changes. | The tree's path check; the package suites against their regenerated copies. |
| validation and import | Part 00 §2.4 gains the checker, of which a validator is one kind, and Part 05 §1 names the four actors it binds. No packet obligation changes: each requirement on a checker already binds the validator performing it. | `evidence/R<N>.json` names the anchors. |
| extensions | Unchanged in meaning and content. The four extension registries leave the tree, and Part 09 names no file. | Each extension's registry checked where it sits. |
| reader, writer, validator, adapters | Each package's build copies the artifacts and checkers it uses from the tree and checks its copies. The reader copies the descriptor checker and Part 03 §5.4's condition, and the validator the registry-document and rule checkers. The writer's `init` template and README name the new core registry path. No runtime behavior changes, and adapters are unchanged. | The copy-agreement checks; the package suites. |
| conformance fixtures and tests | The corpus and its expected findings move into the tree, whose builder already reads only the specification's artifacts; the runner stays in `conformance/`. The complete-result and Tier 2 static checks run from the tree's tools, and Tier 2 execution moves to `conformance/`. Part 08's example becomes a check in `integration/`. The package suites locate the registry at its new path. | §6's cases; `fixtures/corpus.py` at its new path. |
| revision process and tooling | The paths in `check_citations.py`, `ledger.py`, `impact.py`, `repoint.py`, `evidence.py`, `registry-targets.toml` and the verifier move, and R111 §3.3's note gains the checker. The heading tool stops importing the revision tooling. Accepted records and their evidence are unedited. | `ledger.py`, `evidence.py`, `check_citations.py` and `verify.py`. |
| generated publications and developer documentation | The combined rendering and the heading index are regenerated within the tree. The specification README states what the tree holds and counts five actors. The root README, CONTRIBUTING, the agent instructions and the package guides describe the new layout and commands. | `verify.py`. |

## 6. Conformance and implementation evidence

§§3.1 and 3.2 are `applied` at Part 00 §2.1, §§3.3 and 3.4 at Part 00 §2.3, and §3.5 at
Part 00 §2.4, Part 02 §4 and Part 03 §6.5. Each is placed by canonical anchor.

The positive case is the tree alone: a copy of `spec/` in an empty directory, given only the
environment the tree locks, regenerates every generated file and region byte for byte and passes
every check of §3.4.

These cases distinguish the new rules from the current ones:

- a part or incorporated artifact naming a path under `registry/`, or any path outside the tree,
  fails the tree's path check, and an informative part naming `conformance/` by path fails it too;
- a file in `artifacts/` that no part incorporates fails, as does an incorporated artifact outside
  `artifacts/`;
- a tool within the tree importing a package of the repository, such as the validator, fails the
  tree's import check, and one importing a library the tree does not declare fails it too;
- each check of §3.4 refuses a seeded violation: a core registry breaking an invariant of
  Part 02 §9.4, a descriptor failing Part 03 §1's checker, a rule outside Part 11's profile, and an
  override failing Part 03 §5.4, carried by the tests that move with the checkers;
- a package's copy of a tree checker that differs from its source fails that package's agreement
  check; and
- an edit to Part 08's committed regions that the reference writer does not reproduce fails
  `integration/`.

No mechanical case covers §3.5. The incorporation review reads all 26 uses of "checker" against the
roster, and `evidence/R<N>.json` names the three anchors that carry it.
