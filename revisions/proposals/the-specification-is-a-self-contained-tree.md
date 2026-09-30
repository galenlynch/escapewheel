# The specification is a self-contained tree

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-30 |
| **Based on** | `2d2fbe8dba9406b6fcd331e4c5487bda05ecd6b7` |
| **Decision domain** | specification |
| **Affects** | Part 00 §2.1's composition of the specification candidate and of a release; the incorporation statements of Part 02 §§1 and 9.5, Part 03 §1, Part 04 §§1 and 5.5, Part 05 §3.1, Part 11 §1 and Part 12 §§1 and 7; Part 02 §§1 and 9.3's citations of the rendered registry listing; Part 08 §§2–3's generated regions; Part 10 §§1 and 5's citations of conformance probes; the specification README and style guide |

## 1. Problem

Part 00 §2.1 makes the specification candidate the numbered parts together with every artifact a
numbered part expressly incorporates. Nothing places those members together, and nothing keeps the
candidate from depending on the software that implements it.

The numbered parts sit in `escapewheel_poc_docs_v0.2/`, a directory whose name fixes one version,
beside the tools that check and render them. The fourteen incorporated artifacts sit in
`registry/`, among files of three other kinds: the TOML the core registry is assembled from, the
registries of four extensions the specification does not incorporate, and the scripts that build,
vendor and check all of them. A reader handed `registry/` cannot tell from the tree which files
carry normative force.

Producing and checking the candidate also runs the reference implementation. Part 08's example
regions are written by building a packet with the reference writer, and the registry checks import
the reference validator and reader. The candidate therefore cannot be regenerated, checked or handed
to another implementer apart from the packages it is meant to govern, and a release frozen from
this tree has no directory it could be frozen from.

## 2. Evidence

The inventories were taken from the tracked files at the baseline commit. Paths were found by
searching the parts, the specification README and style guide for backticked spans and link
targets, and by extracting every string, including every `description` and `title`, from each
tracked JSON file under `registry/`.

### 2.1 Every incorporated artifact is cited by a path under `registry/`

Nine sections in seven parts incorporate an artifact, and each names it by a repository path:

| part and section | incorporated artifacts |
|---|---|
| Part 02 §1 | `registry/registry.schema.json`, `registry/registry_contract.schema.json`, `registry/registry_contracts/escapewheel-registry-contract-v0.9.json`, `registry/logical_schemas.json` |
| Part 02 §9.5 | `registry/registry_result.schema.json` |
| Part 03 §1 | `registry/physical_profile.schema.json`, `registry/physical_profiles/escapewheel-portable-v0.1.json` |
| Part 04 §1 | `registry/manifest.schema.json` |
| Part 04 §5.5 | `registry/sources.schema.json` |
| Part 05 §3.1 | `registry/recipe.schema.json` |
| Part 11 §1 | `registry/rule_language.schema.json`, `registry/rule_languages/escapewheel-rule-sql-v0.2.json` |
| Part 12 §1 | `registry/resources.schema.json` |
| Part 12 §7 | `registry/adapter.schema.json` |

Parts 01, 06, 07, 08 and 09 name no repository path. Part 02 §§1 and 9.3 cite `registry/tables.md`,
the generated informative listing. Part 10 §1 cites `conformance/`, and §5 cites
`conformance/zarr-probe/` as the source of its Zarr measurements; both lie outside any tree the
specification could be given. `resources.schema.json` is the only incorporated artifact whose text
names a repository path: its root description names `registry/build.py`, the script that derives it.
Every link between parts is relative to the specification directory, and the style guide's link
to the repository README is the only one leaving it.

### 2.2 `registry/` holds 95 tracked files, fourteen of them normative

| kind | files | incorporated |
|---|---:|---|
| incorporated artifacts | 14 | yes |
| TOML source of the core registry, assembled into `logical_schemas.json` | 49 | no |
| extension registries and their TOML source (`aind_opto`, `aind_unit_qc`, `dynamic_foraging`, `vr_foraging`) | 20 | no |
| example documents, which the checks validate against their schemas | 4 | no |
| `assemble.py`, `build.py`, `canonical.py`, `check.py`, `render.py` | 5 | no |
| `README.md`, `tables.md`, `.gitignore` | 3 | no |

No package ships the core registry or an extension document. `escapewheel-aind` registers a source
producing `aind_unit_qc` rows and no registry; its tests read `registry/extensions/aind_unit_qc.json`
from the monorepo. Apart from the checks, probes and tests that read every extension document, and
Part 08's example, which binds all four, `aind_opto`'s document is read by one writer test and
`vr_foraging`'s by two.

### 2.3 Producing and checking the candidate runs the reference implementation

The specification's generated content is produced by five writers:

| generated content | writer | depends on |
|---|---|---|
| `logical_schemas.json`, `tables.md` | `registry/assemble.py`, `registry/render.py` | the standard library |
| `resources.schema.json`; Part 03 §2's profile region; Part 04 §§3, 4.1, 8 and 9's field tables | `registry/build.py` | the standard library |
| Part 06 §4's column table | `columns.py` | the standard library |
| the combined rendering | `combine.py` | the standard library |
| Part 08 §§2–3's layout and manifest excerpt | `integration/example.py` | the reference writer, which validates on commit |

`registry/build.py` also writes thirteen vendored copies into the source trees of the reader,
validator and writer, so the specification's build knows each consumer by path.

`registry/check.py` makes 40 named checks. Six of them reach outside the specification:

- The complete-result check of Part 02 §9.4 imports the reference validator. It runs over the core
  registry and each of the four extensions.
- The physical profile's check imports the reference reader.
- The Tier 2 static and execution check imports the validator's rule checker and DuckDB.
- The table-set check runs a script under `conformance/spec-sweep/` that parses the frozen v0.1
  Part 02.
- The history-cleanup check runs a script under `conformance/history-cleanup/` against Git history.
- One check validates a document under `prototype/registry-codegen/`.

The other 34 checks need only the standard library or `jsonschema`. `headings.py`, the tool that
records each part's stable headings, imports the revision tooling's `impact.py` to list the
citers of a changed heading.

### 2.4 The conformance corpus needs the reader to build

The corpus builder, `fixtures/build.py`, writes 120 packets with PyArrow and imports one function
from the reference reader, `stored_order`. That function returns each table's primary key, except
for the one override of Part 03 §5.4, the stored order of `analysis.spike_events`. Part 03 §5.4's
table is the only statement of that override in the specification: the physical-profile
descriptor does not carry it, and the reader's `ordering.py` restates it for the writer and
validator. The corpus's expected findings sit in `fixtures/corpus.py`, beside the runner that
opens each packet with the reader and validates it with the validator.

### 2.5 The paths are cited widely, but frozen records need not follow them

173 tracked files name `registry/` or `escapewheel_poc_docs_v0.2` literally, excluding the frozen
v0.1 documents and lock files:

- 107 are accepted revisions or their evidence manifests.
- 66 are current files: revision tooling and its data (13), the writer (9), the registry directory
  (8), the specification directory (8), `conformance/` (6), the validator (5), and the root
  documents and scripts.

More scripts compute the paths than name them. These include `verify.py`, `facts.py`,
`check_citations.py`, `ledger.py`, `impact.py`, `repoint.py`, and the package test suites through
`parents[2] / "registry"`.

`revisions/registry-targets.toml` locates 109 accepted clauses in 292 registry paths, and
`ledger.py` refuses a target outside `registry/`.

The accepted records need no edit.

- `revisions/CONTRIBUTING.md#ew-citation-context` makes a committed accepted revision an immutable
  record that "need not resolve against the current working specification".
- `check_citations.py` checks no accepted record's links.
- `evidence.py` resolves only the manifest of a revision not yet committed.

Two conformance probes, `registry-contract/probe.py` and `history-cleanup/probe.py`, do depend on
the old paths. Each reads one path both at a past commit through `git show` and in the working tree.

The field test's recipes name the core registry and all four extensions by absolute path into
`registry/`. No packet records a repository path: a packet embeds the registries it binds (Part 04
§8), and every `$id` is a URL rather than a path.

### 2.6 Other formats keep the specification apart from its implementations

The following were read from each project's repository or documentation on 2026-09-30.

- **NWB.** NWB keeps its schema, its format documentation and a schema for extension documents in
  `NeurodataWithoutBorders/nwb-schema`. PyNWB pins it as a Git submodule at a release commit.
  HDMF's common schema follows the same pattern, and two consumers pin it independently.
- **Parquet.** Parquet keeps its prose and `parquet.thrift` in `apache/parquet-format`, tagged
  separately from parquet-java. parquet-java took the Thrift file from the released format artifact
  until September 2026. It then vendored a copy with a sidecar recording the source commit, because
  a released dependency blocked builds against unreleased format changes (apache/parquet-java pull
  request 3709). Arrow C++ vendors its own copy and synchronises it by hand.
- **OpenAPI and JSON Schema.** Both keep the specification in its own repository and publish
  schemas at versioned URLs. OpenAPI releases its schemas independently of the prose. JSON Schema
  keeps its conformance suite in a third repository, which its README recommends consuming as a Git
  submodule or subtree.
- **GeoParquet.** GeoParquet keeps its specification, JSON Schema, examples and test data in one
  repository, `opengeospatial/geoparquet`, and attaches the specification and schema to each
  release tag.
- **Iceberg.** Iceberg keeps its specification at `format/spec.md` inside the Java implementation's
  repository. It has no specification tags, and its specification page is unversioned. A 2024
  Apache thread on the Variant encoding wanted that specification moved out of Spark, so that
  engines would not depend on another engine's modules; it later moved into `parquet-format`.

Where an implementation vendors a copy that nothing generates or checks, the copy drifts. That
happened to Arrow C++'s Thrift file and to `openapi-spec-validator`'s schemas, which trail several
published iterations.

## 3. Desired outcome and constraints

The specification's members and everything needed to produce and check them should form one
tree that can be read, rebuilt and verified with nothing else present. A second implementer
handed the tree should receive the whole contract and nothing that is only an implementation. The
tree should also be separable into its own repository later without rewriting what it says.

The resolution should preserve:

- the existing members and their authority: Part 00 §2.1's rule that a part's express
  incorporation, and nothing else, gives an artifact normative force, and Part 00 §8's statuses;
- every artifact's `$id`, registry identity and bytes, so that no packet, digest or embedded
  registry changes;
- one owner for each fact, with the packages' copies generated and checked (Part 00 §2.3);
- the packages' rule that a released package depends only on released packages, which today rules
  out a published specification package;
- the accepted records, unedited; and
- the undecided parts of Part 00 §2.1: which files a release includes, and the format of its
  publication record.

## 4. Options and tradeoffs

For where the specification lives:

| option | effect |
|---|---|
| keep today's layout | nothing changes now; the members stay among non-normative files, the candidate is still produced by running the writer, and a release has no tree to be frozen from |
| its own repository now | the boundary becomes physical, as at NWB, Parquet, OpenAPI and JSON Schema; every change to the contract and its implementation becomes a coordinated change to two repositories while the contract still changes with most revisions, and the field test would run across both |
| one self-contained directory in this repository (preferred direction) | the boundary is enforced by checks rather than by repositories; a change stays one commit; the directory can later become its own repository with `git subtree split` and keep its history |

For how a part names an incorporated artifact:

| option | effect |
|---|---|
| a repository path, as now | a path outside the specification's tree stops resolving when the tree is separated |
| an identifier, such as the `$id` | the path disappears from the prose, but the core registry has no `$id`, and an identifier names a version rather than a file a reader can open |
| a path relative to the specification's root (preferred direction) | the citation resolves in any copy of the tree, and the part still names a file a reader can open |

For how the packages obtain the artifacts:

| option | effect |
|---|---|
| a published specification package | blocked while the specification is unreleased, since a released package depends only on released packages; and a change could not be built against before release, the reason parquet-java stopped doing this |
| a Git submodule | not needed while the specification and the packages share a repository |
| vendored copies written by each package's build and checked against the tree (preferred direction) | today's mechanism, with the direction reversed so that the specification no longer knows its consumers' paths |

Under the preferred direction the specification is one directory, `spec/`, holding every member of
the candidate and everything that produces or checks them, and nothing that imports a package:

```
spec/
  README.md, CONTRIBUTING.md   entry point and style guide
  parts/                       Parts 00–12
  artifacts/                   the fourteen incorporated artifacts, and nothing else
  source/core/                 the TOML the core registry is assembled from
  informative/                 the registry listing, the combined rendering, example documents
  conformance/                 the informative conformance corpus and its expected findings
  tools/                       assembly, rendering, heading, combining and static-check tools
```

The rest of the repository depends on `spec/`, and `spec/` depends on none of it:

- **Packages.** The reader, validator, writer and `escapewheel-aind` go under `packages/`. Each
  package's build copies the artifacts it uses from `spec/artifacts/`, and each package checks
  that its copies agree.
- **Extensions.** The four extension registries leave the specification's tree. `aind_opto` and
  `aind_unit_qc` join `escapewheel-aind`, and `dynamic_foraging` and `vr_foraging` go under
  `extensions/`. An extension is not incorporated (Part 09), so where each one sits is repository
  organisation rather than part of this decision.
- **Evidence.** The checks that need an implementation leave `spec/tools/` for `conformance/` and
  `integration/`: Part 02 §9.4's complete result, the physical profile's reader check, and Tier 2
  execution. So does each check that reads Git history or a prototype.
- **Part 08.** Part 08's example regions become committed text, and `integration/` checks that the
  reference writer reproduces them.
- **History.** The frozen v0.1 documents, the root audit documents, `inventory/` and `prototype/`
  go under `history/`.
- **Process.** `revisions/` stays the change process and is not part of the specification. The
  heading tool reports changed headings, and the revision tooling finds their citers.

Four rules state the boundary at the level of the specification:

- every file Part 00 §2.1 makes a member sits within the specification's tree;
- a part or incorporated artifact cites a file by a path relative to that tree's root, and only a
  file within it;
- every generated region and generated artifact is derived from files within the tree, by tools
  within the tree that import no implementation; and
- an informative part may point at evidence outside the tree, such as Part 10's probes, only by
  naming it and not by a path the tree's copy would have to resolve.

The conformance corpus becomes an informative member of the tree. Its builder reads Part 03
§5.4's overriding order from the physical-profile descriptor, which the proposal
`the-profile-descriptor-declares-the-overriding-orders` would make that order's machine-readable
owner (§2.4); this proposal follows that one. The corpus's expected findings become data within the
tree, while the runner, which opens packets with the reader and validates them with the validator,
stays in `conformance/`.

A release is not defined here. Part 00 §2.1 would gain only that a release's members are drawn from
the specification's tree. Which of the tree's informative files a release includes, and the
publication record's format, are left to the release decision.

The cost is one large mechanical move before the field test:

- the 66 current files that name the old paths, and the scripts that compute them, are repointed;
- `registry-targets.toml`'s 292 paths are repointed, and `ledger.py`'s containment check follows
  them;
- the two conformance probes of §2.5 take a separate path for the past commit;
- the field-test recipes change their registry and extension paths; and
- the links in accepted records stop resolving in the current tree, which the citation-context rule
  already permits.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 names no file. |
| logical prose and registry | Part 02 §§1 and 9.5 cite their artifacts under `artifacts/`, and §§1 and 9.3 cite the rendered listing under `informative/`. No declaration, identity or byte of the core registry changes. |
| physical profiles | Part 03 §1 cites its schema and descriptor under `artifacts/`. Neither artifact changes. Part 03 §2's generated region is written by a tool within the tree. |
| packet manifest and JSON Schemas | Part 04 §§1 and 5.5, Part 05 §3.1 and Part 12 §§1 and 7 cite their schemas under `artifacts/`. No schema's `$id` or member changes. `resources.schema.json`'s description stops naming a repository script, which changes its bytes but not its `$id` or shape. |
| validation and import | Unchanged. No packet obligation changes. |
| extensions | Unchanged in meaning. The four extension documents leave the specification's tree unchanged in content. Part 09 names no file. |
| reader, writer, validator, adapters | Each package's build copies the artifacts it uses from the tree, and each package checks its copies. The writer's `init` template and README name the new core registry path. No runtime behavior changes. |
| existing packets | Unchanged. No packet records a repository path. The field-test recipes change their registry and extension paths. |
| conformance fixtures and tests | The corpus becomes an informative member of the tree, and its builder reads the overriding order from the descriptor rather than importing the reader. The expected findings move out of the runner into data. The package-dependent registry checks move to `conformance/`, and Part 08's example becomes a check in `integration/`. The package suites locate the registry at its new path. |
| revision process and tooling | The paths in `check_citations.py`, `ledger.py`, `impact.py`, `repoint.py`, `evidence.py`, `registry-targets.toml` and the verifier move. The heading tool stops importing the revision tooling. Accepted records and their evidence are unedited. The revision guide's own links are repointed as ordinary maintenance. |
| generated publications and developer documentation | The combined rendering and the heading index are regenerated from the new tree. The root README, CONTRIBUTING and the package guides describe the new layout. The specification README states what the tree holds. |

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.
